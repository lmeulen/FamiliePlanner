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

  const SUPPORTED_LANGUAGES = ['nl', 'en', 'de'];
  let _language = 'nl';

  const I18N = {
    nl: {
      'nav.mainAria': 'Hoofdnavigatie',
      'nav.dashboard': 'Overzicht',
      'nav.agenda': 'Agenda',
      'nav.tasks': 'Taken',
      'nav.meals': 'Eten',
      'nav.grocery': 'Winkel',
      'nav.recipes': 'Recepten',
      'nav.family': 'Gezin',
      'nav.photos': "Foto's",
      'nav.search': 'Zoeken',
      'nav.stats': 'Statistieken',
      'nav.settings': 'Instellingen',
      'nav.logout': 'Uitloggen',
      'common.close': 'Sluiten',
      'settings.pageTitle': '⚙️ Instellingen',
      'settings.securityTitle': '🔒 Beveiliging',
      'settings.authRequired': 'Inloggen vereist',
      'settings.authRequiredHint': 'Als uitgeschakeld is de app direct toegankelijk zonder wachtwoord',
      'settings.displayTitle': '🎨 Weergave',
      'settings.language': 'Taal',
      'settings.languageHint': 'Kies de taal van de interface',
      'settings.langNl': 'Nederlands',
      'settings.langEn': 'English',
      'settings.langDe': 'Deutsch',
      'settings.timezone': 'Tijdzone',
      'settings.timezoneHint': 'Tijdzone voor het weergeven van afspraken',
      'settings.theme': 'Thema',
      'settings.themeChoose': 'Thema kiezen',
      'settings.themeLight': '☀️ Licht',
      'settings.themeDark': '🌙 Donker',
      'settings.themeSystem': '🖥️ Systeem',
      'settings.dashboardPhoto': 'Foto tonen op overzichtspagina',
      'settings.dashboardPhotoHint': 'Schakel de foto-diashow op de overzichtspagina in of uit',
      'settings.photoSize': 'Fotogrootte op overzichtspagina',
      'settings.photoSizeHint': 'Hoogte als percentage van het scherm (10-70%)',
      'settings.photoInterval': 'Foto wissel interval',
      'settings.photoIntervalHint': "Tijd tussen foto's in seconden (3-60 s)",
      'settings.screensaverTimeout': 'Screensaver op overzicht (minuten)',
      'settings.screensaverTimeoutHint': 'Start screensaver na  (0-60 min, 0 = uit)',
      'settings.overviewRedirectTimeout': 'Terug naar overzicht (seconden)',
      'settings.overviewRedirectTimeoutHint': 'Bij inactiviteit terug naar overzicht (5-300 s)',
      'settings.weatherWidget': 'Weer widget op overzichtspagina',
      'settings.weatherWidgetHint': 'Toont datum, tijd en het huidige weer boven de taken',
      'settings.weatherLocation': 'Locatie voor weer',
      'settings.weatherLocationHint': 'Plaats, Land (bijv. Amsterdam,NL)',
      'settings.weatherLocationPlaceholder': 'Amsterdam,NL',
      'settings.save': 'Opslaan',
      'settings.saved': '✅ Opgeslagen',
      'settings.backupTitle': '💾 Backup & Restore',
      'settings.backupIntro': 'Backup bevat alle gegevens van de database in JSON-formaat.',
      'settings.downloadBackup': '📥 Download Backup',
      'settings.restoreFromBackup': 'Restore vanuit backup',
      'settings.restoreWarning': '⚠️ Waarschuwing: Dit verwijdert alle huidige gegevens!',
      'settings.validateBackup': '🔍 Valideer Backup',
      'settings.restoreBackup': '📤 Restore Backup',
      'settings.cacheTitle': '⚡ Cache',
      'settings.cacheIntro': 'Browser cache voor snellere laadtijden.',
      'settings.cacheHitRate': 'Hit Rate',
      'settings.cacheItems': 'Items',
      'settings.cacheHits': 'Cache hits:',
      'settings.cacheMisses': 'Cache misses:',
      'settings.cacheStorage': 'Storage gebruikt:',
      'settings.clearCache': '🗑️ Cache Wissen',
      'settings.busy': '⏳ Bezig...',
      'settings.downloaded': '✅ Gedownload!',
      'settings.error': '❌ Fout!',
      'settings.selectBackupFirst': 'Selecteer eerst een backup bestand.',
      'settings.validating': '⏳ Valideren...',
      'settings.backupValid': '✅ Backup is geldig',
      'settings.backupInvalid': '❌ Backup is ongeldig',
      'settings.validationErrors': 'Fouten:',
      'settings.validationError': '❌ Validatie fout',
      'settings.valid': '✅ Geldig!',
      'settings.invalid': '❌ Ongeldig',
      'settings.version': 'Versie',
      'settings.exportedAt': 'Geëxporteerd',
      'settings.totalRecords': 'Totaal records',
      'settings.warnings': '⚠️ Waarschuwingen:',
      'settings.confirmRestore': '⚠️ WAARSCHUWING: Dit verwijdert ALLE huidige gegevens en vervangt ze met de backup.\n\nWeet je zeker dat je wilt doorgaan?',
      'settings.restoring': '⏳ Bezig met restoren...',
      'settings.restored': '✅ Hersteld!',
      'settings.restoreFailed': 'Restore mislukt: {message}',
      'settings.clearCacheConfirm': "Cache wissen? Dit heeft geen invloed op opgeslagen gegevens, alleen op geladen pagina's.",
      'settings.cacheCleared': 'Cache gewist',
      'screensaver.today': 'Vandaag',
      'screensaver.noUpcoming': 'Geen afspraken meer vandaag',
      'screensaver.allDay': 'Hele dag',
      'meal.breakfast': '🌅 Ontbijt',
      'meal.lunch': '☀️ Lunch',
      'meal.dinner': '🌙 Diner',
      'meal.snack': '🍎 Tussendoor',
      'common.everyone': 'Heel gezin / Iedereen',
    },
    en: {
      'nav.mainAria': 'Main navigation',
      'nav.dashboard': 'Overview',
      'nav.agenda': 'Agenda',
      'nav.tasks': 'Tasks',
      'nav.meals': 'Meals',
      'nav.grocery': 'Shop',
      'nav.recipes': 'Recipes',
      'nav.family': 'Family',
      'nav.photos': 'Photos',
      'nav.search': 'Search',
      'nav.stats': 'Statistics',
      'nav.settings': 'Settings',
      'nav.logout': 'Logout',
      'common.close': 'Close',
      'settings.pageTitle': '⚙️ Settings',
      'settings.securityTitle': '🔒 Security',
      'settings.authRequired': 'Login required',
      'settings.authRequiredHint': 'If disabled, the app is directly accessible without a password',
      'settings.displayTitle': '🎨 Display',
      'settings.language': 'Language',
      'settings.languageHint': 'Choose the interface language',
      'settings.langNl': 'Dutch',
      'settings.langEn': 'English',
      'settings.langDe': 'German',
      'settings.timezone': 'Timezone',
      'settings.timezoneHint': 'Timezone for displaying events',
      'settings.theme': 'Theme',
      'settings.themeChoose': 'Choose theme',
      'settings.themeLight': '☀️ Light',
      'settings.themeDark': '🌙 Dark',
      'settings.themeSystem': '🖥️ System',
      'settings.dashboardPhoto': 'Show photo on dashboard',
      'settings.dashboardPhotoHint': 'Enable or disable the photo slideshow on the dashboard',
      'settings.photoSize': 'Photo size on dashboard',
      'settings.photoSizeHint': 'Height as percentage of the screen (10-70%)',
      'settings.photoInterval': 'Photo switch interval',
      'settings.photoIntervalHint': 'Time between photos in seconds (3-60 s)',
      'settings.screensaverTimeout': 'Screensaver on overview (minutes)',
      'settings.screensaverTimeoutHint': 'Start screensaver on overview after inactivity (0-60 min, 0 = off)',
      'settings.overviewRedirectTimeout': 'Return to overview on other pages (seconds)',
      'settings.overviewRedirectTimeoutHint': 'Automatically return to overview after inactivity (5-300 s)',
      'settings.weatherWidget': 'Weather widget on dashboard',
      'settings.weatherWidgetHint': 'Shows date, time and current weather above tasks',
      'settings.weatherLocation': 'Weather location',
      'settings.weatherLocationHint': 'City, Country (e.g. Amsterdam,NL)',
      'settings.weatherLocationPlaceholder': 'Amsterdam,NL',
      'settings.save': 'Save',
      'settings.saved': '✅ Saved',
      'settings.backupTitle': '💾 Backup & Restore',
      'settings.backupIntro': 'Backup contains all database data in JSON format.',
      'settings.downloadBackup': '📥 Download Backup',
      'settings.restoreFromBackup': 'Restore from backup',
      'settings.restoreWarning': '⚠️ Warning: This removes all current data!',
      'settings.validateBackup': '🔍 Validate Backup',
      'settings.restoreBackup': '📤 Restore Backup',
      'settings.cacheTitle': '⚡ Cache',
      'settings.cacheIntro': 'Browser cache for faster load times.',
      'settings.cacheHitRate': 'Hit Rate',
      'settings.cacheItems': 'Items',
      'settings.cacheHits': 'Cache hits:',
      'settings.cacheMisses': 'Cache misses:',
      'settings.cacheStorage': 'Storage used:',
      'settings.clearCache': '🗑️ Clear Cache',
      'settings.busy': '⏳ Working...',
      'settings.downloaded': '✅ Downloaded!',
      'settings.error': '❌ Error!',
      'settings.selectBackupFirst': 'Select a backup file first.',
      'settings.validating': '⏳ Validating...',
      'settings.backupValid': '✅ Backup is valid',
      'settings.backupInvalid': '❌ Backup is invalid',
      'settings.validationErrors': 'Errors:',
      'settings.validationError': '❌ Validation error',
      'settings.valid': '✅ Valid!',
      'settings.invalid': '❌ Invalid',
      'settings.version': 'Version',
      'settings.exportedAt': 'Exported at',
      'settings.totalRecords': 'Total records',
      'settings.warnings': '⚠️ Warnings:',
      'settings.confirmRestore': '⚠️ WARNING: This removes ALL current data and replaces it with the backup.\n\nAre you sure you want to continue?',
      'settings.restoring': '⏳ Restoring...',
      'settings.restored': '✅ Restored!',
      'settings.restoreFailed': 'Restore failed: {message}',
      'settings.clearCacheConfirm': 'Clear cache? This does not affect saved data, only loaded pages.',
      'settings.cacheCleared': 'Cache cleared',
      'screensaver.today': 'Today',
      'screensaver.noUpcoming': 'No more appointments today',
      'screensaver.allDay': 'All day',
      'meal.breakfast': '🌅 Breakfast',
      'meal.lunch': '☀️ Lunch',
      'meal.dinner': '🌙 Dinner',
      'meal.snack': '🍎 Snack',
      'common.everyone': 'Whole family / Everyone',
    },
    de: {
      'nav.mainAria': 'Hauptnavigation',
      'nav.dashboard': 'Übersicht',
      'nav.agenda': 'Kalender',
      'nav.tasks': 'Aufgaben',
      'nav.meals': 'Essen',
      'nav.grocery': 'Geschäft',
      'nav.recipes': 'Rezepte',
      'nav.family': 'Familie',
      'nav.photos': 'Fotos',
      'nav.search': 'Suche',
      'nav.stats': 'Statistiken',
      'nav.settings': 'Einstellungen',
      'nav.logout': 'Abmelden',
      'common.close': 'Schließen',
      'settings.pageTitle': '⚙️ Einstellungen',
      'settings.securityTitle': '🔒 Sicherheit',
      'settings.authRequired': 'Anmeldung erforderlich',
      'settings.authRequiredHint': 'Wenn deaktiviert, ist die App ohne Passwort direkt zugänglich',
      'settings.displayTitle': '🎨 Anzeige',
      'settings.language': 'Sprache',
      'settings.languageHint': 'Wähle die Sprache der Oberfläche',
      'settings.langNl': 'Niederländisch',
      'settings.langEn': 'Englisch',
      'settings.langDe': 'Deutsch',
      'settings.timezone': 'Zeitzone',
      'settings.timezoneHint': 'Zeitzone für die Anzeige von Terminen',
      'settings.theme': 'Design',
      'settings.themeChoose': 'Design wählen',
      'settings.themeLight': '☀️ Hell',
      'settings.themeDark': '🌙 Dunkel',
      'settings.themeSystem': '🖥️ System',
      'settings.dashboardPhoto': 'Foto auf der Übersichtsseite anzeigen',
      'settings.dashboardPhotoHint': 'Foto-Diashow auf der Übersichtsseite ein- oder ausschalten',
      'settings.photoSize': 'Fotogröße auf der Übersichtsseite',
      'settings.photoSizeHint': 'Höhe als Prozentsatz des Bildschirms (10-70%)',
      'settings.photoInterval': 'Foto-Wechselintervall',
      'settings.photoIntervalHint': 'Zeit zwischen Fotos in Sekunden (3-60 s)',
      'settings.screensaverTimeout': 'Bildschirmschoner auf Übersicht (Minuten)',
      'settings.screensaverTimeoutHint': 'Bildschirmschoner auf Übersicht nach Inaktivität starten (0-60 min, 0 = aus)',
      'settings.overviewRedirectTimeout': 'Zur Übersicht auf anderen Seiten zurückkehren (Sekunden)',
      'settings.overviewRedirectTimeoutHint': 'Nach Inaktivität automatisch zur Übersicht zurückkehren (5-300 s)',
      'settings.weatherWidget': 'Wetter-Widget auf der Übersichtsseite',
      'settings.weatherWidgetHint': 'Zeigt Datum, Uhrzeit und aktuelles Wetter über den Aufgaben',
      'settings.weatherLocation': 'Wetterstandort',
      'settings.weatherLocationHint': 'Stadt, Land (z.B. Amsterdam,NL)',
      'settings.weatherLocationPlaceholder': 'Amsterdam,NL',
      'settings.save': 'Speichern',
      'settings.saved': '✅ Gespeichert',
      'settings.backupTitle': '💾 Backup & Restore',
      'settings.backupIntro': 'Das Backup enthält alle Daten der Datenbank im JSON-Format.',
      'settings.downloadBackup': '📥 Backup herunterladen',
      'settings.restoreFromBackup': 'Aus Backup wiederherstellen',
      'settings.restoreWarning': '⚠️ Warnung: Dadurch werden alle aktuellen Daten gelöscht!',
      'settings.validateBackup': '🔍 Backup prüfen',
      'settings.restoreBackup': '📤 Backup wiederherstellen',
      'settings.cacheTitle': '⚡ Cache',
      'settings.cacheIntro': 'Browser-Cache für schnellere Ladezeiten.',
      'settings.cacheHitRate': 'Trefferquote',
      'settings.cacheItems': 'Einträge',
      'settings.cacheHits': 'Cache-Treffer:',
      'settings.cacheMisses': 'Cache-Fehler:',
      'settings.cacheStorage': 'Genutzter Speicher:',
      'settings.clearCache': '🗑️ Cache leeren',
      'settings.busy': '⏳ Bitte warten...',
      'settings.downloaded': '✅ Heruntergeladen!',
      'settings.error': '❌ Fehler!',
      'settings.selectBackupFirst': 'Bitte zuerst eine Backup-Datei auswählen.',
      'settings.validating': '⏳ Wird geprüft...',
      'settings.backupValid': '✅ Backup ist gültig',
      'settings.backupInvalid': '❌ Backup ist ungültig',
      'settings.validationErrors': 'Fehler:',
      'settings.validationError': '❌ Prüfungsfehler',
      'settings.valid': '✅ Gültig!',
      'settings.invalid': '❌ Ungültig',
      'settings.version': 'Version',
      'settings.exportedAt': 'Exportiert am',
      'settings.totalRecords': 'Gesamtanzahl Datensätze',
      'settings.warnings': '⚠️ Warnungen:',
      'settings.confirmRestore': '⚠️ WARNUNG: Dadurch werden ALLE aktuellen Daten gelöscht und durch das Backup ersetzt.\n\nMöchtest du wirklich fortfahren?',
      'settings.restoring': '⏳ Wiederherstellung läuft...',
      'settings.restored': '✅ Wiederhergestellt!',
      'settings.restoreFailed': 'Wiederherstellung fehlgeschlagen: {message}',
      'settings.clearCacheConfirm': 'Cache leeren? Gespeicherte Daten bleiben erhalten, nur geladene Seiten werden beeinflusst.',
      'settings.cacheCleared': 'Cache geleert',
      'screensaver.today': 'Heute',
      'screensaver.noUpcoming': 'Keine weiteren Termine heute',
      'screensaver.allDay': 'Ganztägig',
      'meal.breakfast': '🌅 Frühstück',
      'meal.lunch': '☀️ Mittagessen',
      'meal.dinner': '🌙 Abendessen',
      'meal.snack': '🍎 Snack',
      'common.everyone': 'Ganze Familie / Alle',
    },
  };

  function getLocale(lang = _language) {
    return { nl: 'nl-NL', en: 'en-GB', de: 'de-DE' }[lang] || 'nl-NL';
  }

  function t(key, vars = {}) {
    const template = I18N[_language]?.[key] ?? I18N.nl[key] ?? key;
    return String(template).replace(/\{(\w+)\}/g, (_, name) => String(vars[name] ?? ''));
  }

  function setLanguage(lang, persist = true) {
    _language = SUPPORTED_LANGUAGES.includes(lang) ? lang : 'nl';
    document.documentElement.lang = _language;
    if (persist) localStorage.setItem('fp-language', _language);
    translateDocument();
  }

  function getLanguage() {
    return _language;
  }

  function translateDocument(root = document) {
    root.querySelectorAll('[data-i18n]').forEach(el => {
      const key = el.getAttribute('data-i18n');
      if (key) el.textContent = t(key);
    });

    root.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
      const key = el.getAttribute('data-i18n-placeholder');
      if (key) el.setAttribute('placeholder', t(key));
    });

    root.querySelectorAll('[data-i18n-aria-label]').forEach(el => {
      const key = el.getAttribute('data-i18n-aria-label');
      if (key) el.setAttribute('aria-label', t(key));
    });

    root.querySelectorAll('[data-i18n-title]').forEach(el => {
      const key = el.getAttribute('data-i18n-title');
      if (key) el.setAttribute('title', t(key));
    });
  }

  async function loadMembers(useCache = true) {
    // Check cache first (1 hour TTL)
    if (useCache) {
      const cached = Cache.get('family_members');
      if (cached) {
        _members = cached;
        return _members;
      }
    }

    try {
      _members = await API.get('/api/family/');
      // Cache for 1 hour
      Cache.set('family_members', _members, 3600000);
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

  function agendaEventColors(memberIds = []) {
    const ids = Array.isArray(memberIds) ? memberIds : [];
    const colors = ids
      .map(id => getMember(id))
      .filter(Boolean)
      .map(member => member.color)
      .filter(Boolean);
    return [...new Set(colors)];
  }

  function agendaEventColor(memberIds = []) {
    const colors = agendaEventColors(memberIds);
    return colors[0] || '#9EA7C4';
  }

  function agendaEventBackground(memberIds = []) {
    const colors = agendaEventColors(memberIds);
    if (colors.length <= 1) return agendaEventColor(memberIds);

    const step = 100 / colors.length;
    const stops = colors
      .map((color, index) => {
        const start = Number((index * step).toFixed(2));
        const end = Number(((index + 1) * step).toFixed(2));
        return `${color} ${start}%, ${color} ${end}%`;
      })
      .join(', ');

    return `linear-gradient(135deg, ${stops})`;
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

  function dateToStr(d) {
    // Convert Date object to YYYY-MM-DD string using LOCAL date components
    // (NOT UTC via toISOString which can shift by 1 day due to timezone)
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
  }

  function pad(n) { return String(n).padStart(2, '0'); }

  function formatDate(d) {
    if (!d) return '';
    const dt = d instanceof Date ? d : new Date(d);
    return new Intl.DateTimeFormat(getLocale(), {
      day: '2-digit',
      month: 'long',
      year: 'numeric',
    }).format(dt);
  }

  function formatTime(d) {
    if (!d) return '';
    const dt = d instanceof Date ? d : new Date(d);
    return `${pad(dt.getHours())}:${pad(dt.getMinutes())}`;
  }

  function formatDateShort(d) {
    if (!d) return '';
    const dt = d instanceof Date ? d : new Date(d);
    return new Intl.DateTimeFormat(getLocale(), {
      day: '2-digit',
      month: 'short',
    }).format(dt);
  }

  function dayName(d) {
    const dt = d instanceof Date ? d : new Date(d);
    return new Intl.DateTimeFormat(getLocale(), { weekday: 'short' }).format(dt);
  }

  function dayNameFull(d) {
    const dt = d instanceof Date ? d : new Date(d);
    return new Intl.DateTimeFormat(getLocale(), { weekday: 'long' }).format(dt);
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

  function mealTypeLabel(mealType) {
    return ({
      breakfast: t('meal.breakfast'),
      lunch: t('meal.lunch'),
      dinner: t('meal.dinner'),
      snack: t('meal.snack'),
    }[mealType] || mealType);
  }

  // ── Header date + time ──────────────────────────────────────
  function renderHeaderDate() {
    const el = document.getElementById('header-date');
    if (!el) return;
    const d  = new Date();
    const hh = pad(d.getHours());
    const mm = pad(d.getMinutes());
    const dayLabel = dayNameFull(d);
    const monthLabel = new Intl.DateTimeFormat(getLocale(), { month: 'long' }).format(d);
    el.innerHTML =
      `<div class="header-date-line">${dayLabel} ${d.getDate()} ${monthLabel}</div>` +
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
      opt.value = ''; opt.textContent = t('common.everyone');
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
  let _idleTimer = null;

  function getOverviewRedirectSeconds() {
    const configured = Number(_settings?.overview_redirect_seconds ?? _settings?.idle_redirect_seconds ?? 60);
    if (!Number.isFinite(configured)) return 60;
    return Math.max(5, Math.min(3600, Math.floor(configured)));
  }

  function getDashboardScreensaverSeconds() {
    const configured = Number(_settings?.dashboard_screensaver_seconds ?? _settings?.idle_redirect_seconds ?? 60);
    if (!Number.isFinite(configured)) return 60;
    return Math.max(0, Math.min(3600, Math.floor(configured)));
  }

  function isEditorOpen() {
    const modalOverlay = document.getElementById('modal-overlay');
    if (modalOverlay && !modalOverlay.classList.contains('hidden')) return true;

    const active = document.activeElement;
    if (active && active.matches && active.matches('input, textarea, select, [contenteditable="true"]')) {
      return true;
    }

    return !!document.querySelector('[data-editor-open="true"]');
  }

  function scheduleIdleRedirect() {
    if (_idleTimer) clearTimeout(_idleTimer);
    const currentPath = window.location.pathname;
    const timeoutSeconds = currentPath === '/' ? getDashboardScreensaverSeconds() : getOverviewRedirectSeconds();

    if (currentPath === '/' && timeoutSeconds <= 0) {
      return;
    }

    _idleTimer = setTimeout(() => {
      const currentPath = window.location.pathname;
      if (currentPath === '/login') return;

      if (isEditorOpen()) {
        scheduleIdleRedirect();
        return;
      }

      if (currentPath === '/') {
        if (window.DashboardScreensaver?.activate) {
          window.DashboardScreensaver.activate();
        }
        return;
      }

      window.location.href = '/';
    }, timeoutSeconds * 1000);
  }

  function handleActivity() {
    if (window.DashboardScreensaver?.isActive?.()) {
      window.DashboardScreensaver.deactivate();
    }
    scheduleIdleRedirect();
  }

  function initIdleRedirectWatcher() {
    const resetEvents = ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll'];
    resetEvents.forEach(eventName => {
      document.addEventListener(eventName, handleActivity, { passive: true });
    });

    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        if (_idleTimer) clearTimeout(_idleTimer);
      } else {
        scheduleIdleRedirect();
      }
    });

    scheduleIdleRedirect();
  }

  async function applyPersistedSettings() {
    try {
      const s = await API.get('/api/settings/');
      if (s) {
        _settings = s;
        const langFromSettings = (s.language || localStorage.getItem('fp-language') || 'nl').toLowerCase();
        setLanguage(langFromSettings, false);
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
    } catch {
      const langFromStorage = (localStorage.getItem('fp-language') || 'nl').toLowerCase();
      setLanguage(langFromStorage, false);
    }
    finally { _settingsResolve(); }
  }

  document.addEventListener('DOMContentLoaded', () => {
    renderHeaderDate();
    setInterval(renderHeaderDate, 30_000);  // update clock every 30s
    loadMembers();   // pre-load for all pages
    applyPersistedSettings();
    settingsReady.then(initIdleRedirectWatcher);
  });

  // ── Cache helpers ─────────────────────────────────────────────
  function invalidateCache(pattern) {
    Cache.invalidate(pattern);
  }

  function clearAllCache() {
    Cache.clear();
  }

  function setSettings(newSettings) {
    _settings = { ...(_settings || {}), ...(newSettings || {}) };
    scheduleIdleRedirect();
  }

  return {
    esc,
    loadMembers, getMembers, getMember, memberColor, memberAvatar,
    agendaEventColors, agendaEventColor, agendaEventBackground,
    today, todayStr, dateToStr, pad, formatDate, formatTime, formatDateShort,
    dayName, dayNameFull, isToday, isSameDay, addDays, startOfWeek,
    toLocalDatetimeInput, mealTypeLabel,
    buildMemberChips, populateMemberSelect, buildMemberPicker, getSelectedMemberIds,
    NL_DAYS, NL_DAYS_FULL, NL_MONTHS, NL_MONTHS_SHORT,
    settingsReady,
    getSettings: () => _settings,
    setSettings,
    t,
    getLocale,
    setLanguage,
    getLanguage,
    translateDocument,
    invalidateCache, clearAllCache,
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
