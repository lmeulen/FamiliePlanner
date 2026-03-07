/* ================================================================
   app.js – Global utilities, shared state, date helpers
   ================================================================ */
window.FP = (() => {
  // ── HTML escaping (XSS prevention) ───────────────────────────
  const _esc_map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
  function esc(str) {
    if (str == null) return '';
    return String(str).replace(/[&<>"']/g, c => _esc_map[c]);
  }

  // ── Shared family member state ────────────────────────────────
  let _members = [];

  async function loadMembers() {
    try {
      _members = await API.get('/api/family/');
    } catch {
      _members = [];
    }
    return _members;
  }

  function getMembers() { return _members; }

  function getMember(id) { return _members.find(m => m.id === id); }

  function memberColor(id) {
    const m = getMember(id);
    return m ? m.color : '#9EA7C4';
  }

  function memberAvatar(id) {
    const m = getMember(id);
    return m ? m.avatar : '👤';
  }

  // ── Date helpers ──────────────────────────────────────────────
  const NL_DAYS  = ['zo','ma','di','wo','do','vr','za'];
  const NL_DAYS_FULL = ['Zondag','Maandag','Dinsdag','Woensdag','Donderdag','Vrijdag','Zaterdag'];
  const NL_MONTHS = ['januari','februari','maart','april','mei','juni',
                     'juli','augustus','september','oktober','november','december'];
  const NL_MONTHS_SHORT = ['jan','feb','mrt','apr','mei','jun','jul','aug','sep','okt','nov','dec'];

  function today()  { return new Date(); }
  function todayStr() {
    const d = new Date();
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
  }

  function pad(n) { return String(n).padStart(2, '0'); }

  function formatDate(d) {
    if (!d) return '';
    const dt = d instanceof Date ? d : new Date(d);
    return `${pad(dt.getDate())} ${NL_MONTHS[dt.getMonth()]} ${dt.getFullYear()}`;
  }

  function formatTime(d) {
    if (!d) return '';
    const dt = d instanceof Date ? d : new Date(d);
    return `${pad(dt.getHours())}:${pad(dt.getMinutes())}`;
  }

  function formatDateShort(d) {
    if (!d) return '';
    const dt = d instanceof Date ? d : new Date(d);
    return `${pad(dt.getDate())} ${NL_MONTHS_SHORT[dt.getMonth()]}`;
  }

  function dayName(d) {
    const dt = d instanceof Date ? d : new Date(d);
    return NL_DAYS[dt.getDay()];
  }

  function dayNameFull(d) {
    const dt = d instanceof Date ? d : new Date(d);
    return NL_DAYS_FULL[dt.getDay()];
  }

  function isToday(d) {
    const dt = d instanceof Date ? d : new Date(d);
    const t  = new Date();
    return dt.getFullYear() === t.getFullYear() &&
           dt.getMonth()    === t.getMonth()    &&
           dt.getDate()     === t.getDate();
  }

  function isSameDay(a, b) {
    const da = a instanceof Date ? a : new Date(a);
    const db = b instanceof Date ? b : new Date(b);
    return da.getFullYear() === db.getFullYear() &&
           da.getMonth()    === db.getMonth()    &&
           da.getDate()     === db.getDate();
  }

  function addDays(d, n) {
    const dt = new Date(d);
    dt.setDate(dt.getDate() + n);
    return dt;
  }

  function startOfWeek(d) {
    const dt = new Date(d);
    const day = dt.getDay();          // 0=sun
    const diff = (day === 0) ? -6 : 1 - day; // Monday first
    dt.setDate(dt.getDate() + diff);
    dt.setHours(0,0,0,0);
    return dt;
  }

  function toLocalDatetimeInput(d) {
    const dt = d instanceof Date ? d : new Date(d);
    return `${dt.getFullYear()}-${pad(dt.getMonth()+1)}-${pad(dt.getDate())}T${pad(dt.getHours())}:${pad(dt.getMinutes())}`;
  }

  function mealTypeLabel(t) {
    return { breakfast:'🌅 Ontbijt', lunch:'☀️ Lunch', dinner:'🌙 Diner', snack:'🍎 Tussendoor' }[t] || t;
  }

  // ── Header date + time ──────────────────────────────────────
  function renderHeaderDate() {
    const el = document.getElementById('header-date');
    if (!el) return;
    const d  = new Date();
    const hh = pad(d.getHours());
    const mm = pad(d.getMinutes());
    el.innerHTML =
      `<div class="header-date-line">${NL_DAYS_FULL[d.getDay()]} ${d.getDate()} ${NL_MONTHS[d.getMonth()]}</div>` +
      `<div class="header-time-line">${hh}:${mm}</div>`;
  }

  // ── Member chips builder ──────────────────────────────────────
  async function buildMemberChips(containerId, onFilter) {
    await loadMembers();
    const container = document.getElementById(containerId);
    if (!container) return;

    _members.forEach(m => {
      const btn = document.createElement('button');
      btn.className = 'chip';
      btn.dataset.member = m.id;
      btn.innerHTML = `<span class="chip-avatar">${m.avatar}</span>${esc(m.name)}`;
      btn.style.setProperty('--chip-color', m.color);
      container.appendChild(btn);
    });

    container.addEventListener('click', e => {
      const btn = e.target.closest('.chip');
      if (!btn) return;
      container.querySelectorAll('.chip').forEach(c => c.classList.remove('chip--active'));
      btn.classList.add('chip--active');
      const val = btn.dataset.member;
      onFilter(val === 'all' ? null : parseInt(val));
    });
  }

  // ── Member picker (multi-select toggle buttons) ───────────────
  function buildMemberPicker(containerId, selectedIds = []) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';
    _members.forEach(m => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'member-toggle-btn' + (selectedIds.includes(m.id) ? ' active' : '');
      btn.dataset.memberId = m.id;
      btn.textContent = `${m.avatar} ${m.name}`;
      btn.style.setProperty('--member-color', m.color || '#ccc');
      btn.addEventListener('click', () => btn.classList.toggle('active'));
      container.appendChild(btn);
    });
  }

  function getSelectedMemberIds(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return [];
    return Array.from(container.querySelectorAll('.member-toggle-btn.active'))
      .map(btn => parseInt(btn.dataset.memberId, 10));
  }

  // ── Populate member <select> inside a form ────────────────────
  function populateMemberSelect(sel, includeAll = true) {
    if (!sel) return;
    sel.innerHTML = '';
    if (includeAll) {
      const opt = document.createElement('option');
      opt.value = ''; opt.textContent = 'Heel gezin / Iedereen';
      sel.appendChild(opt);
    }
    _members.forEach(m => {
      const opt = document.createElement('option');
      opt.value = m.id;
      opt.textContent = `${m.avatar} ${m.name}`;
      sel.appendChild(opt);
    });
  }

  // ── Init ──────────────────────────────────────────────────────
  // settingsReady resolves once /api/settings/ has been fetched.
  // Other modules can await FP.settingsReady before checking FP.settings.
  let _settingsResolve;
  let _settings = null;
  const settingsReady = new Promise(res => { _settingsResolve = res; });

  async function applyPersistedSettings() {
    try {
      const s = await API.get('/api/settings/');
      if (s) {
        _settings = s;
        // Photo height CSS variable
        if (s.dashboard_photo_height) {
          document.documentElement.style.setProperty(
            '--dashboard-photo-height', s.dashboard_photo_height + 'vh'
          );
        }
        // Theme (only if not already overridden by localStorage)
        if (s.theme && s.theme !== 'system' && !localStorage.getItem('fp-theme')) {
          document.documentElement.setAttribute('data-theme', s.theme);
          localStorage.setItem('fp-theme', s.theme);
        }
      }
    } catch { /* silently ignore – non-critical */ }
    finally { _settingsResolve(); }
  }

  document.addEventListener('DOMContentLoaded', () => {
    renderHeaderDate();
    setInterval(renderHeaderDate, 30_000);  // update clock every 30s
    loadMembers();   // pre-load for all pages
    applyPersistedSettings();
  });

  return {
    esc,
    loadMembers, getMembers, getMember, memberColor, memberAvatar,
    today, todayStr, pad, formatDate, formatTime, formatDateShort,
    dayName, dayNameFull, isToday, isSameDay, addDays, startOfWeek,
    toLocalDatetimeInput, mealTypeLabel,
    buildMemberChips, populateMemberSelect, buildMemberPicker, getSelectedMemberIds,
    NL_DAYS, NL_DAYS_FULL, NL_MONTHS, NL_MONTHS_SHORT,
    settingsReady,
    getSettings: () => _settings,
  };
})();

// ── Global keyboard shortcuts ─────────────────────────────────────
document.addEventListener('keydown', (e) => {
  // Ctrl+K or Cmd+K → Focus search (or navigate to search page)
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    if (window.location.pathname === '/zoeken') {
      document.getElementById('search-input')?.focus();
    } else {
      window.location.href = '/zoeken';
    }
  }
});
