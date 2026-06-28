// src/api/analytics.ts
import { getCsrfToken } from './analytics_helpers';
import { Vehicle, ToggleCargoResponse } from '../types/live';
import { CONFIG } from './live_constants';

// Допоміжна функція для запитів
const POST = async (url: string, body: any) => {
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify(body)
    });
    
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return response.json(); // Одразу повертаємо JSON
};

// ANALYTICS API
export const AnalyticsAPI = {
    getFleetData: () => fetch('/analytics/fleet-data/').then(r => r.json()),
    
    // Передаємо об'єкт area напряму, POST сам зробить JSON.stringify(body)
    getTopRoutes: (area: any) => POST('/analytics/top-routes/', area),
    
    getHotspots: (area: any) => POST('/analytics/hotspots/', area),
    
    getRoutesInArea: (area: any) => POST('/analytics/routes-in-area/', area),
    
    // Передаємо об'єкт { routes }
    calculateIntersections: (routes: any) => POST('/analytics/calculate-intersections/', { routes })
};
