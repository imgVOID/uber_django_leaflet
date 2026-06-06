from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import User, ClientProfile, DriverProfile, StaffProfile


@receiver(post_save, sender=User)
async def create_profiles_for_user(sender, instance, created, **kwargs):
    """
    Create empty default profiles when a User is created.
    """
    if not created:
        return

    if getattr(instance, 'is_client', False):
        await ClientProfile.objects.aget_or_create(user=instance)

    if getattr(instance, 'is_driver', False):
        await DriverProfile.objects.aget_or_create(user=instance)

    if getattr(instance, 'is_staff', False):
        await StaffProfile.objects.aget_or_create(user=instance)
