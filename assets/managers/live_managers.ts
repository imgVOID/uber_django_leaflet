import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

import { HistoricalSnapshot } from '../types/live';
import { Vehicle } from '../types/live';
import { createCarIcon } from '../utils/live_helpers';
import { CONFIG, SELECTORS } from '../utils/live_constants';
import { FleetApi } from '../utils/api';


// ==================== MarkerManager ====================
export class MarkerManager {
  private markers = new Map<number, L.Marker>();
  private polylines = new Map<number, L.Polyline>(); // <--- ДОДАТИ ЦЕ

  constructor(private map: L.Map, private onMarkerClick: (v: Vehicle) => void) {}

  add(v: Vehicle): void {
    if (this.markers.has(v.vehicle_id)) return;

    const marker = L.marker([v.lat, v.lng], {
      icon: createCarIcon(v.color || '#0d6efd', v.heading),
    }).addTo(this.map);

    marker.on('click', () => this.onMarkerClick(v));
    this.markers.set(v.vehicle_id, marker);

    // ВІДНОВЛЕННЯ ЛІНІЇ ПРИ ЗАВАНТАЖЕННІ
    const savedRoute = localStorage.getItem(`route_${v.vehicle_id}`);
    if (savedRoute && v.is_cargo_active) {
      const points = JSON.parse(savedRoute);
      const poly = L.polyline(points, { color: 'red', weight: 4 }).addTo(this.map);
      this.polylines.set(v.vehicle_id, poly);
    }
  }

  // ОНОВЛЕНИЙ МЕТОД UPDATE
  updatePosition(vehicleId: number, lat: number, lng: number, isCargoActive: boolean, isRewind: boolean = false): void {
    const marker = this.markers.get(vehicleId);
    if (!marker) return;

    marker.setLatLng([lat, lng]);

    // Якщо ми в режимі Rewind, ми просто рухаємо маркер, НЕ записуємо маршрут
    if (!isRewind && isCargoActive) {
        this.updateRoute(vehicleId, [lat, lng]);
    } else if (!isRewind) {
        this.clearRoute(vehicleId);
    }
}

  resetToLive(vehicles: Vehicle[]) {
    this.markers.forEach((marker, id) => {
        const v = vehicles.find(veh => veh.vehicle_id === id);
        if (v) marker.setLatLng([v.lat, v.lng]);
    });
  }

  private updateRoute(vehicleId: number, latLng: [number, number]): void {
    const key = `route_${vehicleId}`;
    const route = JSON.parse(localStorage.getItem(key) || '[]');
    route.push(latLng);
    localStorage.setItem(key, JSON.stringify(route));

    if (!this.polylines.has(vehicleId)) {
      const poly = L.polyline(route, { color: 'red', weight: 4 }).addTo(this.map);
      this.polylines.set(vehicleId, poly);
    } else {
      this.polylines.get(vehicleId)!.setLatLngs(route);
    }
  }

  private clearRoute(vehicleId: number): void {
    localStorage.removeItem(`route_${vehicleId}`);
    if (this.polylines.has(vehicleId)) {
      this.map.removeLayer(this.polylines.get(vehicleId)!);
      this.polylines.delete(vehicleId);
    }
  }

  has(vehicleId: number): boolean { return this.markers.has(vehicleId); }
}


export class RewindController {
  private timestamps: string[] = [];
  private debounceTimer: ReturnType<typeof setTimeout> | null = null;
  isRewinding = false;

  constructor(
    private markerManager: MarkerManager,
    private onSnapshot: (h: HistoricalSnapshot) => void,
    private setCargoButtonsDisabled: (disabled: boolean) => void,
  ) {}

  async init(): Promise<void> {
    const res = await fetch(CONFIG.timestampsEndpoint);
    this.timestamps = await res.json();

    const slider = this.getSlider();
    if (!slider) return;

    slider.max = (this.timestamps.length - 1).toString();
    slider.value = slider.max;

    slider.addEventListener('input', (e) => this.onSliderInput(e));
  }

  setupHistoryToggle(): void {
    const showBtn = document.getElementById(SELECTORS.showHistoryBtn);
    const hideBtn = document.getElementById(SELECTORS.hideHistoryBtn);
    const historyContainer = document.getElementById(SELECTORS.historyContainer);
    const slider = this.getSlider();

    showBtn?.addEventListener('click', () => {
      if (historyContainer) historyContainer.style.display = 'block';
      if (showBtn) showBtn.style.display = 'none';
      if (slider) {
        slider.value = slider.max;
        this.applyMode(slider.value);
      }
    });

    hideBtn?.addEventListener('click', () => {
      if (historyContainer) historyContainer.style.display = 'none';
      if (showBtn) showBtn.style.display = 'block';
      this.applyMode('live');
    });
  }

  private onSliderInput(e: Event): void {
    const val = (e.target as HTMLInputElement).value;
    if (this.debounceTimer) clearTimeout(this.debounceTimer);
    this.debounceTimer = setTimeout(() => this.applyMode(val), CONFIG.rewindDebounceMs);
  }

  private getSlider(): HTMLInputElement | null {
    return document.getElementById(SELECTORS.timeSlider) as HTMLInputElement | null;
  }

  async applyMode(val: string): Promise<void> {
    const slider = this.getSlider();
    const isLive = val === 'live' || (slider !== null && val === slider.max);

    if (isLive) {
      await this.switchToLive();
      return;
    }

    const timestamp = this.timestamps[parseInt(val, 10)];
    if (timestamp) await this.switchToRewind(timestamp);
  }

  private async switchToLive(): Promise<void> {
    this.setMode(false, 'Live', 'none');
    const vehicles = await FleetApi.fetchVehicles();
    this.markerManager.resetToLive(vehicles);
  }

  private async switchToRewind(timestamp: string): Promise<void> {
    this.setMode(true, timestamp, 'grayscale(50%)');

    const res = await fetch(CONFIG.historyEndpoint(timestamp));
    if (!res.ok) return;

    const snapshot: HistoricalSnapshot[] = await res.json();
    snapshot.forEach((h) => {
      if (this.markerManager.has(h.vehicle_id)) {
        this.markerManager.updatePosition(h.vehicle_id, h.lat, h.lng, h.is_cargo_active, true);
        this.onSnapshot(h);
      }
    });
  }

  private setMode(rewinding: boolean, displayText: string, mapFilter: string): void {
    this.isRewinding = rewinding;
    this.setCargoButtonsDisabled(rewinding);

    const display = document.getElementById(SELECTORS.timeDisplay);
    if (display) display.textContent = displayText;

    const mapEl = document.getElementById(SELECTORS.map);
    if (mapEl) mapEl.style.filter = mapFilter;
  }
}