from hashlib import md5
from pathlib import Path

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic.edit import FormView

from optimuspy import celery_app

from .forms import SignUpForm, SubmitForm
from .models import Task

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
def ulist(request: HttpRequest):
    context = {
        'username': request.user.username
    }
    return render(request, 'web/list.html', context=context)


@login_required
def submit(request: HttpRequest):
    if request.method == 'POST':
        if request.FILES:
            handle_upload(request)
        return ulist(request)
    else:
        form = SubmitForm()
        return render(request, 'web/submit.html', {'form': form})


def md5sum(path: Path, chunk_size: int = 4096) -> str:
    hasher = md5()
    for file in path.iterdir():
        with open(file, 'rb') as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
    return hasher.hexdigest()

@celery_app.task
def handle_upload(request: HttpRequest) -> None:
    task = Task(user=request.user, tests=request.POST['tests'])
    task.save()
    task.mkdir()
    for file in request.FILES.getlist('files'):
        with open(task.path / file.name, 'wb+') as f:
            for chunk in file.chunks():
                f.write(chunk)
    task.name = request.POST['title'] or md5sum(task.path)
    task.save()
    # TODO: process files