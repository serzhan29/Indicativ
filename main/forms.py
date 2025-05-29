from django import forms
from .models import UploadedWork, UploadedMainWork
from django.contrib.auth import authenticate


class UploadedWorkForm(forms.ModelForm):
    class Meta:
        model = UploadedWork
        fields = ['file']


class UploadedMainWorkForm(forms.ModelForm):
    class Meta:
        model = UploadedMainWork
        fields = ['file']
