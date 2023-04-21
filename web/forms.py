from django import forms
from django.contrib.auth.forms import UserCreationForm


class SignUpForm(UserCreationForm):
    # class Meta(UserCreationForm.Meta):
    #     labels = {
    #         'username': 'Пользователь',
    #         'password1': 'Пароль',
    #         'password2': 'Повторите пароль',
    #     }

    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    #     for k, v in self.Meta.labels.items():
    #         self[k].label = v

    def __init__(self, *args, **kwargs):
        super(UserCreationForm, self).__init__(*args, **kwargs)
        for name in ('username', 'password1', 'password2'):
            self.fields[name].help_text = None


class SubmitForm(forms.Form):
    title = forms.CharField(max_length=80, label='Имя загрузки (пустое будет заменено хешем)', required=False)
    tests = forms.IntegerField(min_value=1, max_value=10, initial=2, label='Количество тестовых проходов')
    files = forms.FileField(widget=forms.ClearableFileInput(attrs={'multiple': True}), label='Файлы')
