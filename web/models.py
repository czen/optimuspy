from shutil import rmtree

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models


# Create your models here.
class Task(models.Model):
    id: int
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=80)
    path = models.FilePathField()
    date = models.DateTimeField(auto_now_add=True)
    tests = models.PositiveSmallIntegerField()
    ready = models.BooleanField(default=False)

    def mkdir(self) -> None:
        self.path = settings.TASKS_PATH / str(self.id)
        self.path.mkdir()

    def rmdir(self) -> None:
        rmtree(self.path)


class Benchmark(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    value = models.PositiveIntegerField()
    unit = models.CharField(max_length=4)