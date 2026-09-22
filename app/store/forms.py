import re

from django import forms
from django.contrib.auth.models import User
from django.core.validators import EmailValidator

from .models import UsuarioCliente


class RegisterForm(forms.Form):
    first_name = forms.CharField(
        max_length=150,
        label='Nombre',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tu nombre'})
    )
    last_name = forms.CharField(
        max_length=150,
        label='Apellido',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tu apellido'})
    )
    email = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'})
    )
    run = forms.CharField(
        max_length=12,
        label='RUN',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '12.345.678-9'})
    )
    shipping_address = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control', 'placeholder': 'Dirección de envío'}),
        label='Dirección de envío'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '********'}),
        label='Contraseña'
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirmar contraseña'}),
        label='Confirmar contraseña'
    )

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        EmailValidator()(email)
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Este correo ya está registrado.')
        return email

    def clean_run(self):
        run = self.cleaned_data['run'].strip()
        pattern = r'^(\d{1,2}\.?\d{3}\.?\d{3}-[\dkK]|\d{7,8}-[\dkK])$'
        if not re.fullmatch(pattern, run):
            raise forms.ValidationError('El RUN debe tener un formato válido, por ejemplo: 12.345.678-9.')
        return run

    def clean_password(self):
        password = self.cleaned_data['password']
        if len(password) < 6:
            raise forms.ValidationError('La contraseña debe tener al menos 6 caracteres.')
        if not re.search(r'[A-Z]', password):
            raise forms.ValidationError('La contraseña debe tener al menos una letra mayúscula.')
        if not re.search(r'[a-z]', password):
            raise forms.ValidationError('La contraseña debe tener al menos una letra minúscula.')
        if not re.search(r'\d', password):
            raise forms.ValidationError('La contraseña debe tener al menos un número.')
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError('Las contraseñas no coinciden.')

        return cleaned_data

    def save(self):
        email = self.cleaned_data['email']
        user = User.objects.create_user(
            username=email,
            email=email,
            password=self.cleaned_data['password'],
            first_name=self.cleaned_data['first_name'],
            last_name=self.cleaned_data['last_name'],
        )
        UsuarioCliente.objects.create(
            nombre=self.cleaned_data['first_name'],
            apellido=self.cleaned_data['last_name'],
            run=self.cleaned_data['run'],
            correo=email,
            telefono='',
            direccion=self.cleaned_data['shipping_address'],
            password=self.cleaned_data['password'],
        )
        return user


class LoginForm(forms.Form):
    email = forms.EmailField(
        label='Correo electrónico',
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@ejemplo.com'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '********'}),
        label='Contraseña'
    )

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        password = cleaned_data.get('password')

        if email and password:
            user = User.objects.filter(email__iexact=email).first()
            if user is None or not user.check_password(password):
                raise forms.ValidationError('Correo o contraseña incorrectos.')

        return cleaned_data
