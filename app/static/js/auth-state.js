/* ================================================================
   auth-state.js – Offline authentication state management
   ================================================================

   Manages authentication state for offline access. Users must log in
   once while online to gain offline access. This provides device-level
   security without requiring complex JWT token management.

   Security model:
   - First login must be online (server validates credentials)
   - Successful online login sets 'wasAuthenticated' flag in localStorage
   - Offline access granted only if previously authenticated
   - Logout clears the flag (requires re-login online)
   - Relies on device PIN/biometrics for physical security

   ================================================================ */

class AuthState {
  constructor() {
    this.STORAGE_KEY = 'fp_was_authenticated';
    this.LAST_ONLINE_KEY = 'fp_last_online';
  }

  /**
   * Mark user as authenticated (call after successful online login)
   */
  setAuthenticated() {
    localStorage.setItem(this.STORAGE_KEY, 'true');
    localStorage.setItem(this.LAST_ONLINE_KEY, new Date().toISOString());
    console.log('[AuthState] User authenticated, offline access granted');
  }

  /**
   * Clear authentication state (call on logout)
   */
  clearAuthenticated() {
    localStorage.removeItem(this.STORAGE_KEY);
    localStorage.removeItem(this.LAST_ONLINE_KEY);
    console.log('[AuthState] Authentication cleared, offline access revoked');
  }

  /**
   * Check if user was previously authenticated online
   */
  wasAuthenticated() {
    return localStorage.getItem(this.STORAGE_KEY) === 'true';
  }

  /**
   * Get last time user was online (for informational purposes)
   */
  getLastOnlineTime() {
    const timestamp = localStorage.getItem(this.LAST_ONLINE_KEY);
    return timestamp ? new Date(timestamp) : null;
  }

  /**
   * Update last online time (call when successfully connecting to server)
   */
  updateLastOnlineTime() {
    if (this.wasAuthenticated()) {
      localStorage.setItem(this.LAST_ONLINE_KEY, new Date().toISOString());
    }
  }

  /**
   * Check if offline access is allowed
   * Returns { allowed: boolean, reason?: string }
   */
  checkOfflineAccess() {
    const isOnline = navigator.onLine;

    // Online users always have access (handled by server auth)
    if (isOnline) {
      return { allowed: true };
    }

    // Offline users need previous authentication
    if (!this.wasAuthenticated()) {
      return {
        allowed: false,
        reason: 'Je moet eerst online inloggen voordat je offline toegang krijgt'
      };
    }

    return { allowed: true };
  }

  /**
   * Show offline lock screen
   */
  showOfflineLockScreen(reason) {
    const existing = document.getElementById('offline-lock-screen');
    if (existing) return;

    const lockScreen = document.createElement('div');
    lockScreen.id = 'offline-lock-screen';
    lockScreen.className = 'offline-lock-screen';
    lockScreen.innerHTML = `
      <div class="offline-lock-content">
        <div class="offline-lock-icon">🔒</div>
        <h2>Offline toegang niet beschikbaar</h2>
        <p>${reason || 'Je moet eerst online inloggen'}</p>
        <p class="offline-lock-hint">Verbind met het internet en log in om offline toegang te krijgen.</p>
        <button class="btn btn--primary" onclick="window.location.reload()">Opnieuw proberen</button>
      </div>
    `;

    document.body.appendChild(lockScreen);
  }

  /**
   * Hide offline lock screen
   */
  hideOfflineLockScreen() {
    const lockScreen = document.getElementById('offline-lock-screen');
    if (lockScreen) {
      lockScreen.remove();
    }
  }

  /**
   * Initialize auth state monitoring
   */
  init() {
    // Update last online time when coming back online
    window.addEventListener('online', () => {
      this.updateLastOnlineTime();
      this.hideOfflineLockScreen();
    });

    // Check offline access when going offline
    window.addEventListener('offline', () => {
      const access = this.checkOfflineAccess();
      if (!access.allowed) {
        this.showOfflineLockScreen(access.reason);
      }
    });

    // Check on page load
    const access = this.checkOfflineAccess();
    if (!access.allowed) {
      this.showOfflineLockScreen(access.reason);
    }

    console.log('[AuthState] Initialized', {
      wasAuthenticated: this.wasAuthenticated(),
      lastOnline: this.getLastOnlineTime(),
      isOnline: navigator.onLine
    });
  }
}

// Export singleton instance
window.AuthState = new AuthState();
