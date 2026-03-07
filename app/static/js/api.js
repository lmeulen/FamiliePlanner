/* ================================================================
   api.js – Centralised API client with enhanced error handling
   Usage: const events = await API.get('/api/agenda/today');
   ================================================================ */
window.API = (() => {
  const BASE = '';   // same origin
  const _SAFE = new Set(['GET', 'HEAD', 'OPTIONS']);

  function _csrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') ?? '';
  }

  /**
   * Format error response into user-friendly message
   */
  function _formatError(json, status) {
    // New error format with code/message/details
    if (json.code && json.message) {
      let msg = json.message;
      if (json.details) {
        msg += ` (${json.details})`;
      }
      if (json.field) {
        msg += ` Veld: ${json.field}`;
      }
      return msg;
    }

    // Legacy format (detail string)
    if (json.detail) {
      return json.detail;
    }

    // Fallback to status code messages
    const statusMessages = {
      400: 'Ongeldige aanvraag. Controleer je invoer.',
      401: 'Je bent niet ingelogd.',
      403: 'Je hebt geen toegang tot deze actie.',
      404: 'Het item kon niet worden gevonden.',
      409: 'Deze actie kan niet worden uitgevoerd vanwege een conflict.',
      422: 'De ingevoerde gegevens zijn niet geldig.',
      429: 'Te veel verzoeken. Wacht even en probeer opnieuw.',
      500: 'Er is een serverfout opgetreden. Probeer het later opnieuw.',
      502: 'Server tijdelijk niet bereikbaar.',
      503: 'Dienst tijdelijk niet beschikbaar.',
    };

    return statusMessages[status] || `Er is een fout opgetreden (${status})`;
  }

  async function request(method, path, data) {
    const isFormData = data instanceof FormData;
    const opts = {
      method,
      credentials: 'same-origin',
      headers: {},
    };
    if (!isFormData) opts.headers['Content-Type'] = 'application/json';
    if (!_SAFE.has(method)) opts.headers['X-CSRF-Token'] = _csrfToken();
    if (data !== undefined) opts.body = isFormData ? data : JSON.stringify(data);

    let res;
    try {
      res = await fetch(BASE + path, opts);
    } catch (err) {
      // Network error (no internet, CORS, etc.)
      throw new Error('Geen internetverbinding. Controleer je verbinding en probeer opnieuw.');
    }

    // Session expired or not logged in → redirect to login
    if (res.status === 401) {
      window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
      return;
    }

    // No content response
    if (res.status === 204) return null;

    // Parse JSON response
    const json = await res.json().catch(() => ({ detail: res.statusText }));

    // Error response
    if (!res.ok) {
      const errorMessage = _formatError(json, res.status);
      const error = new Error(errorMessage);
      error.status = res.status;
      error.code = json.code;
      error.details = json.details;
      error.field = json.field;
      throw error;
    }

    return json;
  }

  return {
    get:    (path)        => request('GET',    path),
    post:   (path, data)  => request('POST',   path, data),
    put:    (path, data)  => request('PUT',    path, data),
    patch:  (path, data)  => request('PATCH',  path, data),
    delete: (path)        => request('DELETE', path),
  };
})();
