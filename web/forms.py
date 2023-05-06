from django import forms
from django.contrib.auth.forms import UserCreationForm


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
    tests = forms.IntegerField(min_value=1, max_value=100, initial=10, label='Количество тестовых проходов')
    files = MultipleFileField(label='Файлы')


class SignatureChoiceForm(forms.Form):
    def __init__(self, choices, *args, **kw) -> None:
        super().__init__(*args, **kw)
        self.fields['choice'] = forms.CharField(label='', widget=forms.Select(choices=choices), required=True)
