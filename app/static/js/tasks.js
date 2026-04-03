/* ================================================================
   tasks.js – Task lists & task management page (chronological view)
   ================================================================ */
(function () {
  let tasks        = [];
  let lists        = [];
  let activeMember = null;
  let showDone     = false;

  // ── Loaders ───────────────────────────────────────────────────
  async function loadLists() {
    lists = await API.get('/api/tasks/lists').catch(() => []);
    renderListTabs();
  }

  async function loadTasks() {
    let url = '/api/tasks/?';
    if (activeMember)         url += `member_id=${activeMember}&`;
    if (!showDone)            url += `done=false&`;
    tasks = await API.get(url).catch(() => []);
    renderTasks();
  }

  // ── Render list tabs (no longer needed - using chronological view) ──
  function renderListTabs() {
    // List tabs removed - now using chronological view
  }

  // ── Render tasks (chronological view per day) ─────────────────
  function renderTasks() {
    const body  = document.getElementById('tasks-body');
    const empty = document.getElementById('tasks-empty');

    if (!tasks.length) {
      body.innerHTML = '';
      empty.classList.remove('hidden');
      return;
    }
    empty.classList.add('hidden');

    // Group tasks by date
    const tasksByDate = groupTasksByDate(tasks);

    // Render day sections
    const sectionsHtml = Array.from(tasksByDate.values()).map(({ date, tasks: dayTasks }) => {
      const dayLabel = date ? `${FP.dayNameFull(date)} ${FP.formatDate(date)}` : 'Geen vervaldatum';
      const daySub = date && FP.isToday(date) ? 'Vandaag' : '';
      const isOverdue = date && date < new Date() && !FP.isToday(date);

      // Sort tasks within day by list (category)
      const sortedTasks = dayTasks.sort((a, b) => {
        const listA = lists.find(l => l.id === a.list_id);
        const listB = lists.find(l => l.id === b.list_id);
        return (listA?.sort_order || 999) - (listB?.sort_order || 999);
      });

      return `<section class="agenda-day-section${isOverdue ? ' overdue-section' : ''}">
        <div class="agenda-day-section-header">
          <div class="agenda-day-section-title">${FP.esc(dayLabel)}</div>
          ${daySub ? `<div class="agenda-day-section-badge">${daySub}</div>` : ''}
          ${isOverdue ? `<div class="agenda-day-section-badge overdue-badge">Verlopen</div>` : ''}
        </div>
        <div class="agenda-day-section-list">
          ${sortedTasks.map(renderTaskRow).join('')}
        </div>
      </section>`;
    }).join('');

    body.innerHTML = `<div class="agenda-day-list">${sectionsHtml}</div>`;
    bindTaskEvents();
    initSwipeGestures();
  }

  function groupTasksByDate(tasks) {
    const map = new Map();

    tasks.forEach(task => {
      let dateKey, dateObj;

      if (task.due_date) {
        dateObj = new Date(task.due_date + 'T00:00:00');
        dateKey = dateObj.toDateString();
      } else {
        dateKey = 'no-date';
        dateObj = null;
      }

      if (!map.has(dateKey)) {
        map.set(dateKey, { date: dateObj, tasks: [] });
      }
      map.get(dateKey).tasks.push(task);
    });

    // Sort by date (null dates at end)
    return new Map([...map.entries()].sort((a, b) => {
      if (a[0] === 'no-date') return 1;
      if (b[0] === 'no-date') return -1;
      return a[1].date - b[1].date;
    }));
  }

  function renderTaskRow(task) {
    const members = (task.member_ids || []).map(id => FP.getMember(id)).filter(Boolean);
    const list = lists.find(l => l.id === task.list_id) || { name: 'Geen lijst', color: '#9EA7C4' };
    const recurIcon = task.series_id ? ' <span class="recur-icon" title="Herhalende taak">↻</span>' : '';
    const badges = members.map(m => `<div class="event-member-badge" style="background:${m.color}" title="${FP.esc(m.name)}">${m.avatar}</div>`).join('');

    return `
      <div class="card task-card swipeable-item${task.done ? ' task-done' : ''}" data-id="${task.id}">
        <div class="event-color-bar" style="background:${list.color}"></div>
        <button class="task-check ${task.done ? 'done' : ''}" data-id="${task.id}" aria-label="Afvinken"></button>
        <div class="task-body" style="cursor:pointer" data-edit="${task.id}">
          <div class="task-title ${task.done ? 'done' : ''}">${FP.esc(task.title)}${recurIcon}</div>
          <div class="task-meta">
            ${list.name ? `<span class="task-list-label">${FP.esc(list.name)}</span>` : ''}
            ${task.description ? ` · ${FP.esc(task.description)}` : ''}
          </div>
        </div>
        ${badges ? `<div class="event-member-badges">${badges}</div>` : ''}
      </div>`;
  }

  function bindTaskEvents() {
    document.querySelectorAll('.task-check').forEach(btn => {
      btn.addEventListener('click', async e => {
        e.stopPropagation();
        const taskId = parseInt(btn.dataset.id);
        const task = tasks.find(t => t.id === taskId);

        if (!task) return;

        // Optimistically update UI
        const originalDone = task.done;
        task.done = !task.done;
        renderTasks(); // Update UI immediately

        try {
          await API.patch(`/api/tasks/${taskId}/toggle`);
          Cache.invalidate(/^tasks_/);
          Toast.show(task.done ? 'Taak afgerond! 🎉' : 'Taak heropend');
        } catch (err) {
          // Revert on error
          task.done = originalDone;
          renderTasks();
          Toast.show('Kon taak niet bijwerken', 'error');
        }
      });
    });

    document.querySelectorAll('[data-edit]').forEach(el => {
      el.addEventListener('click', () => openTaskForm(parseInt(el.dataset.edit)));
    });
  }

  // ── Swipe gestures ────────────────────────────────────────────
  let swipeHandler = null;
  function initSwipeGestures() {
    // Destroy previous handler if exists
    if (swipeHandler) {
      swipeHandler.destroy();
    }

    // Only initialize on touch devices
    if (!('ontouchstart' in window) || !window.SwipeHandler) {
      return;
    }

    const tasksBody = document.getElementById('tasks-body');
    if (!tasksBody) return;

    swipeHandler = new window.SwipeHandler(tasksBody, {
      selector: '.task-card',
      threshold: 80,
      rightActionIcon: '✓',
      leftActionIcon: '🗑️',
      rightActionColor: '#4CAF50',
      leftActionColor: '#F44336',

      // Swipe right = toggle complete
      onSwipeRight: async (element) => {
        const taskId = parseInt(element.dataset.id);
        try {
          await API.patch(`/api/tasks/${taskId}/toggle`);
          Cache.invalidate(/^tasks_/);
          const task = tasks.find(t => t.id === taskId);
          if (task) {
            Toast.show(task.done ? 'Taak gemarkeerd als niet afgerond' : 'Taak afgerond! ✓');
          }
          await loadTasks();
        } catch (err) {
          Toast.show('Fout bij bijwerken', 'error');
          console.error('Failed to toggle task:', err);
        }
      },

      // Swipe left = delete
      onSwipeLeft: async (element) => {
        const taskId = parseInt(element.dataset.id);
        const task = tasks.find(t => t.id === taskId);

        if (!confirm(`Taak "${task?.title || 'deze'}" verwijderen?`)) {
          return;
        }

        try {
          await API.delete(`/api/tasks/${taskId}`);
          Cache.invalidate(/^tasks_/);
          Toast.show('Taak verwijderd', 'warning');
          await loadTasks();
        } catch (err) {
          Toast.show('Fout bij verwijderen', 'error');
          console.error('Failed to delete task:', err);
        }
      }
    });
  }

  // ── Task form ─────────────────────────────────────────────────
  async function openTaskForm(id = null) {
    const controller = new TaskFormController({
      templateId: 'tpl-task-form',
      formId: 'task-form',
      simplified: false,
      taskCache: tasks,
      onSave: () => {
        Cache.invalidate(/^tasks_/);
        loadTasks();
      },
    });

    await controller.open(id);
  }

  // ── List form (create new) ────────────────────────────────────
  function openListForm() {
    Modal.open('tpl-list-form');
    const form = document.getElementById('list-form');
    form.addEventListener('submit', async e => {
      e.preventDefault();
      const data = { name: form.name.value, color: form.color.value };
      try {
        await API.post('/api/tasks/lists', data);
        Cache.invalidate(/^tasks_/);
        Toast.show('Lijst aangemaakt!');
        Modal.close();
        await loadLists();
        loadTasks();
      } catch (err) {
        Toast.show(err.message || 'Fout', 'error');
      }
    }, { once: true });
  }

  // ── Manage lists order ────────────────────────────────────────
  async function openManageLists() {
    Modal.open('tpl-manage-lists');
    let overduePos = 9999;
    try {
      const res = await API.get('/api/tasks/overdue-position');
      overduePos = res.sort_order;
    } catch {}

    // Build virtual items array: lists + overdue pseudo-entry
    let items = [
      ...lists.map(l => ({ type: 'list', id: l.id, name: l.name, color: l.color, sort_order: l.sort_order })),
      { type: 'overdue', id: null, name: 'Verlopen taken', color: '#E74C3C', sort_order: overduePos },
    ];
    items.sort((a, b) => a.sort_order - b.sort_order || (a.type === 'overdue' ? 1 : -1));

    function renderOrder() {
      const container = document.getElementById('manage-lists-order');
      if (!container) return;
      container.innerHTML = items.map((item, idx) => `
        <div class="manage-list-row" data-idx="${idx}">
          <span class="manage-list-dot" style="background:${item.color}"></span>
          <span class="manage-list-name">${FP.esc(item.name)}</span>
          <div class="manage-list-btns">
            <button class="icon-btn manage-up" data-idx="${idx}" ${idx === 0 ? 'disabled' : ''} title="Omhoog">▲</button>
            <button class="icon-btn manage-down" data-idx="${idx}" ${idx === items.length - 1 ? 'disabled' : ''} title="Omlaag">▼</button>
          </div>
        </div>`).join('');

      container.querySelectorAll('.manage-up').forEach(btn => {
        btn.addEventListener('click', () => {
          const i = parseInt(btn.dataset.idx);
          if (i === 0) return;
          [items[i - 1], items[i]] = [items[i], items[i - 1]];
          renderOrder();
        });
      });
      container.querySelectorAll('.manage-down').forEach(btn => {
        btn.addEventListener('click', () => {
          const i = parseInt(btn.dataset.idx);
          if (i === items.length - 1) return;
          [items[i], items[i + 1]] = [items[i + 1], items[i]];
          renderOrder();
        });
      });
    }
    renderOrder();

    document.getElementById('btn-save-list-order')?.addEventListener('click', async () => {
      // Assign sequential sort_orders
      items.forEach((item, idx) => { item.sort_order = (idx + 1) * 10; });

      const listItems = items.filter(i => i.type === 'list');
      const overdueItem = items.find(i => i.type === 'overdue');

      try {
        await Promise.all([
          API.put('/api/tasks/lists/reorder', listItems.map(i => ({ id: i.id, sort_order: i.sort_order }))),
          API.put('/api/tasks/overdue-position', { sort_order: overdueItem?.sort_order ?? 9999 }),
        ]);
        Cache.invalidate(/^tasks_/);
        Toast.show('Volgorde opgeslagen!');
        Modal.close();
        await loadLists();
        loadTasks();
      } catch (err) { Toast.show(err.message || 'Fout bij opslaan', 'error'); }
    }, { once: true });
  }

  // ── Init ──────────────────────────────────────────────────────
  async function init() {
    await FP.loadMembers();
    await loadLists();
    await loadTasks();

    document.getElementById('btn-add-task')?.addEventListener('click', () => openTaskForm());
    document.getElementById('btn-add-list')?.addEventListener('click', openListForm);
    document.getElementById('btn-manage-lists')?.addEventListener('click', openManageLists);
    document.getElementById('show-done')?.addEventListener('change', e => {
      showDone = e.target.checked;
      loadTasks();
    });

    await FP.buildMemberChips('tasks-member-chips', m => {
      activeMember = m;
      loadTasks();
    });

    // Check for URL parameter to open specific task modal (from search)
    const params = new URLSearchParams(window.location.search);
    const taskId = params.get('task');
    if (taskId) {
      openTaskForm(parseInt(taskId));
      // Clean URL without reload
      window.history.replaceState({}, '', '/taken');
    }
  }

  document.addEventListener('DOMContentLoaded', init);
})();
