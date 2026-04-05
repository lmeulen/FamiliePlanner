/* ================================================================
   agenda-db.js – IndexedDB for offline agenda support
   ================================================================ */

const AGENDA_DB_NAME = 'FamiliePlannerAgenda';
const AGENDA_DB_VERSION = 1;
const AGENDA_STORES = {
  events: 'agenda_events',
  series: 'recurrence_series',
  pendingSync: 'pending_sync',
};

class AgendaDB {
  constructor() {
    this.db = null;
  }

  /**
   * Open IndexedDB connection
   */
  async open() {
    if (this.db) return this.db;

    return new Promise((resolve, reject) => {
      const request = indexedDB.open(AGENDA_DB_NAME, AGENDA_DB_VERSION);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        this.db = request.result;
        resolve(this.db);
      };

      request.onupgradeneeded = (event) => {
        const db = event.target.result;

        // Create events store
        if (!db.objectStoreNames.contains(AGENDA_STORES.events)) {
          const eventStore = db.createObjectStore(AGENDA_STORES.events, { keyPath: 'id' });
          eventStore.createIndex('start_time', 'start_time', { unique: false });
          eventStore.createIndex('series_id', 'series_id', { unique: false });
        }

        // Create recurrence series store
        if (!db.objectStoreNames.contains(AGENDA_STORES.series)) {
          const seriesStore = db.createObjectStore(AGENDA_STORES.series, { keyPath: 'id' });
          seriesStore.createIndex('series_start', 'series_start', { unique: false });
        }

        // Create pending sync queue
        if (!db.objectStoreNames.contains(AGENDA_STORES.pendingSync)) {
          db.createObjectStore(AGENDA_STORES.pendingSync, { keyPath: 'id', autoIncrement: true });
        }
      };
    });
  }

  // ── Events ────────────────────────────────────────────────────

  /**
   * Save events to IndexedDB
   */
  async saveEvents(events) {
    const db = await this.open();
    const tx = db.transaction(AGENDA_STORES.events, 'readwrite');
    const store = tx.objectStore(AGENDA_STORES.events);

    // Don't clear - merge with existing offline events
    for (const event of events) {
      await store.put(event);
    }

    return tx.complete;
  }

  /**
   * Get all events from IndexedDB
   */
  async getEvents() {
    const db = await this.open();
    const tx = db.transaction(AGENDA_STORES.events, 'readonly');
    const store = tx.objectStore(AGENDA_STORES.events);

    return new Promise((resolve, reject) => {
      const request = store.getAll();
      request.onsuccess = () => resolve(request.result || []);
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Get events by date range (optimized for month view)
   */
  async getEventsByDateRange(startDate, endDate) {
    const db = await this.open();
    const tx = db.transaction(AGENDA_STORES.events, 'readonly');
    const store = tx.objectStore(AGENDA_STORES.events);
    const index = store.index('start_time');

    // Convert dates to ISO strings for comparison
    const startISO = startDate instanceof Date
      ? startDate.toISOString()
      : new Date(startDate).toISOString();
    const endISO = endDate instanceof Date
      ? endDate.toISOString()
      : new Date(endDate + 'T23:59:59').toISOString();

    return new Promise((resolve, reject) => {
      const range = IDBKeyRange.bound(startISO, endISO);
      const request = index.getAll(range);
      request.onsuccess = () => {
        // Also include events that start before range but end within/after range
        const allEvents = request.result || [];
        resolve(allEvents);
      };
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Get events overlapping with a date range (includes multi-day events)
   */
  async getEventsOverlapping(startDate, endDate) {
    const allEvents = await this.getEvents();

    const startTime = startDate instanceof Date ? startDate : new Date(startDate);
    const endTime = endDate instanceof Date ? endDate : new Date(endDate + 'T23:59:59');

    return allEvents.filter(event => {
      const eventStart = new Date(event.start_time);
      const eventEnd = new Date(event.end_time);

      // Event overlaps if:
      // - Event starts before range ends AND
      // - Event ends after range starts
      return eventStart < endTime && eventEnd > startTime;
    });
  }

  /**
   * Get a single event by ID
   */
  async getEvent(id) {
    const db = await this.open();
    const tx = db.transaction(AGENDA_STORES.events, 'readonly');
    const store = tx.objectStore(AGENDA_STORES.events);

    return new Promise((resolve, reject) => {
      const request = store.get(id);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Add event locally (for offline mode)
   */
  async addEventOffline(event) {
    const db = await this.open();

    // Generate temporary negative ID for offline events
    const events = await this.getEvents();
    const minId = Math.min(...events.map(e => e.id), 0);
    event.id = minId - 1;

    const tx = db.transaction(AGENDA_STORES.events, 'readwrite');
    await tx.objectStore(AGENDA_STORES.events).put(event);

    console.log('[AgendaDB] Added offline event:', event);
    return event;
  }

  /**
   * Update event locally (for offline mode)
   */
  async updateEventOffline(id, updates) {
    const db = await this.open();
    const tx = db.transaction(AGENDA_STORES.events, 'readwrite');
    const store = tx.objectStore(AGENDA_STORES.events);

    const event = await new Promise((resolve, reject) => {
      const req = store.get(id);
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });

    if (event) {
      Object.assign(event, updates);
      await store.put(event);
      console.log('[AgendaDB] Updated offline event:', event);
    }

    return event;
  }

  /**
   * Delete event locally (for offline mode)
   */
  async deleteEventOffline(id) {
    const db = await this.open();
    const tx = db.transaction(AGENDA_STORES.events, 'readwrite');
    await tx.objectStore(AGENDA_STORES.events).delete(id);
    console.log('[AgendaDB] Deleted offline event:', id);
  }

  // ── Recurrence Series ─────────────────────────────────────────

  /**
   * Save recurrence series to IndexedDB (with pre-generated occurrences from server)
   */
  async saveSeries(seriesList) {
    const db = await this.open();
    const tx = db.transaction(AGENDA_STORES.series, 'readwrite');
    const store = tx.objectStore(AGENDA_STORES.series);

    for (const series of seriesList) {
      await store.put(series);
    }

    return tx.complete;
  }

  /**
   * Get all recurrence series from IndexedDB
   */
  async getAllSeries() {
    const db = await this.open();
    const tx = db.transaction(AGENDA_STORES.series, 'readonly');
    const store = tx.objectStore(AGENDA_STORES.series);

    return new Promise((resolve, reject) => {
      const request = store.getAll();
      request.onsuccess = () => resolve(request.result || []);
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Get a single series by ID
   */
  async getSeries(id) {
    const db = await this.open();
    const tx = db.transaction(AGENDA_STORES.series, 'readonly');
    const store = tx.objectStore(AGENDA_STORES.series);

    return new Promise((resolve, reject) => {
      const request = store.get(id);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  // ── Sync Queue ────────────────────────────────────────────────

  /**
   * Queue an action for sync when online
   */
  async queueSync(action) {
    const db = await this.open();
    const tx = db.transaction(AGENDA_STORES.pendingSync, 'readwrite');
    const store = tx.objectStore(AGENDA_STORES.pendingSync);

    action.timestamp = Date.now();
    await store.put(action);

    console.log('[AgendaDB] Queued sync action:', action);
  }

  /**
   * Get all pending sync actions
   */
  async getPendingSync() {
    const db = await this.open();
    const tx = db.transaction(AGENDA_STORES.pendingSync, 'readonly');
    const store = tx.objectStore(AGENDA_STORES.pendingSync);

    return new Promise((resolve, reject) => {
      const request = store.getAll();
      request.onsuccess = () => resolve(request.result || []);
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Clear sync queue after successful sync
   */
  async clearSyncQueue() {
    const db = await this.open();
    const tx = db.transaction(AGENDA_STORES.pendingSync, 'readwrite');
    await tx.objectStore(AGENDA_STORES.pendingSync).clear();
    console.log('[AgendaDB] Sync queue cleared');
  }

  /**
   * Remove a specific sync action from queue
   */
  async removeSyncAction(id) {
    const db = await this.open();
    const tx = db.transaction(AGENDA_STORES.pendingSync, 'readwrite');
    await tx.objectStore(AGENDA_STORES.pendingSync).delete(id);
  }

  /**
   * Clear all data (for reset)
   */
  async clearAll() {
    const db = await this.open();
    const tx = db.transaction([AGENDA_STORES.events, AGENDA_STORES.series, AGENDA_STORES.pendingSync], 'readwrite');

    await tx.objectStore(AGENDA_STORES.events).clear();
    await tx.objectStore(AGENDA_STORES.series).clear();
    await tx.objectStore(AGENDA_STORES.pendingSync).clear();

    console.log('[AgendaDB] All data cleared');
  }
}

// Export singleton instance
window.AgendaDB = new AgendaDB();
