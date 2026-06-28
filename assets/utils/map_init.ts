import L from 'leaflet';

export const map = L.map('map').setView([50.4501, 30.5234], 13);
export let intersectionsLayer = L.layerGroup().addTo(map);