/* ================================================================
   dashboard.js – Overview page: today events, meals, tasks
   ================================================================ */
(function () {

  // ── Render helpers ────────────────────────────────────────────
  function renderEventCard(ev) {
    const start = new Date(ev.start_time);
    const end   = new Date(ev.end_time);
    const member = FP.getMember(ev.member_id);
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
        ${member ? `<div class="event-member-badge" style="background:${member.color}" title="${member.name}">${member.avatar}</div>` : ''}
      </div>`;
  }

  function renderTaskCard(task) {
    const member = FP.getMember(task.member_id);
    return `
      <div class="card task-card" data-id="${task.id}">
        <button class="task-check ${task.done ? 'done' : ''}" data-id="${task.id}" aria-label="Afvinken"></button>
        <div class="task-body">
          <div class="task-title ${task.done ? 'done' : ''}">${task.title}</div>
          ${member ? `<div class="task-meta">${member.avatar} ${member.name}</div>` : ''}
        </div>
      </div>`;
  }

  function renderMealCard(meal) {
    const cook = meal.cook_member_id ? FP.getMember(meal.cook_member_id) : null;
    return `
      <div class="meal-card" data-id="${meal.id}">
        <span class="meal-type-badge ${meal.meal_type}">${FP.mealTypeLabel(meal.meal_type)}</span>
        <div class="meal-name-row">
          <div class="meal-name">${meal.name}</div>
          ${cook ? `<div class="meal-cook">${cook.avatar} ${cook.name}</div>` : ''}
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
    const container = document.getElementById('today-tasks');
    const empty     = document.getElementById('tasks-empty');
    try {
      const tasks = await API.get('/api/tasks/today');
      if (!tasks.length) {
        container.innerHTML = '';
        empty.classList.remove('hidden');
      } else {
        container.innerHTML = tasks.map(renderTaskCard).join('');
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
