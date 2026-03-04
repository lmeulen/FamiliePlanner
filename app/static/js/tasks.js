/* ================================================================
   tasks.js – Task lists & task management page
   ================================================================ */
(function () {
  let tasks      = [];
  let lists      = [];
  let activeList = 'all';   // list_id or 'all'
  let activeMember = null;
  let showDone   = false;
  let editTaskId = null;

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
    // Keep first "Alle" tab
    const allTab = tabs.querySelector('[data-list="all"]');
    tabs.innerHTML = '';
    tabs.appendChild(allTab);

    lists.forEach(l => {
      const btn = document.createElement('button');
      btn.className = `list-tab${activeList == l.id ? ' active' : ''}`;
      btn.dataset.list = l.id;
      btn.innerHTML = `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${l.color};margin-right:.3rem;vertical-align:middle"></span>${l.name}`;
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
          ${list.name}
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
    const member = FP.getMember(task.member_id);
    const list   = lists.find(l => l.id === task.list_id);
    const isOverdue = task.due_date && !task.done && new Date(task.due_date) < new Date();
    return `
      <div class="card task-card" data-id="${task.id}">
        <button class="task-check ${task.done ? 'done' : ''}" data-id="${task.id}" aria-label="Afvinken"></button>
        <div class="task-body" style="cursor:pointer" data-edit="${task.id}">
          <div class="task-title ${task.done ? 'done' : ''}">${task.title}</div>
          <div class="task-meta">
            ${member ? `<span>${member.avatar} ${member.name}</span>` : ''}
            ${task.due_date ? ` · ${FP.formatDate(task.due_date)}` : ''}
          </div>
        </div>
        ${task.due_date ? `<span class="task-due-badge ${isOverdue ? 'overdue' : ''}">${FP.formatDateShort(task.due_date)}</span>` : ''}
        ${list ? `<span class="task-list-dot" style="background:${list.color}"></span>` : ''}
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
    editTaskId = id;
    Modal.open('tpl-task-form');
    const form   = document.getElementById('task-form');
    const title  = document.getElementById('task-form-title');
    const delBtn = document.getElementById('btn-delete-task');

    FP.populateMemberSelect(form.querySelector('select[name="member_id"]'));

    // Populate list select
    const listSel = form.querySelector('select[name="list_id"]');
    listSel.innerHTML = '<option value="">Geen lijst</option>';
    lists.forEach(l => {
      const opt = document.createElement('option');
      opt.value = l.id; opt.textContent = l.name;
      listSel.appendChild(opt);
    });

    if (id) {
      title.textContent = 'Taak bewerken';
      delBtn.classList.remove('hidden');
      const task = tasks.find(t => t.id === id);
      if (task) {
        form.title.value       = task.title;
        form.description.value = task.description || '';
        listSel.value          = task.list_id || '';
        form.querySelector('select[name="member_id"]').value = task.member_id || '';
        form.due_date.value    = task.due_date || '';
      }
    } else {
      title.textContent = 'Taak toevoegen';
      delBtn.classList.add('hidden');
      if (activeList !== 'all') listSel.value = activeList;
    }

    form.addEventListener('submit', async e => {
      e.preventDefault();
      const data = {
        title:       form.title.value,
        description: form.description.value,
        list_id:     listSel.value ? parseInt(listSel.value) : null,
        member_id:   form.querySelector('select[name="member_id"]').value
                       ? parseInt(form.querySelector('select[name="member_id"]').value) : null,
        due_date:    form.due_date.value || null,
        done:        false,
      };
      try {
        if (editTaskId) {
          const cur = tasks.find(t => t.id === editTaskId);
          await API.put(`/api/tasks/${editTaskId}`, { ...data, done: cur?.done ?? false });
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
      if (!confirm('Taak verwijderen?')) return;
      try {
        await API.delete(`/api/tasks/${editTaskId}`);
        Toast.show('Taak verwijderd', 'warning');
        Modal.close();
        loadTasks();
      } catch { Toast.show('Fout', 'error'); }
    }, { once: true });
  }

  // ── List form ─────────────────────────────────────────────────
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

  // ── Init ──────────────────────────────────────────────────────
  async function init() {
    await FP.loadMembers();
    await loadLists();
    await loadTasks();

    document.getElementById('btn-add-task')?.addEventListener('click', () => openTaskForm());
    document.getElementById('btn-add-list')?.addEventListener('click', openListForm);
    document.getElementById('show-done')?.addEventListener('change', e => {
      showDone = e.target.checked;
      loadTasks();
    });

    await FP.buildMemberChips('tasks-member-chips', m => {
      activeMember = m;
      loadTasks();
    });
  }

  document.addEventListener('DOMContentLoaded', init);
})();
