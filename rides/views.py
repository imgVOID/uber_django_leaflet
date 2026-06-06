from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
import json
from django.views.decorators.csrf import ensure_csrf_cookie
from .services import DriverLocator
from django.views.generic import TemplateView
from django.utils.decorators import method_decorator
import requests
from django.views.decorators.http import require_GET


# Create your views here.
class TaxiRequestView(LoginRequiredMixin, TemplateView):
	template_name = 'taxi_request.html'
	login_url = '/login/'


@require_POST
@login_required
def set_location(request):
	try:
		payload = json.loads(request.body.decode('utf-8') or '{}')
		lat = float(payload.get('lat'))
		lng = float(payload.get('lng'))
	except Exception:
		return HttpResponseBadRequest('Invalid JSON payload')
	loc = {
		'lat': lat,
		'lng': lng,
		'accuracy': payload.get('accuracy'),
		'timestamp': payload.get('timestamp'),
	}
	request.session['user_location'] = loc
	request.session.modified = True
	return JsonResponse({'status': 'ok', 'location': loc})


@login_required
def nearby_drivers(request):
	# Read lat/lng from GET or from session
	try:
		lat = request.GET.get('lat')
		lng = request.GET.get('lng')
		if lat and lng:
			lat = float(lat); lng = float(lng)
		else:
			loc = request.session.get('user_location')
			if not loc:
				return JsonResponse({'drivers': [], 'error': 'no_location'}, status=400)
			lat = float(loc.get('lat'))
			lng = float(loc.get('lng'))
	except Exception:
		return JsonResponse({'drivers': [], 'error': 'invalid_params'}, status=400)

	radius = float(request.GET.get('radius_km') or 5.0)
	drivers = DriverLocator.get_nearby_drivers(lat, lng, radius_km=radius)
	return JsonResponse({'drivers': drivers})


@method_decorator(ensure_csrf_cookie, name='dispatch')
class TaxiMapView(LoginRequiredMixin, TemplateView):
	template_name = 'taxi_map.html'
	login_url = '/login/'


@require_GET
@login_required
def osrm_route(request):
	"""Proxy to OSRM routing service. Expects start_lat, start_lng, end_lat, end_lng as GET params."""
	try:
		start_lat = float(request.GET.get('start_lat'))
		start_lng = float(request.GET.get('start_lng'))
		end_lat = float(request.GET.get('end_lat'))
		end_lng = float(request.GET.get('end_lng'))
	except Exception:
		return HttpResponseBadRequest('Missing or invalid coordinates')

	osrm_url = (
		f"https://router.project-osrm.org/route/v1/driving/{start_lng},{start_lat};{end_lng},{end_lat}"
		"?overview=full&geometries=geojson"
	)

	try:
		resp = requests.get(osrm_url, timeout=10)
		resp.raise_for_status()
		data = resp.json()
	except requests.RequestException:
		return JsonResponse({'error': 'routing_failed'}, status=502)

	if not data.get('routes'):
		return JsonResponse({'error': 'no_route'}, status=404)

	# Return the first route object (same shape as OSRM route)
	return JsonResponse(data['routes'][0])
