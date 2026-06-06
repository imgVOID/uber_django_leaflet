from django.db import models
from django.contrib.gis.db import models as gis_models
from django.core.exceptions import ValidationError
from accounts.models import DriverProfile, ClientProfile
from vehicles.models import Vehicle


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
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True, help_text="When the ride started")
    finished_at = models.DateTimeField(null=True, blank=True, help_text="When the ride finished")
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

    def get_nearby_available_drivers(self, radius_km=5):
        """
        Get available drivers within radius_km of pickup location.
        Returns list of (DriverProfile, distance_km) tuples sorted by distance.
        
        For MVP: Uses simple haversine distance calculation (no PostGIS required).
        """
        if not self.pickup_position:
            return []
        
        from math import radians, sin, cos, sqrt, atan2
        
        def haversine_distance(lat1, lon1, lat2, lon2):
            """Calculate distance in km between two coordinates."""
            R = 6371  # Earth radius in km
            lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            return R * c
        
        nearby_drivers = []
        
        # Get all available drivers' locations
        for location in DriverLocation.objects.select_related('driver').filter(
            driver__driverprofile__is_active_driver=True,
            driver__driverprofile__is_verified=True
        ):
            driver = location.driver
            
            # Check if driver has available vehicle and no active ride
            if not driver.is_available:
                continue
            
            # Calculate distance
            distance = haversine_distance(
                self.pickup_position.y,
                self.pickup_position.x,
                location.position.y,
                location.position.x
            )
            
            if distance <= radius_km:
                nearby_drivers.append((driver, round(distance, 2)))
        
        # Sort by distance
        nearby_drivers.sort(key=lambda x: x[1])
        return nearby_drivers

    def save(self, *args, **kwargs):
        self.is_empty = self.driver is None
        self.is_finished = self.status == 'completed'
        
        super().save(*args, **kwargs)
