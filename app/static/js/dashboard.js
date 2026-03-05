/* ================================================================
   dashboard.js – Overview page: today events, meals, tasks
   ================================================================ */
(function () {

  // ── Render helpers ────────────────────────────────────────────
  function renderEventCard(ev) {
    const start = new Date(ev.start_time);
    const end   = new Date(ev.end_time);
    const members = (ev.member_ids || []).map(id => FP.getMember(id)).filter(Boolean);
    const badges = members.map(m => `<div class="event-member-badge" style="background:${m.color}" title="${m.name}">${m.avatar}</div>`).join('');
    return `
      <div class="card event-card" data-id="${ev.id}" style="cursor:pointer">
        <div class="event-color-bar" style="background:${ev.color}"></div>
        <div class="event-body">
          <div class="event-title">${ev.title}</div>
          <div class="event-meta">
            ${ev.all_day ? 'Hele dag' : `${FP.formatTime(start)} – ${FP.formatTime(end)}`}
            ${ev.location ? ` · 📍 ${ev.location}` : ''}
          </div>
        </div>
        ${badges ? `<div class="event-member-badges">${badges}</div>` : ''}
      </div>`;
  }

  function renderTaskCard(task, overdue = false) {
    const members = (task.member_ids || []).map(id => FP.getMember(id)).filter(Boolean);
    const badges = members.map(m => `<div class="event-member-badge" style="background:${m.color}" title="${m.name}">${m.avatar}</div>`).join('');
    const dueMeta = overdue && task.due_date
      ? `<div class="task-due overdue">Verlopen: ${FP.formatDate(new Date(task.due_date))}</div>`
      : '';
    const recurIcon = task.series_id ? ' <span class="recur-icon" title="Herhalende taak">↻</span>' : '';
    return `
      <div class="card task-card ${overdue ? 'task-overdue' : ''}" data-id="${task.id}">
        <button class="task-check ${task.done ? 'done' : ''}" data-id="${task.id}" aria-label="Afvinken"></button>
        <div class="task-body">
          <div class="task-title ${task.done ? 'done' : ''}">${task.title}${recurIcon}</div>
          ${dueMeta}
        </div>
        ${badges ? `<div class="event-member-badges">${badges}</div>` : ''}
      </div>`;
  }

  function renderMealCard(meal) {
    const cook = meal.cook_member_id ? FP.getMember(meal.cook_member_id) : null;
    const badge = cook ? `<div class="event-member-badge" style="background:${cook.color}" title="${cook.name}">${cook.avatar}</div>` : '';
    return `
      <div class="meal-card" data-id="${meal.id}">
        <span class="meal-type-badge ${meal.meal_type}">${FP.mealTypeLabel(meal.meal_type)}</span>
        <div class="meal-name-row">
          <div class="meal-name">${meal.name}</div>
          ${badge ? `<div class="event-member-badges">${badge}</div>` : ''}
        </div>
        ${meal.description ? `<div class="text-muted" style="font-size:.78rem;margin-top:.2rem">${meal.description}</div>` : ''}
      </div>`;
  }

  // ── Load sections ─────────────────────────────────────────────
  async function loadEvents() {
    const container = document.getElementById('today-events');
    const empty     = document.getElementById('events-empty');
    try {
      const events = await API.get('/api/agenda/today');
      if (!events.length) {
        container.innerHTML = '';
        empty.classList.remove('hidden');
      } else {
        container.innerHTML = events.map(renderEventCard).join('');
        empty.classList.add('hidden');
      }
    } catch {
      container.innerHTML = `<p class="text-muted">Kon agenda niet laden.</p>`;
    }
  }

  async function loadMeals() {
    const container = document.getElementById('today-meals');
    const empty     = document.getElementById('meals-empty');
    try {
      const meals = await API.get('/api/meals/today');
      if (!meals.length) {
        container.innerHTML = '';
        empty.classList.remove('hidden');
      } else {
        container.innerHTML = meals.map(renderMealCard).join('');
        empty.classList.add('hidden');
      }
    } catch {
      container.innerHTML = `<p class="text-muted">Kon maaltijden niet laden.</p>`;
    }
  }

  async function loadTasks() {
    const container = document.getElementById('all-tasks');
    const empty     = document.getElementById('tasks-empty');
    try {
      const [today, overdue, lists] = await Promise.all([
        API.get('/api/tasks/today'),
        API.get('/api/tasks/overdue'),
        API.get('/api/tasks/lists'),
      ]);

      // Build list lookup: id -> name
      const listMap = Object.fromEntries(lists.map(l => [l.id, l.name]));

      // Priority order for known list names
      const PRIORITY = ['Taken', 'Huishouden'];
      const sortedLists = [...lists].sort((a, b) => {
        const ai = PRIORITY.indexOf(a.name), bi = PRIORITY.indexOf(b.name);
        if (ai !== -1 && bi !== -1) return ai - bi;
        if (ai !== -1) return -1;
        if (bi !== -1) return  1;
        return a.name.localeCompare(b.name);
      });

      // Group today's tasks by list_id (null = "Overige")
      const grouped = new Map();
      today.forEach(t => {
        const key = t.list_id ?? null;
        if (!grouped.has(key)) grouped.set(key, []);
        grouped.get(key).push(t);
      });

      let html = '';

      // Named lists in priority order
      sortedLists.forEach(list => {
        const tasks = grouped.get(list.id) || [];
        if (!tasks.length) return;
        html += `<div class="task-group-header">${list.name}</div>`;
        html += tasks.map(t => renderTaskCard(t, false)).join('');
      });

      // Overige taken (no list)
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

      if (!html) {
        container.innerHTML = '';
        empty.classList.remove('hidden');
      } else {
        container.innerHTML = html;
        empty.classList.add('hidden');
        bindTaskToggles(container);
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

  // ── Quick-add: Afspraak ───────────────────────────────────────
  function openDashEventForm() {
    Modal.open('tpl-dash-event-form');
    const form = document.getElementById('event-form');
    FP.buildMemberPicker('event-member-picker');

    const now = new Date();
    const roundedStart = new Date(now);
    roundedStart.setMinutes(Math.ceil(now.getMinutes() / 15) * 15, 0, 0);
    const roundedEnd = new Date(roundedStart);
    roundedEnd.setHours(roundedEnd.getHours() + 1);
    form.start_time.value = FP.toLocalDatetimeInput(roundedStart);
    form.end_time.value   = FP.toLocalDatetimeInput(roundedEnd);

    form.addEventListener('submit', async e => {
      e.preventDefault();
      const startDt = new Date(form.start_time.value);
      const endDt   = new Date(form.end_time.value);
      const endErr  = document.getElementById('end-time-error');
      if (endDt <= startDt) { endErr?.classList.remove('hidden'); return; }
      endErr?.classList.add('hidden');
      try {
        await API.post('/api/agenda/', {
          title:       form.title.value.trim(),
          description: form.description.value.trim(),
          location:    form.location.value.trim(),
          start_time:  startDt.toISOString(),
          end_time:    endDt.toISOString(),
          all_day:     form.all_day.checked,
          color:       form.color.value,
          member_ids:  FP.getSelectedMemberIds('event-member-picker'),
        });
        Modal.close();
        Toast.show('Afspraak toegevoegd!');
        loadEvents();
      } catch (err) { Toast.show(err.message || 'Fout bij opslaan', 'error'); }
    }, { once: true });
  }

  // ── Quick-add: Taak ───────────────────────────────────────────
  async function openDashTaskForm() {
    Modal.open('tpl-dash-task-form');
    const form = document.getElementById('task-form');
    FP.buildMemberPicker('task-member-picker');

    const today = new Date();
    form.due_date.value = `${today.getFullYear()}-${FP.pad(today.getMonth()+1)}-${FP.pad(today.getDate())}`;

    // Populate list select
    const listSel = document.getElementById('dash-task-list-select');
    try {
      const lists = await API.get('/api/tasks/lists');
      lists.forEach(l => {
        const opt = document.createElement('option');
        opt.value = l.id; opt.textContent = l.name;
        listSel.appendChild(opt);
      });
    } catch {}

    form.addEventListener('submit', async e => {
      e.preventDefault();
      try {
        await API.post('/api/tasks/', {
          title:       form.title.value.trim(),
          description: form.description.value.trim(),
          list_id:     listSel.value ? parseInt(listSel.value) : null,
          member_ids:  FP.getSelectedMemberIds('task-member-picker'),
          due_date:    form.due_date.value || null,
        });
        Modal.close();
        Toast.show('Taak toegevoegd!');
        loadTasks();
      } catch (err) { Toast.show(err.message || 'Fout bij opslaan', 'error'); }
    }, { once: true });
  }

  // ── Quick-add: Maaltijd ───────────────────────────────────────
  async function openDashMealForm() {
    Modal.open('tpl-dash-meal-form');
    const form = document.getElementById('meal-form');

    const today = new Date();
    form.date.value = `${today.getFullYear()}-${FP.pad(today.getMonth()+1)}-${FP.pad(today.getDate())}`;

    // Populate cook select
    const cookSel = document.getElementById('dash-cook-select');
    const members = FP.getMembers ? FP.getMembers() : [];
    members.forEach(m => {
      const opt = document.createElement('option');
      opt.value = m.id; opt.textContent = `${m.avatar} ${m.name}`;
      cookSel.appendChild(opt);
    });

    form.addEventListener('submit', async e => {
      e.preventDefault();
      try {
        await API.post('/api/meals/', {
          date:           form.date.value,
          meal_type:      form.meal_type.value,
          name:           form.name.value.trim(),
          description:    form.description.value.trim(),
          cook_member_id: cookSel.value ? parseInt(cookSel.value) : null,
        });
        Modal.close();
        Toast.show('Maaltijd toegevoegd!');
        loadMeals();
      } catch (err) { Toast.show(err.message || 'Fout bij opslaan', 'error'); }
    }, { once: true });
  }

  // ── Init ──────────────────────────────────────────────────────
  async function init() {
    await FP.loadMembers();
    initFab();
    await Promise.all([loadEvents(), loadMeals(), loadTasks()]);
  }

  document.addEventListener('DOMContentLoaded', init);
})();
