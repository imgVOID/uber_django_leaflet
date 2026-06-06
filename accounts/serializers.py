from rest_framework import serializers
from .models import ClientProfile, DriverProfile, StaffProfile


class AbstractProfileSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        fields = ['user', 'first_name', 'last_name', 'gender', 'date_birth']


class ClientProfileSerializer(AbstractProfileSerializer):
    class Meta(AbstractProfileSerializer.Meta):
        model = ClientProfile
        fields = AbstractProfileSerializer.Meta.fields


class DriverProfileSerializer(AbstractProfileSerializer):
    class Meta(AbstractProfileSerializer.Meta):
        model = DriverProfile
        fields = AbstractProfileSerializer.Meta.fields + [
            'is_child_friendly',
            'is_pet_friendly',
            'is_smoke_friendly',
            'is_music_friendly',
            'is_talking_friendly',
            'has_charger',
            'has_aux',
            'is_verified',
            'is_active_driver',
        ]


class StaffProfileSerializer(AbstractProfileSerializer):
    class Meta(AbstractProfileSerializer.Meta):
        model = StaffProfile
        fields = AbstractProfileSerializer.Meta.fields
