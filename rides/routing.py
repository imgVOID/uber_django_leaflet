from django.urls import re_path
from .consumers import DriverTrackingConsumer, RideMapConsumer, LiveViewConsumer

websocket_urlpatterns = [
    re_path(r'ws/live-view/', LiveViewConsumer.as_asgi()),
    re_path(r'ws/tracking/', DriverTrackingConsumer.as_asgi()),
    re_path(r'ws/map/updates/', RideMapConsumer.as_asgi()),
]