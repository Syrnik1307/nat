from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser


class RegistrationForm(UserCreationForm):
    """Форма регистрации с расширенными полями"""
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'example@email.com'
        })
    )
    
    phone_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+7 (999) 123-45-67'
        })
    )
    
    agreed_to_marketing = forms.BooleanField(
        required=False,
        label='Я согласен получать новости и специальные предложения'
    )
    
    class Meta:
        model = CustomUser
        fields = ['email', 'phone_number', 'password1', 'password2', 'role', 'agreed_to_marketing']


class LoginForm(forms.Form):
    """Форма входа (email или телефон)"""
    
    identifier = forms.CharField(
        label='Email или телефон',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email или номер телефона'
        })
    )
    
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите пароль'
        })
    )
