from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile, Faculty
from django.contrib.auth import authenticate


class CustomUserCreationForm(UserCreationForm):
    faculty = forms.ModelChoiceField(queryset=Faculty.objects.all(), required=False, label="Факультет")
    role = forms.ChoiceField(choices=Profile.ROLES, label="Роль")
    phone = forms.CharField(max_length=20, required=False, label="Телефон")

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2", "faculty", "role", "phone"]


class LoginForm(forms.Form):
    login = forms.CharField(label="Логин или Email")
    password = forms.CharField(widget=forms.PasswordInput, label="Пароль")

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user = None
        super().__init__(*args, **kwargs)

    def clean(self):
        login = self.cleaned_data.get('login')
        password = self.cleaned_data.get('password')
        if login and password:
            self.user = authenticate(self.request, username=login, password=password)
            if self.user is None:
                raise forms.ValidationError("Неверный логин/email или пароль")
        return self.cleaned_data

    def get_user(self):
        return self.user