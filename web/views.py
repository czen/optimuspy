from hashlib import md5
from pathlib import Path

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic.edit import FormView
from web.tasks import compiler_job

from .forms import SignUpForm, SubmitForm, SignatureChoiceForm
from .models import Task
from .ops.build_tools.ctags import Ctags, MainFoundException

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

    def form_valid(self, form) -> HttpResponse:
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
        'tasks': Task.objects.filter(user=request.user).reverse(),
        'msg': msg
    }
    return render(request, 'web/list.html', context=context)


@login_required
def tasks_submit(request: HttpRequest):
    if request.method == 'POST':
        form = SubmitForm(request.POST, request.FILES)
        if form.is_valid():
            task = handle_upload(request)

            if task is None:
                request.session['msg'] = 'Отправка отменена из-за несоотвествием требованиям'
                return redirect('list')

            if task.f_name == '':
                return redirect('signature', tid=task.id)
            else:
                request.session['msg'] = 'Отправлено'
                compiler_job.delay(task.id)
            return redirect('list')
    else:
        form = SubmitForm()
    return render(request, 'web/submit.html', {'form': form})


@login_required
def tasks_signature(request: HttpRequest, tid: int):
    task = Task.objects.get(id=tid)
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
    task = Task.objects.get(id=tid)
    if task.user != request.user:
        return redirect('list')

    return redirect('index')
