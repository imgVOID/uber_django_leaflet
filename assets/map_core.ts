export const initMap = (elementId: string, center: [number, number] = [50.4501, 30.5234]) => {
    const map = L.map(elementId).setView(center, 14);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors'
    }).addTo(map);
    return map;
};

export const createPointIcon = (iconClass: string, color: string) => L.divIcon({
    className: 'point-icon',
    html: `<div style="font-size: 24px; color: ${color};"><i class="${iconClass}"></i></div>`,
    iconSize: [24, 24], iconAnchor: [12, 12]
});