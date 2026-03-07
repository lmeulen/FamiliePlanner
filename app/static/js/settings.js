/* global API */
(function () {
  const form              = document.getElementById('settings-form');
  const authToggle        = document.getElementById('auth-required');
  const photoToggle       = document.getElementById('dashboard-photo-enabled');
  const photoHeightRow    = document.getElementById('photo-height-row');
  const photoSlider       = document.getElementById('photo-height');
  const photoValEl        = document.getElementById('photo-height-val');
  const photoIntervalRow  = document.getElementById('photo-interval-row');
  const photoIntervalSlider = document.getElementById('photo-interval');
  const photoIntervalValEl = document.getElementById('photo-interval-val');
  const weatherToggle     = document.getElementById('weather-enabled');
  const weatherLocationRow = document.getElementById('weather-location-row');
  const weatherLocationInput = document.getElementById('weather-location');
  const saveStatus        = document.getElementById('save-status');

  function updatePhotoHeightRow() {
    const enabled = photoToggle.checked;
    photoHeightRow.style.opacity = enabled ? '' : '0.4';
    photoSlider.disabled = !enabled;
    photoIntervalRow.style.opacity = enabled ? '' : '0.4';
    photoIntervalSlider.disabled = !enabled;
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
    photoSlider.value = h;
    photoValEl.textContent = h;

    const interval = s.dashboard_photo_interval || 8;
    photoIntervalSlider.value = interval;
    photoIntervalValEl.textContent = interval;

    const theme = s.theme || 'system';
    const radio = form.querySelector(`input[name="theme"][value="${theme}"]`);
    if (radio) radio.checked = true;

    weatherToggle.checked = !!s.weather_enabled;
    weatherLocationInput.value = s.weather_location || 'Amsterdam,NL';

    updatePhotoHeightRow();
    updateWeatherLocationRow();
  }

  // ── Live slider label ────────────────────────────────────────
  photoSlider.addEventListener('input', () => {
    photoValEl.textContent = photoSlider.value;
  });

  photoIntervalSlider.addEventListener('input', () => {
    photoIntervalValEl.textContent = photoIntervalSlider.value;
  });

  photoToggle.addEventListener('change', updatePhotoHeightRow);
  weatherToggle.addEventListener('change', updateWeatherLocationRow);

  // ── Save ─────────────────────────────────────────────────────
  form.addEventListener('submit', async e => {
    e.preventDefault();
    const theme = form.querySelector('input[name="theme"]:checked')?.value || 'system';
    const payload = {
      auth_required: authToggle.checked,
      dashboard_photo_enabled: photoToggle.checked,
      dashboard_photo_height: parseInt(photoSlider.value, 10),
      dashboard_photo_interval: parseInt(photoIntervalSlider.value, 10),
      theme,
      weather_enabled: weatherToggle.checked,
      weather_location: weatherLocationInput.value.trim() || 'Amsterdam,NL',
    };

    await API.put('/api/settings/', payload);

    // Apply theme immediately
    applyTheme(theme);

    // Apply photo height immediately via CSS variable
    document.documentElement.style.setProperty('--dashboard-photo-height', photoSlider.value + 'vh');

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
      backupBtn.textContent = '⏳ Bezig...';

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

      backupBtn.textContent = '✅ Gedownload!';
      setTimeout(() => {
        backupBtn.textContent = '📥 Download Backup';
        backupBtn.disabled = false;
      }, 2000);
    } catch (err) {
      console.error('Backup error:', err);
      backupBtn.textContent = '❌ Fout!';
      setTimeout(() => {
        backupBtn.textContent = '📥 Download Backup';
        backupBtn.disabled = false;
      }, 2000);
    }
  });

  // Validate backup (dry-run)
  validateBtn.addEventListener('click', async () => {
    const file = restoreFile.files[0];
    if (!file) {
      alert('Selecteer eerst een backup bestand.');
      return;
    }

    try {
      validateBtn.disabled = true;
      validateBtn.textContent = '⏳ Valideren...';
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

        let html = `<div style="font-weight: 600; margin-bottom: 0.5rem;">✅ Backup is geldig</div>`;
        html += `<div style="margin-bottom: 0.25rem;">• Versie: ${result.version}</div>`;
        html += `<div style="margin-bottom: 0.25rem;">• Geëxporteerd: ${new Date(result.exported_at).toLocaleString('nl-NL')}</div>`;

        const totalRecords = Object.values(result.record_counts).reduce((sum, count) => sum + count, 0);
        html += `<div style="margin-bottom: 0.25rem;">• Totaal records: ${totalRecords}</div>`;

        if (result.warnings && result.warnings.length > 0) {
          html += `<div style="margin-top: 0.5rem; font-weight: 600;">⚠️ Waarschuwingen:</div>`;
          result.warnings.forEach(w => {
            html += `<div style="margin-left: 1rem; margin-top: 0.25rem;">• ${w}</div>`;
          });
        }

        validationResult.innerHTML = html;
        validateBtn.textContent = '✅ Geldig!';
      } else {
        validationResult.style.backgroundColor = 'var(--error-bg, #f8d7da)';
        validationResult.style.border = '1px solid var(--error-border, #f5c6cb)';
        validationResult.style.color = 'var(--error-text, #721c24)';

        let html = `<div style="font-weight: 600; margin-bottom: 0.5rem;">❌ Backup is ongeldig</div>`;
        if (result.errors && result.errors.length > 0) {
          html += `<div style="font-weight: 600; margin-top: 0.5rem;">Fouten:</div>`;
          result.errors.forEach(e => {
            html += `<div style="margin-left: 1rem; margin-top: 0.25rem;">• ${e}</div>`;
          });
        }

        validationResult.innerHTML = html;
        validateBtn.textContent = '❌ Ongeldig';
      }

      setTimeout(() => {
        validateBtn.textContent = '🔍 Valideer Backup';
        validateBtn.disabled = false;
      }, 3000);
    } catch (err) {
      console.error('Validation error:', err);
      validationResult.classList.remove('hidden');
      validationResult.style.backgroundColor = 'var(--error-bg, #f8d7da)';
      validationResult.style.border = '1px solid var(--error-border, #f5c6cb)';
      validationResult.style.color = 'var(--error-text, #721c24)';
      validationResult.innerHTML = `<div style="font-weight: 600;">❌ Validatie fout</div><div style="margin-top: 0.25rem;">${err.message}</div>`;

      validateBtn.textContent = '❌ Fout';
      setTimeout(() => {
        validateBtn.textContent = '🔍 Valideer Backup';
        validateBtn.disabled = false;
      }, 3000);
    }
  });

  // Restore backup
  restoreBtn.addEventListener('click', async () => {
    const file = restoreFile.files[0];
    if (!file) {
      alert('Selecteer eerst een backup bestand.');
      return;
    }

    const confirmed = confirm(
      '⚠️ WAARSCHUWING: Dit verwijdert ALLE huidige gegevens en vervangt ze met de backup.\n\n' +
      'Weet je zeker dat je wilt doorgaan?'
    );

    if (!confirmed) return;

    try {
      restoreBtn.disabled = true;
      restoreBtn.textContent = '⏳ Bezig met restoren...';

      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch('/api/settings/restore', {
        method: 'POST',
        headers: { 'X-CSRF-Token': getCsrfToken() },
        body: formData,
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Restore failed');
      }

      restoreBtn.textContent = '✅ Hersteld!';
      setTimeout(() => {
        window.location.reload();
      }, 1500);
    } catch (err) {
      console.error('Restore error:', err);
      alert('Restore mislukt: ' + err.message);
      restoreBtn.textContent = '📤 Restore Backup';
      restoreBtn.disabled = false;
    }
  });

  load();
})();
