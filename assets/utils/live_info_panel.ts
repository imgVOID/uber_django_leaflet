
import 'leaflet/dist/leaflet.css';
import { Vehicle } from '../types/live';
import { CONFIG } from './live_constants';
import { createCarIcon, getCsrfToken, cardTemplate, cargoButtonId, cardId, cargoButtonHtml } from './live_helpers';


// ==================== InfoPanel ====================
export class InfoPanel {
  private selected = new Set<number>();

  constructor(private container: HTMLElement) {}

  toggle(v: Vehicle): void {
    if (this.selected.has(v.vehicle_id)) {
      this.selected.delete(v.vehicle_id);
      document.getElementById(cardId(v.vehicle_id))?.remove();
    } else {
      this.selected.add(v.vehicle_id);
      this.container.insertAdjacentHTML('beforeend', cardTemplate(v));
    }
  }

  isSelected(vehicleId: number): boolean {
    return this.selected.has(vehicleId);
  }

  updateSpeed(vehicleId: number, speed: number): void {
    const card = document.getElementById(cardId(vehicleId));
    if (!card) {
      console.warn(`Картку для авто ${vehicleId} не знайдено в DOM`);
      return;
    }

    const speedEl = card.querySelector('.speed-val');
    if (!speedEl) return;

    speedEl.textContent = speed.toString();
    speedEl.classList.add('text-primary');
    setTimeout(() => speedEl.classList.remove('text-primary'), CONFIG.speedHighlightMs);
  }

  updateCargoButton(vehicleId: number, isActive: boolean): void {
    const btn = document.getElementById(cargoButtonId(vehicleId));
    if (!btn) return;

    btn.className = `btn btn-sm ${isActive ? 'btn-danger' : 'btn-primary'} w-100`;
    btn.innerHTML = cargoButtonHtml(vehicleId, isActive);
  }
}