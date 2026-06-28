import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { LiveUpdateMessage, ToggleCargoResponse, Vehicle } from './types/live';
import { CONFIG, SELECTORS } from './utils/live_constants';
import { InfoPanel } from './utils/live_info_panel';
import { createCarIcon, getCsrfToken } from './utils/live_helpers';
import { LiveSocket } from './utils/live_socket';

// ==================== Types ====================
declare global {
  interface Window { liveMapInstance: LiveViewMap; }
}

// ==================== FleetApi ====================
class FleetApi {
  static async fetchVehicles(): Promise<Vehicle[]> {
    const res = await fetch(CONFIG.fleetEndpoint, {
      method: 'GET',
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
    });
    if (!res.ok) throw new Error(`Fleet fetch failed: ${res.status}`);
    return res.json();
  }

  static async toggleCargo(vehicleId: number): Promise<ToggleCargoResponse> {
    const res = await fetch(CONFIG.toggleCargoEndpoint(vehicleId), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
      },
    });
    if (!res.ok) throw new Error(`Toggle cargo failed: ${res.status}`);
    return res.json();
  }
}

// ==================== MarkerManager ====================
class MarkerManager {
  private markers = new Map<number, L.Marker>();
  private polylines = new Map<number, L.Polyline>();

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

// ==================== LiveViewMap ====================
class LiveViewMap {
  private map: L.Map;
  private markerManager: MarkerManager;
  private infoPanel: InfoPanel;
  private socket: LiveSocket;
  private isRewinding: boolean = false;
  private timestamps: string[] = [];

  constructor() {
        this.map = L.map('map', { closePopupOnClick: false }).setView(CONFIG.mapCenter, CONFIG.mapZoom);
        L.tileLayer(CONFIG.tileUrl).addTo(this.map);

        this.infoPanel = new InfoPanel(document.getElementById(SELECTORS.infoPanels)!);
        this.markerManager = new MarkerManager(this.map, (v) => this.infoPanel.toggle(v));
        this.socket = new LiveSocket((data) => this.handleLiveUpdate(data));

        this.loadInitialVehicles();
        this.fetchTimestamps();
        this.setupRewind();
        this.setupHistoryControls();
    }
    private async fetchTimestamps() {
        const res = await fetch('/live/timestamps/');
        this.timestamps = await res.json();
        const slider = document.getElementById(SELECTORS.timeSlider) as HTMLInputElement;
        if (slider) {
            slider.max = (this.timestamps.length - 1).toString();
            slider.value = slider.max; // Ставимо на "Live"
        }
    }
    private setupHistoryControls() {
        const showBtn = document.getElementById('btn-show-history');
        const hideBtn = document.getElementById('btn-hide-history');
        const historyContainer = document.getElementById('history-container');

        showBtn?.addEventListener('click', () => {
            historyContainer!.style.display = 'block';
            showBtn!.style.display = 'none';
            
            const slider = document.getElementById(SELECTORS.timeSlider) as HTMLInputElement;
            slider.value = slider.max;
            this.applyMode(slider.max);
        });

        hideBtn?.addEventListener('click', () => {
            historyContainer!.style.display = 'none';
            showBtn!.style.display = 'block';
            this.applyMode("live");
        });
    }
    
    private updateAllButtonsState(disabled: boolean): void {
        const buttons = document.querySelectorAll('.vehicle-info-card button[id^="btn-cargo-"]');
        buttons.forEach((btn) => {
            (btn as HTMLButtonElement).disabled = disabled;
        });
    }
    private async onRewind(timestamp: string) {
        this.isRewinding = true;
        
        // Кодуємо параметр часу для правильної передачі символу '+'
        const response = await fetch(`/live/get-time-rec/?time=${encodeURIComponent(timestamp)}`);
        if (!response.ok) return;

        const historicalData: any[] = await response.json();
        historicalData.forEach((h) => {
            if (this.markerManager.has(h.vehicle_id)) {
                this.markerManager.updatePosition(h.vehicle_id, h.lat, h.lng, h.is_cargo_active, true);
                if (this.infoPanel.isSelected(h.vehicle_id)) {
                    this.infoPanel.updateSpeed(h.vehicle_id, h.last_speed);
                }
            }
        });
    }
    

  private async loadInitialVehicles(): Promise<void> {
    try {
      const vehicles = await FleetApi.fetchVehicles();
      vehicles.forEach((v) => this.markerManager.add(v));
    } catch (e) {
      console.error('Помилка при завантаженні:', e);
    }
  }

  private handleLiveUpdate(data: LiveUpdateMessage): void {
    if (this.isRewinding) return;
    const vehicleId = data.vehicle_id;

    if (this.markerManager.has(vehicleId)) {
        // ТУТ ДОДАЛИ is_cargo_active
        this.markerManager.updatePosition(
        vehicleId, 
        data.lat, 
        data.lng, 
        data.is_cargo_active 
        );
    }

    if (this.infoPanel.isSelected(vehicleId)) {
        this.infoPanel.updateSpeed(vehicleId, data.last_speed);
    }
    }

  async toggleCargo(vehicleId: number): Promise<void> {
    try {
      const data = await FleetApi.toggleCargo(vehicleId);
      const isActive = data.status === 'cargo_picked';
      this.infoPanel.updateCargoButton(vehicleId, isActive);
    } catch (e) {
      console.error('Помилка при зміні статусу вантажу:', e);
    }
  }

    private rewindTimeout: any;

    private setupRewind() {
        const slider = document.getElementById(SELECTORS.timeSlider) as HTMLInputElement;
        slider?.addEventListener('input', (e) => {
            const val = (e.target as HTMLInputElement).value;
            clearTimeout(this.rewindTimeout);
            this.rewindTimeout = setTimeout(() => this.applyMode(val), 100);
        });
    }

    // Винесемо логіку перемикання в окремий метод для чистоти
    private async applyMode(val: string) {
        if (val === "live") {
            // Логіка для Live
            return;
        }
        const index = parseInt(val);
        const timestamp = this.timestamps[index];
        const slider = document.getElementById(SELECTORS.timeSlider) as HTMLInputElement;
        const display = document.getElementById('time-display');
        
        // Оновлюємо текст часу
        if (display) {
            display.textContent = (slider && val === slider.max) ? "Live" : this.timestamps[parseInt(val)];
        }

        // Якщо слайдер на максимумі або вибрано "live"
        if (slider && (val === slider.max || val === "live")) {
            this.isRewinding = false;
            this.updateAllButtonsState(false);
            document.getElementById('map')!.style.filter = "none";
            
            // Очищаємо всі старі полілінії (якщо вони були від архіву)
            // Додайте цей метод, якщо його немає, або очистіть через MarkerManager
            // this.markerManager.clearAllRoutes(); 

            const vehicles = await FleetApi.fetchVehicles();
            this.markerManager.resetToLive(vehicles);
        } else {
            // Отримуємо таймстемп з масиву за індексом
            const timestamp = this.timestamps[parseInt(val)];
            
            if (timestamp) {
                this.isRewinding = true;
                this.updateAllButtonsState(true);
                document.getElementById('map')!.style.filter = "grayscale(50%)";
                
                // Виклик вашого існуючого методу onRewind
                this.onRewind(timestamp);
            }
        }
    }
}

// ==================== Bootstrap ====================
document.addEventListener('DOMContentLoaded', () => {
  window.liveMapInstance = new LiveViewMap();
});