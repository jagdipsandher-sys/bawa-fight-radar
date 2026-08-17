/*
 * Browser configuration for the Food & Drinks explorer.
 *
 * A browser Maps key is visible by design. Before adding one here, restrict it
 * in Google Cloud to this site's exact HTTPS referrers and to only:
 *   - Maps JavaScript API
 *   - Places API (New)
 * Never put a server key, service-account credential or unrestricted key here.
 */
window.BAWA_MAPS_CONFIG = Object.freeze({
  apiKey: '',
  mapId: 'DEMO_MAP_ID'
});
