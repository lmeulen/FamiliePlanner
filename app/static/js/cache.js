/**
 * LocalStorage Cache Utility met TTL en Multi-tab Sync
 *
 * Features:
 * - TTL (time-to-live) per cache entry
 * - Automatic expiration
 * - Cache invalidation patterns
 * - Multi-tab synchronization
 * - Cache statistics (hit/miss rate)
 */

class CacheManager {
  constructor() {
    this.prefix = 'fp_cache_';
    this.statsKey = 'fp_cache_stats';
    this.stats = this._loadStats();

    // Listen to storage events for multi-tab sync
    window.addEventListener('storage', (e) => {
      if (e.key && e.key.startsWith(this.prefix)) {
        this._handleStorageChange(e);
      }
    });

    // Cleanup expired entries on init
    this._cleanup();
  }

  /**
   * Get cache entry (returns null if expired or missing)
   */
  get(key) {
    const fullKey = this.prefix + key;

    try {
      const item = localStorage.getItem(fullKey);
      if (!item) {
        this._recordMiss();
        return null;
      }

      const parsed = JSON.parse(item);

      // Check expiration
      if (parsed.expires && Date.now() > parsed.expires) {
        localStorage.removeItem(fullKey);
        this._recordMiss();
        return null;
      }

      this._recordHit();
      return parsed.data;
    } catch (e) {
      console.error('[Cache] Error reading cache:', key, e);
      this._recordMiss();
      return null;
    }
  }

  /**
   * Set cache entry with TTL (in milliseconds)
   * @param {string} key - Cache key
   * @param {*} data - Data to cache (must be JSON serializable)
   * @param {number} ttl - Time to live in milliseconds (default: 5 minutes)
   */
  set(key, data, ttl = 300000) {
    const fullKey = this.prefix + key;

    try {
      const item = {
        data,
        expires: ttl > 0 ? Date.now() + ttl : null,
        created: Date.now()
      };

      localStorage.setItem(fullKey, JSON.stringify(item));

      // Dispatch event for multi-tab sync
      window.dispatchEvent(new CustomEvent('cacheUpdate', {
        detail: { key, data, ttl }
      }));

      return true;
    } catch (e) {
      // Handle quota exceeded
      if (e.name === 'QuotaExceededError') {
        console.warn('[Cache] Storage quota exceeded, clearing old entries');
        this._cleanup(true);

        // Retry
        try {
          localStorage.setItem(fullKey, JSON.stringify(item));
          return true;
        } catch (retryError) {
          console.error('[Cache] Failed to set cache after cleanup:', key);
          return false;
        }
      }

      console.error('[Cache] Error setting cache:', key, e);
      return false;
    }
  }

  /**
   * Remove specific cache entry
   */
  remove(key) {
    const fullKey = this.prefix + key;
    localStorage.removeItem(fullKey);

    window.dispatchEvent(new CustomEvent('cacheInvalidate', {
      detail: { key }
    }));
  }

  /**
   * Invalidate all cache entries matching pattern
   * @param {string|RegExp} pattern - Pattern to match keys
   */
  invalidate(pattern) {
    const regex = pattern instanceof RegExp ? pattern : new RegExp('^' + pattern);
    let count = 0;

    Object.keys(localStorage)
      .filter(key => key.startsWith(this.prefix))
      .forEach(fullKey => {
        const key = fullKey.substring(this.prefix.length);
        if (regex.test(key)) {
          localStorage.removeItem(fullKey);
          count++;
        }
      });

    if (count > 0) {
      console.log(`[Cache] Invalidated ${count} entries matching:`, pattern);

      window.dispatchEvent(new CustomEvent('cacheInvalidate', {
        detail: { pattern, count }
      }));
    }

    return count;
  }

  /**
   * Clear all cache entries
   */
  clear() {
    const count = this.invalidate(/.*/);
    this.stats = { hits: 0, misses: 0 };
    this._saveStats();
    console.log(`[Cache] Cleared all cache (${count} entries)`);
  }

  /**
   * Get cache statistics
   */
  getStats() {
    const total = this.stats.hits + this.stats.misses;
    const hitRate = total > 0 ? ((this.stats.hits / total) * 100).toFixed(1) : 0;

    return {
      hits: this.stats.hits,
      misses: this.stats.misses,
      total,
      hitRate: parseFloat(hitRate),
      entries: this._countEntries(),
      size: this._getStorageSize()
    };
  }

  /**
   * Reset statistics
   */
  resetStats() {
    this.stats = { hits: 0, misses: 0 };
    this._saveStats();
  }

  /**
   * Get all cache keys (for debugging)
   */
  keys() {
    return Object.keys(localStorage)
      .filter(key => key.startsWith(this.prefix))
      .map(key => key.substring(this.prefix.length));
  }

  /**
   * Internal: Cleanup expired entries
   */
  _cleanup(aggressive = false) {
    let removed = 0;
    const now = Date.now();

    Object.keys(localStorage)
      .filter(key => key.startsWith(this.prefix))
      .forEach(fullKey => {
        try {
          const item = JSON.parse(localStorage.getItem(fullKey));

          // Remove expired entries
          if (item.expires && now > item.expires) {
            localStorage.removeItem(fullKey);
            removed++;
          }
          // In aggressive mode, remove old entries (> 1 hour)
          else if (aggressive && (now - item.created) > 3600000) {
            localStorage.removeItem(fullKey);
            removed++;
          }
        } catch (e) {
          // Remove corrupted entries
          localStorage.removeItem(fullKey);
          removed++;
        }
      });

    if (removed > 0) {
      console.log(`[Cache] Cleanup removed ${removed} entries`);
    }
  }

  /**
   * Internal: Handle storage changes from other tabs
   */
  _handleStorageChange(event) {
    // Storage event fired in other tabs when localStorage changes
    const key = event.key.substring(this.prefix.length);

    if (event.newValue === null) {
      // Item was removed
      window.dispatchEvent(new CustomEvent('cacheRemoved', {
        detail: { key }
      }));
    } else {
      // Item was added/updated
      try {
        const item = JSON.parse(event.newValue);
        window.dispatchEvent(new CustomEvent('cacheUpdated', {
          detail: { key, data: item.data }
        }));
      } catch (e) {
        console.error('[Cache] Error parsing storage event:', e);
      }
    }
  }

  /**
   * Internal: Count cache entries
   */
  _countEntries() {
    return Object.keys(localStorage)
      .filter(key => key.startsWith(this.prefix))
      .length;
  }

  /**
   * Internal: Get approximate storage size
   */
  _getStorageSize() {
    let size = 0;
    Object.keys(localStorage)
      .filter(key => key.startsWith(this.prefix))
      .forEach(key => {
        size += (key.length + localStorage.getItem(key).length) * 2; // UTF-16
      });

    // Return human readable size
    if (size < 1024) return size + ' B';
    if (size < 1024 * 1024) return (size / 1024).toFixed(1) + ' KB';
    return (size / (1024 * 1024)).toFixed(1) + ' MB';
  }

  /**
   * Internal: Load statistics from localStorage
   */
  _loadStats() {
    try {
      const stats = localStorage.getItem(this.statsKey);
      return stats ? JSON.parse(stats) : { hits: 0, misses: 0 };
    } catch (e) {
      return { hits: 0, misses: 0 };
    }
  }

  /**
   * Internal: Save statistics to localStorage
   */
  _saveStats() {
    try {
      localStorage.setItem(this.statsKey, JSON.stringify(this.stats));
    } catch (e) {
      console.error('[Cache] Error saving stats:', e);
    }
  }

  /**
   * Internal: Record cache hit
   */
  _recordHit() {
    this.stats.hits++;
    this._saveStats();
  }

  /**
   * Internal: Record cache miss
   */
  _recordMiss() {
    this.stats.misses++;
    this._saveStats();
  }
}

// Create global singleton instance
window.Cache = new CacheManager();

// Expose cache statistics to console
console.log('[Cache] Manager initialized. Use Cache.getStats() to view statistics.');
