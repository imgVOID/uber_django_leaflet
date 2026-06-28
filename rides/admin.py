from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from .models import DriverLocation, Ride, RideRoute, CargoShipment, VehicleTimeSnapshot

# 1. Inline для вантажів (щоб бачити їх в картці авто)
class CargoShipmentInline(admin.TabularInline):
    model = CargoShipment
    extra = 0
    readonly_fields = ("started_at",)

# 2. Inline для маршрутів поїздки
class RideRouteInline(admin.StackedInline):
    model = RideRoute
    readonly_fields = ("created_at", "updated_at")
    extra = 0

# 3. Реєстрація моделей
@admin.register(DriverLocation)
class DriverLocationAdmin(GISModelAdmin):
    list_display = ("driver", "vehicle", "updated_at")
    search_fields = ("driver__name", "vehicle__license_plate")
    list_filter = ("driver", "vehicle")
    readonly_fields = ("created_at", "updated_at")

@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = ("client", "driver", "vehicle", "status", "is_empty", "is_finished", "created_at")
    search_fields = ("client__name", "driver__name", "pickup_address", "dropoff_address")
    list_filter = ("status", "is_empty", "is_finished")
    readonly_fields = ("created_at", "updated_at", "is_empty", "is_finished")
    inlines = [RideRouteInline]

@admin.register(RideRoute)
class RideRouteAdmin(admin.ModelAdmin):
    list_display = ("ride", "speed_avg", "distance", "duration", "updated_at")
    readonly_fields = ("created_at", "updated_at")

@admin.register(CargoShipment)
class CargoShipmentAdmin(admin.ModelAdmin):
    list_display = ("id", "vehicle", "is_active", "started_at", "finished_at")
    list_filter = ("is_active", "started_at")
    search_fields = ("vehicle__model", "vehicle__license_plate", "description")
    readonly_fields = ("started_at",)

@admin.register(VehicleTimeSnapshot)
class VehicleTimeSnapshotAdmin(admin.ModelAdmin):
    list_display = ("vehicle", "timestamp", "speed", "is_cargo_active", "has_blown_tire", "has_low_fuel")
    list_filter = ("is_cargo_active", "has_blown_tire", "has_low_fuel", "timestamp")
    search_fields = ("vehicle__model", "vehicle__license_plate")
    date_hierarchy = "timestamp"
    readonly_fields = ("timestamp",)
