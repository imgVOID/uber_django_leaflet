"""
OSRM Routing Service
Simple service to call Open Source Routing Machine API for route calculation.
Uses free public OSRM API: https://router.project-osrm.org
"""
import requests
from django.contrib.gis.geos import LineString
from routes.models import Route


OSRM_API_URL = "https://router.project-osrm.org/route/v1/driving"


def calculate_route_osrm(ride):
    """
    Calculate route using OSRM API for a ride.
    
    Args:
        ride: Ride instance with pickup_position and dropoff_position
        
    Returns:
        Route instance or None if calculation fails
    """
    try:
        # Extract coordinates (lon, lat format for OSRM)
        pickup_lon = ride.pickup_position.x
        pickup_lat = ride.pickup_position.y
        dropoff_lon = ride.dropoff_position.x
        dropoff_lat = ride.dropoff_position.y
        
        # Build OSRM request URL
        url = f"{OSRM_API_URL}/{pickup_lon},{pickup_lat};{dropoff_lon},{dropoff_lat}"
        params = {
            "overview": "full",  # Get full route geometry
            "geometries": "geojson",  # Return GeoJSON format
            "steps": "false",  # Don't need turn-by-turn for MVP
        }
        
        # Call OSRM API
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        # Check if route was found
        if data.get("code") != "Ok" or not data.get("routes"):
            print(f"OSRM Error: {data.get('code')} - {data.get('message', 'Unknown error')}")
            return None
        
        # Extract first route (best/fastest)
        route_data = data["routes"][0]
        
        # Get geometry (GeoJSON LineString)
        geometry = route_data.get("geometry", {})
        if geometry.get("type") != "LineString" or not geometry.get("coordinates"):
            print("No valid geometry in OSRM response")
            return None
        
        # Convert GeoJSON coordinates to LineString
        coords = geometry["coordinates"]
        path = LineString(coords, srid=4326)
        
        # Extract distance (in meters) and duration (in seconds)
        distance_meters = route_data.get("distance", 0)
        duration_seconds = int(route_data.get("duration", 0))
        
        # Convert distance to kilometers
        distance_km = distance_meters / 1000
        
        # Create or update Route
        route, created = Route.objects.update_or_create(
            ride=ride,
            defaults={
                "path": path,
                "distance": distance_km,
                "duration": duration_seconds,
                "route_provider": "osrm",
            }
        )
        
        action = "Created" if created else "Updated"
        print(f"{action} route for ride {ride.id}: {distance_km:.2f}km, {duration_seconds}s")
        
        return route
        
    except requests.exceptions.RequestException as e:
        print(f"OSRM API Request Error: {str(e)}")
        return None
    except Exception as e:
        print(f"Error calculating route: {str(e)}")
        return None
