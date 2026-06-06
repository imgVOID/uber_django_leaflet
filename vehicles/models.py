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
    is_available = models.BooleanField(default=True, help_text="Whether the vehicle is available for rides")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Vehicle"
        verbose_name_plural = "Vehicles"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.year} {self.brand} {self.model} ({self.license_plate})"
