// ==================== Interfaces ====================
import L from 'leaflet';
import { LocationCoords, Driver } from './types/taxi';

// ==================== API Service ====================
const API = {
    getCsrfToken(): string {
        const meta = document.querySelector('meta[name="csrf-token"]');
        const metaToken = meta ? (meta as HTMLMetaElement).content : '';
        if (metaToken && metaToken !== 'NOTPROVIDED') return metaToken;
        const match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? match[1] : '';
    },

    async getRoute(start: LocationCoords, end: LocationCoords) {
        const res = await fetch(`/osrm_route/?start_lat=${start.lat}&start_lng=${start.lng}&end_lat=${end.lat}&end_lng=${end.lng}`);
        return res.ok ? await res.json() : null;
    },

    async getDrivers(lat: number, lng: number): Promise<Driver[]> {
        const rideId = window.rideData?.ride_id;
        let url = `/nearby_drivers/?lat=${lat}&lng=${lng}&radius_km=5`;
        if (rideId) url += `&ride_id=${rideId}`;
        const res = await fetch(url);
        return res.ok ? (await res.json()).drivers || [] : [];
    },

    async selectDriver(rideId: number, driverId: number, vehicleId: number): Promise<boolean> {
        const res = await fetch(`//select_driver/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': this.getCsrfToken() },
            body: JSON.stringify({ ride_id: rideId, driver_id: driverId, vehicle_id: vehicleId }),
        });
        return res.ok;
    },

    async cancelDriver(rideId: number): Promise<boolean> {
        const res = await fetch(`//cancel_driver/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': this.getCsrfToken() },
            body: JSON.stringify({ ride_id: rideId }),
        });
        return res.ok;
    }
};

// ==================== Interfaces ====================

declare global {
    interface Window {
        rideData: {
            from: string;
            to: string;
            ride_id: number;
            startLat?: number;
            startLng?: number;
            endLat?: number;
            endLng?: number;
            driver_id?: number | null;
        };
    }
}

// ==================== Map Helpers ====================
const createCarIcon = (color: string, heading: number = 0) => L.divIcon({
    className: 'car-icon-marker',
    html: `<div style="font-size: 28px; color: ${color}; filter: drop-shadow(0px 0px 2px rgba(0,0,0,0.75)); transform: rotate(${heading}deg);"><i class="bi-cursor-fill"></i></div>`,
    iconSize: [30, 30], iconAnchor: [15, 15]
});

const createPointIcon = (iconClass: string, color: string) => L.divIcon({
    className: 'point-icon',
    html: `<div style="font-size: 24px; color: ${color};"><i class="${iconClass}"></i></div>`,
    iconSize: [24, 24], iconAnchor: [12, 12]
});

const getStatusIcon = (condition: boolean, iconTrue: string, iconFalse: string) => 
    `<i class="bi ${condition ? iconTrue : iconFalse}" style="color: ${condition ? 'red' : 'green'}; font-size: 1.2rem; margin-right: 5px;"></i>`;

const popupContent = (title: string, colorClass: string, locationName: string, coords: [number, number]) => `
        <div class="p-2">
            <div class="d-flex align-items-center mb-2">
                <i class="bi bi-geo-alt-fill ${colorClass} me-2" style="font-size: 1.2rem;"></i>
                <h6 class="mb-0 ${colorClass}">${title}</h6>
            </div>
            <div class="small text-muted border-top pt-2">
                <div class="fw-bold text-dark">${locationName}</div>
                <div class="text-secondary mt-1">${coords[0].toFixed(5)}, ${coords[1].toFixed(5)}</div>
            </div>
        </div>`;

const renderContent = (d: any, isSelected: boolean) => `
                <div class="driver-popup">
                    <h6 class="text-primary"><u>${d.driver_name}</u></h6>
                    <ul class="list-unstyled small">
                        <li><b>${d.brand} ${d.model}</b> (${d.year})</li>
                        <li><i class="bi bi-circle-fill" style="color: ${d.color}; font-size: 0.8rem; filter: drop-shadow(0 0 0.5px #000);"></i> • <b>${d.vehicle_type}</b> на <b>${d.capacity}</b> ${d.capacity < 5 ? 'місця' : 'місць'}</li>
                        <li><b id="speed-${d.id}">${d.speed_last}</b> км/год</li>
                        <li class="status-row mt-2">
                            <span>${getStatusIcon(d.has_blown_tire, 'bi-exclamation-triangle-fill', 'bi-check-circle-fill')} Шини</span>
                            <span>${getStatusIcon(d.has_low_fuel, 'bi-fuel-pump-fill', 'bi-fuel-pump-fill')} Паливо</span>
                        </li>
                    </ul>
                    <button id="btn-${d.id}" class="btn btn-sm ${isSelected ? 'btn-danger' : 'btn-primary'} w-100">
                        ${isSelected ? 'Скасувати' : 'Вибрати'}
                    </button>
                </div>
            `;

const addClosePopupsControl = (map: L.Map) => {
    const Control = L.Control.extend({
        onAdd: function() {
            const container = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
            const btn = L.DomUtil.create('a', '', container);
            
            btn.innerHTML = `<i class="bi bi-x-lg" style="margin-right: 5px;"></i> Закрити все`;
            btn.title = 'Закрити всі вікна';
            
            btn.style.cssText = `
                cursor: pointer;
                background-color: white;
                display: flex;
                align-items: center;
                padding: 8px 15px;
                font-weight: bold;
                color: red;
                text-decoration: none;
                width: auto;
                height: auto;
                line-height: normal;
            `;
            
            btn.onclick = (e) => {
                e.preventDefault();
                map.eachLayer(l => {
                    if (l instanceof L.Popup) {
                        map.removeLayer(l);
                    }
                });
            };
            return container;
        }
    });

    map.addControl(new Control({ position: 'bottomright' }));
};

// ==================== Main Logic ====================
document.addEventListener('DOMContentLoaded', async () => {
    const { startLat, startLng, endLat, endLng, from, to, ride_id } = window.rideData;

    // 1. Початковий статус
    const statusRes = await fetch(`/status/?ride_id=${ride_id}`);
    if (statusRes.ok) window.rideData.driver_id = (await statusRes.json()).driver_id;

    const map = L.map('map', { closePopupOnClick: false }).setView([startLat!, startLng!], 14);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png').addTo(map);

    addClosePopupsControl(map);

    const route = await API.getRoute(
        { lat: startLat!, lng: startLng! }, 
        { lat: endLat!, lng: endLng! }
    );

    if (route?.geometry) {
        L.geoJSON(route.geometry, { 
            style: { color: '#0d6efd', weight: 6, opacity: 0.7 } 
        }).addTo(map);
    }

    // Точки Pickup / Dropoff
    L.marker([startLat!, startLng!], { icon: createPointIcon('bi-geo-alt-fill', '#198754') })
        .addTo(map)
        .bindPopup(popupContent('Відправлення', 'text-success', from!, [startLat!, startLng!]));

    L.marker([endLat!, endLng!], { icon: createPointIcon('bi-stop-circle-fill', '#dc3545') })
        .addTo(map)
        .bindPopup(popupContent('Призначення', 'text-danger', to!, [endLat!, endLng!]));
    
    const pathLayer = L.polyline([], { color: '#0d6efd', weight: 4, dashArray: '5, 10' }).addTo(map);
    const driverLayer = L.layerGroup().addTo(map);

    const driverMarkers: Record<number, L.Marker> = {};
    const activePopups: Record<number, L.Popup> = {};
    const getSavedPath = (id: number): [number, number][] => {
            const saved = localStorage.getItem(`path_${id}`);
            return saved ? JSON.parse(saved) : [];
        };
    const savePath = (id: number, path: [number, number][]) => {
        localStorage.setItem(`path_${id}`, JSON.stringify(path.slice(-50))); // зберігаємо останні 50 точок
    };
    if (window.rideData.driver_id) {
        pathLayer.setLatLngs(getSavedPath(window.rideData.driver_id));
    }
    const refreshDrivers = async () => {
        const drivers = await API.getDrivers(startLat!, startLng!);
        driverLayer.clearLayers();

        drivers.forEach(d => {
            const isSelected = window.rideData.driver_id === d.id;
            const marker = L.marker([d.lat, d.lng], { icon: createCarIcon(d.color, d.heading || 0) }).addTo(driverLayer);

            marker.on('click', () => {
                if (activePopups[d.id]) return;
                const latLng = marker.getLatLng(); 
                const popup = L.popup({ autoClose: false, closeOnClick: false })
                    .setLatLng(latLng)
                    .setContent(renderContent(d, window.rideData.driver_id === d.id))
                    .openOn(map);
                activePopups[d.id] = popup;
                popup.on('remove', () => delete activePopups[d.id]);
                document.getElementById(`btn-${d.id}`)?.addEventListener('click', async () => {
                    const isNowSelected = window.rideData.driver_id === d.id;
                    const success = isNowSelected ? await API.cancelDriver(ride_id) : await API.selectDriver(ride_id, d.id, d.vehicle_id);
                    if (success) {
                        window.rideData.driver_id = isNowSelected ? null : d.id;
                        pathLayer.setLatLngs([]); // Стираємо шлях на карті
                        if (isNowSelected) localStorage.removeItem(`path_${d.id}`); // Очищаємо локалсторадж
                        await refreshDrivers();
                        map.eachLayer(l => l instanceof L.Popup && map.removeLayer(l));
                    }
                });
            });
            driverMarkers[d.id] = marker;
            if (isSelected) marker.fire('click');
        });
    };

    await refreshDrivers();

    // 3. WebSocket
    const socket = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/map/updates/`);
    socket.onmessage = (e) => {
        const data = JSON.parse(e.data);
        const { driver_id, lat, lng, heading, last_speed } = data;
        const marker = driverMarkers[driver_id];

        if (marker) {
            marker.setLatLng([lat, lng]);
            marker.setIcon(createCarIcon('#0d6efd', heading));

            // Логіка шляху
            if (driver_id === window.rideData.driver_id) {
                const path = getSavedPath(driver_id);
                path.push([lat, lng]);
                savePath(driver_id, path);
                pathLayer.setLatLngs(path);
            }

            if (activePopups[driver_id]) {
                activePopups[driver_id].setLatLng([lat, lng]);
                const speedEl = document.getElementById(`speed-${driver_id}`);
                if (speedEl) speedEl.textContent = `${last_speed}`;
            }
        } else {
            refreshDrivers();
        }
    };
});