# Generated by Django 4.2 on 2023-05-08 08:08

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Benchmark',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pas', models.PositiveSmallIntegerField(null=True)),
                ('value', models.FloatField(null=True)),
                ('unit', models.CharField(max_length=4)),
                ('error', models.BooleanField(default=False)),
                ('compiler', models.PositiveSmallIntegerField(null=True)),
                ('cflags', models.CharField(max_length=4)),
            ],
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=80)),
                ('hash', models.CharField(max_length=32)),
                ('f_name', models.CharField(max_length=40)),
                ('f_sign', models.CharField(max_length=80)),
                ('path', models.FilePathField()),
                ('date', models.DateTimeField(auto_now_add=True)),
                ('tests', models.PositiveSmallIntegerField()),
                ('ready', models.BooleanField(default=False)),
                ('_compilers', models.CharField(max_length=32)),
                ('_cflags', models.CharField(max_length=32)),
                ('_passes', models.CharField(max_length=32)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Result',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('num', models.PositiveIntegerField(null=True)),
                ('error', models.BooleanField(default=False)),
                ('task', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='web.task')),
            ],
        ),
        migrations.CreateModel(
            name='CompError',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.TextField(null=True)),
                ('bench', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='web.benchmark')),
            ],
        ),
        migrations.AddField(
            model_name='benchmark',
            name='task',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='web.task'),
        ),
        migrations.CreateModel(
            name='API',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(max_length=32)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
