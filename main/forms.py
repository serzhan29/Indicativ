from django import forms
from .models import UploadedWork, UploadedMainWork

class UploadedWorkForm(forms.ModelForm):
    class Meta:
        model = UploadedWork
        fields = ['file']

class UploadedMainWorkForm(forms.ModelForm):
    class Meta:
        model = UploadedMainWork
        fields = ['file']
