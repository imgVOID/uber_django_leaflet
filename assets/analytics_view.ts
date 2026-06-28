import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet.heat';
import { getCsrfToken, createCarIcon, drawIntersections, updateButtonVisibility } from './utils/analytics_helpers';
import { map, intersectionsLayer } from './utils/map_init';
import { AnalyticsAPI } from './utils/api';
import { MarkerManager, SelectionManager } from './managers/analytics_managers';

// ==================== Main Logic ====================
document.addEventListener('DOMContentLoaded', async () => {
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png').addTo(map);

    const markerManager = new MarkerManager(map);
    const selectionManager = new SelectionManager(map, markerManager.getMarkersMap());
    const savedRoutes = localStorage.getItem('last_all_routes');
    const savedIntersections = localStorage.getItem('last_intersections');
    const savedPoint = localStorage.getItem('last_popular_point');
    const savedHeat = localStorage.getItem('last_heatmap_data');

    selectionManager.drawSavedSelection(map);

    if (savedIntersections) { drawIntersections(map, JSON.parse(savedIntersections)); }
    if (savedRoutes) {
        const geoJsonList = JSON.parse(savedRoutes);
        geoJsonList.forEach((geoData: any) => {
            L.geoJSON(geoData, {
                style: { color: '#ff7800', weight: 3, opacity: 0.6 }
            }).addTo(map);
        });
    }
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
    if (savedHeat) {
        const points = JSON.parse(savedHeat);
        (L as any).heatLayer(points.map((p: any) => [p.lat, p.lng]), {
            radius: 20, blur: 15, maxZoom: 13,
            gradient: { 0.4: 'blue', 0.65: 'lime', 0.85: 'yellow', 1.0: 'red' }
        }).addTo(map);
    }

    updateButtonVisibility(map);

    try {
        const drivers = await (await fetch('/analytics/fleet-data/')).json();
        drivers.forEach((d: any) => markerManager.add(d));
    } catch (e) { console.error(e); }

    // 1. btn-show-routes
    document.getElementById('btn-show-routes')?.addEventListener('click', async () => {
        const areaRaw = localStorage.getItem('analytics_selection_area');
        if (!areaRaw) return;
        try {
            const d = await AnalyticsAPI.getTopRoutes(JSON.parse(areaRaw));
            if (d.lat && d.lng) {
                map.eachLayer((l: any) => { if (l instanceof L.CircleMarker) map.removeLayer(l); });
                localStorage.setItem('last_popular_point', JSON.stringify(d));
                L.circleMarker([d.lat, d.lng], { radius: 10, color: '#198754', fillColor: '#198754', fillOpacity: 0.7 })
                    .addTo(map)
                    .bindPopup(`<div class="route-popup"><h6>${d.street}</h6><p>Кількість проїздів: <b>${d.count}</b></p><p>Сер. швидкість: <b>${d.avg_speed_on_route} км/год</b></p></div>`)
                    .openPopup();
            }
            updateButtonVisibility(map);
        } catch (e) { console.error("Помилка:", e); }
    });

    // 2. btn-show-heat
    document.getElementById('btn-show-heat')?.addEventListener('click', async () => {
        const areaRaw = localStorage.getItem('analytics_selection_area');
        if (!areaRaw) return;
        try {
            const points = await AnalyticsAPI.getHotspots(JSON.parse(areaRaw));
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

    // 3. btn-show-all-routes
    document.getElementById('btn-show-all-routes')?.addEventListener('click', async () => {
        const areaRaw = localStorage.getItem('analytics_selection_area');
        if (!areaRaw) return;
        try {
            const geoJsonList = await AnalyticsAPI.getRoutesInArea(JSON.parse(areaRaw));
            
            // Замість перебору карти:
            selectionManager.analyticsLayerGroup.clearLayers(); 

            geoJsonList.forEach((geoData: any) => {
                L.geoJSON(geoData, { style: { color: '#ff7800', weight: 3, opacity: 0.6 } })
                .addTo(selectionManager.analyticsLayerGroup); // <--- ДОДАЄМО СЮДИ
            });
            
            localStorage.setItem('last_all_routes', JSON.stringify(geoJsonList));
            updateButtonVisibility(map);
        } catch (e) { console.error("Помилка:", e); }
    });

    // 4. btn-show-intersections
    document.getElementById('btn-show-intersections')?.addEventListener('click', async () => {
        const savedRoutesRaw = localStorage.getItem('last_all_routes');
        if (!savedRoutesRaw) return;
        try {
            const data = await AnalyticsAPI.calculateIntersections(JSON.parse(savedRoutesRaw));
            const intersections = data.intersections || [];
            if (intersections.length > 0) {
                localStorage.setItem('last_intersections', JSON.stringify(intersections));
                drawIntersections(map, intersections);
            } else { alert("Перехресть не знайдено."); }
            updateButtonVisibility(map);
        } catch (e) { console.error("Помилка:", e); }
    });

    document.getElementById('btn-select-area')?.addEventListener('click', () => selectionManager.enableSelection());
    document.getElementById('btn-clear-selection')?.addEventListener('click', () => selectionManager.clearSelection(map));
});