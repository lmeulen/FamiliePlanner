/* ================================================================
   recurrence-ui.js – Shared recurrence UI controller
   Manages progressive disclosure and validation for recurring series
   ================================================================ */
class RecurrenceUIController {
  /**
   * @param {Object} options
   * @param {string} options.formId - ID van het form element
   * @param {string} options.idPrefix - Prefix voor element IDs ('', 'task-', etc.)
   * @param {boolean} options.showToggle - Toon recurrence toggle voor nieuwe items
   */
  constructor(options = {}) {
    this.form = document.getElementById(options.formId);
    this.prefix = options.idPrefix || '';
    this.showToggle = options.showToggle ?? true;

    if (!this.form) {
      console.warn(`RecurrenceUIController: Form with id '${options.formId}' not found`);
      return;
    }

    this.elements = {
      typeSelect: document.getElementById(`${this.prefix}recurrence-type-select`),
      intervalSection: document.getElementById(`${this.prefix}interval-section`),
      intervalUnit: document.getElementById(`${this.prefix}interval-unit`),
      monthlyPatternSection: document.getElementById(`${this.prefix}monthly-pattern-section`),
      endDateSection: document.getElementById(`${this.prefix}end-date-section`),
      endCountSection: document.getElementById(`${this.prefix}end-count-section`),
      endConditionRadios: this.form.querySelectorAll('input[name="end_condition"]') || [],
    };

    this.attachListeners();
    this.updateUI();
  }

  attachListeners() {
    this.elements.typeSelect?.addEventListener('change', () => this.updateRecurrenceTypeUI());
    this.elements.endConditionRadios?.forEach(radio => {
      radio.addEventListener('change', () => this.updateEndConditionUI());
    });
  }

  updateRecurrenceTypeUI() {
    const type = this.elements.typeSelect?.value;
    if (!type) return;

    const showInterval = ['daily', 'weekly', 'monthly', 'yearly'].includes(type);
    this.elements.intervalSection?.classList.toggle('hidden', !showInterval);

    // Update interval unit text
    const unitMap = {
      daily: 'dagen',
      yearly: 'jaren',
      monthly: 'maanden',
      weekly: 'weken'
    };
    if (this.elements.intervalUnit) {
      this.elements.intervalUnit.textContent = unitMap[type] || 'weken';
    }

    this.elements.monthlyPatternSection?.classList.toggle('hidden', type !== 'monthly');
  }

  updateEndConditionUI() {
    const checked = this.form?.querySelector('input[name="end_condition"]:checked');
    const condition = checked?.value;
    this.elements.endDateSection?.classList.toggle('hidden', condition !== 'date');
    this.elements.endCountSection?.classList.toggle('hidden', condition !== 'count');
  }

  updateUI() {
    this.updateRecurrenceTypeUI();
    this.updateEndConditionUI();
  }

  /**
   * Populate form fields from series data
   */
  populateFromSeries(seriesData) {
    if (!this.form || !seriesData) return;

    const typeSelect = this.form.querySelector('[name="recurrence_type"]');
    if (typeSelect) typeSelect.value = seriesData.recurrence_type;

    const intervalInput = this.form.querySelector('input[name="interval"]');
    if (intervalInput) intervalInput.value = seriesData.interval || 1;

    if (seriesData.monthly_pattern) {
      const monthlySelect = this.form.querySelector('[name="monthly_pattern"]');
      if (monthlySelect) monthlySelect.value = seriesData.monthly_pattern;
    }

    if (seriesData.count) {
      const countRadio = this.form.querySelector('input[name="end_condition"][value="count"]');
      if (countRadio) countRadio.checked = true;
      const countInput = this.form.querySelector('[name="count"]');
      if (countInput) countInput.value = seriesData.count;
    } else {
      const dateRadio = this.form.querySelector('input[name="end_condition"][value="date"]');
      if (dateRadio) dateRadio.checked = true;
      const endInput = this.form.querySelector('[name="series_end"]');
      if (endInput) endInput.value = seriesData.series_end;
    }

    this.updateUI();
  }

  /**
   * Extract recurrence payload from form
   */
  getRecurrencePayload() {
    if (!this.form) return null;

    const endCondition = this.form.querySelector('input[name="end_condition"]:checked')?.value;
    const payload = {
      recurrence_type: this.form.querySelector('[name="recurrence_type"]')?.value,
      interval: parseInt(this.form.querySelector('input[name="interval"]')?.value || '1'),
    };

    // Monthly pattern
    const monthlyPattern = this.form.querySelector('[name="monthly_pattern"]');
    if (monthlyPattern && !monthlyPattern.closest('.hidden')) {
      payload.monthly_pattern = monthlyPattern.value;
    }

    // End condition
    if (endCondition === 'date') {
      payload.series_end = this.form.querySelector('[name="series_end"]')?.value;
    } else {
      payload.count = parseInt(this.form.querySelector('[name="count"]')?.value || '0');
    }

    return payload;
  }

  /**
   * Validate recurrence fields
   * @returns {Object} { valid: boolean, error?: string, errorElementId?: string }
   */
  validate(startDateStr) {
    const endCondition = this.form?.querySelector('input[name="end_condition"]:checked')?.value;

    if (endCondition === 'date') {
      const seriesEndInput = this.form?.querySelector('[name="series_end"]');
      const seriesEnd = seriesEndInput?.value;
      if (!seriesEnd || seriesEnd <= startDateStr) {
        return {
          valid: false,
          error: 'Einddatum moet na startdatum liggen',
          errorElementId: `${this.prefix}series-end-error`
        };
      }
    } else {
      const count = parseInt(this.form?.querySelector('[name="count"]')?.value || '0');
      if (count < 1) {
        return {
          valid: false,
          error: 'Vul een aantal herhalingen in'
        };
      }
    }

    return { valid: true };
  }

  /**
   * Show validation error for a specific field
   */
  showValidationError(errorElementId) {
    if (!errorElementId) return;
    const errorEl = document.getElementById(errorElementId);
    errorEl?.classList.remove('hidden');
  }

  /**
   * Hide validation error for a specific field
   */
  hideValidationError(errorElementId) {
    if (!errorElementId) return;
    const errorEl = document.getElementById(errorElementId);
    errorEl?.classList.add('hidden');
  }

  /**
   * Hide all validation errors
   */
  hideAllValidationErrors() {
    this.hideValidationError(`${this.prefix}series-end-error`);
    // Add more error elements if needed
  }
}

// Export for module usage
window.RecurrenceUIController = RecurrenceUIController;
