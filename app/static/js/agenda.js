/* ================================================================
   agenda.js – Full agenda page: week/month/list views + CRUD
   Supports standalone events and recurring series.
   ================================================================ */
(function () {
  let events        = [];
  let members       = [];
  let curView       = 'week';
  let curDate       = new Date();    // anchor date for current view
  let editId        = null;          // id of the event being edited
  let seriesId      = null;          // series_id of the event being edited
  let currentSeries = null;          // fetched RecurrenceSeries object
  let editScope     = 'this';        // 'this' | 'series'
  let activeMember  = null;

  // ── Load & render ─────────────────────────────────────────────
  async function loadEvents() {
    try {
      const start = new Date(curDate);
      start.setMonth(start.getMonth() - 1);
      const end = new Date(curDate);
      end.setMonth(end.getMonth() + 2);
      const fmt = d => `${d.getFullYear()}-${FP.pad(d.getMonth()+1)}-${FP.pad(d.getDate())}`;
      events = await API.get(`/api/agenda/?start=${fmt(start)}&end=${fmt(end)}`);
    } catch {
      events = [];
      Toast.show('Kon agenda niet laden', 'error');
    }
    render();
  }

  function filteredEvents() {
    return activeMember
      ? events.filter(e => !e.member_id || e.member_id === activeMember)
      : events;
  }

  function render() {
    updateTitle();
    if (curView === 'week')       renderWeekView();
    else if (curView === 'month') renderMonthView();
    else                          renderListView();
  }

  function updateTitle() {
    const el = document.getElementById('cal-title');
    if (!el) return;
    if (curView === 'week') {
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
        const m = FP.getMember(ev.member_id);
        html += `<div class="cal-event-chip" style="background:${ev.color}" data-id="${ev.id}">${recurIcon(ev)}${m ? m.avatar + ' ' : ''}${ev.title}</div>`;
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
        const m      = FP.getMember(ev.member_id);
        const colW   = 100 / totalCols;
        html += `<div class="cal-event-block" style="top:${topPx}px;height:${h}px;background:${ev.color};left:calc(${lane*colW}% + 2px);width:calc(${colW}% - 4px);right:auto" data-id="${ev.id}" title="${ev.title}">
          <div class="cal-event-block-title">${recurIcon(ev)}${ev.title}</div>
          ${!isShort && m ? `<div class="cal-event-block-member">${m.avatar} ${m.name}</div>` : ''}
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
          ${dayEvents.slice(0,3).map(ev => `<div class="cal-event-chip" style="background:${ev.color}" data-id="${ev.id}">${recurIcon(ev)}${ev.title}</div>`).join('')}
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

    listView.innerHTML = fe.map(ev => {
      const start = new Date(ev.start_time), end = new Date(ev.end_time);
      const m = FP.getMember(ev.member_id);
      return `<div class="card event-card" data-id="${ev.id}" style="cursor:pointer">
        <div class="event-color-bar" style="background:${ev.color}"></div>
        <div class="event-body">
          <div class="event-title">${recurIcon(ev)}${ev.title}</div>
          <div class="event-meta">
            ${FP.formatDate(start)} · ${ev.all_day ? 'Hele dag' : FP.formatTime(start)+' – '+FP.formatTime(end)}
            ${ev.location ? ` · 📍 ${ev.location}` : ''}
          </div>
        </div>
        ${m ? `<div class="event-member-badge" style="background:${m.color}">${m.avatar}</div>` : ''}
      </div>`;
    }).join('');

    listView.querySelectorAll('.card').forEach(card => {
      card.addEventListener('click', () => openEventForm(parseInt(card.dataset.id)));
    });
  }

  // ── Navigation ────────────────────────────────────────────────
  function navigate(dir) {
    if (curView === 'week') curDate = FP.addDays(curDate, dir * 7);
    else if (curView === 'month') curDate = new Date(curDate.getFullYear(), curDate.getMonth() + dir, 1);
    loadEvents();
  }

  // ── Helpers ───────────────────────────────────────────────────
  function pad(n) { return String(n).padStart(2, '0'); }

  function toTimeStr(dt) {
    return `${pad(dt.getHours())}:${pad(dt.getMinutes())}:00`;
  }

  // ── Event CRUD form ───────────────────────────────────────────
  async function openEventForm(id = null, prefillDate = null, prefillDatetime = null) {
    editId        = id;
    seriesId      = null;
    currentSeries = null;
    editScope     = 'this';

    Modal.open('tpl-event-form');
    const form    = document.getElementById('event-form');
    const titleEl = document.getElementById('event-form-title');
    const delBtn  = document.getElementById('btn-delete-event');

    const toggleRow        = document.getElementById('recurrence-toggle-row');
    const recurToggle      = document.getElementById('recurrence-toggle');
    const recurSection     = document.getElementById('recurrence-section');
    const scopeSelector    = document.getElementById('series-scope-selector');
    const recurFields      = document.getElementById('recurrence-fields');

    FP.populateMemberSelect(form.querySelector('select[name="member_id"]'));

    if (id) {
      // ── Editing existing event ──────────────────────────────
      titleEl.textContent = 'Afspraak bewerken';
      delBtn.classList.remove('hidden');
      const ev = events.find(e => e.id === id);
      if (ev) {
        form.title.value       = ev.title;
        form.description.value = ev.description || '';
        form.location.value    = ev.location || '';
        form.start_time.value  = FP.toLocalDatetimeInput(new Date(ev.start_time));
        form.end_time.value    = FP.toLocalDatetimeInput(new Date(ev.end_time));
        form.all_day.checked   = ev.all_day;
        form.color.value       = ev.color;
        form.querySelector('select[name="member_id"]').value = ev.member_id || '';

        if (ev.series_id) {
          // Part of a series – show scope selector
          seriesId = ev.series_id;
          toggleRow.classList.add('hidden');
          recurSection.classList.remove('hidden');
          scopeSelector.classList.remove('hidden');
          recurFields.classList.add('hidden');   // hidden until scope=series

          // Fetch series data to pre-fill recurrence fields
          try {
            currentSeries = await API.get(`/api/agenda/series/${seriesId}`);
            form.querySelector('select[name="recurrence_type"]').value = currentSeries.recurrence_type;
            form.querySelector('input[name="series_end"]').value = currentSeries.series_end;
          } catch { /* non-critical */ }

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
    }

    // ── Submit ───────────────────────────────────────────────
    form.addEventListener('submit', async e => {
      e.preventDefault();
      const memberIdEl = form.querySelector('select[name="member_id"]');
      const memberId = memberIdEl.value ? parseInt(memberIdEl.value) : null;
      const startDt  = new Date(form.start_time.value);
      const endDt    = new Date(form.end_time.value);

      const eventData = {
        title:       form.title.value,
        description: form.description.value,
        location:    form.location.value,
        start_time:  startDt.toISOString(),
        end_time:    endDt.toISOString(),
        all_day:     form.all_day.checked,
        color:       form.color.value,
        member_id:   memberId,
      };

      try {
        if (!editId) {
          if (recurToggle && recurToggle.checked) {
            // Create recurring series
            const seriesEndVal = form.querySelector('input[name="series_end"]').value;
            if (!seriesEndVal) { Toast.show('Vul een einddatum voor de reeks in', 'error'); return; }
            await API.post('/api/agenda/series', {
              ...eventData,
              recurrence_type:    form.querySelector('select[name="recurrence_type"]').value,
              series_start:       form.start_time.value.split('T')[0],
              series_end:         seriesEndVal,
              start_time_of_day:  toTimeStr(startDt),
              end_time_of_day:    toTimeStr(endDt),
            });
            Toast.show('Herhalende reeks aangemaakt!');
          } else {
            await API.post('/api/agenda/', eventData);
            Toast.show('Afspraak toegevoegd!');
          }
        } else {
          if (seriesId && editScope === 'series') {
            // Update whole series
            const seriesEndVal = form.querySelector('input[name="series_end"]').value;
            await API.put(`/api/agenda/series/${seriesId}`, {
              ...eventData,
              recurrence_type:    form.querySelector('select[name="recurrence_type"]').value,
              series_end:         seriesEndVal,
              start_time_of_day:  toTimeStr(startDt),
              end_time_of_day:    toTimeStr(endDt),
            });
            Toast.show('Reeks bijgewerkt!');
          } else {
            await API.put(`/api/agenda/${editId}`, eventData);
            Toast.show('Afspraak bijgewerkt!');
          }
        }
        Modal.close();
        loadEvents();
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
        loadEvents();
      } catch { Toast.show('Fout bij verwijderen', 'error'); }
    }, { once: true });
  }

  // ── Init ──────────────────────────────────────────────────────
  async function init() {
    await FP.loadMembers();

    document.querySelectorAll('.view-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        curView = btn.dataset.view;
        render();
      });
    });

    document.getElementById('cal-prev')?.addEventListener('click', () => navigate(-1));
    document.getElementById('cal-next')?.addEventListener('click', () => navigate(1));
    document.getElementById('btn-add-event')?.addEventListener('click', () => openEventForm());

    await FP.buildMemberChips('agenda-member-chips', m => { activeMember = m; render(); });

    loadEvents();
  }

  document.addEventListener('DOMContentLoaded', init);
})();
