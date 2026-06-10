/* ================================================================
   date-time-picker.js – Unified Flatpickr + ClockPicker wrapper
   API: window.DateTimePicker.initDate(el), initDateTime(el),
        setValue(el, val), destroy(el)
   ================================================================ */
(function () {
  'use strict';

  function pad(n) {
    return String(n).padStart(2, '0');
  }

  function formatDateForDisplay(dateStr) {
    // dateStr = "YYYY-MM-DD"
    if (!dateStr) return '';
    const parts = dateStr.split('-');
    if (parts.length !== 3) return dateStr;
    return `${parts[2]}-${parts[1]}-${parts[0]}`; // DD-MM-YYYY
  }

  function formatTimeForDisplay(hours, minutes) {
    return `${pad(hours)}:${pad(minutes)}`;
  }

  // ── initDate ────────────────────────────────────────────────────
  function initDate(inputEl) {
    if (!inputEl) return;
    if (inputEl._flatpickr_instance) return; // already initialized

    // Ensure correct type
    inputEl.type = 'text';

    const fp = flatpickr(inputEl, {
      locale: 'nl',
      dateFormat: 'Y-m-d',
      disableMobile: true,
      allowInput: true,
      altInput: true,
      altFormat: 'd-m-Y',
    });

    inputEl._flatpickr_instance = fp;
  }

  // ── initDateTime ────────────────────────────────────────────────
  function initDateTime(inputEl) {
    if (!inputEl) return;
    if (inputEl._dtp) return; // already initialized

    // Parse existing value
    let currentDate = '';
    let currentHours = 9;
    let currentMinutes = 0;

    const existingVal = inputEl.value;
    if (existingVal && existingVal.includes('T')) {
      const [datePart, timePart] = existingVal.split('T');
      currentDate = datePart;
      if (timePart) {
        const [h, m] = timePart.split(':');
        currentHours = parseInt(h) || 0;
        currentMinutes = parseInt(m) || 0;
      }
    } else if (existingVal && existingVal.match(/^\d{4}-\d{2}-\d{2}$/)) {
      currentDate = existingVal;
    }

    // Hide original input (keep in DOM for form value)
    inputEl.style.display = 'none';

    // Build wrapper
    const wrapper = document.createElement('div');
    wrapper.className = 'dtp-wrapper';

    const dateBtn = document.createElement('button');
    dateBtn.type = 'button';
    dateBtn.className = 'dtp-date-btn';
    dateBtn.textContent = currentDate ? formatDateForDisplay(currentDate) : 'Datum';

    const sep = document.createElement('span');
    sep.className = 'dtp-separator';
    sep.textContent = 'om';

    const timeBtn = document.createElement('button');
    timeBtn.type = 'button';
    timeBtn.className = 'dtp-time-btn';
    timeBtn.textContent = currentDate ? formatTimeForDisplay(currentHours, currentMinutes) : 'Tijd';

    wrapper.appendChild(dateBtn);
    wrapper.appendChild(sep);
    wrapper.appendChild(timeBtn);

    // Insert wrapper after the hidden input
    inputEl.parentNode.insertBefore(wrapper, inputEl.nextSibling);

    // Flatpickr on a hidden input won't work well; use a proxy text input
    const proxyInput = document.createElement('input');
    proxyInput.type = 'text';
    proxyInput.style.position = 'absolute';
    proxyInput.style.opacity = '0';
    proxyInput.style.pointerEvents = 'none';
    proxyInput.style.width = '1px';
    proxyInput.style.height = '1px';
    wrapper.appendChild(proxyInput);

    const fpInstance = flatpickr(proxyInput, {
      locale: 'nl',
      dateFormat: 'Y-m-d',
      disableMobile: true,
      defaultDate: currentDate || null,
      onClose(selectedDates, dateStr) {
        if (!dateStr) return;
        dtp.currentDate = dateStr;
        dateBtn.textContent = formatDateForDisplay(dateStr);
        updateHiddenValue();
        // Auto-open clock picker
        ClockPicker.open(dateBtn, {
          hours: dtp.currentHours,
          minutes: dtp.currentMinutes,
          onConfirm({ hours, minutes }) {
            dtp.currentHours = hours;
            dtp.currentMinutes = minutes;
            timeBtn.textContent = formatTimeForDisplay(hours, minutes);
            updateHiddenValue();
          },
          onCancel() {},
        });
      },
    });

    // Click handlers
    dateBtn.addEventListener('click', () => {
      fpInstance.open();
    });

    timeBtn.addEventListener('click', () => {
      ClockPicker.open(timeBtn, {
        hours: dtp.currentHours,
        minutes: dtp.currentMinutes,
        onConfirm({ hours, minutes }) {
          dtp.currentHours = hours;
          dtp.currentMinutes = minutes;
          timeBtn.textContent = formatTimeForDisplay(hours, minutes);
          updateHiddenValue();
        },
        onCancel() {},
      });
    });

    function updateHiddenValue() {
      if (dtp.currentDate) {
        inputEl.value = `${dtp.currentDate}T${pad(dtp.currentHours)}:${pad(dtp.currentMinutes)}`;
        // Fire change event so listeners know
        inputEl.dispatchEvent(new Event('change', { bubbles: true }));
      }
    }

    const dtp = {
      wrapper,
      fpInstance,
      currentDate,
      currentHours,
      currentMinutes,
      _dateBtn: dateBtn,
      _timeBtn: timeBtn,
    };

    inputEl._dtp = dtp;

    // Sync initial value
    if (currentDate) {
      updateHiddenValue();
    }
  }

  // ── setValue ────────────────────────────────────────────────────
  function setValue(inputEl, value) {
    if (!inputEl || !value) return;

    if (value.includes('T')) {
      // datetime
      const [datePart, timePart] = value.split('T');
      const [h, m] = (timePart || '09:00').split(':');
      const hours = parseInt(h) || 0;
      const minutes = parseInt(m) || 0;

      if (inputEl._dtp) {
        const dtp = inputEl._dtp;
        dtp.currentDate = datePart;
        dtp.currentHours = hours;
        dtp.currentMinutes = minutes;
        dtp._dateBtn.textContent = formatDateForDisplay(datePart);
        dtp._timeBtn.textContent = formatTimeForDisplay(hours, minutes);
        dtp.fpInstance.setDate(datePart, false);
        inputEl.value = `${datePart}T${pad(hours)}:${pad(minutes)}`;
      } else {
        inputEl.value = value;
      }
    } else {
      // date only
      if (inputEl._flatpickr_instance) {
        inputEl._flatpickr_instance.setDate(value, false);
        inputEl.value = value;
      } else if (inputEl._dtp) {
        const dtp = inputEl._dtp;
        dtp.currentDate = value;
        dtp._dateBtn.textContent = formatDateForDisplay(value);
        dtp.fpInstance.setDate(value, false);
        inputEl.value = `${value}T${pad(dtp.currentHours)}:${pad(dtp.currentMinutes)}`;
      } else {
        inputEl.value = value;
      }
    }
  }

  // ── destroy ─────────────────────────────────────────────────────
  function destroy(inputEl) {
    if (!inputEl) return;

    if (inputEl._dtp) {
      const dtp = inputEl._dtp;
      if (dtp.fpInstance) {
        try { dtp.fpInstance.destroy(); } catch (e) {}
      }
      if (dtp.wrapper && dtp.wrapper.parentNode) {
        dtp.wrapper.parentNode.removeChild(dtp.wrapper);
      }
      inputEl.style.display = '';
      delete inputEl._dtp;
    }

    if (inputEl._flatpickr_instance) {
      try { inputEl._flatpickr_instance.destroy(); } catch (e) {}
      inputEl.type = 'date';
      inputEl.style.display = '';
      delete inputEl._flatpickr_instance;
    }
  }

  window.DateTimePicker = { initDate, initDateTime, setValue, destroy };
})();
