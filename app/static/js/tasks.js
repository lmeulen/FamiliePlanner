/* ================================================================
   tasks.js – Task lists & task management page
   ================================================================ */
(function () {
  let tasks        = [];
  let lists        = [];
  let activeList   = 'all';   // list_id or 'all'
  let activeMember = null;
  let showDone     = false;

  // ── Loaders ───────────────────────────────────────────────────
  async function loadLists() {
    lists = await API.get('/api/tasks/lists').catch(() => []);
    renderListTabs();
  }

  async function loadTasks() {
    let url = '/api/tasks/?';
    if (activeList !== 'all') url += `list_id=${activeList}&`;
    if (activeMember)         url += `member_id=${activeMember}&`;
    if (!showDone)            url += `done=false&`;
    tasks = await API.get(url).catch(() => []);
    renderTasks();
  }

  // ── Render list tabs ──────────────────────────────────────────
  function renderListTabs() {
    const tabs = document.getElementById('list-tabs');
    const allTab = tabs.querySelector('[data-list="all"]');
    tabs.innerHTML = '';
    tabs.appendChild(allTab);

    lists.forEach(l => {
      const btn = document.createElement('button');
      btn.className = `list-tab${activeList == l.id ? ' active' : ''}`;
      btn.dataset.list = l.id;
      btn.innerHTML = `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${l.color};margin-right:.3rem;vertical-align:middle"></span>${FP.esc(l.name)}`;
      tabs.appendChild(btn);
    });

    allTab.classList.toggle('active', activeList === 'all');
    tabs.querySelectorAll('.list-tab').forEach(btn => {
      btn.addEventListener('click', () => {
        tabs.querySelectorAll('.list-tab').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        activeList = btn.dataset.list;
        loadTasks();
      });
    });
  }

  // ── Render tasks ──────────────────────────────────────────────
  function renderTasks() {
    const body  = document.getElementById('tasks-body');
    const empty = document.getElementById('tasks-empty');

    const grouped = groupByList(tasks);
    if (!tasks.length) {
      body.innerHTML = '';
      empty.classList.remove('hidden');
      return;
    }
    empty.classList.add('hidden');

    let html = '';
    const isMultiList = activeList === 'all';

    if (isMultiList) {
      grouped.forEach((group, listId) => {
        const list = lists.find(l => l.id === parseInt(listId)) || { name: 'Geen lijst', color: '#9EA7C4' };
        html += `<div class="task-group-header">
          <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${list.color};margin-right:.4rem;vertical-align:middle"></span>
          ${FP.esc(list.name)}
        </div>`;
        html += group.map(renderTaskRow).join('');
      });
    } else {
      html = tasks.map(renderTaskRow).join('');
    }

    body.innerHTML = html;
    bindTaskEvents();
    initSwipeGestures();
  }

  function groupByList(tasks) {
    const map = new Map();
    tasks.forEach(t => {
      const key = t.list_id ?? 'none';
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(t);
    });
    return map;
  }

  function renderTaskRow(task) {
    const members = (task.member_ids || []).map(id => FP.getMember(id)).filter(Boolean);
    const list   = lists.find(l => l.id === task.list_id);
    const isOverdue = task.due_date && !task.done && new Date(task.due_date) < new Date();
    const recurIcon = task.series_id ? ' <span class="recur-icon" title="Herhalende taak">↻</span>' : '';
    const badges = members.map(m => `<div class="event-member-badge" style="background:${m.color}" title="${FP.esc(m.name)}">${m.avatar}</div>`).join('');
    return `
      <div class="card task-card swipeable-item${isOverdue ? ' task-overdue' : ''}" data-id="${task.id}">
        <button class="task-check ${task.done ? 'done' : ''}" data-id="${task.id}" aria-label="Afvinken"></button>
        <div class="task-body" style="cursor:pointer" data-edit="${task.id}">
          <div class="task-title ${task.done ? 'done' : ''}">${FP.esc(task.title)}${recurIcon}</div>
          <div class="task-meta">
            ${task.due_date ? FP.formatDate(task.due_date) : ''}
          </div>
        </div>
        ${task.due_date ? `<span class="task-due-badge ${isOverdue ? 'overdue' : ''}">${FP.formatDateShort(task.due_date)}</span>` : ''}
        ${list ? `<span class="task-list-dot" style="background:${list.color}"></span>` : ''}
        ${badges ? `<div class="event-member-badges">${badges}</div>` : ''}
      </div>`;
  }

  function bindTaskEvents() {
    document.querySelectorAll('.task-check').forEach(btn => {
      btn.addEventListener('click', async e => {
        e.stopPropagation();
        try {
          await API.patch(`/api/tasks/${btn.dataset.id}/toggle`);
          Cache.invalidate(/^tasks_/);
          Toast.show('Taak bijgewerkt!');
          loadTasks();
        } catch { Toast.show('Fout', 'error'); }
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
