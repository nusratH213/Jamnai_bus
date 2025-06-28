from django.contrib.auth.forms import AuthenticationForm
from django import forms

class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(label='Your Username', max_length=100)
    password = forms.CharField(label='Your Password', widget=forms.PasswordInput)