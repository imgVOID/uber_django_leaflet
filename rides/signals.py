from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import DriverLocation, Ride
from asgiref.sync import async_to_sync

