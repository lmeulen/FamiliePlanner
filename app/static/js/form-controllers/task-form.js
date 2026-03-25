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
      scopeSel?.classList.add('hidden');
    } else {
      this.setupCreateForm();
      titleEl.textContent = 'Taak toevoegen';
      delBtn?.classList.add('hidden');
      recurRow?.classList.remove('hidden');
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
    if (!task) return;

    this.form.title.value = task.title;
    this.form.description.value = task.description || '';
    this.form.due_date.value = task.due_date || '';

    const listSel = this.form.querySelector('select[name="list_id"]');
    if (listSel) {
      listSel.value = task.list_id || (this.lists[0]?.id ?? '');
    }

    FP.buildMemberPicker(this.getMemberPickerId(), task.member_ids || []);

    if (task.series_id) {
      this.seriesId = task.series_id;
      this.setupSeriesEditMode();
    }
  }

  setupSeriesEditMode() {
    const recurRow = this.form.querySelector('#recurrence-toggle-row');
    const recurFields = this.form.querySelector('#recurrence-fields');
    const scopeSel = this.form.querySelector('#scope-selector');

    recurRow?.classList.add('hidden');
    recurFields?.classList.add('hidden');
    scopeSel?.classList.remove('hidden');

    // Scope radio handler
    this.form.querySelectorAll('input[name="edit_scope"]')?.forEach(radio => {
      radio.addEventListener('change', () => {
        this.editScope = radio.value;
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

    try {
      if (this.editId) {
        const current = this.taskCache.find(t => t.id === this.editId);
        await API.put(`/api/tasks/${this.editId}`, { ...data, done: current?.done ?? false });
        Toast.show('Taak bijgewerkt!');
      } else {
        await API.post('/api/tasks/', data);
        Toast.show('Taak toegevoegd!');
      }
      Modal.close();
      this.onSave();
    } catch (err) {
      Toast.show(err.message || 'Fout bij opslaan', 'error');
    }
  }

  async handleDelete() {
    if (this.seriesId) {
      const scope = this.form.querySelector('[name="edit_scope"]:checked')?.value || 'this';
      if (scope === 'series') {
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
      await API.delete(`/api/tasks/${this.editId}`);
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
