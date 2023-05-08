from crispy_forms.bootstrap import InlineCheckboxes
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Fieldset, Layout, Submit
from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from web.ops.compilers import SubmitFormCflags, Compilers
from web.ops.passes import Passes
from web.models import User, Task


class MultipleFileInput(forms.ClearableFileInput):
    """https://github.com/django/django/commit/eed53d0011622e70b936e203005f0e6f4ac48965#"""
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class SignUpForm(UserCreationForm):

    def __init__(self, *args, **kwargs):
        super(UserCreationForm, self).__init__(*args, **kwargs)
        for name in ('username', 'password1', 'password2'):
            self.fields[name].help_text = None


class SubmitForm(forms.Form):
    title = forms.CharField(max_length=80, label='Имя загрузки (пустое будет заменено хешем)', required=False)
    tests = forms.IntegerField(min_value=1, max_value=100, initial=10, label='Число запусков программы для усреднения времени')
    files = MultipleFileField(label='Файлы')

    compilers = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=[
        (str(i.value), i.name) for i in settings.COMPILERS
    ], label='')

    cflags = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=[
        (i.name, i.name) for i in SubmitFormCflags
    ], label='')

    passes = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple, choices=[
        (str(i.value), i.desc) for i in settings.OPS_PASSES
    ], label='')

    def __init__(self, u: User, *args, **kwargs):
        super().__init__(*args, **kwargs)
        task = Task.objects.filter(user=u).last()
        if task:
            self.fields['compilers'].initial = [str(i) for i in task.compilers]
            self.fields['cflags'].initial = task.cflags
            self.fields['passes'].initial = [str(Passes(i).value) for i in task.passes]
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'title',
            'tests',
            'files',
            Fieldset(
                'Компиляторы',
                InlineCheckboxes(
                    'compilers'
                ),
            ),
            Fieldset(
                'Уровни оптимизации',
                InlineCheckboxes(
                    'cflags'
                ),
            ),
            Fieldset(
                'Проходы',
                InlineCheckboxes(
                    'passes'
                ),
            ),
            Submit('submit', 'Отправить', css_class='btn btn-dark btn-lg mt-3'),
        )


class SignatureChoiceForm(forms.Form):
    def __init__(self, choices, *args, **kw) -> None:
        super().__init__(*args, **kw)
        self.fields['choice'] = forms.CharField(label='', widget=forms.Select(choices=choices), required=True)
