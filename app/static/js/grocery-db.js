/* ================================================================
   grocery-db.js – IndexedDB for offline grocery list support
   ================================================================ */

const DB_NAME = 'FamiliePlannerGrocery';
const DB_VERSION = 1;
const STORES = {
  items: 'grocery_items',
  categories: 'grocery_categories',
  pendingSync: 'pending_sync',
};

class GroceryDB {
  constructor() {
    this.db = null;
  }

  /**
   * Open IndexedDB connection
   */
  async open() {
    if (this.db) return this.db;

    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        this.db = request.result;
        resolve(this.db);
      };

      request.onupgradeneeded = (event) => {
        const db = event.target.result;

        // Create items store
        if (!db.objectStoreNames.contains(STORES.items)) {
          const itemStore = db.createObjectStore(STORES.items, { keyPath: 'id' });
          itemStore.createIndex('checked', 'checked', { unique: false });
          itemStore.createIndex('category_id', 'category_id', { unique: false });
        }

        // Create categories store
        if (!db.objectStoreNames.contains(STORES.categories)) {
          const catStore = db.createObjectStore(STORES.categories, { keyPath: 'id' });
          catStore.createIndex('sort_order', 'sort_order', { unique: false });
        }

        // Create pending sync queue
        if (!db.objectStoreNames.contains(STORES.pendingSync)) {
          db.createObjectStore(STORES.pendingSync, { keyPath: 'id', autoIncrement: true });
        }
      };
    });
  }

  /**
   * Save items to IndexedDB
   */
  async saveItems(items) {
    const db = await this.open();
    const tx = db.transaction(STORES.items, 'readwrite');
    const store = tx.objectStore(STORES.items);

    // Clear existing items
    await store.clear();

    // Add all items
    for (const item of items) {
      await store.put(item);
    }

    return tx.complete;
  }

  /**
   * Get all items from IndexedDB
   */
  async getItems() {
    const db = await this.open();
    const tx = db.transaction(STORES.items, 'readonly');
    const store = tx.objectStore(STORES.items);

    return new Promise((resolve, reject) => {
      const request = store.getAll();
      request.onsuccess = () => resolve(request.result || []);
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Save categories to IndexedDB
   */
  async saveCategories(categories) {
    const db = await this.open();
    const tx = db.transaction(STORES.categories, 'readwrite');
    const store = tx.objectStore(STORES.categories);

    // Clear existing categories
    await store.clear();

    // Add all categories
    for (const cat of categories) {
      await store.put(cat);
    }

    return tx.complete;
  }

  /**
   * Get all categories from IndexedDB
   */
  async getCategories() {
    const db = await this.open();
    const tx = db.transaction(STORES.categories, 'readonly');
    const store = tx.objectStore(STORES.categories);

    return new Promise((resolve, reject) => {
      const request = store.getAll();
      request.onsuccess = () => {
        const cats = request.result || [];
        // Sort by sort_order
        cats.sort((a, b) => a.sort_order - b.sort_order);
        resolve(cats);
      };
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Add item locally (for offline mode)
   */
  async addItemOffline(item) {
    const db = await this.open();

    // Generate temporary negative ID for offline items
    const items = await this.getItems();
    const minId = Math.min(...items.map(i => i.id), 0);
    item.id = minId - 1;

    const tx = db.transaction(STORES.items, 'readwrite');
    await tx.objectStore(STORES.items).put(item);

    return item;
  }

  /**
   * Update item locally (for offline mode)
   */
  async updateItemOffline(id, updates) {
    const db = await this.open();
    const tx = db.transaction(STORES.items, 'readwrite');
    const store = tx.objectStore(STORES.items);

    const item = await new Promise((resolve, reject) => {
      const req = store.get(id);
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });

    if (item) {
      Object.assign(item, updates);
      await store.put(item);
    }

    return item;
  }

  /**
   * Delete item locally (for offline mode)
   */
  async deleteItemOffline(id) {
    const db = await this.open();
    const tx = db.transaction(STORES.items, 'readwrite');
    await tx.objectStore(STORES.items).delete(id);
  }

  /**
   * Queue an action for sync when online
   */
  async queueSync(action) {
    const db = await this.open();
    const tx = db.transaction(STORES.pendingSync, 'readwrite');
    const store = tx.objectStore(STORES.pendingSync);

    action.timestamp = Date.now();
    await store.put(action);

    console.log('[GroceryDB] Queued sync action:', action);
  }

  /**
   * Get all pending sync actions
   */
  async getPendingSync() {
    const db = await this.open();
    const tx = db.transaction(STORES.pendingSync, 'readonly');
    const store = tx.objectStore(STORES.pendingSync);

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
    const tx = db.transaction(STORES.pendingSync, 'readwrite');
    await tx.objectStore(STORES.pendingSync).clear();
    console.log('[GroceryDB] Sync queue cleared');
  }

  /**
   * Clear all data (for reset)
   */
  async clearAll() {
    const db = await this.open();
    const tx = db.transaction([STORES.items, STORES.categories, STORES.pendingSync], 'readwrite');

    await tx.objectStore(STORES.items).clear();
    await tx.objectStore(STORES.categories).clear();
    await tx.objectStore(STORES.pendingSync).clear();

    console.log('[GroceryDB] All data cleared');
  }
}

// Export singleton instance
window.GroceryDB = new GroceryDB();
