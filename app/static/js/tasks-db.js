/* ================================================================
   tasks-db.js – IndexedDB for offline tasks support
   ================================================================ */

const TASKS_DB_NAME = 'FamiliePlannerTasks';
const TASKS_DB_VERSION = 1;
const TASKS_STORES = {
  tasks: 'tasks',
  lists: 'task_lists',
  series: 'task_series',
  pendingSync: 'pending_sync',
};

class TasksDB {
  constructor() {
    this.db = null;
  }

  /**
   * Open IndexedDB connection
   */
  async open() {
    if (this.db) return this.db;

    return new Promise((resolve, reject) => {
      const request = indexedDB.open(TASKS_DB_NAME, TASKS_DB_VERSION);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        this.db = request.result;
        resolve(this.db);
      };

      request.onupgradeneeded = (event) => {
        const db = event.target.result;

        // Create tasks store
        if (!db.objectStoreNames.contains(TASKS_STORES.tasks)) {
          const taskStore = db.createObjectStore(TASKS_STORES.tasks, { keyPath: 'id' });
          taskStore.createIndex('done', 'done', { unique: false });
          taskStore.createIndex('due_date', 'due_date', { unique: false });
          taskStore.createIndex('list_id', 'list_id', { unique: false });
          taskStore.createIndex('series_id', 'series_id', { unique: false });
        }

        // Create task lists store
        if (!db.objectStoreNames.contains(TASKS_STORES.lists)) {
          const listStore = db.createObjectStore(TASKS_STORES.lists, { keyPath: 'id' });
          listStore.createIndex('sort_order', 'sort_order', { unique: false });
        }

        // Create task series store (for recurring tasks)
        if (!db.objectStoreNames.contains(TASKS_STORES.series)) {
          const seriesStore = db.createObjectStore(TASKS_STORES.series, { keyPath: 'id' });
          seriesStore.createIndex('list_id', 'list_id', { unique: false });
        }

        // Create pending sync queue
        if (!db.objectStoreNames.contains(TASKS_STORES.pendingSync)) {
          db.createObjectStore(TASKS_STORES.pendingSync, { keyPath: 'id', autoIncrement: true });
        }
      };
    });
  }

  // ── Tasks ─────────────────────────────────────────────────────

  /**
   * Save tasks to IndexedDB
   */
  async saveTasks(tasks) {
    const db = await this.open();
    const tx = db.transaction(TASKS_STORES.tasks, 'readwrite');
    const store = tx.objectStore(TASKS_STORES.tasks);

    // Don't clear - merge with existing offline tasks
    for (const task of tasks) {
      await store.put(task);
    }

    return tx.complete;
  }

  /**
   * Get all tasks from IndexedDB
   */
  async getTasks() {
    const db = await this.open();
    const tx = db.transaction(TASKS_STORES.tasks, 'readonly');
    const store = tx.objectStore(TASKS_STORES.tasks);

    return new Promise((resolve, reject) => {
      const request = store.getAll();
      request.onsuccess = () => resolve(request.result || []);
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Get tasks by filters (list_id, member_id, done status)
   */
  async getTasksFiltered(filters = {}) {
    const db = await this.open();
    const allTasks = await this.getTasks();

    return allTasks.filter(task => {
      // Filter by list_id
      if (filters.list_id !== undefined && filters.list_id !== 'all') {
        if (task.list_id !== parseInt(filters.list_id)) return false;
      }

      // Filter by member_id
      if (filters.member_id !== undefined && filters.member_id !== null) {
        const memberIds = task.member_ids || [];
        if (!memberIds.includes(parseInt(filters.member_id))) return false;
      }

      // Filter by done status
      if (filters.done !== undefined) {
        if (task.done !== filters.done) return false;
      }

      return true;
    });
  }

  /**
   * Get a single task by ID
   */
  async getTask(id) {
    const db = await this.open();
    const tx = db.transaction(TASKS_STORES.tasks, 'readonly');
    const store = tx.objectStore(TASKS_STORES.tasks);

    return new Promise((resolve, reject) => {
      const request = store.get(id);
      request.onsuccess = () => resolve(request.result);
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Add task locally (for offline mode)
   */
  async addTaskOffline(task) {
    const db = await this.open();

    // Generate temporary negative ID for offline tasks
    const tasks = await this.getTasks();
    const minId = Math.min(...tasks.map(t => t.id), 0);
    task.id = minId - 1;

    const tx = db.transaction(TASKS_STORES.tasks, 'readwrite');
    await tx.objectStore(TASKS_STORES.tasks).put(task);

    console.log('[TasksDB] Added offline task:', task);
    return task;
  }

  /**
   * Update task locally (for offline mode)
   */
  async updateTaskOffline(id, updates) {
    const db = await this.open();
    const tx = db.transaction(TASKS_STORES.tasks, 'readwrite');
    const store = tx.objectStore(TASKS_STORES.tasks);

    const task = await new Promise((resolve, reject) => {
      const req = store.get(id);
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });

    if (task) {
      Object.assign(task, updates);
      await store.put(task);
      console.log('[TasksDB] Updated offline task:', task);
    }

    return task;
  }

  /**
   * Delete task locally (for offline mode)
   */
  async deleteTaskOffline(id) {
    const db = await this.open();
    const tx = db.transaction(TASKS_STORES.tasks, 'readwrite');
    await tx.objectStore(TASKS_STORES.tasks).delete(id);
    console.log('[TasksDB] Deleted offline task:', id);
  }

  // ── Task Lists ────────────────────────────────────────────────

  /**
   * Save task lists to IndexedDB
   */
  async saveLists(lists) {
    const db = await this.open();
    const tx = db.transaction(TASKS_STORES.lists, 'readwrite');
    const store = tx.objectStore(TASKS_STORES.lists);

    // Clear existing lists
    await store.clear();

    // Add all lists
    for (const list of lists) {
      await store.put(list);
    }

    return tx.complete;
  }

  /**
   * Get all task lists from IndexedDB
   */
  async getLists() {
    const db = await this.open();
    const tx = db.transaction(TASKS_STORES.lists, 'readonly');
    const store = tx.objectStore(TASKS_STORES.lists);

    return new Promise((resolve, reject) => {
      const request = store.getAll();
      request.onsuccess = () => {
        const lists = request.result || [];
        // Sort by sort_order
        lists.sort((a, b) => a.sort_order - b.sort_order);
        resolve(lists);
      };
      request.onerror = () => reject(request.error);
    });
  }

  /**
   * Add list locally (for offline mode)
   */
  async addListOffline(list) {
    const db = await this.open();

    // Generate temporary negative ID for offline lists
    const lists = await this.getLists();
    const minId = Math.min(...lists.map(l => l.id), 0);
    list.id = minId - 1;

    const tx = db.transaction(TASKS_STORES.lists, 'readwrite');
    await tx.objectStore(TASKS_STORES.lists).put(list);

    console.log('[TasksDB] Added offline list:', list);
    return list;
  }

  /**
   * Update list locally (for offline mode)
   */
  async updateListOffline(id, updates) {
    const db = await this.open();
    const tx = db.transaction(TASKS_STORES.lists, 'readwrite');
    const store = tx.objectStore(TASKS_STORES.lists);

    const list = await new Promise((resolve, reject) => {
      const req = store.get(id);
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });

    if (list) {
      Object.assign(list, updates);
      await store.put(list);
      console.log('[TasksDB] Updated offline list:', list);
    }

    return list;
  }

  /**
   * Delete list locally (for offline mode)
   */
  async deleteListOffline(id) {
    const db = await this.open();
    const tx = db.transaction(TASKS_STORES.lists, 'readwrite');
    await tx.objectStore(TASKS_STORES.lists).delete(id);
    console.log('[TasksDB] Deleted offline list:', id);
  }

  // ── Task Series ───────────────────────────────────────────────

  /**
   * Save task series to IndexedDB (with pre-generated occurrences from server)
   */
  async saveSeries(seriesList) {
    const db = await this.open();
    const tx = db.transaction(TASKS_STORES.series, 'readwrite');
    const store = tx.objectStore(TASKS_STORES.series);

    for (const series of seriesList) {
      await store.put(series);
    }

    return tx.complete;
  }

  /**
   * Get all task series from IndexedDB
   */
  async getAllSeries() {
    const db = await this.open();
    const tx = db.transaction(TASKS_STORES.series, 'readonly');
    const store = tx.objectStore(TASKS_STORES.series);

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
    const tx = db.transaction(TASKS_STORES.series, 'readonly');
    const store = tx.objectStore(TASKS_STORES.series);

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
    const tx = db.transaction(TASKS_STORES.pendingSync, 'readwrite');
    const store = tx.objectStore(TASKS_STORES.pendingSync);

    action.timestamp = Date.now();
    await store.put(action);

    console.log('[TasksDB] Queued sync action:', action);
  }

  /**
   * Get all pending sync actions
   */
  async getPendingSync() {
    const db = await this.open();
    const tx = db.transaction(TASKS_STORES.pendingSync, 'readonly');
    const store = tx.objectStore(TASKS_STORES.pendingSync);

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
    const tx = db.transaction(TASKS_STORES.pendingSync, 'readwrite');
    await tx.objectStore(TASKS_STORES.pendingSync).clear();
    console.log('[TasksDB] Sync queue cleared');
  }

  /**
   * Remove a specific sync action from queue
   */
  async removeSyncAction(id) {
    const db = await this.open();
    const tx = db.transaction(TASKS_STORES.pendingSync, 'readwrite');
    await tx.objectStore(TASKS_STORES.pendingSync).delete(id);
  }

  /**
   * Clear all data (for reset)
   */
  async clearAll() {
    const db = await this.open();
    const tx = db.transaction([TASKS_STORES.tasks, TASKS_STORES.lists, TASKS_STORES.series, TASKS_STORES.pendingSync], 'readwrite');

    await tx.objectStore(TASKS_STORES.tasks).clear();
    await tx.objectStore(TASKS_STORES.lists).clear();
    await tx.objectStore(TASKS_STORES.series).clear();
    await tx.objectStore(TASKS_STORES.pendingSync).clear();

    console.log('[TasksDB] All data cleared');
  }
}

// Export singleton instance
window.TasksDB = new TasksDB();
