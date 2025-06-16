from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile, Faculty
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


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
                raise forms.ValidationError(_("Invalid username/email or password"))
        return self.cleaned_data

    def get_user(self):
        return self.user


class ProfileUpdateForm(forms.ModelForm):
    first_name = forms.CharField(
        label="Аты",
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        label="Тегі",
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Profile
        fields = ['phone', 'father_name', 'photo']
        widgets = {
            'faculty': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'father_name': forms.TextInput(attrs={'class': 'form-control'}),
            'photo': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        instance = kwargs.get('instance')
        initial = kwargs.get('initial', {}).copy()

        if instance:
            self.user = instance.user

        if self.user:
            initial['first_name'] = self.user.first_name
            initial['last_name'] = self.user.last_name
            initial['email'] = self.user.email

        kwargs['initial'] = initial
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and not email.endswith('@ayu.edu.kz'):
            raise ValidationError("Email должен оканчиваться на @ayu.edu.kz")
        return email

    def save(self, commit=True):
        profile = super().save(commit=False)

        if self.user:
            self.user.first_name = self.cleaned_data.get('first_name')
            self.user.last_name = self.cleaned_data.get('last_name')
            self.user.email = self.cleaned_data.get('email')
            if commit:
                self.user.save()
                profile.user = self.user
                profile.save()
                self.save_m2m()
        elif commit:
            profile.save()
            self.save_m2m()

        return profile
