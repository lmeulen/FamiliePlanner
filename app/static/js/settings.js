/* global API */
(function () {
  const form              = document.getElementById('settings-form');
  const authToggle        = document.getElementById('auth-required');
  const photoToggle       = document.getElementById('dashboard-photo-enabled');
  const photoHeightRow    = document.getElementById('photo-height-row');
  const photoHeightInput  = document.getElementById('photo-height');
  const photoIntervalRow  = document.getElementById('photo-interval-row');
  const photoIntervalInput = document.getElementById('photo-interval');
  const screensaverTimeoutInput = document.getElementById('screensaver-timeout');
  const overviewRedirectTimeoutInput = document.getElementById('overview-redirect-timeout');
  const languageSelect    = document.getElementById('language');
  const timezoneSelect    = document.getElementById('timezone');
  const weatherToggle     = document.getElementById('weather-enabled');
  const weatherLocationRow = document.getElementById('weather-location-row');
  const weatherLocationInput = document.getElementById('weather-location');
  const mealieServerUrlInput = document.getElementById('mealie-server-url');
  const mealieApiTokenInput = document.getElementById('mealie-api-token');
  const saveStatus        = document.getElementById('save-status');

  function t(key, vars = {}) {
    return window.FP?.t ? window.FP.t(key, vars) : key;
  }

  function clampNumber(input, fallback) {
    const min = Number(input.min);
    const max = Number(input.max);
    const step = Number(input.step || 1);
    const raw = Number(input.value);
    const safe = Number.isFinite(raw) ? raw : fallback;
    const bounded = Math.max(min, Math.min(max, safe));
    const normalized = Math.round(bounded / step) * step;
    input.value = String(normalized);
    return normalized;
  }

  function updatePhotoHeightRow() {
    const enabled = photoToggle.checked;
    photoHeightRow.style.opacity = enabled ? '' : '0.4';
    photoHeightInput.disabled = !enabled;
    photoIntervalRow.style.opacity = enabled ? '' : '0.4';
    photoIntervalInput.disabled = !enabled;
  }

  function updateWeatherLocationRow() {
    const enabled = weatherToggle.checked;
    weatherLocationRow.style.opacity = enabled ? '' : '0.4';
    weatherLocationInput.disabled = !enabled;
  }

  // ── Load current settings ────────────────────────────────────
  async function load() {
    const s = await API.get('/api/settings/');
    if (!s) return;

    authToggle.checked  = !!s.auth_required;
    photoToggle.checked = s.dashboard_photo_enabled !== false;

    const h = s.dashboard_photo_height || 35;
    photoHeightInput.value = h;

    const interval = s.dashboard_photo_interval || 8;
    photoIntervalInput.value = interval;

    const screensaverSeconds = s.dashboard_screensaver_seconds ?? s.idle_redirect_seconds ?? 60;
    const screensaverMinutes = Math.max(
      0,
      Math.min(60, screensaverSeconds <= 0 ? 0 : Math.max(1, Math.round(screensaverSeconds / 60)))
    );
    screensaverTimeoutInput.value = screensaverMinutes;

    const overviewRedirectTimeout = s.overview_redirect_seconds || s.idle_redirect_seconds || 60;
    overviewRedirectTimeoutInput.value = overviewRedirectTimeout;

    clampNumber(photoHeightInput, 35);
    clampNumber(photoIntervalInput, 8);
    clampNumber(screensaverTimeoutInput, 0);
    clampNumber(overviewRedirectTimeoutInput, 60);

    if (languageSelect) {
      languageSelect.value = s.language || 'nl';
    }

    if (timezoneSelect) {
      timezoneSelect.value = s.timezone || 'UTC';
    }

    const theme = s.theme || 'system';
    const radio = form.querySelector(`input[name="theme"][value="${theme}"]`);
    if (radio) radio.checked = true;

    weatherToggle.checked = !!s.weather_enabled;
    weatherLocationInput.value = s.weather_location || 'Amsterdam,NL';

    mealieServerUrlInput.value = s.mealie_server_url || '';
    mealieApiTokenInput.value = s.mealie_api_token || '';

    updatePhotoHeightRow();
    updateWeatherLocationRow();
  }

  [photoHeightInput, photoIntervalInput, screensaverTimeoutInput, overviewRedirectTimeoutInput]
    .forEach(input => {
      input?.addEventListener('change', () => clampNumber(input, Number(input.value || 0)));
    });

  photoToggle.addEventListener('change', updatePhotoHeightRow);
  weatherToggle.addEventListener('change', updateWeatherLocationRow);

  // ── Save ─────────────────────────────────────────────────────
  form.addEventListener('submit', async e => {
    e.preventDefault();
    const theme = form.querySelector('input[name="theme"]:checked')?.value || 'system';
    const photoHeight = clampNumber(photoHeightInput, 35);
    const photoInterval = clampNumber(photoIntervalInput, 8);
    const screensaverMinutes = clampNumber(screensaverTimeoutInput, 0);
    const overviewRedirectSeconds = clampNumber(overviewRedirectTimeoutInput, 60);

    const payload = {
      auth_required: authToggle.checked,
      dashboard_photo_enabled: photoToggle.checked,
      dashboard_photo_height: photoHeight,
      dashboard_photo_interval: photoInterval,
      dashboard_screensaver_seconds: screensaverMinutes * 60,
      overview_redirect_seconds: overviewRedirectSeconds,
      language: languageSelect?.value || 'nl',
      timezone: timezoneSelect?.value || 'UTC',
      theme,
      weather_enabled: weatherToggle.checked,
      weather_location: weatherLocationInput.value.trim() || 'Amsterdam,NL',
      mealie_server_url: mealieServerUrlInput.value.trim(),
      mealie_api_token: mealieApiTokenInput.value.trim(),
    };

    const updatedSettings = await API.put('/api/settings/', payload);
    window.FP?.setSettings?.(updatedSettings);

    // Apply language immediately
    window.FP?.setLanguage(payload.language);
    window.FP?.translateDocument();

    // Apply theme immediately
    applyTheme(theme);

    // Apply photo height immediately via CSS variable
    document.documentElement.style.setProperty('--dashboard-photo-height', photoHeightInput.value + 'vh');

    saveStatus.classList.remove('hidden');
    setTimeout(() => saveStatus.classList.add('hidden'), 2500);
  });

  // ── Apply theme (mirrors theme.js logic) ─────────────────────
  function applyTheme(t) {
    const html = document.documentElement;
    if (t === 'system') {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      html.setAttribute('data-theme', prefersDark ? 'dark' : 'light');
      localStorage.removeItem('fp-theme');
    } else {
      html.setAttribute('data-theme', t);
      localStorage.setItem('fp-theme', t);
    }
  }

  // ── Backup & Restore ─────────────────────────────────────────
  const backupBtn = document.getElementById('backup-btn');
  const restoreBtn = document.getElementById('restore-btn');
  const validateBtn = document.getElementById('validate-btn');
  const restoreFile = document.getElementById('restore-file');
  const validationResult = document.getElementById('validation-result');

  function getCsrfToken() {
    return document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') ?? '';
  }

  // Download backup
  backupBtn.addEventListener('click', async () => {
    try {
      backupBtn.disabled = true;
      backupBtn.textContent = t('settings.busy');

      const response = await fetch('/api/settings/backup', {
        method: 'GET',
        headers: { 'X-CSRF-Token': getCsrfToken() },
      });

      if (!response.ok) throw new Error('Backup failed');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = response.headers.get('Content-Disposition')?.split('filename=')[1]?.replace(/"/g, '') || 'backup.json';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      backupBtn.textContent = t('settings.downloaded');
      setTimeout(() => {
        backupBtn.textContent = t('settings.downloadBackup');
        backupBtn.disabled = false;
      }, 2000);
    } catch (err) {
      console.error('Backup error:', err);
      backupBtn.textContent = t('settings.error');
      setTimeout(() => {
        backupBtn.textContent = t('settings.downloadBackup');
        backupBtn.disabled = false;
      }, 2000);
    }
  });

  // Validate backup (dry-run)
  validateBtn.addEventListener('click', async () => {
    const file = restoreFile.files[0];
    if (!file) {
      alert(t('settings.selectBackupFirst'));
      return;
    }

    try {
      validateBtn.disabled = true;
      validateBtn.textContent = t('settings.validating');
      validationResult.classList.add('hidden');

      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/settings/restore?dry_run=true', {
        method: 'POST',
        headers: { 'X-CSRF-Token': getCsrfToken() },
        body: formData,
      });

      const result = await response.json();

      // Display validation result
      validationResult.classList.remove('hidden');

      if (result.valid) {
        validationResult.style.backgroundColor = 'var(--success-bg, #d4edda)';
        validationResult.style.border = '1px solid var(--success-border, #c3e6cb)';
        validationResult.style.color = 'var(--success-text, #155724)';

        let html = `<div style="font-weight: 600; margin-bottom: 0.5rem;">${t('settings.backupValid')}</div>`;
        html += `<div style="margin-bottom: 0.25rem;">• ${t('settings.version')}: ${result.version}</div>`;
        html += `<div style="margin-bottom: 0.25rem;">• ${t('settings.exportedAt')}: ${new Date(result.exported_at).toLocaleString(window.FP?.getLocale?.() || 'nl-NL')}</div>`;

        const totalRecords = Object.values(result.record_counts).reduce((sum, count) => sum + count, 0);
        html += `<div style="margin-bottom: 0.25rem;">• ${t('settings.totalRecords')}: ${totalRecords}</div>`;

        if (result.warnings && result.warnings.length > 0) {
          html += `<div style="margin-top: 0.5rem; font-weight: 600;">${t('settings.warnings')}</div>`;
          result.warnings.forEach(w => {
            html += `<div style="margin-left: 1rem; margin-top: 0.25rem;">• ${w}</div>`;
          });
        }

        validationResult.innerHTML = html;
        validateBtn.textContent = t('settings.valid');
      } else {
        validationResult.style.backgroundColor = 'var(--error-bg, #f8d7da)';
        validationResult.style.border = '1px solid var(--error-border, #f5c6cb)';
        validationResult.style.color = 'var(--error-text, #721c24)';

        let html = `<div style="font-weight: 600; margin-bottom: 0.5rem;">${t('settings.backupInvalid')}</div>`;
        if (result.errors && result.errors.length > 0) {
          html += `<div style="font-weight: 600; margin-top: 0.5rem;">${t('settings.validationErrors')}</div>`;
          result.errors.forEach(e => {
            html += `<div style="margin-left: 1rem; margin-top: 0.25rem;">• ${e}</div>`;
          });
        }

        validationResult.innerHTML = html;
        validateBtn.textContent = t('settings.invalid');
      }

      setTimeout(() => {
        validateBtn.textContent = t('settings.validateBackup');
        validateBtn.disabled = false;
      }, 3000);
    } catch (err) {
      console.error('Validation error:', err);
      validationResult.classList.remove('hidden');
      validationResult.style.backgroundColor = 'var(--error-bg, #f8d7da)';
      validationResult.style.border = '1px solid var(--error-border, #f5c6cb)';
      validationResult.style.color = 'var(--error-text, #721c24)';
      validationResult.innerHTML = `<div style="font-weight: 600;">${t('settings.validationError')}</div><div style="margin-top: 0.25rem;">${err.message}</div>`;

      validateBtn.textContent = t('settings.error');
      setTimeout(() => {
        validateBtn.textContent = t('settings.validateBackup');
        validateBtn.disabled = false;
      }, 3000);
    }
  });

  // Restore backup
  restoreBtn.addEventListener('click', async () => {
    const file = restoreFile.files[0];
    if (!file) {
      alert(t('settings.selectBackupFirst'));
      return;
    }

    const confirmed = confirm(t('settings.confirmRestore'));

    if (!confirmed) return;

    try {
      restoreBtn.disabled = true;
      restoreBtn.textContent = t('settings.restoring');

      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/settings/restore', {
        method: 'POST',
        headers: { 'X-CSRF-Token': getCsrfToken() },
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.details || error.detail || 'Restore failed');
      }

      restoreBtn.textContent = t('settings.restored');
      setTimeout(() => {
        window.location.reload();
      }, 1500);
    } catch (err) {
      console.error('Restore error:', err);
      alert(t('settings.restoreFailed', { message: err.message }));
      restoreBtn.textContent = t('settings.restoreBackup');
      restoreBtn.disabled = false;
    }
  });

  // ── Cache Management ─────────────────────────────────────────
  const cacheHitRateEl = document.getElementById('cache-hit-rate');
  const cacheEntriesEl = document.getElementById('cache-entries');
  const cacheHitsEl = document.getElementById('cache-hits');
  const cacheMissesEl = document.getElementById('cache-misses');
  const cacheSizeEl = document.getElementById('cache-size');
  const clearCacheBtn = document.getElementById('clear-cache-btn');

  function updateCacheStats() {
    if (!window.Cache) return;

    const stats = Cache.getStats();
    cacheHitRateEl.textContent = stats.hitRate + '%';
    cacheEntriesEl.textContent = stats.entries;
    cacheHitsEl.textContent = stats.hits;
    cacheMissesEl.textContent = stats.misses;
    cacheSizeEl.textContent = stats.size;
  }

  clearCacheBtn?.addEventListener('click', () => {
    if (!confirm(t('settings.clearCacheConfirm'))) {
      return;
    }

    Cache.clear();
    Toast.show(t('settings.cacheCleared'), 'success');
    updateCacheStats();
  });

  // Update cache stats every 2 seconds
  updateCacheStats();
  setInterval(updateCacheStats, 2000);

  // ── PWA Install ───────────────────────────────────────────────
  const pwaInstallSection = document.getElementById('pwa-install-section');
  const pwaInstallBtn = document.getElementById('pwa-install-btn');
  let deferredPrompt = null;

  // Check if already installed
  const isInstalled = window.matchMedia('(display-mode: standalone)').matches ||
                      window.navigator.standalone === true;

  if (!isInstalled) {
    // Listen for beforeinstallprompt event
    window.addEventListener('beforeinstallprompt', (e) => {
      console.log('[PWA] Install prompt available in settings');
      e.preventDefault();
      deferredPrompt = e;

      // Show install section
      if (pwaInstallSection) {
        pwaInstallSection.style.display = '';
      }
    });

    // Handle install button click
    pwaInstallBtn?.addEventListener('click', async () => {
      if (!deferredPrompt) {
        Toast.show('Installatie is momenteel niet beschikbaar. Probeer het later opnieuw.', 'warning');
        return;
      }

      // Show browser's install prompt
      deferredPrompt.prompt();

      // Wait for user choice
      const { outcome } = await deferredPrompt.userChoice;
      console.log('[PWA] User choice:', outcome);

      if (outcome === 'accepted') {
        Toast.show('App wordt geïnstalleerd...', 'success');
        if (pwaInstallSection) {
          pwaInstallSection.style.display = 'none';
        }
      } else {
        Toast.show('Installatie geannuleerd', 'info');
      }

      deferredPrompt = null;
    });

    // Listen for successful installation
    window.addEventListener('appinstalled', () => {
      console.log('[PWA] App installed successfully from settings');
      Toast.show('App succesvol geïnstalleerd! 🎉', 'success');
      if (pwaInstallSection) {
        pwaInstallSection.style.display = 'none';
      }
      deferredPrompt = null;
    });
  }

  // ── Calendar Subscription ────────────────────────────────
  const calendarSubUrlInput = document.getElementById('calendar-sub-url');
  const copySubUrlBtn = document.getElementById('copy-sub-url-btn');
  const memberSubscriptionUrlsDiv = document.getElementById('member-subscription-urls');

  function loadSubscriptionUrl() {
    // Build full URL (no token needed - public endpoint)
    const baseUrl = window.location.origin;
    const subscriptionUrl = `${baseUrl}/api/agenda/export/calendar.ics`;
    calendarSubUrlInput.value = subscriptionUrl;

    // Load family members for per-member URLs
    API.get('/api/family/').then(members => {
      if (members && members.length > 0) {
        memberSubscriptionUrlsDiv.innerHTML = '';
        members.forEach(member => {
          const memberUrl = `${baseUrl}/api/agenda/export/calendar.ics?member_id=${member.id}`;

          const container = document.createElement('div');
          container.style.cssText = 'display: flex; gap: 0.5rem; align-items: center;';

          const label = document.createElement('span');
          label.textContent = member.avatar + ' ' + member.name;
          label.style.cssText = 'min-width: 120px; font-weight: 500;';

          const input = document.createElement('input');
          input.type = 'text';
          input.value = memberUrl;
          input.readOnly = true;
          input.style.cssText = 'flex: 1; padding: 0.35rem 0.5rem; border: 1px solid var(--border); border-radius: 6px; background: var(--surface-alt); color: var(--text); font-family: monospace; font-size: 0.85rem;';

          const copyBtn = document.createElement('button');
          copyBtn.type = 'button';
          copyBtn.className = 'btn btn--secondary';
          copyBtn.textContent = '📋';
          copyBtn.style.whiteSpace = 'nowrap';
          copyBtn.onclick = () => {
            navigator.clipboard.writeText(memberUrl);
            Toast.show(`URL voor ${member.name} gekopieerd!`, 'success');
          };

          container.appendChild(label);
          container.appendChild(input);
          container.appendChild(copyBtn);
          memberSubscriptionUrlsDiv.appendChild(container);
        });
      }
    }).catch(err => {
      console.error('Failed to load family members:', err);
    });
  }

  copySubUrlBtn?.addEventListener('click', () => {
    const url = calendarSubUrlInput.value;
    if (url) {
      navigator.clipboard.writeText(url);
      Toast.show('Abonnements-URL gekopieerd!', 'success');
    }
  });

  // Load subscription URL on page load
  loadSubscriptionUrl();

  // ── Database Cleanup Handlers ─────────────────────────────────

  async function clearDatabase(type, endpoint, confirmMessage) {
    if (!confirm(confirmMessage)) return;

    // Double confirmation for destructive action
    if (!confirm('⚠️ LET OP: Dit kan NIET ongedaan worden! Weet je het zeker?')) return;

    try {
      await API.delete(endpoint);
      Toast.show(`✅ ${type} gewist`, 'success');

      // Invalidate relevant caches
      FP.invalidateCache(type.toLowerCase());
    } catch (err) {
      Toast.show(`❌ Fout bij wissen: ${err.message}`, 'error');
    }
  }

  document.getElementById('clear-agenda-btn')?.addEventListener('click', () => {
    clearDatabase(
      'Agenda',
      '/api/agenda/all',
      '🗑️ Alle agenda-items en series verwijderen?\n\nDit verwijdert ALLE afspraken en herhalingen.'
    );
  });

  document.getElementById('clear-tasks-btn')?.addEventListener('click', () => {
    clearDatabase(
      'Taken',
      '/api/tasks/all',
      '🗑️ Alle taken, lijsten en series verwijderen?\n\nDit verwijdert ALLE taken en takenlijsten.'
    );
  });

  document.getElementById('clear-meals-btn')?.addEventListener('click', () => {
    clearDatabase(
      'Maaltijden',
      '/api/meals/all',
      '🗑️ Alle maaltijden verwijderen?\n\nDit verwijdert ALLE geplande maaltijden.'
    );
  });

  document.getElementById('clear-grocery-btn')?.addEventListener('click', () => {
    clearDatabase(
      'Boodschappen',
      '/api/grocery/all',
      '🗑️ Alle boodschappenlijst items verwijderen?\n\nDit verwijdert ALLE boodschappen en leerdata.'
    );
  });

  document.getElementById('clear-birthdays-btn')?.addEventListener('click', () => {
    clearDatabase(
      'Verjaardagen',
      '/api/birthdays/all',
      '🗑️ Alle verjaardagen verwijderen?\n\nDit verwijdert ALLE verjaardagen en hun gekoppelde agenda-items.'
    );
  });

  document.getElementById('clear-family-btn')?.addEventListener('click', () => {
    clearDatabase(
      'Gezinsleden',
      '/api/family/all',
      '🗑️ Alle gezinsleden verwijderen?\n\n⚠️ WAARSCHUWING: Dit verwijdert alle gezinsleden en hun koppelingen aan items.\nDe items zelf blijven behouden maar zonder toegewezen personen.'
    );
  });

  load();
})();
