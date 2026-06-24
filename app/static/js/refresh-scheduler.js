/* ================================================================
   refresh-scheduler.js – polling + midnight rollover helper
   ================================================================ */
(function () {
  class RefreshScheduler {
    constructor(options = {}) {
      this.name = options.name || "default";
      this.intervalSeconds = RefreshScheduler.resolveIntervalSeconds(options.intervalSeconds);
      this.onTick = typeof options.onTick === "function" ? options.onTick : null;
      this.reloadOnDateChange = options.reloadOnDateChange !== false;
      this.runImmediately = options.runImmediately === true;
      this._tickTimer = null;
      this._midnightTimer = null;
      this._isTickRunning = false;
      this._lastDateKey = new Date().toDateString();
      this._started = false;
    }

    static resolveIntervalSeconds(candidate) {
      const fromConfig = Number(window.FP_CONFIG?.dataRefreshIntervalSeconds);
      const raw = Number.isFinite(Number(candidate)) ? Number(candidate) : fromConfig;
      if (!Number.isFinite(raw)) return 120;
      if (raw <= 0) return 0;
      return Math.max(30, Math.floor(raw));
    }

    start() {
      if (this._started) return;
      this._started = true;

      if (this.reloadOnDateChange) {
        this._midnightTimer = window.setInterval(() => {
          this.checkMidnightAndReload();
        }, 30_000);
      }

      if (this.intervalSeconds <= 0 || !this.onTick) return;

      if (this.runImmediately) {
        this.tick();
      }

      this._tickTimer = window.setInterval(() => {
        this.tick();
      }, this.intervalSeconds * 1000);
    }

    stop() {
      if (this._tickTimer) {
        window.clearInterval(this._tickTimer);
        this._tickTimer = null;
      }
      if (this._midnightTimer) {
        window.clearInterval(this._midnightTimer);
        this._midnightTimer = null;
      }
      this._started = false;
    }

    async tick() {
      if (!this.onTick || this._isTickRunning) return;
      this._isTickRunning = true;
      try {
        await this.onTick();
      } catch (err) {
        console.error(`[RefreshScheduler:${this.name}] tick failed`, err);
      } finally {
        this._isTickRunning = false;
      }
    }

    checkMidnightAndReload() {
      const nowKey = new Date().toDateString();
      if (nowKey === this._lastDateKey) return;
      this._lastDateKey = nowKey;
      window.location.reload();
    }
  }

  window.RefreshScheduler = RefreshScheduler;
})();
