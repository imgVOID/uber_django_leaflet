from django.db import models
from accounts.models import DriverProfile


class Vehicle(models.Model):
    VEHICLE_TYPE_CHOICES = [
        ('sedan', 'Sedan'),
        ('suv', 'SUV'),
        ('hatchback', 'Hatchback'),
        ('van', 'Van'),
        ('truck', 'Truck'),
    ]

    driver = models.ForeignKey(
        DriverProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='vehicles',
        help_text="Driver who owns this vehicle"
    )
    brand = models.CharField(max_length=100, help_text="Vehicle brand (e.g., Toyota, Honda)")
    model = models.CharField(max_length=100, help_text="Vehicle model (e.g., Camry, Accord)")
    color = models.CharField(max_length=50, help_text="Vehicle color")
    license_plate = models.CharField(max_length=20, unique=True, help_text="License plate number")
    year = models.IntegerField(help_text="Year of manufacture")
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPE_CHOICES, default='sedan', help_text="Type of vehicle")
    capacity = models.IntegerField(default=4, help_text="Number of passengers the vehicle can accommodate")
    registration_date = models.DateField(help_text="Date of vehicle registration")

    # Is the record active, or temporarily suspended
    is_active = models.BooleanField(default=True, help_text="Whether the vehicle is active")
    # If the vehicle changes driver or become unavailable for a long time, we need to keep the vehicle record.
    # So we need to create another record with another active driver for this vehicle.
    # It's very useful for the speed statistics and database consistency.
    is_deleted = models.BooleanField(default=False, help_text="Whether the vehicle is deleted")
    # Status of an current availability for a ride
    is_available = models.BooleanField(default=True, help_text="Whether the vehicle is available for rides")
    # Emergency status
    is_emergency = models.BooleanField(default=False, help_text="Whether the vehicle is in emergency state")

    # Vehicle condition statuses
    has_blown_tire = models.BooleanField(default=False, help_text="Whether the vehicle has a blown tire")
    has_low_fuel = models.BooleanField(default=False, help_text="Whether the vehicle has low fuel")
    has_been_lost = models.BooleanField(default=False, help_text="Whether the vehicle has been lost")

    # Speed
    speed_max = models.FloatField(null=True, blank=True, help_text="Maximum speed in km/h")
    speed_last = models.FloatField(null=True, blank=True, help_text="Last recorded speed in km/h")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Vehicle"
        verbose_name_plural = "Vehicles"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.year} {self.brand} {self.model} ({self.license_plate})"

    @property
    def speed_stats(self):
        return {
            'min': self.speed_min,
            'max': self.speed_max,
        }

    @property
    def has_dangerous_behaviour(self):
        return self.speed_max > 100
    
    @property
    def has_speed_limit(self):
        return self.speed_avg <= 60

    @property
    def active_ride(self):
        return self.rides.filter(status='in_progress').first()
    
    @property
    def speed_avg(self):
        return (self.speed_min + self.speed_max) / 2
