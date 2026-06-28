
// ==================== Helpers ====================
import L from 'leaflet';
import { intersectionsLayer } from './map_init';

export function getCsrfToken(): string {
    return document.cookie.match(/csrftoken=([^;]+)/)?.[1] ?? '';
}

export function createCarIcon(color: string, heading: number = 0): L.DivIcon {
    return L.divIcon({
        className: 'car-icon-marker',
        html: `<div style="font-size: 28px; color: ${color}; transform: rotate(${heading}deg);"><i class="bi-cursor-fill"></i></div>`,
        iconSize: [30, 30],
        iconAnchor: [15, 15],
    });
}


export function drawIntersections(map: L.Map, intersections: { lat: number; lng: number }[]) {
    intersectionsLayer.clearLayers();

    intersections.forEach((pt) => {
        L.circleMarker([pt.lat, pt.lng], {
            radius: 6,
            color: '#dc3545',
            fillColor: '#dc3545',
            fillOpacity: 0.9,
            weight: 2,
        })
            .bindPopup(`
                <div class="intersection-popup">
                    <b>Перехрестя маршрутів</b><br>
                    Lat: ${pt.lat.toFixed(5)}<br>
                    Lng: ${pt.lng.toFixed(5)}
                </div>
            `)
            .addTo(intersectionsLayer);
    });
}

export function updateButtonVisibility(map: L.Map) {
    const btnRoutes = document.getElementById('btn-show-routes');
    const btnHeat = document.getElementById('btn-show-heat');
    const btnAllRoutes = document.getElementById('btn-show-all-routes');
    const btnIntersections = document.getElementById('btn-show-intersections');
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

    const hasIntersections = intersectionsLayer && intersectionsLayer.getLayers().length > 0;

    // Кнопки аналітики (залежать від hasArea)
    if (btnRoutes) btnRoutes.style.display = (hasArea && !hasPopular) ? 'inline-block' : 'none';
    if (btnHeat) btnHeat.style.display = (hasArea && !hasHeat) ? 'inline-block' : 'none';
    if (btnAllRoutes) btnAllRoutes.style.display = (hasArea && !hasGeoJson) ? 'inline-block' : 'none';

    // Кнопка інтерсекшенів з'являється ЛИШЕ якщо маршрути (геоJSON) вже
    // намальовані, і інтерсекшени ще не показані
    if (btnIntersections) {
        btnIntersections.style.display = (hasGeoJson && !hasIntersections) ? 'inline-block' : 'none';
    }

    // Кнопки виділення
    if (btnSelect) btnSelect.style.display = !hasRectangle ? 'inline-block' : 'none';
    if (btnClear) btnClear.style.display = hasRectangle ? 'inline-block' : 'none';
}