/* ================================================================
   api.js – Centralised API client
   Usage: const events = await API.get('/api/agenda/today');
   ================================================================ */
window.API = (() => {
  const BASE = '';   // same origin
  const _SAFE = new Set(['GET', 'HEAD', 'OPTIONS']);

  function _csrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') ?? '';
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

    const res = await fetch(BASE + path, opts);

    // Session expired or not logged in → redirect to login
    if (res.status === 401) {
      window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
      return;
    }

    if (res.status === 204) return null;

    const json = await res.json().catch(() => ({ detail: res.statusText }));
    if (!res.ok) throw new Error(json.detail || `HTTP ${res.status}`);
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
