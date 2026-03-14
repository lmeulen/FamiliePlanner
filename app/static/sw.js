/* ================================================================
   Service Worker - FamiliePlanner PWA
   Provides offline support and caching for improved performance
   ================================================================ */

const CACHE_VERSION = 'v1';
const STATIC_CACHE = `familieplanner-static-${CACHE_VERSION}`;
const DYNAMIC_CACHE = `familieplanner-dynamic-${CACHE_VERSION}`;
const API_CACHE = `familieplanner-api-${CACHE_VERSION}`;

// Static assets to precache (core app shell)
const STATIC_ASSETS = [
  '/',
  '/static/css/themes.css',
  '/static/css/main.css',
  '/static/js/cache.js',
  '/static/js/api.js',
  '/static/js/modal.js',
  '/static/js/toast.js',
  '/static/js/theme.js',
  '/static/js/app.js',
  '/static/js/form-controllers/recurrence-ui.js',
  '/static/js/form-controllers/event-form.js',
  '/static/js/form-controllers/task-form.js',
  '/static/js/grocery.js',
  '/boodschappen',
];

// ── Install Event ──────────────────────────────────────────────
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      console.log('[SW] Precaching app shell');
      return cache.addAll(STATIC_ASSETS);
    }).then(() => {
      console.log('[SW] Skip waiting');
      return self.skipWaiting();
    })
  );
});

// ── Activate Event ─────────────────────────────────────────────
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== STATIC_CACHE &&
              cacheName !== DYNAMIC_CACHE &&
              cacheName !== API_CACHE) {
            console.log('[SW] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      console.log('[SW] Claiming clients');
      return self.clients.claim();
    })
  );
});

// ── Fetch Event ────────────────────────────────────────────────
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Skip chrome-extension and other protocols
  if (!url.protocol.startsWith('http')) {
    return;
  }

  // API requests: Network first, fallback to cache
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirstStrategy(request, API_CACHE));
    return;
  }

  // Static assets: Cache first, fallback to network
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(cacheFirstStrategy(request, STATIC_CACHE));
    return;
  }

  // HTML pages: Network first, fallback to cache
  if (request.headers.get('accept')?.includes('text/html')) {
    event.respondWith(networkFirstStrategy(request, DYNAMIC_CACHE));
    return;
  }

  // Default: Network only
  event.respondWith(fetch(request));
});

// ── Cache Strategies ───────────────────────────────────────────

/**
 * Network First: Try network, fallback to cache if offline
 * Used for: API calls, HTML pages
 */
async function networkFirstStrategy(request, cacheName) {
  try {
    const networkResponse = await fetch(request);
    // Only cache successful responses
    if (networkResponse.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.log('[SW] Network failed, trying cache:', request.url);
    const cachedResponse = await caches.match(request);

    if (cachedResponse) {
      return cachedResponse;
    }

    // If HTML page and no cache, return offline page
    if (request.headers.get('accept')?.includes('text/html')) {
      return new Response(
        `<!DOCTYPE html>
        <html lang="nl">
        <head>
          <meta charset="UTF-8">
          <meta name="viewport" content="width=device-width, initial-scale=1.0">
          <title>Offline - FamiliePlanner</title>
          <style>
            body {
              font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
              display: flex;
              align-items: center;
              justify-content: center;
              min-height: 100vh;
              margin: 0;
              background: #f5f5f5;
              text-align: center;
              padding: 20px;
            }
            .offline-message {
              max-width: 400px;
            }
            .offline-icon {
              font-size: 4rem;
              margin-bottom: 1rem;
            }
            h1 {
              font-size: 1.5rem;
              color: #333;
              margin-bottom: 0.5rem;
            }
            p {
              color: #666;
              margin-bottom: 1.5rem;
            }
            button {
              background: #6C5CE7;
              color: white;
              border: none;
              padding: 12px 24px;
              border-radius: 8px;
              font-size: 1rem;
              cursor: pointer;
            }
            button:hover {
              background: #5b4bd1;
            }
          </style>
        </head>
        <body>
          <div class="offline-message">
            <div class="offline-icon">📡</div>
            <h1>Geen internetverbinding</h1>
            <p>Je bent offline. Sommige functies zijn mogelijk niet beschikbaar.</p>
            <button onclick="window.location.reload()">Opnieuw proberen</button>
          </div>
        </body>
        </html>`,
        {
          headers: { 'Content-Type': 'text/html' },
          status: 503,
          statusText: 'Service Unavailable'
        }
      );
    }

    // For API calls, return error response
    return new Response(
      JSON.stringify({ detail: 'Offline - geen internetverbinding' }),
      {
        headers: { 'Content-Type': 'application/json' },
        status: 503
      }
    );
  }
}

/**
 * Cache First: Try cache, fallback to network
 * Used for: Static assets (CSS, JS, images)
 */
async function cacheFirstStrategy(request, cacheName) {
  const cachedResponse = await caches.match(request);

  if (cachedResponse) {
    return cachedResponse;
  }

  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.error('[SW] Failed to fetch:', request.url, error);
    return new Response('Offline', { status: 503 });
  }
}

// ── Background Sync (future enhancement) ───────────────────────
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync:', event.tag);
  // Future: sync offline changes when connection restored
});

// ── Push Notifications (future enhancement) ────────────────────
self.addEventListener('push', (event) => {
  console.log('[SW] Push notification received');
  // Future: show notifications for events/tasks
});
