import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.gis.geos import Point
from accounts.models import DriverProfile
from vehicles.models import Vehicle
from .models import DriverLocation, Ride, RideRoute, CargoShipment
from django.utils import timezone

logger = logging.getLogger(__name__)


class LiveViewConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        """Викликається при підключенні клієнта."""
        await self.accept()
        # Додаємо клієнта до групи, щоб він отримував оновлення в реальному часі
        await self.channel_layer.group_add("drivers_broadcast", self.channel_name)

    async def disconnect(self, close_code):
        """Викликається при відключенні клієнта."""
        await self.channel_layer.group_discard("drivers_broadcast", self.channel_name)

    async def receive_json(self, data):
        """Обробка вхідних даних від GPS-трекера."""
        try:
            vehicle_id = data.get('vehicle_id')
            lat = data.get('lat')
            lng = data.get('lng')
            speed = data.get('speed', 0)
            
            vehicle = await Vehicle.objects.filter(pk=vehicle_id).select_related('driver').afirst()
            vehicle.speed_last = speed
            await vehicle.asave(update_fields=['speed_last'])
            
            await DriverLocation.objects.filter(driver_id=vehicle.driver_id).aupdate(
                position=Point(float(lng), float(lat), srid=4326),
                speed=speed,
                heading=data.get('heading'),
                accuracy=data.get('accuracy')
            )

            cargo = await CargoShipment.objects.filter(
                driver_id=vehicle.driver_id, 
                vehicle_id=vehicle_id, 
                is_active=True
            ).afirst()
            if cargo:
                logger.info(f"Знайдено вантаж: ID={cargo.id}, Vehicle={cargo.vehicle_id}")
            else:
                logger.info("Вантаж не знайдено.")

            if cargo:
                new_feature = {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [float(lng), float(lat)]},
                    "properties": {
                        "speed": speed,
                        "altitude": data.get('altitude', 0),
                        "timestamp": timezone.now().isoformat()
                    }
                }
                history = dict(cargo.history) if cargo.history else {"type": "FeatureCollection", "features": []}
                history.setdefault('features', []).append(new_feature)
                
                cargo.history = history
                await cargo.asave(update_fields=['history'])

            # Трансляція оновлення
            await self.channel_layer.group_send(
                "drivers_broadcast",
                {
                    "type": "driver.location.update",
                    "driver_id": str(vehicle.driver_id),
                    "vehicle_id": int(vehicle.id),
                    "lat": lat,
                    "lng": lng,
                    "last_speed": speed,
                    "is_cargo_active": cargo is not None
                }
            )

        except Exception as e:
            logger.error(f"Tracking error: {e}")
    
    async def driver_location_update(self, event):
        """Метод, що відправляє дані в сокет кожного клієнта групи."""
        await self.send_json(event)


class DriverTrackingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            driver_id = data.get('driver_id')
            lat, lng = data.get('lat'), data.get('lng')
            
            if not driver_id or lat is None or lng is None:
                return

            # Знаходимо водія (використовуємо pk замість id)
            driver = await DriverProfile.objects.select_related('user').aget(pk=driver_id)
            
            # Отримуємо активний автомобіль (необхідно для DriverLocation)
            vehicle = await driver.vehicles.afirst()
            if not vehicle:
                return
            
            if vehicle:
                vehicle.speed_last = data.get('speed')
                await vehicle.asave(update_fields=['speed_last'])

            # 1. Оновлюємо DriverLocation
            await DriverLocation.objects.filter(driver=driver).aupdate(
                position=Point(float(lng), float(lat), srid=4326),
                speed=data.get('speed'),
                heading=data.get('heading'),
                accuracy=data.get('accuracy')
            )

            # 2. Логіка історії: дописуємо ТІЛЬКИ якщо є поїздка ТА вже існує RideRoute
            active_ride = await Ride.objects.filter(driver=driver, status='in_progress').afirst()
            if active_ride:
                # Шукаємо ТІЛЬКИ існуючий запис
                route = await RideRoute.objects.filter(ride=active_ride).afirst()
                
                if route and route.history and 'features' in route.history:
                    feature = route.history['features'][0]
                    # Перевіряємо структуру перед додаванням
                    if 'geometry' in feature and 'coordinates' in feature['geometry']:
                        feature['geometry']['coordinates'].append([float(lng), float(lat)])
                        feature['properties']['times'].append(timezone.now().isoformat())
                        await route.asave(update_fields=['history'])

            # 3. Пуш оновлення всім клієнтам
            await self.channel_layer.group_send(
                "drivers_broadcast",
                {
                    "type": "driver.location.update",
                    "driver_id": driver_id,
                    "lat": lat,
                    "lng": lng,
                    "last_speed": data.get('speed', 0),
                    "heading": data.get('heading', 0)
                }
            )

        except Exception as e:
            logger.error(f"Tracking error: {e}")


class RideMapConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Підписуємо клієнта на оновлення всіх водіїв
        await self.channel_layer.group_add("drivers_broadcast", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("drivers_broadcast", self.channel_name)

    async def driver_location_update(self, event):
        await self.send(text_data=json.dumps(event))
