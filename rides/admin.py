# H:\uber_django_leaflet\taxi\admin.py

from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from .models import DriverLocation, Ride


@admin.register(DriverLocation)
class DriverLocationAdmin(GISModelAdmin):  # Наслідуємося від GISModelAdmin
    list_display = ("driver", "vehicle", "updated_at")
    search_fields = ("driver__user__email", "vehicle__license_plate")
    list_filter = ("driver", "vehicle")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = ("client", "driver", "vehicle", "status", "is_empty", "is_finished", "created_at")
    search_fields = ("client__user__email", "driver__user__email", "pickup_address", "dropoff_address")
    list_filter = ("status", "is_empty", "is_finished")
    readonly_fields = ("created_at", "updated_at")
