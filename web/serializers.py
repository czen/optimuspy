from django.contrib.auth.models import User
from rest_framework import serializers
from web.models import Task, Result, Benchmark, CompError


class UserSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = User
        fields = ['url', 'username', 'email']

class TaskSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Task
        fields = ['user', 'name', 'f_name', 'f_sign', 'date', 'tests', 'ready']

class ResultSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Result
        fields = ['task', 'num', 'error']

class BenchmarkSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Benchmark
        fields = ['task', 'pas', 'value', 'unit', 'error', 'compiler', 'cflags']

class CompilerErrorSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = CompError
        fields = ['bench', 'text']


