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

  // ── Init ──────────────────────────────────────────────────────
  async function init() {
    await FP.loadMembers();
    await Promise.all([loadEvents(), loadMeals(), loadTasks()]);
  }

  document.addEventListener('DOMContentLoaded', init);
})();
