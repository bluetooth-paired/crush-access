/* Frontend-only endpoint configuration. Never place model API keys or secrets here.
 * After deploying Wenqing's backend, fill in its public HTTPS origin below.
 * Example: baseUrl: 'https://your-api.example.com'
 */
const isLocalIntegrationPreview = window.location.origin === 'http://127.0.0.1:8789';
window.HeartSignalAPIConfig = Object.freeze({
  baseUrl: isLocalIntegrationPreview ? window.location.origin : '',
  localIntegrationPreview: isLocalIntegrationPreview,
  timeoutMs: 90000,
  enabled: true       // Requests remain blocked until baseUrl is configured
});
