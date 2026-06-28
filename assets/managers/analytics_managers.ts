
import L from 'leaflet';
import { intersectionsLayer } from '../utils/map_init';
import { createCarIcon, updateButtonVisibility } from '../utils/analytics_helpers';

// ==================== Managers ====================
export class MarkerManager {
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

export class SelectionManager {
    public readonly analyticsLayerGroup: L.LayerGroup;

    constructor(private map: L.Map, private allMarkers: Map<number, L.Marker>) {
        this.analyticsLayerGroup = L.layerGroup().addTo(map);
    }
    // Використовуємо групу для відображення
    public addAnalyticalLayer(layer: L.Layer) {
        this.analyticsLayerGroup.addLayer(layer);
    }

    enableSelection() {
        this.map.getContainer().style.cursor = 'crosshair';
        this.map.dragging.disable();
        this.map.once('mousedown', (e: any) => this.startSelection(e));
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
            }
            updateButtonVisibility(this.map);
        };

        this.map.on('mousemove', onMouseMove);
        document.addEventListener('mouseup', onMouseUp);
    }

    
    public clearSelection(map: L.Map) {
        localStorage.removeItem('analytics_selection_area');
        localStorage.removeItem('last_popular_point');
        localStorage.removeItem('last_heatmap_data');
        localStorage.removeItem('last_all_routes');
        localStorage.removeItem('last_intersections');

        this.allMarkers.forEach((marker) => marker.getElement()?.classList.remove('selected-marker'));

        intersectionsLayer?.clearLayers();

        map.eachLayer((l: any) => {
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