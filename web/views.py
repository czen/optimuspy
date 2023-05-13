import csv
from hashlib import md5
from io import StringIO
from math import pi
from pathlib import Path

from bokeh.embed import components
from bokeh.models import ColumnDataSource, HoverTool
from bokeh.plotting import figure
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic.edit import FormView
from rest_framework import viewsets
from rest_framework import permissions
from rest_framework.response import Response
from web.forms import SignatureChoiceForm, SignUpForm, SubmitForm
from web.models import Benchmark, CompError, Result, Task
from web.ops.build_tools.ctags import Ctags, MainFoundException
from web.ops.compilers import Compiler, Compilers, GenericCflags
from web.ops.passes import Passes
from web.tasks import compiler_job
from web.serializers import UserSerializer, TaskSerializer, ResultSerializer, BenchmarkSerializer, CompilerErrorSerializer



# Create your views here.


def index(request: HttpRequest):
    return render(request, 'web/index.html')


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
                return redirect('signature', tid=task.id)
            else:
                request.session['msg'] = 'Отправлено'
                compiler_job.delay(task.id)
            return redirect('list')
    else:
        form = SubmitForm(request.user)
    return render(request, 'web/submit.html', {'form': form})


@login_required
def tasks_signature(request: HttpRequest, tid: int):
    try:
        task = Task.objects.get(id=tid)
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
    hasher = md5()
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
def tasks_result(request: HttpRequest, tid: int):
    try:
        task = Task.objects.get(id=tid)
    except Task.DoesNotExist:
        return redirect('list')

    if task.f_name == '':
        return redirect('signature', tid=task.id)

    if task.user != request.user:
        return redirect('list')

    if task.ready:
        q1 = list(Benchmark.objects.filter(task=task))
        q2 = list(Result.objects.filter(task=task))

        _x ,_y, _time = [], [], []
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
            _time.append(b.value)
            _unit.append(b.unit)
            _col.append('blue' if not b.error else 'red')
            _e = CompError.objects.filter(bench=b).first()
            _err.append(_e.text if _e else str(_e))

        data = ColumnDataSource(data={
            'x': _x,
            'y': _y,
            'time': _time,
            'unit': _unit,
            'cflags': _cflags,
            'comps': _comps,
            'pass': _pass,
            'color': _col,
            'err': _err
        })

        hover = HoverTool(
            tooltips=[
                ('time', '@time @unit'),
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
            'tid': task.id
        }
        return render(request, 'web/result_ready.html', context=context)
    else:
        context = {
            'tid': task.id,
            'timeout': 10000
        }
        return render(request, 'web/result_wait.html', context=context)


def tasks_ready(_: HttpRequest, tid: int):
    try:
        task = Task.objects.get(id=tid)
        return JsonResponse({'ready': task.ready})
    except Task.DoesNotExist:
        return JsonResponse({'ready': False})


@login_required
def tasks_stats(request: HttpRequest, tid: int):
    try:
        task = Task.objects.get(id=tid)
    except Task.DoesNotExist:
        return redirect('list')

    if task.f_name == '':
        return redirect('signature', tid=task.id)

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

class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

class TaskViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows tasks to be viewed or edited.
    """
    queryset = Task.objects.all().order_by('-date')
    serializer_class = TaskSerializer
    permission_classes = [permissions.IsAuthenticated]

class ResultViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows task results to be viewed.
    """
    queryset = Result.objects.all().order_by('-id')
    serializer_class = ResultSerializer
    permission_classes = [permissions.IsAuthenticated]

class BenchmarkViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows benchmark results to be viewed.
    """
    queryset = Benchmark.objects.all().order_by('-id')
    serializer_class = BenchmarkSerializer
    permission_classes = [permissions.IsAuthenticated]

class CompilerErrorViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows compiler errors to be viewed.
    """
    queryset = CompError.objects.all().order_by('-id')
    serializer_class = CompilerErrorSerializer
    permission_classes = [permissions.IsAuthenticated]
