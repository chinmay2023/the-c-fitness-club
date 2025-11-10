#mainapp/forms.py
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django import forms
from .models import ContactInquiry, Member


class RegistrationForm(UserCreationForm):
    full_name = forms.CharField(
        max_length=100,
        required=True,
        label="Full Name",
        widget=forms.TextInput(attrs={
            'class': 'w-full bg-gray-600 bg-opacity-20 focus:bg-transparent focus:ring-2 '
                     'focus:ring-indigo-900 rounded border border-gray-600 focus:border-indigo-500 '
                     'text-base outline-none text-gray-100 py-1 px-3 leading-8 transition-colors '
                     'duration-200 ease-in-out mb-4',
            'placeholder': 'Your full name'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'w-full bg-gray-600 bg-opacity-20 focus:bg-transparent focus:ring-2 '
                     'focus:ring-indigo-900 rounded border border-gray-600 focus:border-indigo-500 '
                     'text-base outline-none text-gray-100 py-1 px-3 leading-8 transition-colors '
                     'duration-200 ease-in-out mb-4',
            'placeholder': 'you@example.com'
        })
    )
    username = forms.CharField(
        max_length=150,
        required=True,
        label="Username",
        widget=forms.TextInput(attrs={
            'class': 'w-full bg-gray-600 bg-opacity-20 focus:bg-transparent focus:ring-2 '
                     'focus:ring-indigo-900 rounded border border-gray-600 focus:border-indigo-500 '
                     'text-base outline-none text-gray-100 py-1 px-3 leading-8 transition-colors '
                     'duration-200 ease-in-out mb-4',
            'placeholder': 'Your username'
        })
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full bg-gray-600 bg-opacity-20 focus:bg-transparent focus:ring-2 '
                     'focus:ring-indigo-900 rounded border border-gray-600 focus:border-indigo-500 '
                     'text-base outline-none text-gray-100 py-1 px-3 leading-8 transition-colors '
                     'duration-200 ease-in-out mb-4',
            'placeholder': 'Password'
        })
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            'class': 'w-full bg-gray-600 bg-opacity-20 focus:bg-transparent focus:ring-2 '
                     'focus:ring-indigo-900 rounded border border-gray-600 focus:border-indigo-500 '
                     'text-base outline-none text-gray-100 py-1 px-3 leading-8 transition-colors '
                     'duration-200 ease-in-out mb-4',
            'placeholder': 'Confirm password'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'full_name', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with that email already exists.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        email = self.cleaned_data.get('email').lower()
        full_name = self.cleaned_data.get('full_name')
        username = self.cleaned_data.get('username')
        user.username = username
        user.email = email
        user.first_name = full_name
        if commit:
            user.save()
            Member.objects.update_or_create(
                email=email,
                defaults={'full_name': full_name}
            )
        return user


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactInquiry
        fields = ['email', 'message']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-3 py-2 rounded bg-gray-700 text-white',
                'placeholder': 'you@example.com'
            }),
            'message': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 rounded bg-gray-700 text-white',
                'rows': 4,
                'placeholder': 'Your message'
            })
        }
