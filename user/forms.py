from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Profile, Faculty


class CustomUserCreationForm(UserCreationForm):
    faculty = forms.ModelChoiceField(queryset=Faculty.objects.all(), required=False, label="Факультет")
    role = forms.ChoiceField(choices=Profile.ROLES, label="Роль")
    phone = forms.CharField(max_length=20, required=False, label="Телефон")

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2", "faculty", "role", "phone"]
