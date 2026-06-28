
// ==================== Constants ====================
export const CONFIG = {
  mapCenter: [50.4501, 30.5234] as [number, number],
  mapZoom: 13,
  tileUrl: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
  fleetEndpoint: '/live-fleet/',
  toggleCargoEndpoint: (vehicleId: number) => `/live/toggle-cargo/${vehicleId}/`,
  wsPath: '/ws/live-view/',
  speedHighlightMs: 500,
};

export const SELECTORS = {
  infoPanels: 'info-panels',
  timeSlider: 'time-slider',
};
