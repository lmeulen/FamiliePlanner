/* global API */
(function () {
  const form           = document.getElementById('settings-form');
  const authToggle     = document.getElementById('auth-required');
  const photoToggle    = document.getElementById('dashboard-photo-enabled');
  const photoHeightRow = document.getElementById('photo-height-row');
  const photoSlider    = document.getElementById('photo-height');
  const photoValEl     = document.getElementById('photo-height-val');
  const saveStatus     = document.getElementById('save-status');

  function updatePhotoHeightRow() {
    const enabled = photoToggle.checked;
    photoHeightRow.style.opacity = enabled ? '' : '0.4';
    photoSlider.disabled = !enabled;
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

    const theme = s.theme || 'system';
    const radio = form.querySelector(`input[name="theme"][value="${theme}"]`);
    if (radio) radio.checked = true;

    updatePhotoHeightRow();
  }

  // ── Live slider label ────────────────────────────────────────
  photoSlider.addEventListener('input', () => {
    photoValEl.textContent = photoSlider.value;
  });

  photoToggle.addEventListener('change', updatePhotoHeightRow);

  // ── Save ─────────────────────────────────────────────────────
  form.addEventListener('submit', async e => {
    e.preventDefault();
    const theme = form.querySelector('input[name="theme"]:checked')?.value || 'system';
    const payload = {
      auth_required: authToggle.checked,
      dashboard_photo_enabled: photoToggle.checked,
      dashboard_photo_height: parseInt(photoSlider.value, 10),
      theme,
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
  const restoreFile = document.getElementById('restore-file');

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
