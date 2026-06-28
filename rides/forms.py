from django import forms
from django.utils.translation import gettext_lazy as _


class SpeedTestForm(forms.Form):
    speed = forms.FloatField(
        label="Speed in km/h",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'id': 'speedInput'})
    )

class RideRequestForm(forms.Form):
    pickup_address = forms.CharField(max_length=255)
    dropoff_address = forms.CharField(max_length=255, required=False)
    pickup_lat = forms.FloatField()
    pickup_lng = forms.FloatField()
    dropoff_lat = forms.FloatField(required=False)
    dropoff_lng = forms.FloatField(required=False)
