/**
 * search.js – Global search functionality
 */

(function() {
  'use strict';

  let searchTimeout = null;
  let lastQuery = '';

  const searchInput = document.getElementById('search-input');
  const emptyState = document.getElementById('search-empty');
  const loadingState = document.getElementById('search-loading');
  const noResultsState = document.getElementById('search-no-results');
  const resultsContainer = document.getElementById('search-results');

  const eventsSection = document.getElementById('events-section');
  const tasksSection = document.getElementById('tasks-section');
  const mealsSection = document.getElementById('meals-section');

  const eventsList = document.getElementById('events-list');
  const tasksList = document.getElementById('tasks-list');
  const mealsList = document.getElementById('meals-list');

  const eventsCount = document.getElementById('events-count');
  const tasksCount = document.getElementById('tasks-count');
  const mealsCount = document.getElementById('meals-count');

  // ── Search input handler ──────────────────────────────────────
  searchInput?.addEventListener('input', (e) => {
    const query = e.target.value.trim();

    // Clear previous timeout
    if (searchTimeout) clearTimeout(searchTimeout);

    // Reset if query is too short
    if (query.length < 3) {
      showEmptyState();
      lastQuery = '';
      return;
    }

    // Debounce search (300ms)
    searchTimeout = setTimeout(() => performSearch(query), 300);
  });

  // ── Perform search ────────────────────────────────────────────
  async function performSearch(query) {
    if (query === lastQuery) return;
    lastQuery = query;

    showLoadingState();

    try {
      const data = await API.get(`/api/search/?q=${encodeURIComponent(query)}`);
      displayResults(data, query);
    } catch (err) {
      Toast.show('Fout bij zoeken', 'error');
      showEmptyState();
    }
  }

  // ── Display results ───────────────────────────────────────────
  function displayResults(data, query) {
    const totalResults = data.events.length + data.tasks.length + data.meals.length;

    if (totalResults === 0) {
      showNoResults(query);
      return;
    }

    // Show results container
    hideAllStates();
    resultsContainer.classList.remove('hidden');

    // Render events
    if (data.events.length > 0) {
      eventsSection.classList.remove('hidden');
      eventsCount.textContent = data.events.length;
      eventsList.innerHTML = data.events.map(event => renderEventCard(event, query)).join('');

      // Attach click handlers
      eventsList.querySelectorAll('.search-result-card').forEach(card => {
        card.addEventListener('click', () => openEventDetail(parseInt(card.dataset.id)));
      });
    } else {
      eventsSection.classList.add('hidden');
    }

    // Render tasks
    if (data.tasks.length > 0) {
      tasksSection.classList.remove('hidden');
      tasksCount.textContent = data.tasks.length;
      tasksList.innerHTML = data.tasks.map(task => renderTaskCard(task, query)).join('');

      // Attach click handlers
      tasksList.querySelectorAll('.search-result-card').forEach(card => {
        card.addEventListener('click', () => openTaskDetail(parseInt(card.dataset.id)));
      });
    } else {
      tasksSection.classList.add('hidden');
    }

    // Render meals
    if (data.meals.length > 0) {
      mealsSection.classList.remove('hidden');
      mealsCount.textContent = data.meals.length;
      mealsList.innerHTML = data.meals.map(meal => renderMealCard(meal, query)).join('');

      // Attach click handlers
      mealsList.querySelectorAll('.search-result-card').forEach(card => {
        card.addEventListener('click', () => openMealDetail(parseInt(card.dataset.id)));
      });
    } else {
      mealsSection.classList.add('hidden');
    }
  }

  // ── Render cards ──────────────────────────────────────────────
  function renderEventCard(event, query) {
    const start = new Date(event.start_time);
    const dateStr = FP.formatDate(start);
    const timeStr = event.all_day ? 'Hele dag' : FP.formatTime(start);
    const members = (event.member_ids || []).map(id => FP.getMember(id)).filter(Boolean);
    const accentColor = FP.agendaEventColor(event.member_ids || []);
    const badges = members.map(m => `<div class="event-member-badge" style="background:${m.color}">${m.avatar}</div>`).join('');

    const title = highlightMatch(FP.esc(event.title), query);
    const location = event.location ? `📍 ${highlightMatch(FP.esc(event.location), query)}` : '';

    return `
      <div class="search-result-card card" data-id="${event.id}" style="cursor:pointer; border-left: 4px solid ${accentColor}">
        <div class="event-body">
          <div class="event-title">${title}</div>
          <div class="event-meta">
            ${dateStr} · ${timeStr}
            ${location}
          </div>
        </div>
        ${badges ? `<div class="event-member-badges">${badges}</div>` : ''}
      </div>
    `;
  }

  function renderTaskCard(task, query) {
    const title = highlightMatch(FP.esc(task.title), query);
    const doneIcon = task.done ? '✅' : '⬜';
    const dueDate = task.due_date ? `📅 ${FP.formatDate(new Date(task.due_date))}` : '';
    const members = (task.member_ids || []).map(id => FP.getMember(id)).filter(Boolean);
    const memberStr = members.map(m => `${m.avatar} ${m.name}`).join(', ');

    return `
      <div class="search-result-card card" data-id="${task.id}" style="cursor:pointer">
        <div class="task-content">
          <span class="task-icon">${doneIcon}</span>
          <div class="task-details">
            <div class="task-title">${title}</div>
            <div class="task-meta">
              ${dueDate}
              ${memberStr ? ` · ${memberStr}` : ''}
            </div>
          </div>
        </div>
      </div>
    `;
  }

  function renderMealCard(meal, query) {
    const name = highlightMatch(FP.esc(meal.name), query);
    const dateStr = FP.formatDate(new Date(meal.date));
    const mealTypeIcons = {
      breakfast: '🌅',
      lunch: '☀️',
      dinner: '🌙',
      snack: '🍎'
    };
    const icon = mealTypeIcons[meal.meal_type] || '🍽️';
    const cook = meal.cook_member_id ? FP.getMember(meal.cook_member_id) : null;
    const cookStr = cook ? `👨‍🍳 ${cook.name}` : '';

    return `
      <div class="search-result-card card" data-id="${meal.id}" style="cursor:pointer">
        <div class="meal-content">
          <span class="meal-icon">${icon}</span>
          <div class="meal-details">
            <div class="meal-title">${name}</div>
            <div class="meal-meta">
              ${dateStr}
              ${cookStr ? ` · ${cookStr}` : ''}
            </div>
          </div>
        </div>
      </div>
    `;
  }

  // ── Highlight matching text ───────────────────────────────────
  function highlightMatch(text, query) {
    if (!query) return text;
    const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(`(${escapedQuery})`, 'gi');
    return text.replace(regex, '<mark>$1</mark>');
  }

  // ── State management ──────────────────────────────────────────
  function showEmptyState() {
    hideAllStates();
    emptyState.classList.remove('hidden');
  }

  function showLoadingState() {
    hideAllStates();
    loadingState.classList.remove('hidden');
  }

  function showNoResults(query) {
    hideAllStates();
    noResultsState.classList.remove('hidden');
    document.getElementById('search-query-text').textContent = query;
  }

  function hideAllStates() {
    emptyState.classList.add('hidden');
    loadingState.classList.add('hidden');
    noResultsState.classList.add('hidden');
    resultsContainer.classList.add('hidden');
    eventsSection.classList.add('hidden');
    tasksSection.classList.add('hidden');
    mealsSection.classList.add('hidden');
  }

  // ── Open detail modals (reuse existing modal functions) ───────
  // These functions should be defined in agenda.js, tasks.js, meals.js
  // For now, we'll navigate to the respective pages
  function openEventDetail(id) {
    window.location.href = `/agenda?event=${id}`;
  }

  function openTaskDetail(id) {
    window.location.href = `/taken?task=${id}`;
  }

  function openMealDetail(id) {
    window.location.href = `/maaltijden?meal=${id}`;
  }

})();
