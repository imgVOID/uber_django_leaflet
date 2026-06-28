import L from 'leaflet';
import { Vehicle } from '../types/live';

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

export function cardId(vehicleId: number): string {
  return `card-vehicle-${vehicleId}`;
}

export function cargoButtonId(vehicleId: number): string {
  return `btn-cargo-${vehicleId}`;
}

export function cargoButtonHtml(vehicleId: number, isActive: boolean): string {
  return `
    <i class="bi ${isActive ? 'bi-box-arrow-up' : 'bi-box-seam'}"></i>
    <span class="btn-text">${isActive ? 'Скинути вантаж' : 'Взяти вантаж'}</span>
  `;
}

export function cardTemplate(v: Vehicle): string {
  const hasIssue = v.has_blown_tire || v.has_low_fuel;
  
  // Допоміжна функція для відображення іконки статусу
  const getStatusIcon = (condition: boolean, iconTrue: string, iconFalse: string) => `
    <i class="bi ${condition ? iconTrue : iconFalse}" 
       style="color: ${condition ? '#dc3545' : '#198754'}; font-size: 1.1rem; vertical-align: middle;">
    </i>`;

  return `
    <div class="vehicle-info-card border-start border-4 ${hasIssue ? 'border-danger' : 'border-success'} shadow-sm p-3 bg-white"
         id="${cardId(v.vehicle_id)}" data-driver-id="${v.id}">

      <div class="d-flex justify-content-between align-items-center mb-2">
        <h6 class="mb-0 text-truncate" style="max-width: 150px;">${v.brand} ${v.model}</h6>
        <button class="btn-close btn-sm" onclick="document.getElementById('${cardId(v.vehicle_id)}').remove()"></button>
      </div>

      <ul class="list-unstyled small mb-0">
        <li><i class="bi bi-person"></i> ${v.driver_name}</li>
        <li><i class="bi bi-speedometer2"></i> <span class="speed-val">${v.speed_last}</span> км/год</li>
        
        <li class="status-row mt-2 d-flex gap-3">
            <span title="Стан шин">
                ${getStatusIcon(v.has_blown_tire, 'bi-exclamation-triangle-fill', 'bi-check-circle-fill')}
                <span class="${v.has_blown_tire ? 'text-danger' : 'text-success'}">Шини</span>
            </span>
            <span title="Рівень палива">
                ${getStatusIcon(v.has_low_fuel, 'bi-fuel-pump-fill', 'bi-fuel-pump-fill')}
                <span class="${v.has_low_fuel ? 'text-danger' : 'text-success'}">Паливо</span>
            </span>
        </li>

        <li class="mt-3">
          <button class="btn btn-sm ${v.is_cargo_active ? 'btn-danger' : 'btn-primary'} w-100 "
                  ${liveMapInstance.isRewinding ? 'disabled' : ''}
                  id="${cargoButtonId(v.vehicle_id)}"
                  onclick="liveMapInstance.toggleCargo(${v.vehicle_id})">
            ${cargoButtonHtml(v.vehicle_id, v.is_cargo_active)}
          </button>
        </li>
      </ul>
    </div>
  `;
}