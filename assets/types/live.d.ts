export interface Vehicle {
  id: number;
  vehicle_id: number;
  driver_name: string;
  lat: number;
  lng: number;
  brand: string;
  model: string;
  speed_last: number;
  has_blown_tire: boolean;
  has_low_fuel: boolean;
  color: string;
  heading: number;
  is_cargo_active: boolean;
}

export interface LiveUpdateMessage {
  type: 'driver.location.update';
  driver_id: string;
  vehicle_id: number;
  lat: number;
  lng: number;
  last_speed: number;
  is_cargo_active: boolean;
}

export interface ToggleCargoResponse {
  status: 'cargo_picked' | 'cargo_dropped';
}

export interface HistoricalSnapshot {
  vehicle_id: number;
  lat: number;
  lng: number;
  last_speed: number;
  is_cargo_active: boolean;
}