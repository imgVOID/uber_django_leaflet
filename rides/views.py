import json
import requests
import logging
import hashlib
from collections import Counter
from django.utils import timezone
from django.shortcuts import redirect
from django.views.generic import TemplateView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db.models import Avg, Exists, OuterRef, Subquery
from django.db import transaction
from django.views.generic import TemplateView
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.gis.geos import Point, Polygon
from django.db.models import Exists, OuterRef
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_datetime
from rest_framework.permissions import IsAuthenticated
from django.db.models import F
from django.db.models import Avg
from django.db.models import Count
from collections import defaultdict
from django.contrib.gis.geos import Point, Polygon, LineString
import json
from django.core.serializers.json import DjangoJSONEncoder

from rides.models import Ride, RideRoute, DriverLocation, CargoShipment, VehicleTimeSnapshot
from accounts.models import DriverProfile
from vehicles.models import Vehicle

from .services import DriverLocator
from .forms import SpeedTestForm, RideRequestForm

logger = logging.getLogger(__name__)

# LIVE VIEW
class LiveView(LoginRequiredMixin, TemplateView):
    template_name = 'live_view/live_view.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class LiveFleetDataView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        qs = DriverLocation.objects.filter(
            driver__is_active_driver=True,
            driver__is_verified=True,
        ).annotate(
            is_cargo_active=Exists(
                CargoShipment.objects.filter(vehicle=OuterRef('vehicle'), is_active=True) # Виправлено: vehicle замість pk
            )
        ).select_related('driver', 'vehicle')

        data = []
        for loc in qs:
            # ЗАХИСТ ВІД ПУСТИХ ЗНАЧЕНЬ
            if not loc.vehicle or not loc.driver:
                continue
                
            data.append({
                'id': loc.driver.user.pk,
                'driver_name': loc.driver.name,
                'lat': loc.position.y,
                'lng': loc.position.x,
                'brand': getattr(loc.vehicle, 'brand', 'N/A'),
                'model': getattr(loc.vehicle, 'model', 'N/A'),
                'vehicle_id': loc.vehicle.id,
                'speed_last': getattr(loc.vehicle, 'speed_last', 0),
                'is_busy': getattr(loc, 'is_busy', False),
                'color': getattr(loc.vehicle, 'color', '#fd7e14').lower(),
                'heading': getattr(loc, 'heading', 0),
                'has_blown_tire': getattr(loc.vehicle, 'has_blown_tire', False),
                'has_low_fuel': getattr(loc.vehicle, 'has_low_fuel', False),
                'is_cargo_active': loc.is_cargo_active
            })

        return Response(data)

@csrf_exempt
def toggle_cargo(request, vehicle_id):
    if request.method == 'POST':
        # 1. Отримуємо профіль водія за поточним користувачем
        vehicle = Vehicle.objects.select_related('driver').get(id=vehicle_id)
        driver = vehicle.driver
        print(driver)
        
        # 3. Логіка перемикання вантажу
        active_cargo = CargoShipment.objects.filter(vehicle_id=vehicle.id, driver_id=vehicle.driver.id, is_active=True).first()
        
        if active_cargo:
            active_cargo.is_active = False
            active_cargo.finished_at = timezone.now()
            active_cargo.save()
            return JsonResponse({'status': 'cargo_dropped'})
        else:
            CargoShipment.objects.create(
                vehicle=vehicle,
                driver=vehicle.driver,
                history={"type": "FeatureCollection", "features": []}
            )
            return JsonResponse({'status': 'cargo_picked'})
            
    return JsonResponse({'error': 'Invalid method'}, status=400)

def get_history_at_time(request):
    target_time_str = request.GET.get('time')
    
    if not target_time_str:
        return JsonResponse({'error': 'Timestamp missing'}, status=400)

    # Спробуємо замінити пробіли, якщо фронтенд їх передає некоректно
    # (іноді браузери кодують '+' як ' ')
    target_time_str = target_time_str.replace(' ', '+')
    
    target_time = parse_datetime(target_time_str)
    
    if not target_time:
        return JsonResponse({'error': 'Invalid timestamp format'}, status=400)
    
    if not target_time:
        return JsonResponse({'error': 'Invalid timestamp'}, status=400)

    # Використовуємо .filter().distinct('vehicle_id') для SQL-оптимізації
    snapshots = VehicleTimeSnapshot.objects.filter(
        timestamp__lte=target_time
    ).order_by('vehicle_id', '-timestamp').distinct('vehicle_id')
    
    data = [{
        "vehicle_id": s.vehicle_id,
        "lat": s.lat,
        "lng": s.lng,
        "last_speed": s.speed,
        "is_cargo_active": s.is_cargo_active,
        "has_blown_tire": s.has_blown_tire,
        "has_low_fuel": s.has_low_fuel
    } for s in snapshots]
    
    return JsonResponse(data, safe=False)


def get_available_timestamps(request):
    # Отримуємо унікальні часові мітки, наприклад, останні 100 записів
    timestamps = VehicleTimeSnapshot.objects.values_list('timestamp', flat=True) \
        .distinct().order_by('-timestamp')[:100]
    
    # Конвертуємо в список та розвертаємо, щоб найдавніші були зліва (0), а найновіші справа (100)
    data = sorted([t.isoformat() for t in timestamps])
    return JsonResponse(data, safe=False)



# ANALYTICS VIEWS

class AnalyticsDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'analytics_view/analytics_view.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        shipments = CargoShipment.objects.filter(is_active=True).select_related('vehicle__driver')
        
        vehicles_data = [
            {
                'driver_name': s.vehicle.driver.full_name if s.vehicle.driver else "Водій",
                'brand': s.vehicle.brand,
                'model': s.vehicle.model,
                'speed_last': s.speed_avg or 0,
                'lat': s.start_point.y,
                'lng': s.start_point.x,
                'color': getattr(s.vehicle, 'color', '#0d6efd')
            } for s in shipments
        ]
        context['initial_vehicles'] = json.dumps(vehicles_data, cls=DjangoJSONEncoder)
        return context


class AnalyticsFleetDataView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # 1. Створюємо підзапит для середньої швидкості
        avg_speed_subquery = CargoShipment.objects.filter(
            vehicle=OuterRef('vehicle'),
            is_active=False
        ).values('vehicle').annotate(
            avg=Avg('speed_avg')
        ).values('avg')

        # 2. Використовуємо його в основному запиті
        qs = DriverLocation.objects.filter(
            driver__is_active_driver=True,
            driver__is_verified=True,
        ).annotate(
            is_cargo_active=Exists(
                CargoShipment.objects.filter(vehicle=OuterRef('vehicle'), is_active=True)
            ),
            # Отримуємо середнє значення через підзапит
            avg_speed=Subquery(avg_speed_subquery)
        ).select_related('driver', 'vehicle')

        data = []
        for loc in qs:
            if not loc.vehicle or not loc.driver:
                continue
                
            data.append({
                'id': loc.driver.user.pk,
                'driver_name': loc.driver.name,
                'lat': loc.position.y,
                'lng': loc.position.x,
                'brand': getattr(loc.vehicle, 'brand', 'N/A'),
                'model': getattr(loc.vehicle, 'model', 'N/A'),
                'vehicle_id': loc.vehicle.id,
                'speed_last': getattr(loc.vehicle, 'speed_last', 0),
                'is_busy': getattr(loc, 'is_busy', False),
                'color': getattr(loc.vehicle, 'color', '#fd7e14').lower(),
                'heading': getattr(loc, 'heading', 0),
                'has_blown_tire': getattr(loc.vehicle, 'has_blown_tire', False),
                'has_low_fuel': getattr(loc.vehicle, 'has_low_fuel', False),
                'is_cargo_active': loc.is_cargo_active,
                'avg_speed': round(loc.avg_speed or 0, 1)
            })

        return Response(data)

class TopRoutesAPI(APIView):
    def post(self, request):
        data = request.data
        sw = data.get("southWest")
        ne = data.get("northEast")
        if not sw or not ne:
            return JsonResponse({"error": "Invalid data"}, status=400)

        try:
            min_lng, max_lng = sorted([float(sw["lng"]), float(ne["lng"])])
            min_lat, max_lat = sorted([float(sw["lat"]), float(ne["lat"])])
        except (ValueError, TypeError):
            return JsonResponse({"error": "Invalid coordinates"}, status=400)

        GRID_PRECISION = 3
        cell_groups = defaultdict(lambda: {
            "points": [],
            "shipment_ids": set(),
            "speed_sum": 0.0,
            "speed_count": 0,
            "counted_shipments": set(),
        })

        shipments = CargoShipment.objects.exclude(history__isnull=True).exclude(history={})
        logger.warning(f"DEBUG: знайдено {shipments.count()} shipments з історією")

        for s in shipments:
            logger.warning(f"DEBUG: shipment {s.id} speed_avg={s.speed_avg!r} (type={type(s.speed_avg)})")

            features = s.history.get("features", [])
            if not features and "geometry" in s.history:
                features = [s.history]

            for feature in features:
                geometry = feature.get("geometry", {})
                geo_type = geometry.get("type")
                coords = geometry.get("coordinates", [])
                if not coords:
                    continue

                flat_coords = []
                if geo_type == "Point":
                    flat_coords = [coords]
                elif geo_type == "LineString":
                    flat_coords = coords
                elif geo_type == "MultiLineString":
                    for line in coords:
                        flat_coords.extend(line)

                matched_points = 0
                for pt in flat_coords:
                    lng, lat = float(pt[0]), float(pt[1])
                    in_bbox = (min_lng <= lng <= max_lng) and (min_lat <= lat <= max_lat)
                    if not in_bbox:
                        continue
                    matched_points += 1

                    cell_key = (round(lng, GRID_PRECISION), round(lat, GRID_PRECISION))
                    group = cell_groups[cell_key]
                    group["points"].append((lng, lat))
                    group["shipment_ids"].add(s.id)

                    if s.id not in group["counted_shipments"]:
                        group["counted_shipments"].add(s.id)
                        if s.speed_avg and s.speed_avg > 0:
                            group["speed_sum"] += s.speed_avg
                            group["speed_count"] += 1
                            logger.warning(f"DEBUG: ✅ shipment {s.id} додав speed_avg={s.speed_avg} в комірку {cell_key}")
                        else:
                            logger.warning(f"DEBUG: ❌ shipment {s.id} НЕ додав швидкість (speed_avg={s.speed_avg!r})")

                logger.warning(f"DEBUG: shipment {s.id} мав {matched_points} точок у bbox")

        if not cell_groups:
            logger.warning("DEBUG: cell_groups порожній — жодна точка не потрапила в bbox")
            return JsonResponse({"message": "Даних немає"}, status=200)

        best_cell_key, best_group = max(
            cell_groups.items(),
            key=lambda kv: len(kv[1]["shipment_ids"])
        )

        logger.warning(f"DEBUG: best_cell={best_cell_key}, shipment_ids={best_group['shipment_ids']}, speed_sum={best_group['speed_sum']}, speed_count={best_group['speed_count']}")

        avg_speed = (
            best_group["speed_sum"] / best_group["speed_count"]
            if best_group["speed_count"] > 0 else 0
        )

        path = best_group["points"]
        lng, lat = best_cell_key

        street_name = "Невідома вулиця"
        try:
            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lng}&zoom=18"
            res = requests.get(url, headers={'User-Agent': 'TaxiAnalyticsApp/1.0'}, timeout=3)
            if res.status_code == 200:
                addr = res.json().get("address", {})
                street_name = addr.get("road") or addr.get("path") or "Невідома вулиця"
        except Exception:
            pass

        return JsonResponse({
            'path': path,
            'lat': lat,
            'lng': lng,
            'count': len(best_group["shipment_ids"]),
            'street': street_name,
            'avg_speed_on_route': round(avg_speed, 1)
        })




class CargoHotspotsAPI(APIView):
    def post(self, request):
        data = request.data
        sw = data.get('southWest')
        ne = data.get('northEast')
        
        if not sw or not ne:
            return JsonResponse({'error': 'Invalid data'}, status=400)

        # Створюємо багатокутник (bbox) з координат користувача
        bbox = Polygon.from_bbox((sw['lng'], sw['lat'], ne['lng'], ne['lat']))
        bbox.srid = 4326

        # Фільтруємо завантаження, де start_point знаходиться всередині bbox
        shipments = CargoShipment.objects.filter(start_point__contained=bbox)
        
        # Перетворюємо об'єкти в список координат
        hotspots = [
            {'lat': s.start_point.y, 'lng': s.start_point.x}
            for s in shipments if s.start_point
        ]
        
        return JsonResponse(hotspots, safe=False)


def transform_points_to_linestring(feature_collection):
    """
    Перетворює FeatureCollection з Point у FeatureCollection з одним LineString
    """
    features = feature_collection.get("features", [])
    if not features:
        return feature_collection

    # Витягуємо всі координати з точок
    coordinates = [f["geometry"]["coordinates"] for f in features if f["geometry"]["type"] == "Point"]
    
    # Створюємо нову структуру
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": coordinates
            },
            "properties": {"total_points": len(coordinates)}
        }]
    }

class RoutesInAreaAPI(APIView):
    def post(self, request):
        data = request.data
        sw = data.get("southWest")
        ne = data.get("northEast")

        if not sw or not ne:
            return JsonResponse({"error": "Invalid data"}, status=400)

        min_lng, max_lng = sorted([float(sw["lng"]), float(ne["lng"])])
        min_lat, max_lat = sorted([float(sw["lat"]), float(ne["lat"])])
        
        shipments = CargoShipment.objects.filter(start_point__isnull=False).extra(
            where=[
                "ST_X(start_point) >= %s AND ST_X(start_point) <= %s",
                "ST_Y(start_point) >= %s AND ST_Y(start_point) <= %s"
            ],
            params=[min_lng, max_lng, min_lat, max_lat]
        )
        
        # Обробляємо кожну історію
        processed_routes = []
        for s in shipments:
            if s.history:
                # Перевіряємо, чи це колекція точок, і трансформуємо, якщо треба
                if self._is_point_collection(s.history):
                    processed_routes.append(transform_points_to_linestring(s.history))
                else:
                    processed_routes.append(s.history)
        
        return JsonResponse(processed_routes, safe=False)

    def _is_point_collection(self, history):
        """Допоміжний метод для перевірки типу геометрії"""
        features = history.get("features", [])
        if features and features[0].get("geometry", {}).get("type") == "Point":
            return True
        return False


class CalculateIntersectionsAPI(APIView):
    def post(self, request):
        routes = request.data.get("routes", [])
        
        # 1. Перевірка кількості отриманих маршрутів
        print(f"DEBUG: Отримано {len(routes)} маршрутів.")
        
        geo_routes = []
        for index, item in enumerate(routes):
            try:
                features = item.get('features', [])
                if not features:
                    continue
                
                geometry = features[0].get('geometry', {})
                coords = geometry.get('coordinates')
                
                if coords and len(coords) >= 2:
                    geo_routes.append(LineString(coords))
                else:
                    print(f"DEBUG: Маршрут {index} не має валідних координат.")
                    
            except Exception as e:
                print(f"DEBUG: Помилка парсингу маршруту {index}: {e}")
        
        print(f"DEBUG: Сформовано {len(geo_routes)} об'єктів LineString.")
        
        intersections = []
        intersection_count = 0
        
        # 2. Дебаг циклу перетинів
        for i in range(len(geo_routes)):
            for j in range(i + 1, len(geo_routes)):
                if geo_routes[i].intersects(geo_routes[j]):
                    inter = geo_routes[i].intersection(geo_routes[j])
                    
                    if inter.geom_type == 'Point':
                        intersections.append({'lat': inter.y, 'lng': inter.x})
                        intersection_count += 1
                    elif inter.geom_type == 'MultiPoint':
                        for pt in inter:
                            intersections.append({'lat': pt.y, 'lng': pt.x})
                            intersection_count += 1
                    else:
                        print(f"DEBUG: Знайдено перетин типу {inter.geom_type} між {i} та {j}")
        
        print(f"DEBUG: Всього знайдено точок перетину: {intersection_count}")
                            
        return JsonResponse({"intersections": intersections})


def get_vehicle_avg_speed(vehicle_id):
    return CargoShipment.objects.filter(
        vehicle_id=vehicle_id, 
        is_active=False
    ).aggregate(total_avg=Avg('speed_avg'))['total_avg']

def get_avg_speed_view(request, vehicle_id):
    get_object_or_404(Vehicle, id=vehicle_id)
    avg_val = CargoShipment.objects.filter(
        vehicle_id=vehicle_id, 
        is_active=False
    ).aggregate(total_avg=Avg('speed_avg'))['total_avg']
    return JsonResponse({'avg_speed': float(avg_val)})

def get_cargo_start_points(request):
    # Отримуємо межі з запиту
    lat_min = float(request.GET.get('lat_min'))
    lat_max = float(request.GET.get('lat_max'))
    lng_min = float(request.GET.get('lng_min'))
    lng_max = float(request.GET.get('lng_max'))

    # Створюємо полігон області
    bbox = Polygon.from_bbox((lng_min, lat_min, lng_max, lat_max))

    # Використовуємо __within для вибірки точок у полігоні
    points = CargoShipment.objects.filter(start_point__within=bbox).annotate(
        lat=Y('start_point'),
        lng=X('start_point')
    ).values('lat', 'lng')
    
    return JsonResponse(list(points), safe=False)


def get_hotspots_api(request):
    # Беремо всі точки, де start_point задано
    hotspots = CargoShipment.objects.filter(start_point__isnull=False).annotate(
        lat=Y('start_point'),
        lng=X('start_point')
    ).values('lat', 'lng')
    
    # Можна додати intensity, якщо групувати точки (наприклад, Count)
    data = [{'lat': h['lat'], 'lng': h['lng'], 'intensity': 1} for h in hotspots]
    return JsonResponse(data, safe=False)

# ROUTES RIDES

class TaxiRequestView(LoginRequiredMixin, TemplateView):
	template_name = 'taxi_request.html'
	login_url = '/login/'
 
	def dispatch(self, request, *args, **kwargs):
		active_statuses = ['pending', 'accepted', 'in_progress']
		active_ride = Ride.objects.filter(
			client__user=request.user,
			status__in=active_statuses
		).first()
		if active_ride:
			return redirect('rides:taxi-map')
		return super().dispatch(request, *args, **kwargs)


class TaxiMapView(LoginRequiredMixin, TemplateView):
    template_name = 'taxi_map.html'
    
    def dispatch(self, request, *args, **kwargs):
        # ... (ваш існуючий код)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active_ride = Ride.objects.filter(
            client__user=self.request.user, 
            is_finished=False
        ).order_by('-created_at').first()
        
        if active_ride:
            context['ride'] = active_ride 
            context['ride_data'] = {
                'ride_id': active_ride.id,
                'from_addr': active_ride.pickup_address,
                'to_addr': active_ride.dropoff_address,
                'start_lat': active_ride.pickup_position.y if active_ride.pickup_position else None,
                'start_lng': active_ride.pickup_position.x if active_ride.pickup_position else None,
                'end_lat': active_ride.dropoff_position.y if active_ride.dropoff_position else None,
                'end_lng': active_ride.dropoff_position.x if active_ride.dropoff_position else None
            }
        return context


class SpeedSocketTestView(LoginRequiredMixin, FormView):
    template_name = 'speed_test.html'
    form_class = SpeedTestForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ride'] = get_object_or_404(Ride, id=self.kwargs.get('ride_id'))
        return context

    def form_valid(self, form):
        return super().form_valid(form)

@require_GET
@login_required
def get_ride_status(request):
    ride_id = request.GET.get('ride_id')
    if not ride_id or not ride_id.isdigit():
        return JsonResponse({'error': 'Invalid ride_id'}, status=400)
    
    ride = get_object_or_404(Ride, id=int(ride_id), client__user=request.user)
    return JsonResponse({
        'driver_id': ride.driver.user.id if ride.driver else None
    })

@require_POST
@login_required
def start_ride_view(request):
    import json
    data = json.loads(request.body)
    form = RideRequestForm(data)
    
    if form.is_valid():
        d = form.cleaned_data
        ride = Ride.objects.create(
            client=request.user.clientprofile,
            pickup_address=d['pickup_address'],
            dropoff_address=d['dropoff_address'],
            pickup_position=Point(d['pickup_lng'], d['pickup_lat']),
            dropoff_position=Point(d['dropoff_lng'], d['dropoff_lat']) if d.get('dropoff_lng') else None,
            status='pending',
            is_empty=True
        )
        return JsonResponse({'ride_id': ride.id, 'status': 'created'})
    
    return JsonResponse({'error': form.errors}, status=400)


@require_POST
@login_required
@ensure_csrf_cookie
def select_driver_view(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        ride_id = data.get('ride_id')
        driver_id = data.get('driver_id')
        vehicle_id = data.get('vehicle_id')
        
        if not all([ride_id, driver_id, vehicle_id]):
            return JsonResponse({'error': 'Missing parameters'}, status=400)
        ride = get_object_or_404(Ride, id=ride_id, client__user=request.user)
        driver = get_object_or_404(DriverProfile, user_id=driver_id)
        vehicle = get_object_or_404(Vehicle, id=vehicle_id)
        
        if vehicle.driver != driver:
            return JsonResponse({'error': 'Vehicle mismatch'}, status=400)

        ride.driver = driver
        ride.vehicle = vehicle
        ride.status = 'accepted'
        ride.is_empty = False
        ride.save()
        
        return JsonResponse({'status': 'success', 'driver_id': driver.id, 'vehicle_id': vehicle.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_POST
@login_required
@ensure_csrf_cookie
def start_ride_driver_arrived_view(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        ride_id = data.get('ride_id')
        if not ride_id:
            return JsonResponse({'error': 'Missing ride_id'}, status=400)
        ride = Ride.objects.select_for_update().get(id=ride_id, driver__user=request.user)
        if ride.status != 'accepted':
            return JsonResponse({'error': 'Ride cannot be started in current status'}, status=400)
        with transaction.atomic():
            ride.status = 'in_progress'
            ride.started_at = timezone.now()
            ride.history = {
                'type': 'FeatureCollection', 
                'features': [{
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [ride.driver_location.lng, ride.driver_location.lat]},
                    "properties": {"timestamp": timezone.now().isoformat()}
                }]
            }
            ride.save()
            RideRoute.objects.get_or_create(
                ride=ride, defaults={'history': {'type': 'FeatureCollection', 'features': []}}
            )
        return JsonResponse({
            'status': 'success', 
            'ride_id': ride.id,
            'started_at': ride.started_at
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@require_POST
@login_required
def cancel_driver_selection(request):
    try:
        data = json.loads(request.body.decode('utf-8'))
        ride_id = data.get('ride_id')
        
        if not ride_id:
            return JsonResponse({'error': 'Missing ride_id'}, status=400)
            
        ride = get_object_or_404(Ride, id=ride_id, client__user=request.user)
        ride.driver = None
        ride.vehicle = None
        ride.status = 'pending'
        ride.save()
        
        return JsonResponse({'status': 'cancelled'})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


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
    try:
        lat = request.GET.get('lat')
        lng = request.GET.get('lng')
        ride_id = request.GET.get('ride_id')
        
        active_driver_id = None
        if ride_id and ride_id.isdigit():
            ride = Ride.objects.filter(id=int(ride_id), client__user=request.user).first()
            if ride and ride.driver:
                active_driver_id = ride.driver.user.id

        if active_driver_id:
            drivers = DriverLocator.get_nearby_drivers(0, 0, driver_id=active_driver_id)
            return JsonResponse({'drivers': drivers})

        if lat and lng:
            lat, lng = float(lat), float(lng)
        else:
            loc = request.session.get('user_location')
            if not loc:
                return JsonResponse({'drivers': [], 'error': 'no_location'}, status=400)
            lat, lng = float(loc.get('lat')), float(loc.get('lng'))
        
        radius = float(request.GET.get('radius_km') or 5.0)
        drivers = DriverLocator.get_nearby_drivers(lat, lng, radius_km=radius)
        
        return JsonResponse({'drivers': drivers})
        
    except Exception as e:
        return JsonResponse({'drivers': [], 'error': str(e)}, status=500)


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
