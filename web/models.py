from functools import cached_property
from pathlib import Path
from shutil import rmtree

from django.conf import settings
# pylint: disable=imported-auth-user
from django.contrib.auth.models import User
from django.db import models

from .ops.passes import Passes

# Create your models here.


class Task(models.Model):
    id: int
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=80)
    hash = models.CharField(max_length=32)
    f_name = models.CharField(max_length=40)
    f_sign = models.CharField(max_length=80)
    path = models.FilePathField()
    date = models.DateTimeField(auto_now_add=True)
    tests = models.PositiveSmallIntegerField()
    ready = models.BooleanField(default=False)

    def mkdir(self) -> None:
        self.path = settings.TASKS_PATH / str(self.id)
        self.path.mkdir()

    def rmdir(self) -> None:
        rmtree(self.path)

    def date_name(self) -> str:
        return self.date.strftime(r'%d %b %Y %H:%M:%S') + ': ' + self.name


class Benchmark(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    num = models.PositiveIntegerField(null=True)
    value = models.FloatField(null=True)
    unit = models.CharField(max_length=4)
    error = models.BooleanField(default=False)

    @cached_property
    def path(self):
        return Path(self.task.path) / f'{self.num}/{self.task.hash}.{Passes(self.num)}.tar.gz'

    @cached_property
    def text(self):
        return Passes(self.num).to_str()
