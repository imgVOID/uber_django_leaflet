import asyncio
import json
import websockets
import requests
import random

# --- КОНСТАНТИ ---
WS_URL = "ws://127.0.0.1:8000/ws/live-view/"

BASE_DATA = {
    "vehicle_id": 3,
    "speed": 45.5,
    "heading": 180.0,
    "altitude": 120.0,
    "accuracy": 5.0
}

def get_route_points(start_lat, start_lng, end_lat, end_lng, steps=10):
    # Використовуємо публічне API OSRM
    url = f"http://router.project-osrm.org/route/v1/driving/{start_lng},{start_lat};{end_lng},{end_lat}?overview=full&geometries=geojson"
    response = requests.get(url)
    data = response.json()
    
    if "routes" in data and data["routes"]:
        # Отримуємо всі координати маршруту (їх багато)
        coords = data["routes"][0]["geometry"]["coordinates"]
        
        # Розбиваємо на 'steps' рівномірних точок
        indices = [int(i * (len(coords) - 1) / (steps - 1)) for i in range(steps)]
        return [{"lat": coords[i][1], "lng": coords[i][0]} for i in indices]
    return []

async def run_driver_client():
    # Координати старт/фініш
    start = {"lat": 50.4423890, "lng": 30.4299749}
    end = {"lat": 50.4474466, "lng": 30.4410307}
    
    # Отримуємо 10 точок маршруту
    route_points = get_route_points(start["lat"], start["lng"], end["lat"], end["lng"], steps=10)
    
    async with websockets.connect(WS_URL) as websocket:
        print(f"Connected. Route points: {len(route_points)}")
        
        while True:
            for point in route_points:
                payload = {
                    "vehicle_id": BASE_DATA["vehicle_id"],
                    "lat": point["lat"],
                    "lng": point["lng"],
                    "heading": 270.0,
                    "speed": 80.0 - float(random.randint(0, 10)),
                    "accuracy": 4.2
                }
                
                await websocket.send(json.dumps(payload))
                print(f"Sent: {payload['lat']}, {payload['lng']}")
                await asyncio.sleep(3)

if __name__ == "__main__":
    try:
        asyncio.run(run_driver_client())
    except KeyboardInterrupt:
        print("Client stopped.")
