from django import forms
from django.core.exceptions import ValidationError
from vehicles.models import Vehicle
from datetime import date
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _
from .models import User


class EmailAuthenticationForm(AuthenticationForm):
    # Overriding the default username field to handle emails explicitly
    username = forms.EmailField(
        label=_("Email address"),
        widget=forms.EmailInput(
            attrs={
                "autofocus": True,
                "class": "form-control",
                "placeholder": "name@example.com",
            }
        ),
    )

class RegistrationForm(forms.Form):
    ROLE_CHOICES = (
        ('client', 'Client (Passenger)'),
        ('driver', 'Driver'),
    )

    email = forms.EmailField(max_length=64, widget=forms.EmailInput(attrs={'placeholder': 'Email'}))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password'}))
    role = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.RadioSelect, initial='client')
    first_name = forms.CharField(max_length=32, required=False, widget=forms.TextInput(attrs={'placeholder': 'First name'}))
    last_name = forms.CharField(max_length=32, required=False, widget=forms.TextInput(attrs={'placeholder': 'Last name'}))

    # Vehicle fields (optional; used when role == 'driver')
    vehicle_brand = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'placeholder': 'Vehicle brand'}))
    vehicle_model = forms.CharField(max_length=100, required=False, widget=forms.TextInput(attrs={'placeholder': 'Vehicle model'}))
    vehicle_license = forms.CharField(max_length=20, required=False, widget=forms.TextInput(attrs={'placeholder': 'License plate'}))

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('A user with that email already exists.')
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password1')
        p2 = cleaned.get('password2')
        if p1 and p2 and p1 != p2:
            raise ValidationError('Passwords do not match')
        return cleaned

    def save(self):
        data = self.cleaned_data
        email = data['email']
        password = data['password1']
        role = data['role']

        extra = {}
        if role == 'client':
            extra['is_client'] = True
        elif role == 'driver':
            extra['is_driver'] = True

        user = User.objects.create_user(email=email, password=password, **extra)

        # Update basic profile names if provided
        try:
            profile = user.clientprofile if role == 'client' else user.driverprofile
            profile.first_name = data.get('first_name') or ''
            profile.last_name = data.get('last_name') or ''
            profile.save()
        except Exception:
            # Profiles may be created by signals; ignore if not present
            pass

        # If driver and vehicle info was provided, create a Vehicle
        if role == 'driver' and data.get('vehicle_brand') and data.get('vehicle_model') and data.get('vehicle_license'):
            Vehicle.objects.create(
                driver=user.driverprofile,
                brand=data.get('vehicle_brand'),
                model=data.get('vehicle_model'),
                color=data.get('vehicle_color') or 'unknown',
                license_plate=data.get('vehicle_license'),
                year=data.get('vehicle_year') or date.today().year,
                vehicle_type=data.get('vehicle_type') or 'sedan',
                capacity=data.get('vehicle_capacity') or 4,
                registration_date=data.get('vehicle_registration_date') or date.today(),
            )

        return user
