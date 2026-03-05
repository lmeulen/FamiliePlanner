/* ================================================================
   dashboard.js – Overview page: today events, meals, tasks
   ================================================================ */
(function () {

  // ── Module-level data caches (used by edit forms) ─────────────
  let _events = [];
  let _meals  = [];
  let _tasks  = [];   // combined today + overdue

  // ── Weather Widget ────────────────────────────────────────────
  async function initWeatherWidget() {
    const weatherWidget = document.getElementById('weather-widget');
    const widgetDate = document.getElementById('widget-date');
    const widgetTime = document.getElementById('widget-time');
    const weatherInfo = document.getElementById('weather-info');

    if (!weatherWidget) {
      console.warn('[Weather] Weather widget element not found');
      return;
    }

    console.log('[Weather] Initializing weather widget');
    const settings = await API.get('/api/settings/').catch(err => {
      console.error('[Weather] Failed to load settings:', err);
      return null;
    });

    console.log('[Weather] Settings loaded:', settings);

    // Widget is altijd zichtbaar (toont minimaal datum/tijd)
    updateDateTime();
    setInterval(updateDateTime, 30000); // Update elke 30 seconden

    // Laad weer alleen als ingeschakeld
    if (settings && settings.weather_enabled) {
      console.log('[Weather] Weather is enabled, location:', settings.weather_location);
      loadWeather(settings.weather_location || 'Amsterdam,NL');
    } else {
      console.log('[Weather] Weather is disabled');
      weatherInfo.innerHTML = ''; // Verberg weer sectie
    }

    function updateDateTime() {
      const now = new Date();
      const days = ['Zondag', 'Maandag', 'Dinsdag', 'Woensdag', 'Donderdag', 'Vrijdag', 'Zaterdag'];
      const months = ['januari', 'februari', 'maart', 'april', 'mei', 'juni', 'juli', 'augustus', 'september', 'oktober', 'november', 'december'];

      const dayName = days[now.getDay()];
      const day = now.getDate();
      const month = months[now.getMonth()];
      const year = now.getFullYear();

      widgetDate.textContent = `${dayName} ${day} ${month} ${year}`;

      const hours = String(now.getHours()).padStart(2, '0');
      const minutes = String(now.getMinutes()).padStart(2, '0');
      widgetTime.textContent = `${hours}:${minutes}`;
    }

    async function loadWeather(location) {
      try {
        weatherInfo.innerHTML = '<div class="weather-widget-loading">⏳</div>';

        console.log('[Weather] Fetching weather for:', location);
        const data = await API.get(`/api/settings/weather?location=${encodeURIComponent(location)}`);
        console.log('[Weather] Received data:', data);

        if (!data || !data.main || !data.weather || !data.weather[0]) {
          throw new Error('Invalid weather data structure');
        }

        const temp = Math.round(data.main.temp);
        const description = data.weather[0].description;
        const icon = getWeatherIcon(data.weather[0].icon);

        weatherInfo.innerHTML = `
          <div class="weather-widget-icon">${icon}</div>
          <div>
            <div class="weather-widget-temp">${temp}°C</div>
            <div class="weather-widget-details">${description}</div>
          </div>
        `;
        console.log('[Weather] Successfully displayed');
      } catch (err) {
        console.error('[Weather] Failed to load weather:', err);
        console.error('[Weather] Error details:', err.message);

        let errorMsg = 'Weer niet beschikbaar';
        if (err.message) {
          if (err.message.includes('API key') || err.message.includes('401')) {
            errorMsg = '⚠️ Ongeldige API key';
          } else if (err.message.includes('503')) {
            errorMsg = '⚙️ Geen API key ingesteld';
          }
        }

        weatherInfo.innerHTML = `<div class="weather-widget-details" style="font-size: 0.75rem; color: var(--text-muted);">${errorMsg}</div>`;
      }
    }

    function getWeatherIcon(code) {
      const icons = {
        '01d': '☀️', '01n': '🌙',
        '02d': '⛅', '02n': '☁️',
        '03d': '☁️', '03n': '☁️',
        '04d': '☁️', '04n': '☁️',
        '09d': '🌧️', '09n': '🌧️',
        '10d': '🌦️', '10n': '🌧️',
        '11d': '⛈️', '11n': '⛈️',
        '13d': '❄️', '13n': '❄️',
        '50d': '🌫️', '50n': '🌫️',
      };
      return icons[code] || '🌤️';
    }
  }

  // ── Render helpers ────────────────────────────────────────────
  function renderEventCard(ev) {
    const start = new Date(ev.start_time);
    const end   = new Date(ev.end_time);
    const members = (ev.member_ids || []).map(id => FP.getMember(id)).filter(Boolean);
    const badges = members.map(m => `<div class="event-member-badge" style="background:${m.color}" title="${FP.esc(m.name)}">${m.avatar}</div>`).join('');
    return `
      <div class="card event-card" data-id="${ev.id}" style="cursor:pointer">
        <div class="event-color-bar" style="background:${ev.color}"></div>
        <div class="event-body">
          <div class="event-title">${FP.esc(ev.title)}</div>
          <div class="event-meta">
            ${ev.all_day ? 'Hele dag' : `${FP.formatTime(start)} – ${FP.formatTime(end)}`}
            ${ev.location ? ` · 📍 ${FP.esc(ev.location)}` : ''}
          </div>
        </div>
        ${badges ? `<div class="event-member-badges">${badges}</div>` : ''}
      </div>`;
  }

  function renderTaskCard(task, overdue = false) {
    const members = (task.member_ids || []).map(id => FP.getMember(id)).filter(Boolean);
    const badges = members.map(m => `<div class="event-member-badge" style="background:${m.color}" title="${FP.esc(m.name)}">${m.avatar}</div>`).join('');
    const dueMeta = overdue && task.due_date
      ? `<div class="task-due overdue">Verlopen: ${FP.formatDate(new Date(task.due_date))}</div>`
      : '';
    const recurIcon = task.series_id ? ' <span class="recur-icon" title="Herhalende taak">↻</span>' : '';
    return `
      <div class="card task-card ${overdue ? 'task-overdue' : ''}" data-id="${task.id}">
        <button class="task-check ${task.done ? 'done' : ''}" data-id="${task.id}" aria-label="Afvinken"></button>
        <div class="task-body">
          <div class="task-title ${task.done ? 'done' : ''}">${FP.esc(task.title)}${recurIcon}</div>
          ${dueMeta}
        </div>
        ${badges ? `<div class="event-member-badges">${badges}</div>` : ''}
      </div>`;
  }

  function renderMealCard(meal) {
    const cook = meal.cook_member_id ? FP.getMember(meal.cook_member_id) : null;
    const badge = cook ? `<div class="event-member-badge" style="background:${cook.color}" title="${FP.esc(cook.name)}">${cook.avatar}</div>` : '';
    return `
      <div class="meal-card" data-id="${meal.id}">
        <span class="meal-type-badge ${meal.meal_type}">${FP.mealTypeLabel(meal.meal_type)}</span>
        <div class="meal-name-row">
          <div class="meal-name">${FP.esc(meal.name)}</div>
          ${badge ? `<div class="event-member-badges">${badge}</div>` : ''}
        </div>
        ${meal.description ? `<div class="text-muted" style="font-size:.78rem;margin-top:.2rem">${FP.esc(meal.description)}</div>` : ''}
      </div>`;
  }

  // ── Load sections ─────────────────────────────────────────────
  async function loadEvents() {
    const container = document.getElementById('today-events');
    const empty     = document.getElementById('events-empty');
    try {
      _events = await API.get('/api/agenda/today');
      if (!_events.length) {
        container.innerHTML = '';
        empty.classList.remove('hidden');
      } else {
        container.innerHTML = _events.map(renderEventCard).join('');
        empty.classList.add('hidden');
        container.querySelectorAll('.event-card').forEach(card => {
          card.addEventListener('click', () => openDashEventForm(parseInt(card.dataset.id)));
        });
      }
    } catch {
      container.innerHTML = `<p class="text-muted">Kon agenda niet laden.</p>`;
    }
  }

  async function loadMeals() {
    const container = document.getElementById('today-meals');
    const empty     = document.getElementById('meals-empty');
    try {
      _meals = await API.get('/api/meals/today');
      if (!_meals.length) {
        container.innerHTML = '';
        empty.classList.remove('hidden');
      } else {
        container.innerHTML = _meals.map(renderMealCard).join('');
        empty.classList.add('hidden');
        container.querySelectorAll('.meal-card').forEach(card => {
          card.style.cursor = 'pointer';
          card.addEventListener('click', () => openDashMealForm(parseInt(card.dataset.id)));
        });
      }
    } catch {
      container.innerHTML = `<p class="text-muted">Kon maaltijden niet laden.</p>`;
    }
  }

  async function loadTasks() {
    const container = document.getElementById('all-tasks');
    const empty     = document.getElementById('tasks-empty');
    try {
      const [today, overdue, lists, overduePos] = await Promise.all([
        API.get('/api/tasks/today'),
        API.get('/api/tasks/overdue'),
        API.get('/api/tasks/lists'),
        API.get('/api/tasks/overdue-position').catch(() => ({ sort_order: 9999 })),
      ]);
      _tasks = [...today, ...overdue];

      // Lists are already ordered by sort_order from API
      // Build virtual items: lists + overdue pseudo-entry at its configured position
      const virtualItems = [
        ...lists.map(l => ({ type: 'list', list: l })),
        { type: 'overdue', sort_order: overduePos.sort_order },
      ].sort((a, b) => {
        const aOrd = a.type === 'list' ? a.list.sort_order : a.sort_order;
        const bOrd = b.type === 'list' ? b.list.sort_order : b.sort_order;
        return aOrd - bOrd;
      });

      // Group today's tasks by list_id (null = "Overige")
      const grouped = new Map();
      today.forEach(t => {
        const key = t.list_id ?? null;
        if (!grouped.has(key)) grouped.set(key, []);
        grouped.get(key).push(t);
      });

      let html = '';

      virtualItems.forEach(item => {
        if (item.type === 'list') {
          const tasks = grouped.get(item.list.id) || [];
          if (!tasks.length) return;
          html += `<div class="task-group-header">${item.list.name}</div>`;
          html += tasks.map(t => renderTaskCard(t, false)).join('');
        } else {
          // Overige taken (null list_id)
          const overige = grouped.get(null) || [];
          if (overige.length) {
            html += `<div class="task-group-header">Overige taken</div>`;
            html += overige.map(t => renderTaskCard(t, false)).join('');
          }
          // Verlopen taken
          if (overdue.length) {
            html += `<div class="task-group-header task-group-header--overdue">Verlopen taken</div>`;
            html += overdue.map(t => renderTaskCard(t, true)).join('');
          }
        }
      });

      if (!html) {
        container.innerHTML = '';
        empty.classList.remove('hidden');
      } else {
        container.innerHTML = html;
        empty.classList.add('hidden');
        bindTaskToggles(container);
        // Click on task body → open edit form
        container.querySelectorAll('.task-body').forEach(body => {
          body.style.cursor = 'pointer';
          body.addEventListener('click', () => {
            const id = parseInt(body.closest('.task-card').dataset.id);
            openDashTaskForm(id);
          });
        });
      }
    } catch {
      container.innerHTML = `<p class="text-muted">Kon taken niet laden.</p>`;
    }
  }

  // ── Task toggle ───────────────────────────────────────────────
  function bindTaskToggles(container) {
    container.querySelectorAll('.task-check').forEach(btn => {
      btn.addEventListener('click', async () => {
        try {
          await API.patch(`/api/tasks/${btn.dataset.id}/toggle`);
          loadTasks();
          Toast.show('Taak bijgewerkt!');
        } catch {
          Toast.show('Fout bij bijwerken', 'error');
        }
      });
    });
  }

  // ── FAB speed dial ────────────────────────────────────────────
  function initFab() {
    const fab      = document.getElementById('fab-main');
    const dial     = document.getElementById('fab-speed-dial');
    if (!fab || !dial) return;

    function openDial() {
      dial.classList.remove('hidden');
      fab.setAttribute('aria-expanded', 'true');
      fab.style.transform = 'rotate(45deg)';
    }
    function closeDial() {
      dial.classList.add('hidden');
      fab.setAttribute('aria-expanded', 'false');
      fab.style.transform = '';
    }

    fab.addEventListener('click', e => {
      e.stopPropagation();
      dial.classList.contains('hidden') ? openDial() : closeDial();
    });

    document.addEventListener('click', () => closeDial());

    document.getElementById('fab-add-event')?.addEventListener('click', () => {
      closeDial();
      openDashEventForm();
    });
    document.getElementById('fab-add-task')?.addEventListener('click', () => {
      closeDial();
      openDashTaskForm();
    });
    document.getElementById('fab-add-meal')?.addEventListener('click', () => {
      closeDial();
      openDashMealForm();
    });
  }

  // ── Form: Afspraak (create / edit) ───────────────────────────
  function openDashEventForm(id = null) {
    Modal.open('tpl-dash-event-form');
    const form    = document.getElementById('event-form');
    const titleEl = document.getElementById('dash-event-form-title');
    const delBtn  = document.getElementById('dash-btn-delete-event');

    FP.buildMemberPicker('event-member-picker');

    if (id) {
      titleEl.textContent = 'Afspraak bewerken';
      delBtn.classList.remove('hidden');
      const ev = _events.find(e => e.id === id);
      if (ev) {
        form.title.value       = ev.title;
        form.description.value = ev.description || '';
        form.location.value    = ev.location || '';
        form.start_time.value  = FP.toLocalDatetimeInput(new Date(ev.start_time));
        form.end_time.value    = FP.toLocalDatetimeInput(new Date(ev.end_time));
        form.all_day.checked   = ev.all_day;
        form.color.value       = ev.color;
        FP.buildMemberPicker('event-member-picker', ev.member_ids || []);
      }
    } else {
      titleEl.textContent = 'Afspraak toevoegen';
      delBtn.classList.add('hidden');
      const now = new Date();
      const s = new Date(now); s.setMinutes(Math.ceil(now.getMinutes() / 15) * 15, 0, 0);
      const e = new Date(s);   e.setHours(e.getHours() + 1);
      form.start_time.value = FP.toLocalDatetimeInput(s);
      form.end_time.value   = FP.toLocalDatetimeInput(e);
    }

    form.addEventListener('submit', async ev => {
      ev.preventDefault();
      const startDt = new Date(form.start_time.value);
      const endDt   = new Date(form.end_time.value);
      const endErr  = document.getElementById('end-time-error');
      if (endDt <= startDt) { endErr?.classList.remove('hidden'); return; }
      endErr?.classList.add('hidden');
      const data = {
        title:       form.title.value.trim(),
        description: form.description.value.trim(),
        location:    form.location.value.trim(),
        start_time:  startDt.toISOString(),
        end_time:    endDt.toISOString(),
        all_day:     form.all_day.checked,
        color:       form.color.value,
        member_ids:  FP.getSelectedMemberIds('event-member-picker'),
      };
      try {
        if (id) {
          await API.put(`/api/agenda/${id}`, data);
          Toast.show('Afspraak bijgewerkt!');
        } else {
          await API.post('/api/agenda/', data);
          Toast.show('Afspraak toegevoegd!');
        }
        Modal.close(); loadEvents();
      } catch (err) { Toast.show(err.message || 'Fout bij opslaan', 'error'); }
    }, { once: true });

    delBtn.addEventListener('click', async () => {
      if (!confirm('Afspraak verwijderen?')) return;
      try {
        await API.delete(`/api/agenda/${id}`);
        Toast.show('Afspraak verwijderd', 'warning');
        Modal.close(); loadEvents();
      } catch { Toast.show('Fout bij verwijderen', 'error'); }
    }, { once: true });
  }

  // ── Form: Taak (create / edit) ────────────────────────────────
  async function openDashTaskForm(id = null) {
    Modal.open('tpl-dash-task-form');
    const form    = document.getElementById('task-form');
    const titleEl = document.getElementById('dash-task-form-title');
    const delBtn  = document.getElementById('dash-btn-delete-task');

    FP.buildMemberPicker('task-member-picker');

    // Populate list select (required – no empty option)
    const listSel = document.getElementById('dash-task-list-select');
    listSel.innerHTML = '';
    let dashLists = [];
    try {
      dashLists = await API.get('/api/tasks/lists');
      dashLists.forEach(l => {
        const opt = document.createElement('option');
        opt.value = l.id; opt.textContent = l.name;
        listSel.appendChild(opt);
      });
    } catch {}

    if (id) {
      titleEl.textContent = 'Taak bewerken';
      delBtn.classList.remove('hidden');
      const task = _tasks.find(t => t.id === id);
      if (task) {
        form.title.value       = task.title;
        form.description.value = task.description || '';
        listSel.value          = task.list_id || (dashLists[0]?.id ?? '');
        FP.buildMemberPicker('task-member-picker', task.member_ids || []);
        form.due_date.value    = task.due_date || '';
      }
    } else {
      titleEl.textContent = 'Taak toevoegen';
      delBtn.classList.add('hidden');
      form.due_date.value = FP.todayStr();
      if (dashLists.length) listSel.value = dashLists[0].id;
    }

    form.addEventListener('submit', async e => {
      e.preventDefault();
      const data = {
        title:       form.title.value.trim(),
        description: form.description.value.trim(),
        list_id:     listSel.value ? parseInt(listSel.value) : null,
        member_ids:  FP.getSelectedMemberIds('task-member-picker'),
        due_date:    form.due_date.value || null,
      };
      try {
        if (id) {
          await API.put(`/api/tasks/${id}`, data);
          Toast.show('Taak bijgewerkt!');
        } else {
          await API.post('/api/tasks/', data);
          Toast.show('Taak toegevoegd!');
        }
        Modal.close(); loadTasks();
      } catch (err) { Toast.show(err.message || 'Fout bij opslaan', 'error'); }
    }, { once: true });

    delBtn.addEventListener('click', async () => {
      if (!confirm('Taak verwijderen?')) return;
      try {
        await API.delete(`/api/tasks/${id}`);
        Toast.show('Taak verwijderd', 'warning');
        Modal.close(); loadTasks();
      } catch { Toast.show('Fout bij verwijderen', 'error'); }
    }, { once: true });
  }

  // ── Form: Maaltijd (create / edit) ────────────────────────────
  async function openDashMealForm(id = null) {
    Modal.open('tpl-dash-meal-form');
    const form    = document.getElementById('meal-form');
    const titleEl = document.getElementById('dash-meal-form-title');
    const delBtn  = document.getElementById('dash-btn-delete-meal');

    // Populate cook select
    const cookSel = document.getElementById('dash-cook-select');
    (FP.getMembers?.() || []).forEach(m => {
      const opt = document.createElement('option');
      opt.value = m.id; opt.textContent = `${m.avatar} ${m.name}`;
      cookSel.appendChild(opt);
    });

    if (id) {
      titleEl.textContent = 'Maaltijd bewerken';
      delBtn.classList.remove('hidden');
      const meal = _meals.find(m => m.id === id);
      if (meal) {
        form.date.value        = meal.date;
        form.meal_type.value   = meal.meal_type;
        form.name.value        = meal.name;
        form.description.value = meal.description || '';
        form.recipe_url.value  = meal.recipe_url || '';
        cookSel.value          = meal.cook_member_id || '';
      }
    } else {
      titleEl.textContent = 'Maaltijd toevoegen';
      delBtn.classList.add('hidden');
      form.date.value = FP.todayStr();
    }

    form.addEventListener('submit', async e => {
      e.preventDefault();
      const data = {
        date:           form.date.value,
        meal_type:      form.meal_type.value,
        name:           form.name.value.trim(),
        description:    form.description.value.trim(),
        recipe_url:     form.recipe_url.value.trim(),
        cook_member_id: cookSel.value ? parseInt(cookSel.value) : null,
      };
      try {
        if (id) {
          await API.put(`/api/meals/${id}`, data);
          Toast.show('Maaltijd bijgewerkt!');
        } else {
          await API.post('/api/meals/', data);
          Toast.show('Maaltijd toegevoegd!');
        }
        Modal.close(); loadMeals();
      } catch (err) { Toast.show(err.message || 'Fout bij opslaan', 'error'); }
    }, { once: true });

    delBtn.addEventListener('click', async () => {
      if (!confirm('Maaltijd verwijderen?')) return;
      try {
        await API.delete(`/api/meals/${id}`);
        Toast.show('Maaltijd verwijderd', 'warning');
        Modal.close(); loadMeals();
      } catch { Toast.show('Fout bij verwijderen', 'error'); }
    }, { once: true });
  }

  // ── Dashboard photo rotator ───────────────────────────────────
  (function initDashboardPhoto() {
    const wrap  = document.getElementById('dashboard-photo-wrap');
    const img   = document.getElementById('dashboard-photo');
    const dots  = document.getElementById('dashboard-photo-dots');
    let photos  = [];
    let current = 0;
    let timer   = null;

    function showPhoto(index) {
      if (!photos.length) return;
      current = (index + photos.length) % photos.length;
      img.classList.add('fading');
      setTimeout(() => {
        img.src = photos[current].url;
        img.alt = photos[current].display_name || 'Foto';
        img.classList.remove('fading');
      }, 250);
      dots.querySelectorAll('.dot').forEach((d, i) => d.classList.toggle('active', i === current));
    }

    function buildDots() {
      dots.innerHTML = photos.map((_, i) =>
        `<span class="dot${i === 0 ? ' active' : ''}" data-i="${i}" role="button" tabindex="0" aria-label="Foto ${i+1}"></span>`
      ).join('');
      dots.querySelectorAll('.dot').forEach(d => {
        d.addEventListener('click', () => { clearInterval(timer); showPhoto(+d.dataset.i); startTimer(); });
      });
    }

    function startTimer() {
      if (photos.length > 1) timer = setInterval(() => showPhoto(current + 1), 8000);
    }

    async function load() {
      try {
        await FP.settingsReady;
        const s = FP.getSettings();
        if (s && s.dashboard_photo_enabled === false) return;
        const data = await API.get('/api/photos/');
        if (!data || !data.length) return;
        photos = data.sort(() => Math.random() - .5);
        wrap.style.display = '';
        wrap.removeAttribute('aria-hidden');
        buildDots();
        showPhoto(0);
        startTimer();
      } catch { /* geen fotos beschikbaar */ }
    }

    load();
  })();

  // ── Init ──────────────────────────────────────────────────────
  async function init() {
    initWeatherWidget();
    await FP.loadMembers();
    initFab();
    await Promise.all([loadEvents(), loadMeals(), loadTasks()]);
  }

  document.addEventListener('DOMContentLoaded', init);
})();
