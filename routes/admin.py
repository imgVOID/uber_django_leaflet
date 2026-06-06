from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin

from .models import Route


@admin.register(Route)
class RouteAdmin(GISModelAdmin):
	list_display = ("ride", "distance", "duration", "route_provider", "created_at")
	search_fields = ("ride__client__user__email", "ride__driver__user__email")
	list_filter = ("route_provider",)
	readonly_fields = ("created_at", "updated_at")
