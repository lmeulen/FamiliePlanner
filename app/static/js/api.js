/* ================================================================
   api.js – Centralised API client
   Usage: const events = await API.get('/api/agenda/today');
   ================================================================ */
window.API = (() => {
  const BASE = '';   // same origin

  async function request(method, path, data) {
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
    };
    if (data !== undefined) opts.body = JSON.stringify(data);

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
