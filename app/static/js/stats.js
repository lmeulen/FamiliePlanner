/* global API */
(function () {
  let currentPeriod = 'all';

  const loadingEl = document.getElementById('stats-loading');
  const contentEl = document.getElementById('stats-content');

  // ── Load statistics ───────────────────────────────────────────────
  async function loadStats() {
    try {
      loadingEl.classList.remove('hidden');
      contentEl.classList.add('hidden');

      const stats = await API.get(`/api/stats/?period=${currentPeriod}`);
      if (!stats) return;

      renderStats(stats);

      loadingEl.classList.add('hidden');
      contentEl.classList.remove('hidden');
    } catch (err) {
      console.error('Failed to load stats:', err);
      loadingEl.innerHTML = '<div style="text-align: center; padding: 3rem; color: var(--error);">❌ Fout bij laden van statistieken</div>';
    }
  }

  // ── Render statistics ─────────────────────────────────────────────
  function renderStats(stats) {
    // Database counts
    const dbCounts = stats.database_counts;
    document.getElementById('db-family-count').textContent = dbCounts.family_members;
    document.getElementById('db-tasks-count').textContent = dbCounts.tasks;
    document.getElementById('db-events-count').textContent = dbCounts.agenda_events;
    document.getElementById('db-meals-count').textContent = dbCounts.meals;
    document.getElementById('db-photos-count').textContent = dbCounts.photos;
    document.getElementById('db-series-count').textContent = dbCounts.task_series + dbCounts.event_series;

    // Task completion stats
    const taskStats = stats.task_stats;
    document.getElementById('task-completion-rate').textContent = taskStats.completion_rate + '%';
    document.getElementById('task-completed-count').textContent = taskStats.completed;
    document.getElementById('task-total-count').textContent = taskStats.total;

    // Task completions by member
    const taskCompletionList = document.getElementById('task-completion-list');
    const taskCompletionEmpty = document.getElementById('task-completion-empty');

    if (stats.task_completions.length > 0) {
      taskCompletionList.innerHTML = stats.task_completions.map(member => `
        <div class="stat-member-row">
          <div class="stat-member-info">
            <span class="stat-member-avatar">${member.avatar}</span>
            <span class="stat-member-name">${FP.esc(member.name)}</span>
          </div>
          <div class="stat-member-count">
            <span class="stat-count-badge">${member.count}</span>
            <span class="stat-count-label">taken</span>
          </div>
        </div>
      `).join('');
      taskCompletionList.classList.remove('hidden');
      taskCompletionEmpty.classList.add('hidden');
    } else {
      taskCompletionList.classList.add('hidden');
      taskCompletionEmpty.classList.remove('hidden');
    }

    // Cooking frequency
    const cookingList = document.getElementById('cooking-frequency-list');
    const cookingEmpty = document.getElementById('cooking-frequency-empty');

    if (stats.cooking_frequency.length > 0) {
      cookingList.innerHTML = stats.cooking_frequency.map(member => `
        <div class="stat-member-row">
          <div class="stat-member-info">
            <span class="stat-member-avatar">${member.avatar}</span>
            <span class="stat-member-name">${FP.esc(member.name)}</span>
          </div>
          <div class="stat-member-count">
            <span class="stat-count-badge">${member.count}</span>
            <span class="stat-count-label">maaltijden</span>
          </div>
        </div>
      `).join('');
      cookingList.classList.remove('hidden');
      cookingEmpty.classList.add('hidden');
    } else {
      cookingList.classList.add('hidden');
      cookingEmpty.classList.remove('hidden');
    }

    // Top meals
    const topMealsList = document.getElementById('top-meals-list');
    const topMealsEmpty = document.getElementById('top-meals-empty');

    if (stats.top_meals.length > 0) {
      const maxCount = Math.max(...stats.top_meals.map(m => m.count));
      topMealsList.innerHTML = stats.top_meals.map((meal, index) => {
        const percentage = (meal.count / maxCount) * 100;
        return `
          <div class="stat-meal-row">
            <div class="stat-meal-rank">${index + 1}</div>
            <div class="stat-meal-info">
              <div class="stat-meal-name">${FP.esc(meal.name)}</div>
              <div class="stat-meal-bar">
                <div class="stat-meal-bar-fill" style="width: ${percentage}%"></div>
              </div>
            </div>
            <div class="stat-meal-count">${meal.count}×</div>
          </div>
        `;
      }).join('');
      topMealsList.classList.remove('hidden');
      topMealsEmpty.classList.add('hidden');
    } else {
      topMealsList.classList.add('hidden');
      topMealsEmpty.classList.remove('hidden');
    }

    // Agenda activity
    document.getElementById('agenda-events-per-week').textContent = stats.agenda_activity.events_per_week;
    document.getElementById('agenda-total-events').textContent = stats.agenda_activity.total_events;
  }

  // ── Period filter ─────────────────────────────────────────────────
  document.querySelectorAll('.view-btn[data-period]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.view-btn[data-period]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentPeriod = btn.dataset.period;
      loadStats();
    });
  });

  // ── Init ──────────────────────────────────────────────────────────
  loadStats();
})();
