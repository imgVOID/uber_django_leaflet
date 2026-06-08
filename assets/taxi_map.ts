
interface LocationCoords {
  lat: number;
  lng: number;
}

interface Driver {
  lat: number;
  lng: number;
  driver_name: string;
  distance_km: number;
  color: string;
}

interface RouteData {
  geometry: any;
}

declare const L: any;

const NOMINATIM_UA: string = 'UberDjangoLeafletMVP/1.0';

// Geocoding: converts text to coordinates
async function geocode(query: string): Promise<LocationCoords> {
  const coordMatch = query.trim().match(/^(-?\d+(?:\.\d+)?)[,\s]+(-?\d+(?:\.\d+)?)$/);
  if (coordMatch) {
    return { lat: parseFloat(coordMatch[1]), lng: parseFloat(coordMatch[2]) };
  }
  
  const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}`;
  const res = await fetch(url, { headers: { 'Accept-Language': 'en', 'User-Agent': NOMINATIM_UA } });
  const arr = await res.json();
  
  if (!arr || arr.length === 0) throw new Error('Location not found');
  return { lat: parseFloat(arr[0].lat), lng: parseFloat(arr[0].lon) };
}

// Route building through backend (proxy to OSRM)
async function osrmRoute(start: LocationCoords, end: LocationCoords): Promise<RouteData> {
  const url = `/taxi/osrm_route/?start_lat=${start.lat}&start_lng=${start.lng}&end_lat=${end.lat}&end_lng=${end.lng}`;
  const r = await fetch(url);
  if (!r.ok) throw new Error('Route request failed');
  return await r.json();
}

// Fetch list of drivers from Django backend
async function fetchNearbyDrivers(lat: number, lng: number, radius_km: number = 5): Promise<Driver[]> {
  const resp = await fetch(`/taxi/nearby_drivers/?lat=${lat}&lng=${lng}&radius_km=${radius_km}`);
  if (!resp.ok) return [];
  const data = await resp.json();
  return data.drivers || [];
}

// Control buttons creation
function createControlButtons(map: any, onOk: () => void, onEdit: () => void): void {
  const control = L.control({ position: 'topright' });
  control.onAdd = function() {
    const div = L.DomUtil.create('div', 'leaflet-control-custom');
    div.innerHTML = '<button id="okBtn" class="btn btn-success">Confirm Ride</button><button id="editBtn" class="btn btn-secondary">Edit</button>';
    return div;
  };
  control.addTo(map);
  
  setTimeout(() => {
    const okBtn = document.getElementById('okBtn');
    const editBtn = document.getElementById('editBtn');
    if (okBtn) okBtn.onclick = onOk;
    if (editBtn) editBtn.onclick = onEdit;
  }, 100);
}

// Main initialization
(async function(): Promise<void> {
  const raw = localStorage.getItem('last_taxi_request');
  if (!raw) { window.location.href = '/taxi/'; return; }
  
  const req = JSON.parse(raw);
  let start: LocationCoords, end: LocationCoords;
  
  try {
    start = await geocode(req.from);
    end = await geocode(req.to);
  } catch (err) {
    alert('Error resolving addresses.');
    window.location.href = '/taxi/';
    return;
  }

  const map = L.map('map').setView([start.lat, start.lng], 13);
  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png').addTo(map);

  L.marker([start.lat, start.lng]).addTo(map).bindPopup('Pickup');
  L.marker([end.lat, end.lng]).addTo(map).bindPopup('Destination');

  // 1. Add drivers to map
  const drivers = await fetchNearbyDrivers(start.lat, start.lng, 5);
  drivers.forEach((d: Driver) => {
    L.circleMarker([d.lat, d.lng], {
      radius: 8,
      color: '#ff00ff',
      weight: 3,
      fillColor: d.color,
      fillOpacity: 1
    })
    .addTo(map)
    .bindPopup(`<b>${d.driver_name}</b><br>Dist: ${d.distance_km} km`);
  });

  // 2. Add route
  try {
    const route = await osrmRoute(start, end);
    L.geoJSON(route.geometry, { style: { color: '#0d6efd', weight: 5 } }).addTo(map);
    map.fitBounds([ [start.lat, start.lng], [end.lat, end.lng] ]);
  } catch (e) { console.warn('Route failed', e); }

  createControlButtons(map, () => alert('Ride requested!'), () => window.location.href = '/taxi/');
})();
