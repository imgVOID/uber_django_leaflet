// ==================== Interfaces ====================
import { LocationCoords, Driver } from './types/taxi';

// ==================== API Service ====================
const API = {
    getCsrfToken(): string {
        const meta = document.querySelector('meta[name="csrf-token"]');
        const metaToken = meta ? (meta as HTMLMetaElement).content : '';
        if (metaToken && metaToken !== 'NOTPROVIDED') return metaToken;
        const match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? match[1] : '';
    },

    async getRoute(start: LocationCoords, end: LocationCoords) {
        const res = await fetch(`/taxi/osrm_route/?start_lat=${start.lat}&start_lng=${start.lng}&end_lat=${end.lat}&end_lng=${end.lng}`);
        return res.ok ? await res.json() : null;
    },

    async getDrivers(lat: number, lng: number): Promise<Driver[]> {
        const rideId = window.rideData?.ride_id;
        let url = `/taxi/nearby_drivers/?lat=${lat}&lng=${lng}&radius_km=5`;
        if (rideId) url += `&ride_id=${rideId}`;
        const res = await fetch(url);
        return res.ok ? (await res.json()).drivers || [] : [];
    },

    async selectDriver(rideId: number, driverId: number, vehicleId: number): Promise<boolean> {
        const res = await fetch(`/taxi/ride/select_driver/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': this.getCsrfToken() },
            body: JSON.stringify({ ride_id: rideId, driver_id: driverId, vehicle_id: vehicleId }),
        });
        return res.ok;
    },

    async cancelDriver(rideId: number): Promise<boolean> {
        const res = await fetch(`/taxi/ride/cancel_driver/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': this.getCsrfToken() },
            body: JSON.stringify({ ride_id: rideId }),
        });
        return res.ok;
    }
};

export default API;