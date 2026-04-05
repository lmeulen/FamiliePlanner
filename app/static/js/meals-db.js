/* ================================================================
   meals-db.js – IndexedDB for offline meals support
   ================================================================ */

const MEALS_DB_NAME = 'FamiliePlannerMeals';
const MEALS_DB_VERSION = 1;
const MEALS_STORES = {
  meals: 'meals',
  pendingSync: 'pending_sync',
};

class MealsDB {
  constructor() {
    this.db = null;
  }

  /**
   * Open IndexedDB connection
   */
  async open() {
    if (this.db) return this.db;

    return new Promise((resolve, reject) => {
      const request = indexedDB.open(MEALS_DB_NAME, MEALS_DB_VERSION);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        this.db = request.result;
        resolve(this.db);
      };

      request.onupgradeneeded = (event) => {
        const db = event.target.result;

        // Create meals store
        if (!db.objectStoreNames.contains(MEALS_STORES.meals)) {
          const mealStore = db.createObjectStore(MEALS_STORES.meals, { keyPath: 'id' });
          mealStore.createIndex('date', 'date', { unique: false });
          mealStore.createIndex('meal_type', 'meal_type', { unique: false });
        }

        // Create pending sync queue
        if (!db.objectStoreNames.contains(MEALS_STORES.pendingSync)) {
          db.createObjectStore(MEALS_STORES.pendingSync, { keyPath: 'id', autoIncrement: true });
        }
      };
    });
  }

  /**
   * Save meals to IndexedDB
   */
  async saveMeals(meals) {
    const db = await this.open();
    const tx = db.transaction(MEALS_STORES.meals, 'readwrite');
    const store = tx.objectStore(MEALS_STORES.meals);

    // Clear existing meals
    await store.clear();

    // Add all meals
    for (const meal of meals) {
      await store.put(meal);
    }

    return tx.complete;
  }

  /**
   * Get all meals from IndexedDB
   */
  async getMeals() {
    const db = await this.open();
    const tx = db.transaction(MEALS_STORES.meals, 'readonly');
    const store = tx.objectStore(MEALS_STORES.meals);

    return new Promise((resolve, reject) => {
      const request = store.getAll();
      request.onsuccess = () => resolve(request.result || []);
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Get meals for a date range
   */
  async getMealsByDateRange(startDate, endDate) {
    const db = await this.open();
    const tx = db.transaction(MEALS_STORES.meals, 'readonly');
    const store = tx.objectStore(MEALS_STORES.meals);
    const index = store.index('date');

    return new Promise((resolve, reject) => {
      const range = IDBKeyRange.bound(startDate, endDate);
      const request = index.getAll(range);
      request.onsuccess = () => resolve(request.result || []);
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Get a single meal by ID
   */
  async getMeal(id) {
    const db = await this.open();
    const tx = db.transaction(MEALS_STORES.meals, 'readonly');
    const store = tx.objectStore(MEALS_STORES.meals);

    return new Promise((resolve, reject) => {
      const request = store.get(id);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Add meal locally (for offline mode)
   */
  async addMealOffline(meal) {
    const db = await this.open();

    // Generate temporary negative ID for offline meals
    const meals = await this.getMeals();
    const minId = Math.min(...meals.map(m => m.id), 0);
    meal.id = minId - 1;

    const tx = db.transaction(MEALS_STORES.meals, 'readwrite');
    await tx.objectStore(MEALS_STORES.meals).put(meal);

    console.log('[MealsDB] Added offline meal:', meal);
    return meal;
  }

  /**
   * Update meal locally (for offline mode)
   */
  async updateMealOffline(id, updates) {
    const db = await this.open();
    const tx = db.transaction(MEALS_STORES.meals, 'readwrite');
    const store = tx.objectStore(MEALS_STORES.meals);

    const meal = await new Promise((resolve, reject) => {
      const req = store.get(id);
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });

    if (meal) {
      Object.assign(meal, updates);
      await store.put(meal);
      console.log('[MealsDB] Updated offline meal:', meal);
    }

    return meal;
  }

  /**
   * Delete meal locally (for offline mode)
   */
  async deleteMealOffline(id) {
    const db = await this.open();
    const tx = db.transaction(MEALS_STORES.meals, 'readwrite');
    await tx.objectStore(MEALS_STORES.meals).delete(id);
    console.log('[MealsDB] Deleted offline meal:', id);
  }

  /**
   * Queue an action for sync when online
   */
  async queueSync(action) {
    const db = await this.open();
    const tx = db.transaction(MEALS_STORES.pendingSync, 'readwrite');
    const store = tx.objectStore(MEALS_STORES.pendingSync);

    action.timestamp = Date.now();
    await store.put(action);

    console.log('[MealsDB] Queued sync action:', action);
  }

  /**
   * Get all pending sync actions
   */
  async getPendingSync() {
    const db = await this.open();
    const tx = db.transaction(MEALS_STORES.pendingSync, 'readonly');
    const store = tx.objectStore(MEALS_STORES.pendingSync);

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
    const tx = db.transaction(MEALS_STORES.pendingSync, 'readwrite');
    await tx.objectStore(MEALS_STORES.pendingSync).clear();
    console.log('[MealsDB] Sync queue cleared');
  }

  /**
   * Remove a specific sync action from queue
   */
  async removeSyncAction(id) {
    const db = await this.open();
    const tx = db.transaction(MEALS_STORES.pendingSync, 'readwrite');
    await tx.objectStore(MEALS_STORES.pendingSync).delete(id);
  }

  /**
   * Clear all data (for reset)
   */
  async clearAll() {
    const db = await this.open();
    const tx = db.transaction([MEALS_STORES.meals, MEALS_STORES.pendingSync], 'readwrite');

    await tx.objectStore(MEALS_STORES.meals).clear();
    await tx.objectStore(MEALS_STORES.pendingSync).clear();

    console.log('[MealsDB] All data cleared');
  }
}

// Export singleton instance
window.MealsDB = new MealsDB();
