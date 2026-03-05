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

  load();
})();
