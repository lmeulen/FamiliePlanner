/* ================================================================
   event-form.js – Shared event form controller
   Manages event CRUD for both agenda and dashboard pages
   ================================================================ */
class EventFormController {
  constructor(options = {}) {
    this.templateId = options.templateId;
    this.formId = options.formId;
    this.simplified = options.simplified ?? false;
    this.onSave = options.onSave || (() => {});
    this.eventCache = options.eventCache || [];

    this.form = null;
    this.editId = null;
    this.seriesId = null;
    this.currentSeries = null;
    this.editScope = 'this';
    this.recurrenceUI = null;
  }

  async open(eventId = null, prefillDate = null, prefillDatetime = null) {
    this.editId = eventId;
    this.seriesId = null;
    this.currentSeries = null;
    this.editScope = 'this';

    Modal.open(this.templateId);
    this.form = document.getElementById(this.formId);

    if (!this.form) {
      console.error(`EventFormController: Form with id '${this.formId}' not found`);
      return;
    }

    await this.setupForm(eventId, prefillDate, prefillDatetime);
    this.attachEventListeners();
  }

  async setupForm(eventId, prefillDate, prefillDatetime) {
    const titleEl = this.form.querySelector('.modal-title');
    const delBtn = this.form.querySelector('[id*="delete-event"]');
    const exportBtn = this.form.querySelector('[id*="export-event"]');
    const toggleRow = this.form.querySelector('#recurrence-toggle-row');
    const recurSection = this.form.querySelector('#recurrence-section');
    const scopeSelector = this.form.querySelector('#series-scope-selector');

    // Calculate anchor date
    const anchorDateObj = prefillDate ? new Date(`${prefillDate}T00:00`) : new Date();
    anchorDateObj.setHours(0, 0, 0, 0);
    const anchorDateStr = this.toDateOnlyStr(anchorDateObj);
    this.form.dataset.anchorDate = anchorDateStr;

    // Build member picker
    FP.buildMemberPicker(this.getMemberPickerId());

    // Initialize recurrence UI
    this.recurrenceUI = new RecurrenceUIController({
      formId: this.formId,
      idPrefix: '',
      showToggle: !eventId,
    });

    if (eventId) {
      await this.populateEditForm(eventId, anchorDateStr);
      titleEl.textContent = 'Afspraak bewerken';
      delBtn?.classList.remove('hidden');
      if (!this.simplified) exportBtn?.classList.remove('hidden');
    } else {
      this.setupCreateForm(prefillDate, prefillDatetime, anchorDateStr);
      titleEl.textContent = 'Afspraak toevoegen';
      delBtn?.classList.add('hidden');
      exportBtn?.classList.add('hidden');
      toggleRow?.classList.remove('hidden');
      recurSection?.classList.add('hidden');
      scopeSelector?.classList.add('hidden');
    }

    this.setupAllDayToggle(anchorDateStr);
  }

  async populateEditForm(eventId, anchorDateStr) {
    const event = this.eventCache.find(e => e.id === eventId);
    if (!event) return;

    this.form.title.value = event.title;
    this.form.description.value = event.description || '';
    this.form.location.value = event.location || '';
    this.form.start_time.value = FP.toLocalDatetimeInput(new Date(event.start_time));
    this.form.end_time.value = FP.toLocalDatetimeInput(new Date(event.end_time));
    this.form.all_day.checked = event.all_day;
    FP.buildMemberPicker(this.getMemberPickerId(), event.member_ids || []);
    this.updateAllDayInputMode(event.all_day, anchorDateStr);

    if (event.series_id && !this.simplified) {
      this.seriesId = event.series_id;
      this.setupSeriesEditMode(event, anchorDateStr);
    } else {
      const toggleRow = this.form.querySelector('#recurrence-toggle-row');
      const recurSection = this.form.querySelector('#recurrence-section');
      toggleRow?.classList.add('hidden');
      recurSection?.classList.add('hidden');
    }
  }

  setupSeriesEditMode(event, anchorDateStr) {
    const toggleRow = this.form.querySelector('#recurrence-toggle-row');
    const recurSection = this.form.querySelector('#recurrence-section');
    const scopeSelector = this.form.querySelector('#series-scope-selector');
    const recurFields = this.form.querySelector('#recurrence-fields');

    toggleRow?.classList.add('hidden');
    recurSection?.classList.remove('hidden');
    scopeSelector?.classList.remove('hidden');
    recurFields?.classList.add('hidden');

    // Scope radio handler
    this.form.querySelectorAll('input[name="edit_scope"]')?.forEach(radio => {
      radio.addEventListener('change', () => {
        this.editScope = radio.value;
        recurFields?.classList.toggle('hidden', this.editScope !== 'series');

        if (this.editScope === 'series' && this.currentSeries) {
          this.form.start_time.value = `${this.currentSeries.series_start}T${this.currentSeries.start_time_of_day.slice(0,5)}`;
          this.form.end_time.value = `${this.currentSeries.series_start}T${this.currentSeries.end_time_of_day.slice(0,5)}`;
        } else {
          this.form.start_time.value = FP.toLocalDatetimeInput(new Date(event.start_time));
          this.form.end_time.value = FP.toLocalDatetimeInput(new Date(event.end_time));
        }
        this.updateAllDayInputMode(this.form.all_day.checked, anchorDateStr);
      });
    });

    // Load series data
    if (this.seriesId) {
      API.get(`/api/agenda/series/${this.seriesId}`).then(s => {
        this.currentSeries = s;
        this.recurrenceUI.populateFromSeries(s);
      }).catch(() => {});
    }
  }

  setupCreateForm(prefillDate, prefillDatetime, anchorDateStr) {
    if (prefillDatetime) {
      const start = new Date(prefillDatetime);
      this.form.start_time.value = FP.toLocalDatetimeInput(start);
      const end = new Date(start);
      end.setHours(end.getHours() + 1);
      this.form.end_time.value = FP.toLocalDatetimeInput(end);
    } else if (prefillDate) {
      const start = new Date(prefillDate + 'T09:00');
      this.form.start_time.value = FP.toLocalDatetimeInput(start);
      const end = new Date(start);
      end.setHours(end.getHours() + 1);
      this.form.end_time.value = FP.toLocalDatetimeInput(end);
    } else {
      const now = new Date();
      const start = new Date(now);
      start.setMinutes(Math.ceil(now.getMinutes() / 15) * 15, 0, 0);
      const end = new Date(start);
      end.setHours(end.getHours() + 1);
      this.form.start_time.value = FP.toLocalDatetimeInput(start);
      this.form.end_time.value = FP.toLocalDatetimeInput(end);
    }

    // Default series_end (4 weeks ahead)
    const defaultEnd = new Date();
    defaultEnd.setDate(defaultEnd.getDate() + 28);
    const endInput = this.form.querySelector('[name="series_end"]');
    if (endInput) {
      endInput.value = `${defaultEnd.getFullYear()}-${this.pad(defaultEnd.getMonth()+1)}-${this.pad(defaultEnd.getDate())}`;
    }

    // Recurrence toggle listener
    const recurToggle = this.form.querySelector('#recurrence-toggle');
    const recurSection = this.form.querySelector('#recurrence-section');
    recurToggle?.addEventListener('change', () => {
      recurSection?.classList.toggle('hidden', !recurToggle.checked);
    });

    this.updateAllDayInputMode(false, anchorDateStr);
  }

  setupAllDayToggle(anchorDateStr) {
    const allDayInput = this.form.querySelector('[name="all_day"]');
    allDayInput?.addEventListener('change', () => {
      this.updateAllDayInputMode(allDayInput.checked, anchorDateStr);
    });
  }

  updateAllDayInputMode(isAllDay, anchorDateStr) {
    const startInput = this.form.start_time;
    const endInput = this.form.end_time;
    if (!startInput || !endInput) return;

    if (isAllDay) {
      const startDate = startInput.value?.split('T')[0] || anchorDateStr;
      const endDate = endInput.value?.split('T')[0] || startDate;
      startInput.type = 'date';
      endInput.type = 'date';
      startInput.value = startDate;
      endInput.value = endDate;
    } else {
      const startDate = startInput.value?.split('T')[0] || anchorDateStr;
      const endDate = endInput.value?.split('T')[0] || startDate;
      startInput.type = 'datetime-local';
      endInput.type = 'datetime-local';
      if (!startInput.value.includes('T')) startInput.value = `${startDate}T09:00`;
      if (!endInput.value.includes('T')) endInput.value = `${endDate}T10:00`;
    }
  }

  attachEventListeners() {
    this.form.addEventListener('submit', (e) => this.handleSubmit(e), { once: true });

    const delBtn = this.form.querySelector('[id*="delete-event"]');
    delBtn?.addEventListener('click', () => this.handleDelete(), { once: true });

    if (!this.simplified) {
      const exportBtn = this.form.querySelector('[id*="export-event"]');
      exportBtn?.addEventListener('click', () => this.handleExport(), { once: true });
    }
  }

  async handleSubmit(e) {
    e.preventDefault();

    const isAllDay = this.form.all_day.checked;
    const forcedDate = this.form.dataset.anchorDate || this.toDateOnlyStr(new Date());

    let startDt, endDt;
    if (isAllDay) {
      const startDateVal = this.form.start_time.value || forcedDate;
      const endDateVal = this.form.end_time.value || startDateVal;
      startDt = new Date(`${startDateVal}T00:00:00`);
      endDt = new Date(`${endDateVal}T23:59:59`);
    } else {
      startDt = new Date(this.form.start_time.value);
      endDt = new Date(this.form.end_time.value);
    }

    // Validate end > start
    const endTimeErr = this.form.querySelector('#end-time-error');
    if ((!isAllDay && endDt <= startDt) || (isAllDay && endDt < startDt)) {
      endTimeErr?.classList.remove('hidden');
      this.form.end_time.focus();
      return;
    }
    endTimeErr?.classList.add('hidden');

    // Trim inputs
    this.form.title.value = this.form.title.value.trim();
    this.form.description.value = this.form.description.value.trim();
    this.form.location.value = this.form.location.value.trim();

    // Validate series end date if recurrence visible
    const startDate = this.form.start_time.value.split('T')[0];
    const recurSectionEl = this.form.querySelector('#recurrence-section');
    const recurFieldsEl = this.form.querySelector('#recurrence-fields');
    const seriesEndVisible = !recurSectionEl?.classList.contains('hidden') &&
                            !recurFieldsEl?.classList.contains('hidden');

    if (seriesEndVisible) {
      const validation = this.recurrenceUI.validate(startDate);
      if (!validation.valid) {
        if (validation.errorElementId) {
          this.recurrenceUI.showValidationError(validation.errorElementId);
        }
        Toast.show(validation.error, 'error');
        return;
      }
      this.recurrenceUI.hideAllValidationErrors();
    }

    const eventData = {
      title: this.form.title.value,
      description: this.form.description.value,
      location: this.form.location.value,
      start_time: this.toApiDateTimeStr(startDt),
      end_time: this.toApiDateTimeStr(endDt),
      all_day: isAllDay,
      member_ids: FP.getSelectedMemberIds(this.getMemberPickerId()),
    };

    const saveButton = this.form.querySelector('button[type="submit"]');

    await API.withButtonLoading(saveButton, async () => {
      try {
        if (!this.editId) {
          await this.handleCreate(eventData, startDt, endDt);
        } else {
          await this.handleUpdate(eventData, startDt, endDt);
        }

        Modal.close();
        this.onSave();
      } catch (err) {
        Toast.show(err.message || 'Fout bij opslaan', 'error');
      }
    });
  }

  async handleCreate(eventData, startDt, endDt) {
    const recurToggle = this.form.querySelector('#recurrence-toggle');
    const isMultiDayAllDay = this.form.all_day.checked &&
      Math.floor((endDt - startDt) / (1000 * 60 * 60 * 24)) > 0;
    const isOnline = navigator.onLine;
    const db = window.AgendaDB;

    if ((recurToggle?.checked || isMultiDayAllDay) && !this.simplified) {
      // Series creation requires online connection
      if (!isOnline) {
        Toast.show('Herhalende afspraken aanmaken vereist online verbinding', 'error');
        return;
      }

      // Create series
      const recurrencePayload = this.recurrenceUI.getRecurrencePayload();
      const seriesPayload = {
        ...eventData,
        series_start: this.form.start_time.value.split('T')[0],
        start_time_of_day: this.toTimeStr(startDt),
        end_time_of_day: this.toTimeStr(endDt),
        ...recurrencePayload,
      };

      // Handle multi-day all-day auto-conversion
      if (isMultiDayAllDay && !recurToggle?.checked) {
        seriesPayload.recurrence_type = 'daily';
        seriesPayload.interval = 1;

        const endTime = this.form.end_time.value.split('T')[1];
        let seriesEndDate = this.form.end_time.value.split('T')[0];
        if (endTime === '00:00' || endTime.startsWith('00:00:')) {
          const endDateObj = new Date(seriesEndDate);
          endDateObj.setDate(endDateObj.getDate() - 1);
          seriesEndDate = FP.dateToStr(endDateObj);
        }
        seriesPayload.series_end = seriesEndDate;
        delete seriesPayload.count;
      }

      await API.post('/api/agenda/series', seriesPayload);
      Toast.show(isMultiDayAllDay && !recurToggle?.checked ? 'Meerdaagse afspraak aangemaakt!' : 'Herhalende reeks aangemaakt!');
    } else {
      // Create single event
      if (isOnline) {
        await API.post('/api/agenda/', eventData);
      } else {
        // Add locally and queue sync
        await db.addEventOffline(eventData);
        await db.queueSync({
          type: 'add_event',
          payload: eventData
        });
      }
      Toast.show('Afspraak toegevoegd!');
    }
  }

  async handleUpdate(eventData, startDt, endDt) {
    const isOnline = navigator.onLine;
    const db = window.AgendaDB;

    if (this.seriesId && this.editScope === 'series' && !this.simplified) {
      // Series update requires online connection
      if (!isOnline) {
        Toast.show('Herhalende afspraken bijwerken vereist online verbinding', 'error');
        return;
      }

      // Update series
      const recurrencePayload = this.recurrenceUI.getRecurrencePayload();
      const seriesPayload = {
        ...eventData,
        start_time_of_day: this.toTimeStr(startDt),
        end_time_of_day: this.toTimeStr(endDt),
        ...recurrencePayload,
      };

      await API.put(`/api/agenda/series/${this.seriesId}`, seriesPayload);
      Toast.show('Reeks bijgewerkt!');
    } else {
      // Update single event
      const isMultiDayAllDay = this.form.all_day.checked &&
        Math.floor((endDt - startDt) / (1000 * 60 * 60 * 24)) > 0;

      if (isMultiDayAllDay) {
        Toast.show('Let op: meerdaagse afspraken worden alleen op de eerste dag getoond. Maak een nieuwe herhalende afspraak aan voor alle dagen.', 'warning');
      }

      if (isOnline) {
        await API.put(`/api/agenda/${this.editId}`, eventData);
      } else {
        // Update locally and queue sync
        await db.updateEventOffline(this.editId, eventData);
        await db.queueSync({
          type: 'update_event',
          eventId: this.editId,
          payload: eventData
        });
      }
      Toast.show('Afspraak bijgewerkt!');
    }
  }

  async handleDelete() {
    const isSeries = this.seriesId && this.editScope === 'series';
    const isOnline = navigator.onLine;
    const db = window.AgendaDB;

    if (!confirm(isSeries ? 'Hele reeks verwijderen?' : 'Afspraak verwijderen?')) return;

    try {
      if (isSeries) {
        // Series deletion requires online connection
        if (!isOnline) {
          Toast.show('Herhalende reeks verwijderen vereist online verbinding', 'error');
          return;
        }
        await API.delete(`/api/agenda/series/${this.seriesId}`);
        Toast.show('Reeks verwijderd', 'warning');
      } else {
        if (isOnline) {
          await API.delete(`/api/agenda/${this.editId}`);
        } else {
          // Delete locally and queue sync
          await db.deleteEventOffline(this.editId);
          await db.queueSync({
            type: 'delete_event',
            eventId: this.editId
          });
        }
        Toast.show('Afspraak verwijderd', 'warning');
      }
      Modal.close();
      this.onSave();
    } catch {
      Toast.show('Fout bij verwijderen', 'error');
    }
  }

  handleExport() {
    if (!this.editId) return;
    window.location.href = `/api/agenda/${this.editId}/export`;
    Toast.show('Afspraak geëxporteerd!');
  }

  // Utility methods
  getMemberPickerId() {
    return 'event-member-picker';
  }

  toDateOnlyStr(dt) {
    return `${dt.getFullYear()}-${this.pad(dt.getMonth()+1)}-${this.pad(dt.getDate())}`;
  }

  pad(n) {
    return String(n).padStart(2, '0');
  }

  toTimeStr(dt) {
    return `${this.pad(dt.getHours())}:${this.pad(dt.getMinutes())}:00`;
  }

  toApiDateTimeStr(dt) {
    const dateStr = `${dt.getFullYear()}-${this.pad(dt.getMonth()+1)}-${this.pad(dt.getDate())}`;
    return `${dateStr}T${this.pad(dt.getHours())}:${this.pad(dt.getMinutes())}:${this.pad(dt.getSeconds())}`;
  }
}

window.EventFormController = EventFormController;
