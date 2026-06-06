from django.urls import path
from .views import *

app_name = 'rides'

urlpatterns = [
    path('', TaxiRequestView.as_view(), name='taxi-request'),
    path('set_location/', set_location, name='set-location'),
    path('nearby_drivers/', nearby_drivers, name='nearby-drivers'),
    path('osrm_route/', osrm_route, name='osrm-route'),
    path('map/', TaxiMapView.as_view(), name='taxi-map'),
]
