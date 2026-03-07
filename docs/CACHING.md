# Caching Strategy

FamiliePlanner implementeert een hybrid caching strategie met zowel frontend (LocalStorage) als backend (HTTP Cache-Control headers) caching voor optimale performance.

## Architectuur

```
┌─────────────────────────────────────────────────────────────┐
│ Frontend Cache (LocalStorage)                               │
│ - Instant UX (0ms bij cache hit)                           │
│ - TTL per entry (1 min - 1 uur)                            │
│ - Automatic invalidation bij mutations                      │
│ - Multi-tab sync via storage events                         │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Browser HTTP Cache                                          │
│ - Gecontroleerd door Cache-Control headers                  │
│ - Transparant (browser handelt af)                          │
│ - Vermijdt onnodige netwerk requests                        │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Backend (FastAPI)                                            │
│ - SQLite queries (snel genoeg, geen Redis nodig)            │
│ - Cache-Control headers op responses                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Frontend Cache (LocalStorage)

### Features

- **TTL (Time-To-Live):** Automatische expiratie van oude entries
- **Cache Invalidation:** Pattern-based invalidatie bij mutations
- **Multi-tab Sync:** Storage events voor synchronisatie tussen tabs
- **Statistics:** Hit/miss rate tracking voor monitoring
- **Quota Handling:** Automatische cleanup bij storage quota overschrijding

### API

```javascript
// Get cached value (null if expired/missing)
const data = Cache.get('key');

// Set value with TTL (milliseconds)
Cache.set('key', data, 300000); // 5 minutes

// Remove specific entry
Cache.remove('key');

// Invalidate pattern (regex or string)
Cache.invalidate('events_');           // All keys starting with 'events_'
Cache.invalidate(/^agenda_\d{4}/);    // Regex pattern

// Clear all cache
Cache.clear();

// Get statistics
const stats = Cache.getStats();
// { hits: 42, misses: 10, total: 52, hitRate: 80.8, entries: 12, size: "125.3 KB" }
```

### Usage in Frontend Scripts

**1. Load with cache:**

```javascript
async function loadEvents() {
  const cacheKey = `events_${start}_${end}`;

  // Try cache first
  const cached = Cache.get(cacheKey);
  if (cached) {
    events = cached;
    render();
    return;
  }

  // Fetch from API
  events = await API.get(`/api/agenda/?start=${start}&end=${end}`);

  // Cache for 1 minute
  Cache.set(cacheKey, events, 60000);
  render();
}
```

**2. Invalidate on mutation:**

```javascript
async function createEvent(data) {
  await API.post('/api/agenda/', data);

  // Invalidate all agenda caches
  Cache.invalidate('agenda_events_');

  // Reload fresh data (skip cache)
  loadEvents(false);
}
```

**3. Multi-tab sync (automatic):**

```javascript
// Listen to cache updates from other tabs
window.addEventListener('cacheUpdated', (e) => {
  console.log('Cache updated in other tab:', e.detail.key);
  // Optionally refresh UI
});
```

---

## Backend Cache Headers

### Static Files

Automatically configured via `CachedStaticFiles` in `main.py`:

| File Type | Cache-Control | Duration |
|-----------|---------------|----------|
| Thumbnails (`/uploads/thumbnails/`) | `public, max-age=31536000, immutable` | 1 year |
| Photos (`/uploads/`) | `public, max-age=86400` | 1 day |
| CSS/JS | `public, max-age=3600` | 1 hour |
| Images/Fonts | `public, max-age=604800` | 1 week |
| Other | `public, max-age=3600` | 1 hour |

**Waarom immutable voor thumbnails?**
- Thumbnails hebben UUID-based filenames → wijzigen nooit
- `immutable` voorkomt revalidatie requests (zelfs bij refresh)
- Maximale caching efficiency

### API Endpoints

| Endpoint | Cache-Control | Reden |
|----------|---------------|-------|
| `GET /api/family/` | `private, max-age=3600` | Family members wijzigen zelden |
| `GET /api/settings/` | `private, max-age=600` | Settings wijzigen zelden |
| `GET /api/stats/` | `private, max-age=300` | Expensive queries, mag 5 min oud zijn |
| Andere endpoints | Geen cache headers | Dynamische data (events, tasks, meals) |

**private vs public:**
- `private`: Alleen browser cache, niet CDN/proxy
- `public`: Deelbaar via CDN/proxy (alleen voor public static files)

---

## Cache Keys Conventie

Gebruik consistente naming voor cache keys:

```javascript
// ✅ Good: Descriptive + parameters
`agenda_events_${start}_${end}`
`tasks_list_${listId}`
`family_members`
`settings`
`photos_metadata`

// ❌ Bad: Vague or hard to invalidate
`data`
`events`
`cache_1`
```

---

## TTL Guidelines

| Data Type | TTL | Reden |
|-----------|-----|-------|
| Family members | 1 uur (3600000ms) | Wijzigt zeer zelden |
| Settings | 10 min (600000ms) | Wijzigt zelden |
| Agenda events | 1 min (60000ms) | Frequent geüpdatet |
| Tasks | 1 min (60000ms) | Frequent geüpdatet |
| Photos metadata | 5 min (300000ms) | Matige update frequentie |
| Statistics | 5 min (300000ms) | Expensive queries |

**Rule of thumb:**
- Frequently mutated data: 1-2 minutes
- Semi-static data: 5-10 minutes
- Rarely changing data: 30-60 minutes

---

## Invalidation Patterns

**Invalidate bij mutations:**

```javascript
// After CREATE
Cache.invalidate('agenda_events_');  // Clear all agenda caches
Cache.invalidate('family_members');  // Clear family cache

// After UPDATE
Cache.invalidate(`tasks_list_${listId}`); // Clear specific list
Cache.invalidate('tasks_');               // Or clear all tasks

// After DELETE
Cache.invalidate(/^photos_/); // Regex: all photo-related caches
```

**Best practices:**
1. Invalidate **specifiek** waar mogelijk (`tasks_list_5`)
2. Fallback naar **pattern** bij onzekerheid (`tasks_`)
3. **Reload met `useCache=false`** na invalidatie

---

## Cache Statistics Dashboard

Beschikbaar op **Instellingen pagina** → Cache sectie:

- **Hit Rate:** Percentage cache hits (hoger = beter)
- **Entries:** Aantal gecachte items
- **Hits/Misses:** Absolute counts
- **Storage:** Totale LocalStorage gebruikt

**Target metrics:**
- Hit rate > 60%: Goed geconfigureerd
- Hit rate < 40%: Te korte TTL of veel mutations
- Entries > 100: Mogelijk cleanup nodig

**Clear cache:**
- Handmatige clear knop voor troubleshooting
- Geen effect op database (alleen browser cache)

---

## Implementation Checklist

Nieuwe pagina met caching:

- [ ] Import cache.js in base.html (✅ Done)
- [ ] Add cache logic to load function
- [ ] Set appropriate TTL for data type
- [ ] Invalidate cache on CREATE/UPDATE/DELETE
- [ ] Test multi-tab behavior
- [ ] Monitor cache hit rate in settings

---

## Troubleshooting

### Cache werkt niet

```javascript
// Check if Cache is loaded
console.log(Cache.getStats());

// Check browser console for errors
// [Cache] Manager initialized. Use Cache.getStats() to view statistics.
```

### Stale data na update

```javascript
// Ensure invalidation after mutation
await API.post('/api/agenda/', data);
Cache.invalidate('agenda_events_'); // ← Add this
loadEvents(false); // Skip cache
```

### Quota exceeded error

```javascript
// Cache automatically cleans up old entries
// If persistent, check Chrome DevTools → Application → Storage
```

### Multi-tab niet sync

```javascript
// Storage events only fire in OTHER tabs, not current
// Test: open 2 tabs, mutate in tab 1, check tab 2
```

---

## Performance Metrics

**Before caching:**
- Family members: 150ms (API call)
- Agenda events: 200ms (API call)
- Settings: 100ms (API call)

**After caching (cache hit):**
- Family members: <5ms (LocalStorage)
- Agenda events: <5ms (LocalStorage)
- Settings: <5ms (LocalStorage)

**Target:**
- 95%+ cache hits op family members
- 60%+ cache hits op events/tasks
- <10ms perceived load time

---

## Future Enhancements

1. **Service Worker:** Offline-first capability
2. **IndexedDB:** Voor grote datasets (>5MB)
3. **Cache warming:** Pre-load frequent queries
4. **Smart invalidation:** WebSocket push voor real-time sync
5. **Cache versioning:** Automatic invalidation bij app updates

---

## Related Files

- `app/static/js/cache.js` - Cache manager implementation
- `app/main.py` - CachedStaticFiles class
- `app/routers/family.py` - Cache-Control headers example
- `app/templates/settings.html` - Cache dashboard UI
- `app/static/js/settings.js` - Cache stats rendering
