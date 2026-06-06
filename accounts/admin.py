from django.contrib import admin

from .models import User, ClientProfile, DriverProfile, StaffProfile
from vehicles.models import Vehicle


class VehicleInline(admin.TabularInline):
	model = Vehicle
	fields = ("brand", "model", "license_plate", "is_available")
	extra = 0
	readonly_fields = ("brand", "model", "license_plate")


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
	list_display = ("email", "role", "is_staff", "is_active", "date_joined")
	search_fields = ("email",)
	list_filter = ("role", "is_staff", "is_active")
	ordering = ("-date_joined",)
	readonly_fields = ("date_joined",)


@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
	list_display = ("user_email", "name", "gender_verbose", "date_birth")
	search_fields = ("user__email", "first_name", "last_name")


@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
	list_display = ("user_email", "name", "is_verified", "is_active_driver")
	search_fields = ("user__email", "first_name", "last_name")
	list_filter = ("is_verified", "is_active_driver")
	inlines = (VehicleInline,)


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
	list_display = ("user_email", "name")
	search_fields = ("user__email", "first_name", "last_name")
