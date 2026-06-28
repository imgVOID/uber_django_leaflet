import uuid
from datetime import date, timedelta
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from accounts.managers import EmailUserManager


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model with role-based access control.
    Supports: Client, Driver, Staff roles.
    """
    class RoleChoices(models.TextChoices):
        CLIENT = 'client', _('Client')
        DRIVER = 'driver', _('Driver')
        STAFF = 'staff', _('Staff')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, unique=True, editable=False, db_index=True)
    email = models.EmailField(_("email address"), unique=True, max_length=64)
    role = models.CharField(max_length=20, choices=RoleChoices.choices, default=RoleChoices.CLIENT, help_text="User role for access control")
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    
    # OAuth2 / JWT fields
    last_login_ip = models.GenericIPAddressField(null=True, blank=True, help_text="Last login IP address")
    oauth2_provider = models.CharField(max_length=50, blank=True, help_text="OAuth2 provider (google, github, etc.)")
    oauth2_id = models.CharField(max_length=255, blank=True, help_text="External provider user ID")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = EmailUserManager()

    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
        ]

    def __str__(self):
        return f"{self.email} ({self.get_role_display()})"

    @property
    def is_client(self):
        return self.role == self.RoleChoices.CLIENT
    
    @property
    def is_driver(self):
        return self.role == self.RoleChoices.DRIVER
    
    def has_role(self, role):
        """Check if user has specific role."""
        return self.role == role
    
    def can_create_ride(self):
        """Check if user can create rides."""
        return self.is_client and self.is_active
    
    def can_accept_ride(self):
        """Check if user can accept rides."""
        return self.is_driver and self.is_active


class AbstractProfile(models.Model):
    class GenderChoices(models.IntegerChoices):
        EMPTY = 0, _("Empty")
        MALE = 1, _("Male")
        FEMALE = 2, _("Female")

    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, editable=False)
    first_name = models.CharField(max_length=32, blank=True)
    last_name = models.CharField(max_length=32, blank=True)
    gender = models.SmallIntegerField(choices=GenderChoices.choices, default=GenderChoices.EMPTY)
    date_birth = models.DateField(default=date.today()-timedelta(days=18*365), blank=True, null=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.user.email

    @property
    def id(self):
        return self.pk

    @property
    def user_email(self):
        return self.user.email
    
    @property
    def name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    @property
    def name_reversed(self):
        return f'{self.last_name} {self.first_name}'

    @property
    def age(self):
        return (date.today() - self.date_birth).days / 365

    @property
    def is_adult(self):
        return True if self.age > 18 else False

    @property
    def gender_verbose(self):
        return self.get_gender_display()

    @property
    def is_filled(self):
        return bool(self.name)

    @property
    def is_empty(self):
        return not self.is_filled


class ClientProfile(AbstractProfile):
    """Profile for client/passenger users."""
    class Meta:
        verbose_name = _("Profile Client")
        verbose_name_plural = _("Profiles Client")
        default_related_name = "clientprofile"


class DriverProfile(AbstractProfile):
    """Profile for driver users with vehicle and service preferences."""
    is_child_friendly = models.BooleanField(default=False, help_text="Driver accepts children")
    is_pet_friendly = models.BooleanField(default=False, help_text="Driver accepts pets")
    is_smoke_friendly = models.BooleanField(default=False, help_text="Smoking is allowed in vehicle")
    is_music_friendly = models.BooleanField(default=True, help_text="Driver plays music during rides")
    is_talking_friendly = models.BooleanField(default=True, help_text="Driver is open to conversation")
    has_charger = models.BooleanField(default=False, help_text="Vehicle has phone charger")
    has_aux = models.BooleanField(default=False, help_text="Vehicle has aux cable for music")
    is_verified = models.BooleanField(default=False, help_text="Driver is verified")
    is_active_driver = models.BooleanField(default=True, help_text="Driver is currently active")
    
    class Meta:
        verbose_name = _("Profile Driver")
        verbose_name_plural = _("Profiles Driver")
        default_related_name = "driverprofile"
    
    @property
    def fleet(self):
        return self.vehicles.all()

    @property
    def current_location(self):
        """Get driver's most recent location."""
        return self.locations.first() if self.locations.exists() else None
    
    @property
    def is_available(self):
        """Check if driver is available (active, verified, has vehicle, no active ride)."""
        if not self.is_active_driver or not self.is_verified:
            return False
        if not self.vehicles.filter(is_available=True).exists():
            return False
        # Check if driver has active ride
        active_rides = self.assigned_rides.filter(status__in=['accepted', 'arrived', 'in_progress']).exists()
        return not active_rides

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_available_vehicle(self):
        """Get first available vehicle for this driver."""
        return self.vehicles.filter(is_available=True).first()


class StaffProfile(AbstractProfile):
    """Profile for staff/admin users."""
    class Meta:
        verbose_name = _("Profile Staff")
        verbose_name_plural = _("Profiles Staff")
