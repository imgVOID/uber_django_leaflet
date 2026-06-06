from django.contrib import admin

from .models import Vehicle


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
	list_display = ("license_plate", "driver", "brand", "model", "year", "vehicle_type", "is_available", "created_at")
	search_fields = ("license_plate", "brand", "model")
	list_filter = ("vehicle_type", "is_available")
	readonly_fields = ("created_at", "updated_at")
