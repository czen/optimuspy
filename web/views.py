import base64 as b64
import csv
import json
from hashlib import md5
from io import StringIO, BytesIO
from math import pi
from pathlib import Path
import binascii
import tarfile

from bokeh.embed import components
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.plotting import figure
from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from django.views.generic.edit import FormView

from web.forms import SignatureChoiceForm, SignUpForm, SubmitForm
from web.models import API, Benchmark, CompError, Result, Task, User
from web.ops.build_tools.ctags import Ctags, MainFoundException
from web.ops.compilers import (Compiler, Compilers, GenericCflags,
                               SubmitFormCflags)
from web.ops.passes import Passes
from web.tasks import compiler_job

# Create your views here.


def index(request: HttpRequest):

    return render(request, 'web/index.html')


@login_required
def profile(request: HttpRequest):
    context = {
        'username': request.user.username,
        'token': request.user.api.key,
        'date_joined': request.user.date_joined,
        'last_login': request.user.last_login,
        'email': request.user.email
    }
    return render(request, 'web/profile.html', context=context)


@login_required
def ulogout(request: HttpRequest):
    logout(request)
    return redirect('index')


class LogIn(LoginView):
    template_name = 'web/login.html'
    fields = '__all__'
    redirect_authenticated_user = True

    def get_success_url(self) -> str:
        return reverse_lazy('list')

    def form_invalid(self, form) -> HttpResponse:
        response = super().form_invalid(form)
        error_msg = 'Invalid username or password'
        self.request.session['error_msg'] = error_msg
        return response


class SignUp(FormView):
    template_name = 'web/signup.html'
    form_class = SignUpForm
    redirect_authenticated_user = True
    success_url = reverse_lazy('list')

    def form_valid(self, form: SignUpForm) -> HttpResponse:
        user = form.save()

        if user is not None:
            login(self.request, user)

        return super(SignUp, self).form_valid(form)

    def get(self, request, *args, **kwargs) -> HttpResponse:
        if self.request.user.is_authenticated:
            return redirect('list')

        return super(SignUp, self).get(request, *args, **kwargs)


@login_required
def tasks_list(request: HttpRequest):
    msg = request.session.pop('msg', '')
    context = {
        'username': request.user.username,
        'tasks': Task.objects.filter(user=request.user).order_by('-date'),
        'msg': msg
    }
    return render(request, 'web/list.html', context=context)


@login_required
def tasks_submit(request: HttpRequest):
    if request.method == 'POST':
        form = SubmitForm(request.user, request.POST, request.FILES)
        if form.is_valid():
            task = handle_upload(request)

            if task is None:
                request.session['msg'] = 'Отправка отменена из-за несоотвествием требованиям'
                return redirect('list')

            task.compilers = form.cleaned_data['compilers']
            task.cflags = form.cleaned_data['cflags']
            task.passes = form.cleaned_data['passes']
            task.save()

            if task.f_name == '':
                return redirect('signature', th=task.hash)
            else:
                request.session['msg'] = 'Отправлено'
                compiler_job.delay(task.id)
            return redirect('list')
    else:
        form = SubmitForm(request.user)
    return render(request, 'web/submit.html', {'form': form})


@login_required
def tasks_signature(request: HttpRequest, th: str):
    try:
        task = Task.objects.get(hash=th)
    except Task.DoesNotExist:
        return redirect('submit')

    if task.user != request.user:
        return redirect('list')

    ct = Ctags(task.path)
    choices = [(i, l.sign) for i, l in enumerate(ct.signatures)]

    if request.method == 'POST':
        if request.POST.get('btn') == 'cancel':
            task.rmdir()
            task.delete()
            request.session['msg'] = 'Отправка отменена пользователем'
            return redirect('list')

        form = SignatureChoiceForm(choices, request.POST)
        if form.is_valid():
            i = int(request.POST.get('choice'))
            task.f_name = ct.signatures[i].name
            task.f_sign = ct.signatures[i].sign
            task.save()
            compiler_job.delay(task.id)
            request.session['msg'] = 'Отправлено'
            return redirect('list')
    else:
        form = SignatureChoiceForm(choices)

    return render(request, 'web/signature.html', {'form': form})


def md5sum(path: Path, chunk_size: int = 4096) -> str:
    hasher = md5(str(path).encode('utf-8'))
    for file in path.iterdir():
        with open(file, 'rb') as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
    return hasher.hexdigest()


def handle_upload(request: HttpRequest) -> Task | None:
    task = Task(user=request.user, tests=request.POST['tests'])
    task.save()
    task.mkdir()
    for file in request.FILES.getlist('files'):
        with open(task.path / file.name, 'wb+') as f:
            for chunk in file.chunks():
                f.write(chunk)
    task.hash = md5sum(task.path)
    task.name = request.POST['title'] or task.hash

    try:
        ct = Ctags(task.path)
    except MainFoundException:
        task.rmdir()
        task.delete()
        return None

    if len(ct.signatures) == 0:
        task.rmdir()
        task.delete()
        return None

    if r := ct.resolve_signature():
        task.f_sign = r.sign
        task.f_name = r.name
    task.save()
    return task


@login_required
def tasks_result(request: HttpRequest, th: str):
    try:
        task = Task.objects.get(hash=th)
    except Task.DoesNotExist:
        return redirect('list')

    if task.f_name == '':
        return redirect('signature', th=task.hash)

    if task.user != request.user:
        return redirect('list')

    if task.ready:
        q1 = list(Benchmark.objects.filter(task=task))
        q2 = list(Result.objects.filter(task=task))

        _x, _y, _value = [], [], []
        _unit, _cflags = [], []
        _comps, _pass = [], []
        _col, _err = [], []
        for b in q1:
            comp: Compiler = Compilers(b.compiler).obj
            cflags: GenericCflags = comp.cflags[b.cflags]
            pas = Passes(b.pas)
            _cflags.append(cflags.value)
            _comps.append(comp.name)
            _pass.append(pas.name)
            _x.append(f'{comp.short} {cflags} {pas.short}')
            _y.append(b.value)
            _value.append(b.value)
            _unit.append(b.unit)
            _col.append('blue' if not b.error else 'red')
            _e = CompError.objects.filter(bench=b).first()
            _err.append(_e.text if _e else str(_e))

        data = ColumnDataSource(data={
            'x': _x,
            'y': _y,
            'value': _value,
            'unit': _unit,
            'comps': _comps,
            'cflags': _cflags,
            'pass': _pass,
            'color': _col,
            'err': _err
        })

        hover = HoverTool(
            tooltips=[
                ('time', '@value @unit'),
                ('compiler', '@comps'),
                ('cflags', '@cflags'),
                ('ops', '@pass'),
                ('error', '@err')
            ]
        )

        plot = figure(title=task.name, x_range=data.data['x'], sizing_mode='stretch_width')
        plot.vbar(x='x', top='y', color='color', width=0.5, source=data)
        plot.xaxis.axis_label = 'Проход/компилятор'
        plot.yaxis.axis_label = 'Время работы программы'
        plot.xaxis.major_label_orientation = pi/4
        plot.add_tools(hover)

        script, div = components(plot)

        context = {
            'username': request.user.username,
            'script': script, 'div': div,
            'downloads': q2,
            'th': task.hash
        }
        return render(request, 'web/result_ready.html', context=context)
    else:
        context = {
            'th': task.hash,
            'timeout': 10000
        }
        return render(request, 'web/result_wait.html', context=context)


def tasks_ready(_: HttpRequest, th: str):
    try:
        task = Task.objects.get(hash=th)
        return JsonResponse({'ready': task.ready})
    except Task.DoesNotExist:
        return JsonResponse({'ready': False})


@login_required
def tasks_stats(request: HttpRequest, th: str):
    try:
        task = Task.objects.get(hash=th)
    except Task.DoesNotExist:
        return redirect('list')

    if task.f_name == '':
        return redirect('signature', th=task.hash)

    if task.user != request.user:
        return redirect('list')

    if task.ready:
        q = list(Benchmark.objects.filter(task=task))

        data = StringIO()
        w = csv.writer(data, delimiter=';', quoting=csv.QUOTE_NONNUMERIC)
        w.writerow(['Проход', 'Компилятор', 'Уровень оптимизации', 'Время',
                    'Единица измерения', 'Флаги компилятора', 'Флаги OPS', 'Вывод компилятора'])
        for b in q:
            comp: Compiler = Compilers(b.compiler).obj
            cflags: GenericCflags = comp.cflags[b.cflags]
            pas = Passes(b.pas)
            err = CompError.objects.filter(bench=b).first()
            row = [
                pas.name, comp.name, cflags.name, b.value,
                b.unit, cflags.value, ' '.join(pas.obj.args),
                err.text if err else ''
            ]
            w.writerow(row)

        response = HttpResponse(data.getvalue(), content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename={task.hash}.csv'
        return response


@login_required
def result_download(request: HttpRequest, rid: int):
    try:
        b = Result.objects.get(id=rid)
    except Result.DoesNotExist:
        return redirect('list')

    if b.task.user != request.user:
        return redirect('list')

    data = None

    with open(b.path, 'rb') as f:
        data = f.read()

    response = HttpResponse(data, content_type='application/tar+gzip')
    response['Content-Length'] = b.path.stat().st_size
    response['Content-Disposition'] = f'attachment; filename={b.path.name}'
    return response


@csrf_exempt
def api_auth(request: HttpRequest):
    resp = {
        'error': True,
        'status': 'success',
        'token': ''
    }
    req: dict = json.loads(request.body)
    uname, pwd = req.get('username'), req.get('password')
    if uname and pwd:
        try:
            user = User.objects.get(username=uname)
        except User.DoesNotExist:
            resp['status'] = 'user does not exist'
        else:
            if user.check_password(pwd):
                resp['error'] = False
                resp['token'] = user.api.key
            else:
                resp['status'] = 'invalid password'
    else:
        resp['status'] = 'invalid parameters'

    return JsonResponse(resp)


@csrf_exempt
def api_compilers(request: HttpRequest):
    resp = {
        'error': False,
        'status': 'success',
        'compilers': [c.name for c in settings.COMPILERS]
    }
    return JsonResponse(resp)


@csrf_exempt
def api_passes(request: HttpRequest):
    resp = {
        'error': False,
        'status': 'success',
        'passes': [p.name for p in settings.OPS_PASSES]
    }
    return JsonResponse(resp)


@csrf_exempt
def api_tasks(request: HttpRequest):
    resp = {
        'error': True,
        'status': 'success',
        'tasks': []
    }
    req: dict = json.loads(request.body)
    token = req.get('token')

    user: User = None
    try:
        user = API.objects.get(key=token).user
    except API.DoesNotExist:
        resp['status'] = 'invalid token'
        return JsonResponse(resp)

    resp['tasks'] = [t.hash for t in Task.objects.filter(user=user).order_by('-date')]
    resp['status'] = 'success'
    resp['error'] = False
    return JsonResponse(resp)


@csrf_exempt
def api_submit(request: HttpRequest):
    resp = {
        'error': True,
        'status': 'success',
        'task': ''
    }
    req: dict = json.loads(request.body)
    token = req.get('token')
    comps = req.get('compilers')
    passes = req.get('passes')
    cflags = req.get('cflags')
    files = req.get('files')
    tests = req.get('tests')

    # validate parameters presence
    if any(i is None for i in (token, comps, passes, cflags, files, tests)):
        resp['status'] = 'invalid parameters'
        return JsonResponse(resp)

    user: User = None
    try:
        user = API.objects.get(key=token).user
    except API.DoesNotExist:
        resp['status'] = 'invalid token'
        return JsonResponse(resp)

    # ensure that compilers list is not empty
    if comps == []:
        resp['status'] = 'compilers list is empty'
        return JsonResponse(resp)

    # ensure that passes list is not empty
    if passes == []:
        resp['status'] = 'passes list is empty'
        return JsonResponse(resp)

    # ensure that cflags list is not empty
    if cflags == []:
        resp['status'] = 'cflags list is empty'
        return JsonResponse(resp)

    try:  # validate compilers
        _t = []
        for i in comps:
            c = Compilers[i]
            if c in settings.COMPILERS:
                _t.append(c.value)
            else:
                resp['status'] = f'compiler {c.name} is disabled'
                return JsonResponse(resp)
        comps = _t
    except KeyError as e:
        resp['status'] = f"invalid compiler '{e.args[0]}'"
        return JsonResponse(resp)

    try:  # validate passes
        _t = []
        for i in passes:
            p = Passes[i]
            if p in settings.OPS_PASSES:
                _t.append(p.value)
            else:
                resp['status'] = f'pass {p.name} is disabled'
                return JsonResponse(resp)
        passes = _t
    except KeyError as e:
        resp['status'] = f"invalid pass '{e.args[0]}'"
        return JsonResponse(resp)

    try:  # validate cflags
        cflags = [SubmitFormCflags[i].name for i in cflags]
    except KeyError as e:
        resp['status'] = f"invalid cflags '{e.args[0]}'"
        return JsonResponse(resp)

    try:  # ensure that files is a base6-encoded string
        files = BytesIO(b64.b64decode(files, validate=True))
    except binascii.Error:
        resp['status'] = 'files are not properly encoded'
        return JsonResponse(resp)

    # validate tests
    if isinstance(tests, int):
        if not 0 < tests <= 100:
            resp['status'] = 'invalid number of tests'
            return JsonResponse(resp)
    else:
        resp['status'] = 'number of tests must be int'
        return JsonResponse(resp)

    task = Task(user=user, tests=tests)
    task.save()
    task.mkdir()

    try:  # extract all files to task dir
        with tarfile.open(fileobj=files, mode='r:*') as tar:
            tar.extractall(task.path)
    except tarfile.TarError:
        resp['status'] = 'files are not properly archived'
        task.rmdir()
        task.delete()
        return JsonResponse(resp)

    # resolve target function signature and name
    try:
        ct = Ctags(task.path)
    except MainFoundException:
        task.rmdir()
        task.delete()
        resp['status'] = 'files must not contain main function declaration'
        return JsonResponse(resp)

    # if no signatures detected
    if len(ct.signatures) == 0:
        task.rmdir()
        task.delete()
        resp['status'] = 'could not find any function signatures in files'
        return JsonResponse(resp)

    # if an only signature is detected
    if r := ct.resolve_signature():
        task.f_sign = r.sign
        task.f_name = r.name
    else:  # if we can't auto resolve target function
        task.rmdir()
        task.delete()
        resp['status'] = 'could not resolve target function signature'
        return JsonResponse(resp)

    task.hash = md5sum(task.path)
    task.name = task.hash
    task.compilers = comps
    task.passes = passes
    task.cflags = cflags
    task.save()

    resp['error'] = False
    resp['task'] = task.hash
    compiler_job.delay(task.id)
    return JsonResponse(resp)


@csrf_exempt
def api_result(request: HttpRequest):
    resp = {
        'error': True,
        'status': 'success',
        'benchmarks': []
    }

    req: dict = json.loads(request.body)
    token = req.get('token')
    task = req.get('task')
    if token is None or task is None:
        resp['status'] = 'invalid parameters'
        return JsonResponse(resp)

    user: User = None
    try:
        user = API.objects.get(key=token).user
    except API.DoesNotExist:
        resp['status'] = 'invalid token'
        return JsonResponse(resp)

    try:
        task = Task.objects.get(user=user, hash=task)
    except Task.DoesNotExist:
        resp['status'] = 'no such task'
        return JsonResponse(resp)

    if not task.ready:
        resp['status'] = 'task is not ready yet'
        return JsonResponse(resp)

    resp['benchmarks'] = []  # this is for a linter to see
    for b in Benchmark.objects.filter(task=task):
        comp = Compilers(b.compiler)
        pas = Passes(b.pas)
        resp['benchmarks'].append(
            {
                'value': b.value,
                'unit': b.unit,
                'compiler': comp.name,
                'cflags': comp.obj.cflags[b.cflags].name,
                'pas': pas.name,
                'error': b.error,
            }
        )
    resp['error'] = False
    return JsonResponse(resp)


@csrf_exempt
def api_download(request: HttpRequest):
    resp = {
        'error': True,
        'status': 'success',
        'file': ''
    }
    req: dict = json.loads(request.body)
    token = req.get('token')
    task = req.get('task')
    pas = req.get('pas')

    if any(i is None for i in (token, task, pas)):
        resp['status'] = 'invalid parameters'
        return JsonResponse(resp)

    user: User = None
    try:
        user = API.objects.get(key=token).user
    except API.DoesNotExist:
        resp['status'] = 'invalid token'
        return JsonResponse(resp)

    try:
        pas = Passes[pas]
    except KeyError as e:
        resp['status'] = f"invalid pass '{e.args[0]}'"
        return JsonResponse(resp)

    try:
        task = Task.objects.get(user=user, hash=task)
    except Task.DoesNotExist:
        resp['status'] = 'no such task'
        return JsonResponse(resp)

    if not task.ready:
        resp['status'] = 'task is not ready yet'
        return JsonResponse(resp)

    if pas.value not in task.passes:
        resp['status'] = 'task has no result for this pass'
        return JsonResponse(resp)

    try:
        result = Result.objects.get(task=task, num=pas.value)
    except Result.DoesNotExist:
        resp['status'] = 'unknown error occured'
        return JsonResponse(resp)

    data = BytesIO()
    with open(result.path, 'rb') as f:
        while chunk := f.read(4096):
            data.write(chunk)
    resp['error'] = False
    resp['file'] = b64.b64encode(data.getbuffer()).decode('utf-8')
    return JsonResponse(resp)
