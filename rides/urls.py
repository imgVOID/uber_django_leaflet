from django.urls import path
from .views import *

app_name = 'rides'

urlpatterns = [
    path('', TaxiRequestView.as_view(), name='taxi-request'),
    path('set_location/', set_location, name='set-location'),
    path('nearby_drivers/', nearby_drivers, name='nearby-drivers'),
    path('osrm_route/', osrm_route, name='osrm-route'),
    path('map/', TaxiMapView.as_view(), name='taxi-map'),
    path('test_websocket/', SpeedSocketTestView.as_view(), name='test-websocket'),
    path('ride/start/', start_ride_view, name='start-ride'),
    path('ride/select_driver/', select_driver_view, name='select-driver'),
    path('ride/cancel_driver/', cancel_driver_selection, name='cancel-ride'),
    path('ride/status/', get_ride_status, name='ride-status'),
    # live view
    path('live/', LiveView.as_view(), name='live-view'),
    path('live-fleet/', LiveFleetDataView.as_view(), name='api-live-fleet'),
    path('live/toggle-cargo/<int:vehicle_id>/', toggle_cargo, name='toggle-cargo'),
    path('live/get-time-rec/', get_history_at_time, name='get-history-time'),
    path('live/timestamps/', get_available_timestamps, name='get-history-timestamps'),
    path('analytics/', AnalyticsDashboardView.as_view(), name='analytics-dashboard'),
    path('analytics/fleet-data/', AnalyticsFleetDataView.as_view(), name='analytics-fleet-data'),
    path('analytics/hotspots/', CargoHotspotsAPI.as_view(), name='analytics-hotspots'),
    path('analytics/top-routes/', TopRoutesAPI.as_view(), name='analytics-top-routes'),
    path('analytics/cargo-start/', get_cargo_start_points, name='analytics-cargo-start'),
    path('analytics/avg-speed/<int:vehicle_id>/', get_avg_speed_view, name='analytics-avg-speed'),
    path('analytics/routes-in-area/', RoutesInAreaAPI.as_view(), name='analytics-routes-in-area'),
    path('analytics/calculate-intersections/', CalculateIntersectionsAPI.as_view(), name='calculate-intersections'),
]