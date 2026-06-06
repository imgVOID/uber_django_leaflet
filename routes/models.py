from django.db import models
from django.contrib.gis.db import models as gis_models


class Route(models.Model):
    """
    Simple route model storing a direct path from pickup to dropoff point.
    LineString from point A to B for taxi ride visualization on map.
    """
    ride = models.OneToOneField(
        'rides.Ride',
        on_delete=models.CASCADE,
        related_name='route',
        help_text="Associated ride"
    )
    path = gis_models.LineStringField(srid=4326, help_text="Route path as LineString (GeoJSON) from pickup to dropoff")
    distance = models.FloatField(help_text="Distance in kilometers")
    duration = models.IntegerField(help_text="Estimated duration in seconds")
    route_provider = models.CharField(max_length=50, default='osrm', choices=[('osrm', 'OSRM - Open Source Routing Machine'), ('osm', 'OpenStreetMap'), ('vroom', 'Vroom')], help_text="Free routing service used")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Route"
        verbose_name_plural = "Routes"
        ordering = ['-created_at']

    def __str__(self):
        return f"Route for Ride #{self.ride.id} - {self.distance:.2f}km"

    def to_geojson(self):
        """
        Convert route to GeoJSON for Leaflet display.
        Returns a LineString Feature with route properties.
        """
        coords = list(self.path.coords)
        
        return {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": coords
            },
            "properties": {
                "id": self.id,
                "ride_id": self.ride_id,
                "distance_km": round(self.distance, 2),
                "duration_minutes": round(self.duration / 60, 1),
                "pickup_address": self.ride.pickup_address,
                "dropoff_address": self.ride.dropoff_address,
                "route_provider": self.route_provider,
            }
        }

    def to_geojson_with_waypoints(self):
        """
        Convert route to GeoJSON FeatureCollection with pickup/dropoff markers.
        Perfect for complete map display.
        """
        features = []
        
        # Main route line
        features.append(self.to_geojson())
        
        # Pickup marker (green)
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [self.ride.pickup_position.x, self.ride.pickup_position.y]
            },
            "properties": {
                "type": "pickup",
                "address": self.ride.pickup_address,
                "color": "green",
                "marker": "A"
            }
        })
        
        # Dropoff marker (red)
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [self.ride.dropoff_position.x, self.ride.dropoff_position.y]
            },
            "properties": {
                "type": "dropoff",
                "address": self.ride.dropoff_address,
                "color": "red",
                "marker": "B"
            }
        })
        
        return {
            "type": "FeatureCollection",
            "features": features
        }
