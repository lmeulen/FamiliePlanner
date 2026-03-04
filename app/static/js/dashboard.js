/* ================================================================
   dashboard.js – Overview page: today events, meals, tasks, week
   ================================================================ */
(function () {
  let activeMember = null;

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
    return `
      <div class="meal-card" data-id="${meal.id}">
        <span class="meal-type-badge ${meal.meal_type}">${FP.mealTypeLabel(meal.meal_type)}</span>
        <div class="meal-name">${meal.name}</div>
        ${meal.description ? `<div class="text-muted" style="font-size:.78rem;margin-top:.2rem">${meal.description}</div>` : ''}
      </div>`;
  }

  // ── Load sections ─────────────────────────────────────────────
  async function loadEvents() {
    const container = document.getElementById('today-events');
    const empty     = document.getElementById('events-empty');
    try {
      const events = await API.get('/api/agenda/today');
      const filtered = activeMember ? events.filter(e => !e.member_id || e.member_id === activeMember) : events;
      if (!filtered.length) {
        container.innerHTML = '';
        empty.classList.remove('hidden');
      } else {
        container.innerHTML = filtered.map(renderEventCard).join('');
        empty.classList.add('hidden');
      }
    } catch (e) {
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
    } catch (e) {
      container.innerHTML = `<p class="text-muted">Kon maaltijden niet laden.</p>`;
    }
  }

  async function loadTasks() {
    const container = document.getElementById('today-tasks');
    const empty     = document.getElementById('tasks-empty');
    try {
      const url = activeMember
        ? `/api/tasks/today?member_id=${activeMember}`
        : '/api/tasks/today';
      const tasks = await API.get(url);
      if (!tasks.length) {
        container.innerHTML = '';
        empty.classList.remove('hidden');
      } else {
        container.innerHTML = tasks.map(renderTaskCard).join('');
        empty.classList.add('hidden');
        bindTaskToggles(container);
      }
    } catch (e) {
      container.innerHTML = `<p class="text-muted">Kon taken niet laden.</p>`;
    }
  }

  async function loadWeekStrip() {
    const strip = document.getElementById('week-strip');
    const events = await API.get('/api/agenda/week').catch(() => []);
    const meals  = await API.get('/api/meals/week').catch(() => []);

    strip.innerHTML = '';
    const today = FP.today();
    for (let i = 0; i < 7; i++) {
      const day  = FP.addDays(today, i);
      const dayEvents = events.filter(e => FP.isSameDay(new Date(e.start_time), day));
      const dayMeals  = meals.filter(m  => FP.isSameDay(new Date(m.date), day));

      const dots = [
        ...dayEvents.map(e => `<span class="week-dot" style="background:${e.color}"></span>`),
        ...dayMeals.map(()  => `<span class="week-dot" style="background:var(--meal-dinner)"></span>`),
      ].slice(0, 5).join('');

      const isToday = i === 0;
      strip.innerHTML += `
        <div class="week-day-card ${isToday ? 'week-day-card--today' : ''}">
          <div class="week-day-name">${FP.NL_DAYS[day.getDay()]}</div>
          <div class="week-day-num">${day.getDate()}</div>
          <div class="week-day-dots">${dots}</div>
        </div>`;
    }
  }

  // ── Task toggle ───────────────────────────────────────────────
  function bindTaskToggles(container) {
    container.querySelectorAll('.task-check').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = btn.dataset.id;
        try {
          await API.patch(`/api/tasks/${id}/toggle`);
          loadTasks();
          Toast.show('Taak bijgewerkt!');
        } catch (e) {
          Toast.show('Fout bij bijwerken', 'error');
        }
      });
    });
  }

  // ── Greeting ──────────────────────────────────────────────────
  function setGreeting() {
    const h = new Date().getHours();
    const greeting = h < 12 ? 'Goedemorgen! 👋' : h < 18 ? 'Goedemiddag! ☀️' : 'Goedenavond! 🌙';
    const el = document.querySelector('.page-title');
    if (el) el.textContent = greeting;
  }

  // ── Init ──────────────────────────────────────────────────────
  async function init() {
    setGreeting();
    await FP.loadMembers();
    await FP.buildMemberChips('member-chips', member => {
      activeMember = member;
      loadEvents();
      loadTasks();
    });

    await Promise.all([loadEvents(), loadMeals(), loadTasks(), loadWeekStrip()]);
  }

  document.addEventListener('DOMContentLoaded', init);
})();
