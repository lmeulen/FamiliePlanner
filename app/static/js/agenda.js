/* ================================================================
   agenda.js – Full agenda page: week/month/list views + CRUD
   Supports standalone events and recurring series.
   ================================================================ */
(function () {
  let events        = [];
  let members       = [];
  let curView       = 'day';
  let curDate       = new Date();    // anchor date for current view
  let editId        = null;          // id of the event being edited
  let seriesId      = null;          // series_id of the event being edited
  let currentSeries = null;          // fetched RecurrenceSeries object
  let editScope     = 'this';        // 'this' | 'series'
  let activeMember  = null;

  // ── Load & render ─────────────────────────────────────────────
  async function loadEvents(useCache = true) {
    try {
      const start = new Date(curDate);
      start.setMonth(start.getMonth() - 1);
      const end = new Date(curDate);
      end.setMonth(end.getMonth() + 2);
      const fmt = d => `${d.getFullYear()}-${FP.pad(d.getMonth()+1)}-${FP.pad(d.getDate())}`;

      // Build cache key based on date range
      const cacheKey = `agenda_events_${fmt(start)}_${fmt(end)}`;

      // Try cache first
      if (useCache) {
        const cached = Cache.get(cacheKey);
        if (cached) {
          events = cached;
          render();
          return;
        }
      }

      // Fetch from API
      events = await API.get(`/api/agenda/?start=${fmt(start)}&end=${fmt(end)}`);

      // Cache for 1 minute (events change frequently)
      Cache.set(cacheKey, events, 60000);
    } catch {
      events = [];
      Toast.show('Kon agenda niet laden', 'error');
    }
    render();
  }

  function filteredEvents() {
    return activeMember
      ? events.filter(e => !e.member_ids?.length || e.member_ids.includes(activeMember))
      : events;
  }

  function render() {
    updateTitle();
    if (curView === 'day')        renderDayView();
    else if (curView === 'week')  renderWeekView();
    else if (curView === 'month') renderMonthView();
    else                          renderListView();
  }

  function updateTitle() {
    const el = document.getElementById('cal-title');
    if (!el) return;
    if (curView === 'day') {
      const rangeEnd = FP.addDays(curDate, 3);
      el.textContent = `${FP.formatDateShort(curDate)} – ${FP.formatDateShort(rangeEnd)}`;
    } else if (curView === 'week') {
      const mon = FP.startOfWeek(curDate);
      const sun = FP.addDays(mon, 6);
      el.textContent = `${FP.formatDateShort(mon)} – ${FP.formatDateShort(sun)} ${sun.getFullYear()}`;
    } else if (curView === 'month') {
      el.textContent = `${FP.NL_MONTHS[curDate.getMonth()]} ${curDate.getFullYear()}`;
    } else {
      el.textContent = 'Aankomende afspraken';
    }
  }

  const HOUR_HEIGHT = 32;
  const START_HOUR  = 7;
  const END_HOUR    = 22;

  function computeEventLayout(evs) {
    if (!evs.length) return [];
    const sorted = [...evs].sort((a, b) => new Date(a.start_time) - new Date(b.start_time));
    const laneEnds = [];
    const items = sorted.map(ev => {
      const start = new Date(ev.start_time);
      const end   = new Date(ev.end_time);
      let lane = laneEnds.findIndex(laneEnd => laneEnd <= start);
      if (lane === -1) lane = laneEnds.length;
      laneEnds[lane] = end;
      return { ev, lane };
    });
    return items.map(item => {
      const start = new Date(item.ev.start_time);
      const end   = new Date(item.ev.end_time);
      const concurrent = items.filter(o => {
        const os = new Date(o.ev.start_time), oe = new Date(o.ev.end_time);
        return os < end && oe > start;
      });
      const totalCols = Math.max(...concurrent.map(c => c.lane)) + 1;
      return { ev: item.ev, lane: item.lane, totalCols };
    });
  }

  function recurIcon(ev) { return ev.series_id ? '<span class="recur-icon" title="Herhalend">↻</span> ' : ''; }

  function renderAgendaEventCard(ev, opts = {}) {
    const { includeDate = false } = opts;
    const start = new Date(ev.start_time), end = new Date(ev.end_time);
    const members = (ev.member_ids || []).map(id => FP.getMember(id)).filter(Boolean);
    const eventBackground = FP.agendaEventBackground(ev.member_ids || []);
    const badges = members.map(m => `<div class="event-member-badge" style="background:${m.color}">${m.avatar}</div>`).join('');
    const timeLabel = ev.all_day ? 'Hele dag' : `${FP.formatTime(start)} – ${FP.formatTime(end)}`;
    const datePrefix = includeDate ? `${FP.formatDate(start)} · ` : '';
    return `<div class="card event-card" data-id="${ev.id}" style="cursor:pointer">
      <div class="event-color-bar" style="background:${eventBackground}"></div>
      <div class="event-body">
        <div class="event-title">${recurIcon(ev)}${FP.esc(ev.title)}</div>
        <div class="event-meta">
          ${datePrefix}${timeLabel}
          ${ev.location ? ` · 📍 ${FP.esc(ev.location)}` : ''}
        </div>
      </div>
      ${badges ? `<div class="event-member-badges">${badges}</div>` : ''}
    </div>`;
  }

  function renderDayView() {
    const calView = document.getElementById('cal-view');
    const listView = document.getElementById('events-list-view');
    calView.classList.add('hidden');
    listView.classList.remove('hidden');

    const fe = filteredEvents();
    const days = Array.from({ length: 4 }, (_, idx) => {
      const day = new Date(curDate);
      day.setHours(0, 0, 0, 0);
      day.setDate(day.getDate() + idx);
      return day;
    });

    const sectionsHtml = days.map(day => {
      const dayEvents = fe
        .filter(e => FP.isSameDay(new Date(e.start_time), day))
        .sort((a, b) => new Date(a.start_time) - new Date(b.start_time));

      const dayLabel = FP.formatDate(day);
      const daySub = FP.isToday(day) ? 'Vandaag' : '';

      return `<section class="agenda-day-section">
        <div class="agenda-day-section-header">
          <div class="agenda-day-section-title">${FP.esc(dayLabel)}</div>
          ${daySub ? `<div class="agenda-day-section-badge">${daySub}</div>` : ''}
        </div>
        <div class="agenda-day-section-list card-list">
          ${dayEvents.length
            ? dayEvents.map(renderAgendaEventCard).join('')
            : '<div class="agenda-day-section-empty">Geen afspraken</div>'}
        </div>
      </section>`;
    }).join('');

    listView.innerHTML = `<div class="agenda-day-list">${sectionsHtml}</div>`;
    listView.querySelectorAll('.event-card').forEach(card => {
      card.addEventListener('click', () => openEventForm(parseInt(card.dataset.id)));
    });
  }

  function renderWeekView() {
    const calView  = document.getElementById('cal-view');
    const listView = document.getElementById('events-list-view');
    calView.classList.remove('hidden');
    listView.classList.add('hidden');

    const mon  = FP.startOfWeek(curDate);
    const days = Array.from({length: 7}, (_, i) => FP.addDays(mon, i));
    const fe   = filteredEvents();
    const allDayEvents = fe.filter(e => e.all_day);
    const timedEvents  = fe.filter(e => !e.all_day);

    let html = '<div class="cal-week-wrapper">';
    html += '<div class="cal-week-head">';
    html += '<div class="cal-corner"></div>';
    days.forEach(d => {
      const isTod = FP.isToday(d);
      html += `<div class="cal-day-hdr ${isTod ? 'cal-day-hdr--today' : ''}">
        <div class="cal-day-hdr-name">${FP.NL_DAYS[d.getDay()]}</div>
        <div class="cal-day-hdr-num">${d.getDate()}</div>
      </div>`;
    });
    html += '</div>';

    html += '<div class="cal-week-allday">';
    html += '<div class="cal-allday-label">Hele<br>dag</div>';
    days.forEach(d => {
      const chips = allDayEvents.filter(e => FP.isSameDay(new Date(e.start_time), d));
      html += '<div class="cal-allday-cell">';
      chips.forEach(ev => {
        const m = ev.member_ids?.length === 1 ? FP.getMember(ev.member_ids[0]) : null;
        html += `<div class="cal-event-chip" style="background:${FP.agendaEventBackground(ev.member_ids || [])}" data-id="${ev.id}">${recurIcon(ev)}${m ? m.avatar + ' ' : ''}${FP.esc(ev.title)}</div>`;
      });
      html += '</div>';
    });
    html += '</div>';

    html += '<div class="cal-week-scroll"><div class="cal-week-timegrid">';
    html += '<div class="cal-time-labels">';
    for (let h = START_HOUR; h <= END_HOUR; h++) {
      html += `<div class="cal-time-slot">${FP.pad(h)}:00</div>`;
    }
    html += '</div>';

    days.forEach(day => {
      const dateStr = `${day.getFullYear()}-${FP.pad(day.getMonth()+1)}-${FP.pad(day.getDate())}`;
      const isToday = FP.isToday(day);
      const dayTimed = timedEvents.filter(e => FP.isSameDay(new Date(e.start_time), day));

      html += `<div class="cal-day-col ${isToday ? 'cal-day-col--today' : ''}" data-date="${dateStr}">`;
      for (let h = START_HOUR; h <= END_HOUR; h++) html += `<div class="cal-hour-line"></div>`;

      if (isToday) {
        const now = new Date();
        const nowPx = (now.getHours() + now.getMinutes() / 60 - START_HOUR) * HOUR_HEIGHT;
        if (nowPx >= 0 && nowPx <= (END_HOUR - START_HOUR) * HOUR_HEIGHT) {
          html += `<div class="cal-now-line" style="top:${nowPx}px"></div>`;
        }
      }

      const layout = computeEventLayout(dayTimed);
      layout.forEach(({ ev, lane, totalCols }) => {
        const start  = new Date(ev.start_time), end = new Date(ev.end_time);
        const topPx  = Math.max(0, (start.getHours() + start.getMinutes() / 60 - START_HOUR) * HOUR_HEIGHT);
        const botPx  = Math.min((end.getHours() + end.getMinutes() / 60 - START_HOUR) * HOUR_HEIGHT, (END_HOUR - START_HOUR) * HOUR_HEIGHT);
        const h      = Math.max(26, botPx - topPx);
        const isShort = h < 46;
        const m      = ev.member_ids?.length === 1 ? FP.getMember(ev.member_ids[0]) : null;
        const colW   = 100 / totalCols;
        html += `<div class="cal-event-block" style="top:${topPx}px;height:${h}px;background:${FP.agendaEventBackground(ev.member_ids || [])};left:calc(${lane*colW}% + 2px);width:calc(${colW}% - 4px);right:auto" data-id="${ev.id}" title="${FP.esc(ev.title)}">
          <div class="cal-event-block-title">${recurIcon(ev)}${FP.esc(ev.title)}</div>
          ${!isShort && m ? `<div class="cal-event-block-member">${m.avatar} ${FP.esc(m.name)}</div>` : ''}
        </div>`;
      });
      html += '</div>';
    });

    html += '</div></div></div>';
    calView.innerHTML = html;

    calView.querySelectorAll('.cal-day-col').forEach(col => {
      col.addEventListener('click', e => {
        if (e.target.closest('.cal-event-block')) return;
        const y = e.clientY - col.getBoundingClientRect().top;
        const rawHour = y / HOUR_HEIGHT + START_HOUR;
        const hour = Math.min(Math.max(Math.floor(rawHour), START_HOUR), END_HOUR - 1);
        const mins = Math.round((rawHour - Math.floor(rawHour)) * 60 / 15) * 15;
        const dt = `${col.dataset.date}T${FP.pad(hour)}:${FP.pad(mins === 60 ? 0 : mins)}`;
        openEventForm(null, col.dataset.date, dt);
      });
    });
    calView.querySelectorAll('.cal-event-block').forEach(b => {
      b.addEventListener('click', e => { e.stopPropagation(); openEventForm(parseInt(b.dataset.id)); });
    });
    calView.querySelectorAll('.cal-event-chip').forEach(c => {
      c.addEventListener('click', () => openEventForm(parseInt(c.dataset.id)));
    });

    const scroll = calView.querySelector('.cal-week-scroll');
    if (scroll) scroll.scrollTop = Math.max(0, (new Date().getHours() - START_HOUR - 1)) * HOUR_HEIGHT;
  }

  function renderMonthView() {
    const calView = document.getElementById('cal-view');
    document.getElementById('events-list-view').classList.add('hidden');
    calView.classList.remove('hidden');

    const year = curDate.getFullYear(), month = curDate.getMonth();
    const first = new Date(year, month, 1), last = new Date(year, month + 1, 0);
    const startDay = (first.getDay() + 6) % 7;
    const fe = filteredEvents();

    let html = '<div class="cal-month-grid">';
    ['Ma','Di','Wo','Do','Vr','Za','Zo'].forEach(d => { html += `<div class="cal-month-header">${d}</div>`; });

    for (let i = 0; i < startDay; i++) {
      const prev = new Date(year, month, 1 - startDay + i);
      html += `<div class="cal-month-day cal-day--other-month"><div class="cal-month-day-num">${prev.getDate()}</div></div>`;
    }

    for (let d = 1; d <= last.getDate(); d++) {
      const day = new Date(year, month, d);
      const dayEvents = fe.filter(e => FP.isSameDay(new Date(e.start_time), day));
      const dayStr = `${day.getFullYear()}-${FP.pad(day.getMonth()+1)}-${FP.pad(day.getDate())}`;
      html += `<div class="cal-month-day ${FP.isToday(day) ? 'cal-day--today' : ''}" data-date="${dayStr}">
        <div class="cal-month-day-num">${d}</div>
        <div class="cal-month-events">
          ${dayEvents.slice(0,3).map(ev => `<div class="cal-event-chip" style="background:${FP.agendaEventBackground(ev.member_ids || [])}" data-id="${ev.id}">${recurIcon(ev)}${FP.esc(ev.title)}</div>`).join('')}
          ${dayEvents.length > 3 ? `<div style="font-size:.65rem;color:var(--text-muted);padding:.1rem .2rem">+${dayEvents.length-3}</div>` : ''}
        </div></div>`;
    }

    const used = startDay + last.getDate();
    const trailing = (7 - (used % 7)) % 7;
    for (let i = 1; i <= trailing; i++) {
      html += `<div class="cal-month-day cal-day--other-month"><div class="cal-month-day-num">${i}</div></div>`;
    }
    html += '</div>';
    calView.innerHTML = html;

    calView.querySelectorAll('.cal-month-day[data-date]').forEach(cell => {
      cell.addEventListener('click', e => {
        if (e.target.classList.contains('cal-event-chip')) return;
        openEventForm(null, cell.dataset.date);
      });
    });
    calView.querySelectorAll('.cal-event-chip').forEach(chip => {
      chip.addEventListener('click', e => { e.stopPropagation(); openEventForm(parseInt(chip.dataset.id)); });
    });
  }

  function renderListView() {
    const calView = document.getElementById('cal-view');
    const listView = document.getElementById('events-list-view');
    calView.classList.add('hidden');
    listView.classList.remove('hidden');

    const fe = filteredEvents()
      .filter(e => new Date(e.start_time) >= new Date())
      .sort((a, b) => new Date(a.start_time) - new Date(b.start_time));

    if (!fe.length) { listView.innerHTML = '<p class="empty-state">Geen aankomende afspraken</p>'; return; }

    listView.innerHTML = fe.map(ev => renderAgendaEventCard(ev, { includeDate: true })).join('');

    listView.querySelectorAll('.card').forEach(card => {
      card.addEventListener('click', () => openEventForm(parseInt(card.dataset.id)));
    });
  }

  // ── Navigation ────────────────────────────────────────────────
  function navigate(dir) {
    if (curView === 'day') curDate = FP.addDays(curDate, dir);
    else if (curView === 'week') curDate = FP.addDays(curDate, dir * 7);
    else if (curView === 'month') curDate = new Date(curDate.getFullYear(), curDate.getMonth() + dir, 1);
    loadEvents();
  }

  // ── Helpers ───────────────────────────────────────────────────
  function pad(n) { return String(n).padStart(2, '0'); }

  function toTimeStr(dt) {
    return `${pad(dt.getHours())}:${pad(dt.getMinutes())}:00`;
  }

  function toApiDateTimeStr(dt) {
    return `${toDateOnlyStr(dt)}T${pad(dt.getHours())}:${pad(dt.getMinutes())}:${pad(dt.getSeconds())}`;
  }

  function toDateOnlyStr(dt) {
    return `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())}`;
  }

  function setAllDayInputMode(form, isAllDay, anchorDateStr) {
    const startInput = form.start_time;
    const endInput = form.end_time;
    if (!startInput || !endInput) return;

    if (isAllDay) {
      const startDate = startInput.value?.split('T')[0] || anchorDateStr || toDateOnlyStr(new Date());
      const endDate = endInput.value?.split('T')[0] || startDate;
      startInput.type = 'date';
      endInput.type = 'date';
      startInput.value = startDate;
      endInput.value = endDate;
      startInput.readOnly = false;
      endInput.readOnly = false;
    } else {
      const startDate = startInput.value?.split('T')[0] || anchorDateStr || toDateOnlyStr(new Date());
      const endDate = endInput.value?.split('T')[0] || startDate;
      startInput.type = 'datetime-local';
      endInput.type = 'datetime-local';
      startInput.readOnly = false;
      endInput.readOnly = false;
      if (!startInput.value.includes('T')) startInput.value = `${startDate}T09:00`;
      if (!endInput.value.includes('T')) endInput.value = `${endDate}T10:00`;
    }
  }

  // ── Event CRUD form ───────────────────────────────────────────
  async function openEventForm(id = null, prefillDate = null, prefillDatetime = null) {
    editId        = id;
    seriesId      = null;
    currentSeries = null;
    editScope     = 'this';

    Modal.open('tpl-event-form');
    const form      = document.getElementById('event-form');
    const titleEl   = document.getElementById('event-form-title');
    const delBtn    = document.getElementById('btn-delete-event');
    const exportBtn = document.getElementById('btn-export-event');

    const toggleRow        = document.getElementById('recurrence-toggle-row');
    const recurToggle      = document.getElementById('recurrence-toggle');
    const recurSection     = document.getElementById('recurrence-section');
    const scopeSelector    = document.getElementById('series-scope-selector');
    const recurFields      = document.getElementById('recurrence-fields');
    const allDayInput      = form.querySelector('input[name="all_day"]');

    const anchorDateObj = prefillDate ? new Date(`${prefillDate}T00:00`) : new Date(curDate);
    anchorDateObj.setHours(0, 0, 0, 0);
    const anchorDateStr = toDateOnlyStr(anchorDateObj);
    form.dataset.anchorDate = anchorDateStr;

    FP.buildMemberPicker('event-member-picker');

    if (id) {
      // ── Editing existing event ──────────────────────────────
      titleEl.textContent = 'Afspraak bewerken';
      delBtn.classList.remove('hidden');
      exportBtn.classList.remove('hidden');
      const ev = events.find(e => e.id === id);
      if (ev) {
        form.title.value       = ev.title;
        form.description.value = ev.description || '';
        form.location.value    = ev.location || '';
        form.start_time.value  = FP.toLocalDatetimeInput(new Date(ev.start_time));
        form.end_time.value    = FP.toLocalDatetimeInput(new Date(ev.end_time));
        form.all_day.checked   = ev.all_day;
        FP.buildMemberPicker('event-member-picker', ev.member_ids || []);
        setAllDayInputMode(form, ev.all_day, anchorDateStr);

        if (ev.series_id) {
          // Part of a series – show scope selector
          seriesId = ev.series_id;
          toggleRow.classList.add('hidden');
          recurSection.classList.remove('hidden');
          scopeSelector.classList.remove('hidden');
          recurFields.classList.add('hidden');   // hidden until scope=series

          // Scope radio change handler
          form.querySelectorAll('input[name="edit_scope"]').forEach(radio => {
            radio.addEventListener('change', () => {
              editScope = radio.value;
              recurFields.classList.toggle('hidden', editScope !== 'series');
              if (editScope === 'series' && currentSeries) {
                // Show series-level times in date inputs
                form.start_time.value = `${currentSeries.series_start}T${currentSeries.start_time_of_day.slice(0,5)}`;
                form.end_time.value   = `${currentSeries.series_start}T${currentSeries.end_time_of_day.slice(0,5)}`;
              } else {
                form.start_time.value = FP.toLocalDatetimeInput(new Date(ev.start_time));
                form.end_time.value   = FP.toLocalDatetimeInput(new Date(ev.end_time));
              }
              setAllDayInputMode(form, form.all_day.checked, anchorDateStr);
            });
          });
        } else {
          // Standalone event – no recurrence UI
          toggleRow.classList.add('hidden');
          recurSection.classList.add('hidden');
        }
      }
    } else {
      // ── Creating new event ──────────────────────────────────
      titleEl.textContent = 'Afspraak toevoegen';
      delBtn.classList.add('hidden');
      exportBtn.classList.add('hidden');
      toggleRow.classList.remove('hidden');
      recurSection.classList.add('hidden');
      scopeSelector.classList.add('hidden');

      if (prefillDatetime) {
        const dStart = new Date(prefillDatetime);
        form.start_time.value = FP.toLocalDatetimeInput(dStart);
        const dEnd = new Date(dStart); dEnd.setHours(dEnd.getHours() + 1);
        form.end_time.value = FP.toLocalDatetimeInput(dEnd);
      } else if (prefillDate) {
        const d = new Date(prefillDate + 'T09:00');
        form.start_time.value = FP.toLocalDatetimeInput(d);
        d.setHours(d.getHours() + 1);
        form.end_time.value = FP.toLocalDatetimeInput(d);
      }

      // Set default series_end (4 weeks ahead)
      const defaultEnd = new Date(); defaultEnd.setDate(defaultEnd.getDate() + 28);
      form.querySelector('input[name="series_end"]').value =
        `${defaultEnd.getFullYear()}-${pad(defaultEnd.getMonth()+1)}-${pad(defaultEnd.getDate())}`;

      recurToggle.addEventListener('change', () => {
        recurSection.classList.toggle('hidden', !recurToggle.checked);
      });
      setAllDayInputMode(form, false, anchorDateStr);
    }

    allDayInput?.addEventListener('change', () => {
      setAllDayInputMode(form, allDayInput.checked, anchorDateStr);
    });

    // ── Progressive disclosure for recurrence UI ─────
    const recurrenceUI = new RecurrenceUIController({
      formId: 'event-form',
      idPrefix: '',
      showToggle: !id,
    });

    // ── Submit (registered here, before any async series-data fetch) ─────
    form.addEventListener('submit', async e => {
      e.preventDefault();
      const memberIds = FP.getSelectedMemberIds('event-member-picker');
      const isAllDay = form.all_day.checked;
      const forcedDate = form.dataset.anchorDate || toDateOnlyStr(new Date());
      let startDt;
      let endDt;

      if (isAllDay) {
        const startDateVal = form.start_time.value || forcedDate;
        const endDateVal = form.end_time.value || startDateVal;
        startDt = new Date(`${startDateVal}T00:00:00`);
        endDt = new Date(`${endDateVal}T23:59:59`);
      } else {
        startDt = new Date(form.start_time.value);
        endDt = new Date(form.end_time.value);
      }

      // Cross-field: end must be after start
      const endTimeErr = document.getElementById('end-time-error');
      if ((!isAllDay && endDt <= startDt) || (isAllDay && endDt < startDt)) {
        endTimeErr?.classList.remove('hidden');
        form.end_time.focus();
        return;
      }
      endTimeErr?.classList.add('hidden');

      // Trim text inputs
      form.title.value       = form.title.value.trim();
      form.description.value = form.description.value.trim();
      form.location.value    = form.location.value.trim();

      // Series end date validation (only when recurrence-fields is visible)
      const startDate         = form.start_time.value.split('T')[0];
      const recurSectionEl    = document.getElementById('recurrence-section');
      const recurFieldsEl     = document.getElementById('recurrence-fields');
      const seriesEndVisible  = !recurSectionEl?.classList.contains('hidden') &&
                                !recurFieldsEl?.classList.contains('hidden');
      if (seriesEndVisible) {
        const validation = recurrenceUI.validate(startDate);
        if (!validation.valid) {
          if (validation.errorElementId) {
            recurrenceUI.showValidationError(validation.errorElementId);
          }
          Toast.show(validation.error, 'error');
          return;
        }
        recurrenceUI.hideAllValidationErrors();
      }

      const eventData = {
        title:       form.title.value,
        description: form.description.value,
        location:    form.location.value,
        start_time:  toApiDateTimeStr(startDt),
        end_time:    toApiDateTimeStr(endDt),
        all_day:     form.all_day.checked,
        member_ids:  memberIds,
      };

      try {
        if (!editId) {
          // Check if this is a multi-day all-day event that should become a series
          const isMultiDayAllDay = form.all_day.checked &&
            Math.floor((endDt - startDt) / (1000 * 60 * 60 * 24)) > 0;

          if (recurToggle && recurToggle.checked || isMultiDayAllDay) {
            // Create recurring series (either user-requested or auto-converted multi-day)
            const recurrencePayload = recurrenceUI.getRecurrencePayload();
            const seriesPayload = {
              ...eventData,
              series_start:       form.start_time.value.split('T')[0],
              start_time_of_day:  toTimeStr(startDt),
              end_time_of_day:    toTimeStr(endDt),
              ...recurrencePayload,
            };

            // Override for multi-day all-day auto-conversion
            if (isMultiDayAllDay && !recurToggle.checked) {
              seriesPayload.recurrence_type = 'daily';
              seriesPayload.interval = 1;
              // If end time is at midnight (00:00), subtract one day from series_end
              const endTime = form.end_time.value.split('T')[1];
              let seriesEndDate = form.end_time.value.split('T')[0];
              if (endTime === '00:00' || endTime.startsWith('00:00:')) {
                const endDateObj = new Date(seriesEndDate);
                endDateObj.setDate(endDateObj.getDate() - 1);
                seriesEndDate = endDateObj.toISOString().split('T')[0];
              }
              seriesPayload.series_end = seriesEndDate;
              delete seriesPayload.count; // Ensure we use series_end
            }

            await API.post('/api/agenda/series', seriesPayload);
            Toast.show(isMultiDayAllDay && !recurToggle.checked ? 'Meerdaagse afspraak aangemaakt!' : 'Herhalende reeks aangemaakt!');
          } else {
            await API.post('/api/agenda/', eventData);
            Toast.show('Afspraak toegevoegd!');
          }
        } else {
          if (seriesId && editScope === 'series') {
            // Update whole series
            const recurrencePayload = recurrenceUI.getRecurrencePayload();
            const seriesPayload = {
              ...eventData,
              start_time_of_day:  toTimeStr(startDt),
              end_time_of_day:    toTimeStr(endDt),
              ...recurrencePayload,
            };

            await API.put(`/api/agenda/series/${seriesId}`, seriesPayload);
            Toast.show('Reeks bijgewerkt!');
          } else {
            // Check if editing a standalone event to multi-day all-day
            const isMultiDayAllDay = form.all_day.checked &&
              Math.floor((endDt - startDt) / (1000 * 60 * 60 * 24)) > 0;

            if (isMultiDayAllDay) {
              Toast.show('Let op: meerdaagse afspraken worden alleen op de eerste dag getoond. Maak een nieuwe herhalende afspraak aan voor alle dagen.', 'warning');
            }

            const updated = await API.put(`/api/agenda/${editId}`, eventData);
            // Update local array immediately so reopening the form shows fresh data
            const idx = events.findIndex(e => e.id === editId);
            if (idx !== -1) events[idx] = updated;
            Toast.show('Afspraak bijgewerkt!');
          }
        }
        Modal.close();
        // Invalidate agenda cache on mutation
        Cache.invalidate('agenda_events_');
        loadEvents(false); // Skip cache, fetch fresh data
      } catch (err) {
        Toast.show(err.message || 'Fout bij opslaan', 'error');
      }
    }, { once: true });

    // ── Delete ───────────────────────────────────────────────
    delBtn.addEventListener('click', async () => {
      const isSeries = seriesId && editScope === 'series';
      if (!confirm(isSeries ? 'Hele reeks verwijderen?' : 'Afspraak verwijderen?')) return;
      try {
        if (isSeries) {
          await API.delete(`/api/agenda/series/${seriesId}`);
          Toast.show('Reeks verwijderd', 'warning');
        } else {
          await API.delete(`/api/agenda/${editId}`);
          Toast.show('Afspraak verwijderd', 'warning');
        }
        Modal.close();
        // Invalidate agenda cache on delete
        Cache.invalidate('agenda_events_');
        loadEvents(false); // Skip cache, fetch fresh data
      } catch { Toast.show('Fout bij verwijderen', 'error'); }
    }, { once: true });

    // ── Export ───────────────────────────────────────────────
    exportBtn.addEventListener('click', () => {
      if (!editId) return;
      window.location.href = `/api/agenda/${editId}/export`;
      Toast.show('Afspraak geëxporteerd!');
    }, { once: true });

    // Fetch series data non-blocking (recurrence fields pre-fill)
    if (seriesId) {
      API.get(`/api/agenda/series/${seriesId}`).then(s => {
        currentSeries = s;
        recurrenceUI.populateFromSeries(s);
      }).catch(() => {});
    }
  }

  // ── Init ──────────────────────────────────────────────────────
  async function init() {
    await FP.loadMembers();

    document.querySelectorAll('.view-btn[data-view]').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.view-btn[data-view]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        curView = btn.dataset.view;
        render();
      });
    });

    document.getElementById('cal-prev')?.addEventListener('click', () => navigate(-1));
    document.getElementById('cal-next')?.addEventListener('click', () => navigate(1));
    document.getElementById('btn-today')?.addEventListener('click', () => {
      curDate = new Date();
      loadEvents();
    });
    document.getElementById('btn-add-event')?.addEventListener('click', () => openEventForm());

    await FP.buildMemberChips('agenda-member-chips', m => { activeMember = m; render(); });

    await loadEvents();

    // Check for URL parameter to open specific event modal (from search)
    const params = new URLSearchParams(window.location.search);
    const eventId = params.get('event');
    if (eventId) {
      openEventForm(parseInt(eventId));
      // Clean URL without reload
      window.history.replaceState({}, '', '/agenda');
    }
  }

  document.addEventListener('DOMContentLoaded', init);
})();
