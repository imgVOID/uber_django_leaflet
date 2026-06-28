import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet.heat';

// ==================== Helpers ====================
function getCsrfToken(): string {
    return document.cookie.match(/csrftoken=([^;]+)/)?.[1] ?? '';
}

function createCarIcon(color: string, heading: number = 0): L.DivIcon {
    return L.divIcon({
        className: 'car-icon-marker',
        html: `<div style="font-size: 28px; color: ${color}; transform: rotate(${heading}deg);"><i class="bi-cursor-fill"></i></div>`,
        iconSize: [30, 30],
        iconAnchor: [15, 15],
    });
}

function updateButtonVisibility(map: L.Map) {
    const btnRoutes = document.getElementById('btn-show-routes');
    const btnHeat = document.getElementById('btn-show-heat');
    const btnAllRoutes = document.getElementById('btn-show-all-routes');
    const btnSelect = document.getElementById('btn-select-area');
    const btnClear = document.getElementById('btn-clear-selection');
    
    const hasArea = !!localStorage.getItem('analytics_selection_area');
    
    let hasHeat = false;
    let hasPopular = false;
    let hasGeoJson = false;
    let hasRectangle = false;

    map.eachLayer((l: any) => {
        if (l._heat) hasHeat = true;
        if (l instanceof L.CircleMarker && !(l as any)._icon) hasPopular = true;
        if (l instanceof L.GeoJSON) hasGeoJson = true;
        if (l instanceof L.Rectangle) hasRectangle = true;
    });

    // Кнопки аналітики (залежать від hasArea)
    if (btnRoutes) btnRoutes.style.display = (hasArea && !hasPopular) ? 'inline-block' : 'none';
    if (btnHeat) btnHeat.style.display = (hasArea && !hasHeat) ? 'inline-block' : 'none';
    if (btnAllRoutes) btnAllRoutes.style.display = (hasArea && !hasGeoJson) ? 'inline-block' : 'none';

    // Кнопки виділення
    // btn-select-area відображається, якщо НІЯКОГО прямокутника немає
    if (btnSelect) btnSelect.style.display = !hasRectangle ? 'inline-block' : 'none';
    // btn-clear-selection відображається, якщо прямокутник Є
    if (btnClear) btnClear.style.display = hasRectangle ? 'inline-block' : 'none';
}

// ==================== Managers ====================
class MarkerManager {
    private markers = new Map<number, L.Marker>();
    constructor(private map: L.Map) {}

    getMarkersMap(): Map<number, L.Marker> { return this.markers; }

    add(v: any): void {
        const marker = L.marker([v.lat, v.lng], {
            icon: createCarIcon(v.color || '#0d6efd', v.heading),
        }).addTo(this.map);

        marker.bindPopup(`
            <div class="vehicle-popup">
                <h6 class="mb-2">${v.brand} ${v.model}</h6>
                <div class="alert alert-light p-2 mb-0">
                    <small class="text-muted d-block">Сер. швидкість:</small>
                    <span class="fw-bold text-primary">${v.avg_speed} км/год</span>
                </div>
            </div>
        `);
        this.markers.set(v.vehicle_id, marker);
    }
}

class SelectionManager {
    constructor(private map: L.Map, private allMarkers: Map<number, L.Marker>) {}

    enableSelection() {
        this.map.getContainer().style.cursor = 'crosshair';
        this.map.dragging.disable();
        this.map.off('mousedown');
        this.map.on('mousedown', (e: any) => this.startSelection(e));
    }

    public drawSavedSelection(map: L.Map) {
        const areaRaw = localStorage.getItem('analytics_selection_area');
        if (!areaRaw) return;

        try {
            const area = JSON.parse(areaRaw);
            const bounds = L.latLngBounds(
                [area.southWest.lat, area.southWest.lng],
                [area.northEast.lat, area.northEast.lng]
            );
            L.rectangle(bounds, { color: '#0d6efd', weight: 1, fillOpacity: 0.1 }).addTo(map);
            
            this.allMarkers.forEach((marker) => {
                if (bounds.contains(marker.getLatLng())) {
                    marker.getElement()?.classList.add('selected-marker');
                }
            });
        } catch (e) { console.error("Помилка відновлення області:", e); }
    }

    public clearSelection(map: L.Map) {
        localStorage.removeItem('analytics_selection_area');
        localStorage.removeItem('last_popular_point');
        localStorage.removeItem('last_heatmap_data');
        localStorage.removeItem('last_all_routes'); 
        
        this.allMarkers.forEach((marker) => marker.getElement()?.classList.remove('selected-marker'));
        
        map.eachLayer((l: any) => {
            // Видаляємо всі типи шарів, які ми створюємо динамічно
            if (l instanceof L.Rectangle || 
                l instanceof L.Polyline || 
                l instanceof L.GeoJSON ||
                l._heat || 
                l instanceof L.CircleMarker) {
                map.removeLayer(l);
            }
        });
        updateButtonVisibility(map);
    }

    private startSelection(e: any) {
        L.DomEvent.preventDefault(e);
        this.clearSelection(this.map); 
        const startPoint = e.latlng;
        let rect: L.Rectangle;

        const onMouseMove = (moveE: any) => {
            if (rect) this.map.removeLayer(rect);
            rect = L.rectangle([startPoint, moveE.latlng], { color: '#0d6efd', weight: 1 }).addTo(this.map);
        };

        const onMouseUp = (upE: any) => {
            this.map.off('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
            this.map.dragging.enable();
            this.map.getContainer().style.cursor = '';
            if (rect) {
                this.filterMarkersInBounds(rect.getBounds());
                updateButtonVisibility(this.map);
            }
        };

        this.map.on('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
    }

    public filterMarkersInBounds(bounds: L.LatLngBounds) {
        localStorage.setItem('analytics_selection_area', JSON.stringify({
            southWest: bounds.getSouthWest(),
            northEast: bounds.getNorthEast()
        }));
        this.allMarkers.forEach((marker) => {
            if (bounds.contains(marker.getLatLng())) marker.getElement()?.classList.add('selected-marker');
            else marker.getElement()?.classList.remove('selected-marker');
        });
    }
}

// ==================== Main Logic ====================
document.addEventListener('DOMContentLoaded', async () => {
    const map = L.map('map').setView([50.4501, 30.5234], 13);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png').addTo(map);

    const markerManager = new MarkerManager(map);
    const selectionManager = new SelectionManager(map, markerManager.getMarkersMap());

    selectionManager.drawSavedSelection(map);

    const savedRoutes = localStorage.getItem('last_all_routes');
    if (savedRoutes) {
        const geoJsonList = JSON.parse(savedRoutes);
        geoJsonList.forEach((geoData: any) => {
            L.geoJSON(geoData, {
                style: { color: '#ff7800', weight: 3, opacity: 0.6 }
            }).addTo(map);
        });
    }

    const savedPoint = localStorage.getItem('last_popular_point');
    if (savedPoint) {
        const p = JSON.parse(savedPoint);
        let marker = L.circleMarker([p.lat, p.lng], { radius: 10, color: '#198754', fillColor: '#198754', fillOpacity: 0.7 })
            .addTo(map)
            .bindPopup(`
                <div class="route-popup">
                <h6>${p.street}</h6>
                <p>Кількість проїздів: <b>${p.count}</b></p>
                <p>Сер. швидкість: <b>${p.avg_speed_on_route} км/год</b></p>
            </div>`);
        marker.openPopup();
    }

    const savedHeat = localStorage.getItem('last_heatmap_data');
    if (savedHeat) {
        const points = JSON.parse(savedHeat);
        (L as any).heatLayer(points.map((p: any) => [p.lat, p.lng]), { 
            radius: 20, blur: 15, maxZoom: 13,
            gradient: { 0.4: 'blue', 0.65: 'lime', 0.85: 'yellow', 1.0: 'red' } 
        }).addTo(map);
    }
    updateButtonVisibility(map);
    try {
        const drivers = await (await fetch('/taxi/analytics/fleet-data/')).json();
        drivers.forEach((d: any) => markerManager.add(d));
    } catch (e) { console.error(e); }

    document.getElementById('btn-show-routes')?.addEventListener('click', async () => {
        const areaRaw = localStorage.getItem('analytics_selection_area');
        if (!areaRaw) return;
        const area = JSON.parse(areaRaw);
        try {
            const res = await fetch('/taxi/analytics/top-routes/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
                body: JSON.stringify(area)
            });
            const d = await res.json();
            if (d.lat && d.lng) {
                map.eachLayer((l: any) => { if (l instanceof L.CircleMarker) map.removeLayer(l); });
                localStorage.setItem('last_popular_point', JSON.stringify(d));
                L.circleMarker([d.lat, d.lng], { radius: 10, color: '#198754', fillColor: '#198754', fillOpacity: 0.7 })
                    .addTo(map)
                    .bindPopup(`
                        <div class="route-popup">
                            <h6>${d.street}</h6>
                            <p>Кількість проїздів: <b>${d.count}</b></p>
                            <p>Сер. швидкість: <b>${d.avg_speed_on_route} км/год</b></p>
                        </div>
                    `)
                    .openPopup();
            }
            updateButtonVisibility(map);
        } catch (e) { console.error("Помилка:", e); }
    });

    document.getElementById('btn-show-heat')?.addEventListener('click', async () => {
        const areaRaw = localStorage.getItem('analytics_selection_area');
        if (!areaRaw) return;
        try {
            const res = await fetch('/taxi/analytics/hotspots/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
                body: areaRaw
            });
            const points = await res.json();
            if (Array.isArray(points) && points.length > 0) {
                localStorage.setItem('last_heatmap_data', JSON.stringify(points));
                map.eachLayer((l: any) => { if (l._heat) map.removeLayer(l); });
                (L as any).heatLayer(points.map((p: any) => [p.lat, p.lng]), {
                    radius: 20, blur: 15, maxZoom: 13,
                    gradient: { 0.4: 'blue', 0.65: 'lime', 0.85: 'yellow', 1.0: 'red' }
                }).addTo(map);
            } else { alert("Немає даних для відображення."); }
            updateButtonVisibility(map);
        } catch (e) { console.error("Помилка:", e); }
    });
    document.getElementById('btn-show-all-routes')?.addEventListener('click', async () => {
        const areaRaw = localStorage.getItem('analytics_selection_area');
        if (!areaRaw) return;
        
        try {
            const res = await fetch('/taxi/analytics/routes-in-area/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken() },
                body: areaRaw
            });
            const geoJsonList = await res.json();

            // Очищаємо старі лінії
            map.eachLayer((l: any) => { if (l instanceof L.GeoJSON) map.removeLayer(l); });

            // Малюємо нові лінії
            geoJsonList.forEach((geoData: any) => {
                L.geoJSON(geoData, {
                    style: { color: '#ff7800', weight: 3, opacity: 0.6 }
                }).addTo(map);
            });

            localStorage.setItem('last_all_routes', JSON.stringify(geoJsonList));
            updateButtonVisibility(map); // Це приховає кнопку після натискання
        } catch (e) { console.error("Помилка:", e); }
    });

    document.getElementById('btn-select-area')?.addEventListener('click', () => selectionManager.enableSelection());
    document.getElementById('btn-clear-selection')?.addEventListener('click', () => selectionManager.clearSelection(map));
});