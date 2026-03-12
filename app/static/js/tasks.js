/* ================================================================
   tasks.js – Task lists & task management page
   ================================================================ */
(function () {
  let tasks        = [];
  let lists        = [];
  let activeList   = 'all';   // list_id or 'all'
  let activeMember = null;
  let showDone     = false;
  let editTaskId   = null;
  let editSeriesId = null;

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
      <div class="card task-card${isOverdue ? ' task-overdue' : ''}" data-id="${task.id}">
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
          Toast.show('Taak bijgewerkt!');
          loadTasks();
        } catch { Toast.show('Fout', 'error'); }
      });
    });

    document.querySelectorAll('[data-edit]').forEach(el => {
      el.addEventListener('click', () => openTaskForm(parseInt(el.dataset.edit)));
    });
  }

  // ── Task form ─────────────────────────────────────────────────
  async function openTaskForm(id = null) {
    editTaskId   = id;
    editSeriesId = null;
    Modal.open('tpl-task-form');
    const form        = document.getElementById('task-form');
    const titleEl     = document.getElementById('task-form-title');
    const delBtn      = document.getElementById('btn-delete-task');
    const recurToggle = document.getElementById('recurrence-toggle');
    const recurFields = document.getElementById('recurrence-fields');
    const recurRow    = document.getElementById('recurrence-toggle-row');
    const scopeSel    = document.getElementById('scope-selector');

    FP.buildMemberPicker('task-member-picker');

    // Populate list select (required – no empty option)
    const listSel = form.querySelector('select[name="list_id"]');
    listSel.innerHTML = '';
    lists.forEach(l => {
      const opt = document.createElement('option');
      opt.value = l.id; opt.textContent = l.name;
      listSel.appendChild(opt);
    });

    // Recurrence toggle behaviour
    recurToggle.addEventListener('change', () => {
      recurFields.classList.toggle('hidden', !recurToggle.checked);
      if (recurToggle.checked) {
        form.querySelector('[name="series_end"]').value = '';
      }
    });

    // ── Progressive disclosure for recurrence UI ─────
    const recurrenceUI = new RecurrenceUIController({
      formId: 'task-form',
      idPrefix: 'task-',
      showToggle: !id,
    });

    if (id) {
      titleEl.textContent = 'Taak bewerken';
      delBtn.classList.remove('hidden');
      const task = tasks.find(t => t.id === id);
      if (task) {
        form.title.value       = task.title;
        form.description.value = task.description || '';
        listSel.value          = task.list_id || '';
        FP.buildMemberPicker('task-member-picker', task.member_ids || []);
        form.due_date.value    = task.due_date || '';

        if (task.series_id) {
          editSeriesId = task.series_id;
          recurRow.classList.add('hidden');    // hide toggle when editing
          recurFields.classList.add('hidden');
          scopeSel.classList.remove('hidden');

          // Scope radio change handler - show recurrence fields when editing series
          form.querySelectorAll('input[name="edit_scope"]').forEach(radio => {
            radio.addEventListener('change', () => {
              const scope = radio.value;
              recurFields.classList.toggle('hidden', scope !== 'series');
              if (scope === 'series' && editSeriesId) {
                // Load series data and populate fields
                API.get(`/api/tasks/series/${editSeriesId}`).then(s => {
                  recurrenceUI.populateFromSeries(s);
                }).catch(() => {});
              }
            });
          });
        } else {
          recurRow.classList.remove('hidden');
          scopeSel.classList.add('hidden');
        }
      }
    } else {
      titleEl.textContent = 'Taak toevoegen';
      delBtn.classList.add('hidden');
      recurRow.classList.remove('hidden');
      scopeSel.classList.add('hidden');
      recurFields.classList.add('hidden');
      // Default to active list or first list
      if (activeList !== 'all') {
        listSel.value = activeList;
      } else if (lists.length) {
        listSel.value = lists[0].id;
      }
      // Default due date to today
      form.due_date.value = FP.todayStr();
    }

    form.addEventListener('submit', async e => {
      e.preventDefault();
      const scope = form.querySelector('[name="edit_scope"]:checked')?.value || 'this';
      const memberIds = FP.getSelectedMemberIds('task-member-picker');

      // Trim text inputs
      form.title.value       = form.title.value.trim();
      form.description.value = form.description.value.trim();

      if (!form.title.value) {
        form.title.focus();
        return;
      }

      // Creating a new recurring series
      if (!editTaskId && recurToggle.checked) {
        // Validate recurrence fields
        const dueDate = form.due_date.value;
        const validation = recurrenceUI.validate(dueDate);
        if (!validation.valid) {
          if (validation.errorElementId) {
            recurrenceUI.showValidationError(validation.errorElementId);
          }
          Toast.show(validation.error, 'error');
          return;
        }
        recurrenceUI.hideAllValidationErrors();

        const recurrencePayload = recurrenceUI.getRecurrencePayload();
        const payload = {
          title:           form.title.value,
          description:     form.description.value,
          list_id:         listSel.value ? parseInt(listSel.value) : lists[0]?.id || null,
          member_ids:      memberIds,
          series_start:    dueDate,
          ...recurrencePayload,
        };

        try {
          await API.post('/api/tasks/series', payload);
          Toast.show('Reeks aangemaakt!');
          Modal.close();
          loadTasks();
        } catch (err) { Toast.show(err.message || 'Fout bij opslaan', 'error'); }
        return;
      }

      // Editing series as a whole
      if (editSeriesId && scope === 'series') {
        const recurrencePayload = recurrenceUI.getRecurrencePayload();
        const payload = {
          title:           form.title.value,
          description:     form.description.value,
          list_id:         listSel.value ? parseInt(listSel.value) : lists[0]?.id || null,
          member_ids:      memberIds,
          ...recurrencePayload,
        };

        try {
          await API.put(`/api/tasks/series/${editSeriesId}`, payload);
          Toast.show('Reeks bijgewerkt!');
          Modal.close();
          loadTasks();
        } catch (err) { Toast.show(err.message || 'Fout bij opslaan', 'error'); }
        return;
      }

      // Single task create / edit
      const data = {
        title:       form.title.value,
        description: form.description.value,
        list_id:     listSel.value ? parseInt(listSel.value) : lists[0]?.id || null,
        member_ids:  memberIds,
        due_date:    form.due_date.value || null,
        done:        false,
      };
      try {
        if (editTaskId) {
          const cur = tasks.find(t => t.id === editTaskId);
          const updated = await API.put(`/api/tasks/${editTaskId}`, { ...data, done: cur?.done ?? false });
          // Update local array immediately so reopening the form shows fresh data
          const idx = tasks.findIndex(t => t.id === editTaskId);
          if (idx !== -1) tasks[idx] = updated;
          Toast.show('Taak bijgewerkt!');
        } else {
          await API.post('/api/tasks/', data);
          Toast.show('Taak toegevoegd!');
        }
        Modal.close();
        loadTasks();
      } catch (err) {
        Toast.show(err.message || 'Fout bij opslaan', 'error');
      }
    }, { once: true });

    delBtn.addEventListener('click', async () => {
      if (editSeriesId) {
        const scope = form.querySelector('[name="edit_scope"]:checked')?.value || 'this';
        if (scope === 'series') {
          if (!confirm('Hele reeks verwijderen?')) return;
          try {
            await API.delete(`/api/tasks/series/${editSeriesId}`);
            Toast.show('Reeks verwijderd', 'warning');
            Modal.close();
            loadTasks();
          } catch { Toast.show('Fout', 'error'); }
          return;
        }
      }
      if (!confirm('Taak verwijderen?')) return;
      try {
        await API.delete(`/api/tasks/${editTaskId}`);
        Toast.show('Taak verwijderd', 'warning');
        Modal.close();
        loadTasks();
      } catch { Toast.show('Fout', 'error'); }
    }, { once: true });
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
