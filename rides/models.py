from django.db import models
from django.contrib.gis.db import models as gis_models
from django.core.exceptions import ValidationError
from accounts.models import DriverProfile, ClientProfile
from vehicles.models import Vehicle


class CargoShipment(models.Model):
    driver = models.ForeignKey(DriverProfile, on_delete=models.SET_NULL, null=True, blank=True)
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='cargo_shipments')
    is_active = models.BooleanField(default=True)
    description = models.CharField(max_length=255, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    start_point = gis_models.PointField(srid=4326, null=True, blank=True)
    history = models.JSONField(
        default=dict, blank=True, 
        help_text="GeoJSON: {'type': 'FeatureCollection', 'features': [...]}"
    )
    speed_min = models.FloatField(null=True, blank=True, help_text="Minimum speed in km/h")
    speed_avg = models.FloatField(null=True, blank=True, help_text="Average speed in km/h")
    speed_max = models.FloatField(null=True, blank=True, help_text="Maximum speed in km/h")
    speed_last = models.FloatField(null=True, blank=True, help_text="Last speed in km/h")
    altitude_min = models.FloatField(null=True, blank=True, help_text="Minimum altitude in km")
    altitude_avg = models.FloatField(null=True, blank=True, help_text="Average altitude in km")
    altitude_max = models.FloatField(null=True, blank=True, help_text="Maximum altitude in km")

    def __str__(self):
        return f"Cargo {self.id} on {self.vehicle.model}"
    
    def save(self, *args, **kwargs):
        if not self.start_point and self.history:
            from django.contrib.gis.geos import Point
            try:
                coords = self.history['features'][0]['geometry']['coordinates']
                self.start_point = Point(coords[0], coords[1], srid=4326)
            except (KeyError, IndexError, TypeError):
                pass
        super().save(*args, **kwargs)


class VehicleTimeSnapshot(models.Model):
    """
    Знімок стану авто на конкретний момент часу.
    Використовується для реалізації режиму Rewind (історія за 6 місяців).
    """
    vehicle = models.ForeignKey(
        Vehicle, 
        on_delete=models.CASCADE, 
        related_name='time_snapshots'
    )
    timestamp = models.DateTimeField(db_index=True, help_text="Точний момент знімка")

    lat = models.FloatField()
    lng = models.FloatField()

    has_blown_tire = models.BooleanField(default=False, help_text="Whether the vehicle has a blown tire")
    has_low_fuel = models.BooleanField(default=False, help_text="Whether the vehicle has low fuel")

    speed = models.FloatField(help_text="Швидкість авто на момент знімка")
    heading = models.FloatField(null=True, blank=True, help_text="Напрямок руху в градусах")

    is_cargo_active = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['vehicle', '-timestamp']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.vehicle.model} @ {self.timestamp}"


class DriverLocation(models.Model):
    """
    Model to track driver and vehicle position in real-time.
    Stores geographic location in GeoJSON format.
    """
    driver = models.ForeignKey(
        DriverProfile,
        on_delete=models.CASCADE,
        related_name='locations',
        help_text="Driver associated with this location"
    )
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.CASCADE,
        related_name='locations',
        help_text="Vehicle associated with this location"
    )
    position = gis_models.PointField(srid=4326, help_text="Geographic position (latitude, longitude) in WGS84 format")
    heading = models.FloatField(null=True, blank=True, help_text="Direction in degrees (0-360)")
    speed = models.FloatField(null=True, blank=True, help_text="Current speed in km/h")
    altitude = models.FloatField(null=True, blank=True, help_text="Altitude in meters")
    accuracy = models.FloatField(null=True, blank=True, help_text="GPS accuracy in meters")
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Driver Location"
        verbose_name_plural = "Driver Locations"
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['driver', '-updated_at']),
            models.Index(fields=['vehicle', '-updated_at']),
        ]

    def __str__(self):
        return f"{self.driver.name} - {self.vehicle} at {self.updated_at}"

    def clean(self):
        if self.vehicle and self.vehicle.driver != self.driver:
            raise ValidationError("The selected vehicle does not belong to this driver.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class Ride(models.Model):
    """
    Model for a contract/ride between a client and a driver.
    Client can create an empty ride without a driver initially.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('arrived', 'Arrived'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    # Relationships
    client = models.ForeignKey(
        ClientProfile,
        on_delete=models.CASCADE,
        related_name='rides',
        help_text="Client who requested the ride"
    )
    driver = models.ForeignKey(
        DriverProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_rides',
        help_text="Driver assigned to this ride"
    )
    vehicle = models.ForeignKey(
        Vehicle,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='rides',
        help_text="Vehicle used for this ride"
    )

    # Address fields
    pickup_address = models.CharField(max_length=255, blank=True, help_text="Pickup location address")
    dropoff_address = models.CharField(max_length=255, blank=True, help_text="Dropoff location address")

    # Geographic positions
    pickup_position = gis_models.PointField(srid=4326, null=True, blank=True, help_text="Pickup location coordinates")
    dropoff_position = gis_models.PointField(srid=4326, null=True, blank=True, help_text="Dropoff location coordinates")

    # Ride details
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Ride price")
    distance = models.FloatField(null=True, blank=True, help_text="Estimated distance in km")
    duration = models.IntegerField(null=True, blank=True, help_text="Estimated duration in minutes")
    notes = models.TextField(blank=True, help_text="Additional notes or special requests")

    # Status flags
    is_empty = models.BooleanField(default=True, help_text="Ride is empty (no driver assigned yet)")
    is_finished = models.BooleanField(default=False, help_text="Ride is finished")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', help_text="Current status of the ride")

    # Timestamps
    started_at = models.DateTimeField(null=True, blank=True, help_text="When the ride started")
    finished_at = models.DateTimeField(null=True, blank=True, help_text="When the ride finished")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ride"
        verbose_name_plural = "Rides"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['client', '-created_at']),
            models.Index(fields=['driver', '-created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        driver_name = self.driver.name if self.driver else "No Driver"
        return f"Ride by {self.client.name} with {driver_name} - {self.status}"

    def save(self, *args, **kwargs):
        self.is_empty = self.driver is None
        self.is_finished = self.status == 'completed'
        
        super().save(*args, **kwargs)


# Creating when the driver arrived
class RideRoute(models.Model):
    ride = models.OneToOneField(Ride, on_delete=models.CASCADE, primary_key=True)
    history = models.JSONField(
        default=dict, blank=True, 
        help_text="GeoJSON: {'type': 'FeatureCollection', 'features': [...]}"
    )
    speed_min = models.FloatField(null=True, blank=True, help_text="Minimum speed in km/h")
    speed_avg = models.FloatField(null=True, blank=True, help_text="Average speed in km/h")
    speed_max = models.FloatField(null=True, blank=True, help_text="Maximum speed in km/h")
    speed_last = models.FloatField(null=True, blank=True, help_text="Last speed in km/h")
    altitude_min = models.FloatField(null=True, blank=True, help_text="Minimum altitude in km")
    altitude_avg = models.FloatField(null=True, blank=True, help_text="Average altitude in km")
    altitude_max = models.FloatField(null=True, blank=True, help_text="Maximum altitude in km")
    distance = models.FloatField(null=True, blank=True, help_text="Real distance in km")
    duration = models.IntegerField(null=True, blank=True, help_text="Real duration in minutes")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def status(self):
        return self.ride.status
    
    @property
    def is_finished(self):
        return self.ride.is_finished
