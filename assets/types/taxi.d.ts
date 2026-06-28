export interface LocationData {
    lat: number;
    lng: number;
    accuracy: number;
    timestamp: number;
}

export interface LocationCoords {
    lat: number;
    lng: number;
}


export interface TaxiRequest {
    pickup_address: string;
    pickup_lat: number;
    pickup_lng: number;
    dropoff_address: string;
    dropoff_lat: number | null;
    dropoff_lng: number | null;
}

export interface NominatimResult {
    lat: string;
    lon: string;
    display_name: string;
}

export interface StartRideResponse {
    ride_id: number;
    status: string;
}


export interface TaxiRequestPayload {
    pickup_address: string;
    pickup_lat: number;
    pickup_lng: number;
    dropoff_address: string;
    dropoff_lat: number | null;
    dropoff_lng: number | null;
}

export interface Driver {
    id: number;
    vehicle_id: number;
    lat: number;
    lng: number;
    driver_name: string;
    distance_km: number;
    color: string;
    brand: string;
    model: string;
    year: number;
    capacity: number;
    vehicle_type: string;
    has_blown_tire: boolean;
    has_low_fuel: boolean;
    heading: number | null;
    speed_last: number | null;
}