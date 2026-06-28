from typing import List, Dict

from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.contrib.gis.db.models.functions import Distance as GeoDistance
from django.db.models import Exists, OuterRef
from .models import DriverLocation, Ride


class DriverLocator:
    """Adapter to fetch nearby drivers using GeoDjango/PostGIS
    """

    @staticmethod
    def get_nearby_drivers(lat: float, lng: float, radius_km: float = 5.0, driver_id=None) -> List[Dict]:
        point = Point(lng, lat, srid=4326)
        
        if driver_id:
            qs = DriverLocation.objects.filter(driver__user_id=driver_id)
        else:
            busy_drivers = Ride.objects.filter(
                driver_id=OuterRef('driver_id'),
                status__in=['accepted', 'arrived', 'in_progress']
            )
            qs = DriverLocation.objects.filter(
                position__distance_lte=(point, D(km=radius_km)),
                driver__is_active_driver=True,
                driver__is_verified=True,
            ).annotate(
                is_busy=Exists(busy_drivers)
            ).filter(is_busy=False)

        qs = qs.annotate(dist=GeoDistance('position', point)) \
            .select_related('driver', 'vehicle') \
            .order_by('dist')[:200]

        return [
            {
                'id': loc.driver.user.pk,
                'driver_name': loc.driver.name,
                'lat': loc.position.y,
                'lng': loc.position.x,
                'brand': loc.vehicle.brand,
                'model': loc.vehicle.model,
                'vehicle_id': loc.vehicle.id,
                'vehicle_type': loc.vehicle.vehicle_type,
                'speed_last': loc.vehicle.speed_last,
                'distance_km': round(loc.dist.km, 3) if loc.dist else 0,
                'color': getattr(loc.vehicle, 'color', '#fd7e14').lower(),
                'heading': getattr(loc, 'heading', 0),
                'capacity': getattr(loc.vehicle, 'capacity', 4),
                'year': getattr(loc.vehicle, 'year', 0),
                'has_blown_tire': getattr(loc.vehicle, 'has_blown_tire', False),
                'has_low_fuel': getattr(loc.vehicle, 'has_low_fuel', False)
            }
            for loc in qs
        ]
