# mainapp/forms.py
from django import forms
from .models import ContactInquiry, Member


class MemberRegistrationForm(forms.ModelForm):
    """
    Create a Member only (do NOT create a Django auth.User).
    Password fields are validated here and then hashed with Member.set_password().
    """

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
        model = Member
        fields = ['username', 'full_name', 'email']

        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'w-full bg-gray-600 bg-opacity-20 focus:bg-transparent focus:ring-2 '
                         'focus:ring-indigo-900 rounded border border-gray-600 focus:border-indigo-500 '
                         'text-base outline-none text-gray-100 py-1 px-3 leading-8 transition-colors '
                         'duration-200 ease-in-out mb-4',
                'placeholder': 'Your username'
            }),
            'full_name': forms.TextInput(attrs={
                'class': 'w-full bg-gray-600 bg-opacity-20 focus:bg-transparent focus:ring-2 '
                         'focus:ring-indigo-900 rounded border border-gray-600 focus:border-indigo-500 '
                         'text-base outline-none text-gray-100 py-1 px-3 leading-8 transition-colors '
                         'duration-200 ease-in-out mb-4',
                'placeholder': 'Your full name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full bg-gray-600 bg-opacity-20 focus:bg-transparent focus:ring-2 '
                         'focus:ring-indigo-900 rounded border border-gray-600 focus:border-indigo-500 '
                         'text-base outline-none text-gray-100 py-1 px-3 leading-8 transition-colors '
                         'duration-200 ease-in-out mb-4',
                'placeholder': 'you@example.com'
            }),
        }

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        qs = Member.objects.filter(email__iexact=email)
        # exclude current instance when editing (safe for both create and update)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A member with that email already exists.")
        return email

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        qs = Member.objects.filter(username__iexact=username)
        # exclude current instance when editing
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned

    def save(self, commit=True):
        # don't call super().save(commit=True) yet — assign normalized values first
        member = super().save(commit=False)

        # normalize and set essential fields
        email = (self.cleaned_data.get('email') or '').strip().lower()
        username = (self.cleaned_data.get('username') or '').strip()
        full_name = (self.cleaned_data.get('full_name') or '').strip()

        member.email = email
        member.username = username
        member.full_name = full_name

        raw_password = self.cleaned_data.get('password1')
        if raw_password:
            member.set_password(raw_password)  # uses your Member.set_password (hashes)

        if commit:
            member.save()
        return member


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
