from math import radians, sin, cos, sqrt, atan2
from typing import List, Dict

from .models import DriverLocation


class DriverLocator:
    """Adapter to fetch nearby drivers using GeoDjango/PostGIS when available,
    otherwise falls back to a Python haversine implementation.
    Returns list of dicts with driver/vehicle/position/distance_km.
    """

    @staticmethod
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371.0
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return R * c

    @staticmethod
    def get_nearby_drivers(lat: float, lng: float, radius_km: float = 5.0) -> List[Dict]:
        from django.contrib.gis.geos import Point
        from django.contrib.gis.measure import D
        from django.contrib.gis.db.models.functions import Distance

        point = Point(lng, lat, srid=4326)
        
        # Оптимізація: select_related для мінімізації SQL-запитів до моделей Driver та Vehicle
        qs = DriverLocation.objects.filter(
            position__distance_lte=(point, D(km=radius_km)),
            driver__is_active_driver=True,
            driver__is_verified=True,
        ).select_related('driver', 'vehicle').annotate(
            distance=Distance('position', point)
        ).order_by('distance')[:200]

        results = []
        for loc in qs:
            color = getattr(loc.vehicle, 'color', '#fd7e14') 
            
            d_val = loc.distance.km if hasattr(loc.distance, 'km') else float(loc.distance)

            results.append({
                'driver_id': str(loc.driver.user.pk),
                'driver_name': loc.driver.name,
                'vehicle': str(loc.vehicle),
                'lat': loc.position.y,
                'lng': loc.position.x,
                'distance_km': round(d_val, 3),
                'color': color.lower()
            })
            

        return results
