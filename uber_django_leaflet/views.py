from django.conf import settings
from django.shortcuts import render


def map_demo(request):
    center = settings.LEAFLET_CONFIG.get('DEFAULT_CENTER', (51.505, -0.09))
    zoom = settings.LEAFLET_CONFIG.get('DEFAULT_ZOOM', 13)
    return render(request, 'map_demo.html', {'center': center, 'zoom': zoom})
