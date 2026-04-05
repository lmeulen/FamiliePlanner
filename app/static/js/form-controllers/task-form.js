/* ================================================================
   task-form.js – Shared task form controller
   Manages task CRUD for both tasks and dashboard pages
   ================================================================ */
class TaskFormController {
  constructor(options = {}) {
    this.templateId = options.templateId;
    this.formId = options.formId;
    this.simplified = options.simplified ?? false;
    this.onSave = options.onSave || (() => {});
    this.taskCache = options.taskCache || [];

    this.form = null;
    this.editId = null;
    this.seriesId = null;
    this.editScope = 'this';
    this.recurrenceUI = null;
    this.lists = [];
  }

  async open(taskId = null) {
    this.editId = taskId;
    this.seriesId = null;
    this.editScope = 'this';

    Modal.open(this.templateId);
    this.form = document.getElementById(this.formId);

    if (!this.form) {
      console.error(`TaskFormController: Form with id '${this.formId}' not found`);
      return;
    }

    await this.setupForm(taskId);
    this.attachEventListeners();
  }

  async setupForm(taskId) {
    const titleEl = this.form.querySelector('.modal-title');
    const delBtn = this.form.querySelector('[id*="delete-task"]');
    const recurToggle = this.form.querySelector('#recurrence-toggle');
    const recurSection = this.form.querySelector('#recurrence-section');
    const recurFields = this.form.querySelector('#recurrence-fields');
    const recurRow = this.form.querySelector('#recurrence-toggle-row');
    const scopeSel = this.form.querySelector('#scope-selector');

    // Build member picker
    FP.buildMemberPicker(this.getMemberPickerId());

    // Load task lists
    await this.loadLists();

    // Initialize recurrence UI
    this.recurrenceUI = new RecurrenceUIController({
      formId: this.formId,
      idPrefix: 'task-',
      showToggle: !taskId,
    });

    // Recurrence toggle behavior
    recurToggle?.addEventListener('change', () => {
      recurSection?.classList.toggle('hidden', !recurToggle.checked);
      recurFields?.classList.toggle('hidden', !recurToggle.checked);
      if (recurToggle.checked) {
        this.form.querySelector('[name="series_end"]').value = '';
      }
    });

    if (taskId) {
      await this.populateEditForm(taskId);
      titleEl.textContent = 'Taak bewerken';
      delBtn?.classList.remove('hidden');
      recurRow?.classList.add('hidden');
      recurSection?.classList.add('hidden');
      scopeSel?.classList.add('hidden');
    } else {
      this.setupCreateForm();
      titleEl.textContent = 'Taak toevoegen';
      delBtn?.classList.add('hidden');
      recurRow?.classList.remove('hidden');
      recurSection?.classList.add('hidden');
      scopeSel?.classList.add('hidden');
      recurFields?.classList.add('hidden');
    }
  }

  async loadLists() {
    try {
      this.lists = await API.get('/api/tasks/lists');
      const listSel = this.form.querySelector('select[name="list_id"]');
      if (listSel) {
        listSel.innerHTML = '';
        this.lists.forEach(l => {
          const opt = document.createElement('option');
          opt.value = l.id;
          opt.textContent = l.name;
          listSel.appendChild(opt);
        });
      }
    } catch (err) {
      console.error('Failed to load task lists:', err);
      this.lists = [];
    }
  }

  async populateEditForm(taskId) {
    const task = this.taskCache.find(t => t.id === taskId);
    if (!task) {
      console.warn('TaskFormController: Task not found in cache, id=', taskId);
      return;
    }

    console.log('TaskFormController: Editing task', {id: task.id, series_id: task.series_id, is_exception: task.is_exception});

    this.form.title.value = task.title;
    this.form.description.value = task.description || '';
    this.form.due_date.value = task.due_date || '';

    const listSel = this.form.querySelector('select[name="list_id"]');
    if (listSel) {
      listSel.value = task.list_id || (this.lists[0]?.id ?? '');
    }

    FP.buildMemberPicker(this.getMemberPickerId(), task.member_ids || []);

    if (task.series_id) {
      console.log('TaskFormController: Task is part of series, showing scope selector');
      this.seriesId = task.series_id;
      this.setupSeriesEditMode();
    } else {
      console.log('TaskFormController: Task is NOT part of series (series_id is null/undefined)');
    }
  }

  setupSeriesEditMode() {
    const recurRow = this.form.querySelector('#recurrence-toggle-row');
    const recurSection = this.form.querySelector('#recurrence-section');
    const recurFields = this.form.querySelector('#recurrence-fields');
    const scopeSel = this.form.querySelector('#scope-selector');

    console.log('TaskFormController: setupSeriesEditMode', {
      recurRow: !!recurRow,
      recurSection: !!recurSection,
      recurFields: !!recurFields,
      scopeSel: !!scopeSel,
      seriesId: this.seriesId
    });

    recurRow?.classList.add('hidden');
    recurSection?.classList.remove('hidden');  // Show wrapper
    scopeSel?.classList.remove('hidden');       // Show scope selector
    recurFields?.classList.add('hidden');       // Hide fields initially

    if (!scopeSel) {
      console.error('TaskFormController: #scope-selector element not found in form!');
      return;
    }

    // Debug: check if hidden was actually removed
    setTimeout(() => {
      console.log('TaskFormController: After classList changes', {
        scopeHasHidden: scopeSel.classList.contains('hidden'),
        scopeStyle: window.getComputedStyle(scopeSel).display,
        scopeClasses: Array.from(scopeSel.classList)
      });
    }, 100);

    // Scope radio handler
    this.form.querySelectorAll('input[name="edit_scope"]')?.forEach(radio => {
      radio.addEventListener('change', () => {
        this.editScope = radio.value;
        console.log('TaskFormController: Edit scope changed to', this.editScope);
        recurFields?.classList.toggle('hidden', this.editScope !== 'series');

        if (this.editScope === 'series' && this.seriesId) {
          API.get(`/api/tasks/series/${this.seriesId}`).then(s => {
            this.recurrenceUI.populateFromSeries(s);
          }).catch(() => {});
        }
      });
    });
  }

  setupCreateForm() {
    // Default due date to today
    this.form.due_date.value = FP.todayStr();

    // Default to first list if available
    const listSel = this.form.querySelector('select[name="list_id"]');
    if (listSel && this.lists.length) {
      listSel.value = this.lists[0].id;
    }
  }

  attachEventListeners() {
    this.form.addEventListener('submit', (e) => this.handleSubmit(e), { once: true });

    const delBtn = this.form.querySelector('[id*="delete-task"]');
    delBtn?.addEventListener('click', () => this.handleDelete(), { once: true });
  }

  async handleSubmit(e) {
    e.preventDefault();

    const memberIds = FP.getSelectedMemberIds(this.getMemberPickerId());

    // Trim inputs
    this.form.title.value = this.form.title.value.trim();
    this.form.description.value = this.form.description.value.trim();

    if (!this.form.title.value) {
      this.form.title.focus();
      return;
    }

    const listSel = this.form.querySelector('select[name="list_id"]');
    const listId = listSel?.value ? parseInt(listSel.value) : (this.lists[0]?.id || null);

    const saveButton = this.form.querySelector('button[type="submit"]');

    await API.withButtonLoading(saveButton, async () => {
      // Check if creating new recurring series
      const recurToggle = this.form.querySelector('#recurrence-toggle');
      if (!this.editId && recurToggle?.checked) {
        await this.handleCreateSeries(listId, memberIds);
        return;
      }

      // Check if editing series
      if (this.seriesId && this.editScope === 'series') {
        await this.handleUpdateSeries(listId, memberIds);
        return;
      }

      // Single task create/update
      await this.handleSingleTask(listId, memberIds);
    });
  }

  async handleCreateSeries(listId, memberIds) {
    // Recurring series creation requires online connection
    if (!navigator.onLine) {
      Toast.show('Herhalende taken aanmaken vereist online verbinding', 'error');
      return;
    }

    const dueDate = this.form.due_date.value;
    const validation = this.recurrenceUI.validate(dueDate);
    if (!validation.valid) {
      if (validation.errorElementId) {
        this.recurrenceUI.showValidationError(validation.errorElementId);
      }
      Toast.show(validation.error, 'error');
      return;
    }
    this.recurrenceUI.hideAllValidationErrors();

    const recurrencePayload = this.recurrenceUI.getRecurrencePayload();
    const payload = {
      title: this.form.title.value,
      description: this.form.description.value,
      list_id: listId,
      member_ids: memberIds,
      series_start: dueDate,
      ...recurrencePayload,
    };

    try {
      await API.post('/api/tasks/series', payload);
      Toast.show('Reeks aangemaakt!');
      Modal.close();
      this.onSave();
    } catch (err) {
      Toast.show(err.message || 'Fout bij opslaan', 'error');
    }
  }

  async handleUpdateSeries(listId, memberIds) {
    // Recurring series update requires online connection
    if (!navigator.onLine) {
      Toast.show('Herhalende taken bijwerken vereist online verbinding', 'error');
      return;
    }

    const recurrencePayload = this.recurrenceUI.getRecurrencePayload();
    const payload = {
      title: this.form.title.value,
      description: this.form.description.value,
      list_id: listId,
      member_ids: memberIds,
      ...recurrencePayload,
    };

    try {
      await API.put(`/api/tasks/series/${this.seriesId}`, payload);
      Toast.show('Reeks bijgewerkt!');
      Modal.close();
      this.onSave();
    } catch (err) {
      Toast.show(err.message || 'Fout bij opslaan', 'error');
    }
  }

  async handleSingleTask(listId, memberIds) {
    const data = {
      title: this.form.title.value,
      description: this.form.description.value,
      list_id: listId,
      member_ids: memberIds,
      due_date: this.form.due_date.value || null,
      done: false,
    };

    const isOnline = navigator.onLine;
    const db = window.TasksDB;

    try {
      if (this.editId) {
        const current = this.taskCache.find(t => t.id === this.editId);
        const payload = { ...data, done: current?.done ?? false };

        if (isOnline) {
          await API.put(`/api/tasks/${this.editId}`, payload);
        } else {
          // Update locally and queue sync
          await db.updateTaskOffline(this.editId, payload);
          await db.queueSync({
            type: 'update_task',
            taskId: this.editId,
            payload: payload
          });
        }
        Toast.show('Taak bijgewerkt!');
      } else {
        if (isOnline) {
          await API.post('/api/tasks/', data);
        } else {
          // Add locally and queue sync
          await db.addTaskOffline(data);
          await db.queueSync({
            type: 'add_task',
            payload: data
          });
        }
        Toast.show('Taak toegevoegd!');
      }
      Modal.close();
      this.onSave();
    } catch (err) {
      Toast.show(err.message || 'Fout bij opslaan', 'error');
    }
  }

  async handleDelete() {
    const isOnline = navigator.onLine;
    const db = window.TasksDB;

    if (this.seriesId) {
      const scope = this.form.querySelector('[name="edit_scope"]:checked')?.value || 'this';
      if (scope === 'series') {
        if (!isOnline) {
          Toast.show('Reeks verwijderen vereist online verbinding', 'error');
          return;
        }
        if (!confirm('Hele reeks verwijderen?')) return;
        try {
          await API.delete(`/api/tasks/series/${this.seriesId}`);
          Toast.show('Reeks verwijderd', 'warning');
          Modal.close();
          this.onSave();
        } catch {
          Toast.show('Fout bij verwijderen', 'error');
        }
        return;
      }
    }

    if (!confirm('Taak verwijderen?')) return;
    try {
      if (isOnline) {
        await API.delete(`/api/tasks/${this.editId}`);
      } else {
        // Delete locally and queue sync
        await db.deleteTaskOffline(this.editId);
        await db.queueSync({
          type: 'delete_task',
          taskId: this.editId
        });
      }
      Toast.show('Taak verwijderd', 'warning');
      Modal.close();
      this.onSave();
    } catch {
      Toast.show('Fout bij verwijderen', 'error');
    }
  }

  // Utility methods
  getMemberPickerId() {
    return 'task-member-picker';
  }
}

window.TaskFormController = TaskFormController;
