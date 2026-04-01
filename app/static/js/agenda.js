/* ================================================================
   agenda.js – Full agenda page: week/month/list views + CRUD
   Supports standalone events and recurring series.
   ================================================================ */
(function () {
  let events        = [];
  let members       = [];
  let curView       = 'day';
  let curDate       = new Date();    // anchor date for current view
  let activeMember  = null;

  // ── Load & render ─────────────────────────────────────────────
  async function loadEvents(useCache = true) {
    // Show skeleton at start
    const skeleton = document.getElementById('cal-skeleton') || document.getElementById('list-skeleton');
    if (skeleton) skeleton.classList.remove('hidden');

    // Hide actual content during load
    const calGrid = document.getElementById('cal-grid');
    const listBody = document.getElementById('events-list-body');
    if (calGrid) calGrid.classList.add('hidden');
    if (listBody) listBody.classList.add('hidden');

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
          // Hide skeleton, show content
          if (skeleton) skeleton.classList.add('hidden');
          if (calGrid) calGrid.classList.remove('hidden');
          if (listBody) listBody.classList.remove('hidden');
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
    } finally {
      // Hide skeleton after load (success or error)
      if (skeleton) skeleton.classList.add('hidden');
      if (calGrid) calGrid.classList.remove('hidden');
      if (listBody) listBody.classList.remove('hidden');
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
      el.textContent = `${FP.dayNameFull(curDate)} ${FP.formatDateShort(curDate)} – ${FP.formatDateShort(rangeEnd)}`;
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

      const dayLabel = `${FP.dayNameFull(day)} ${FP.formatDate(day)}`;
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
          ${dayEvents.slice(0,3).map(ev => `<div class="cal-event-chip" style="background:${FP.agendaEventBackground(ev.member_ids || [])}" data-id="${ev.id}" title="${FP.esc(ev.title)}">${recurIcon(ev)}${FP.esc(ev.title)}</div>`).join('')}
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

    if (!fe.length) {
      listView.innerHTML = '<p class="empty-state">Geen aankomende afspraken</p>';
      return;
    }

    // Group events by date
    const eventsByDate = new Map();
    fe.forEach(event => {
      const eventDate = new Date(event.start_time);
      const dateKey = eventDate.toDateString();
      if (!eventsByDate.has(dateKey)) {
        eventsByDate.set(dateKey, { date: eventDate, events: [] });
      }
      eventsByDate.get(dateKey).events.push(event);
    });

    // Render date sections
    const sectionsHtml = Array.from(eventsByDate.values()).map(({ date, events }) => {
      const dayLabel = `${FP.dayNameFull(date)} ${FP.formatDate(date)}`;
      const daySub = FP.isToday(date) ? 'Vandaag' : '';

      return `<section class="agenda-day-section">
        <div class="agenda-day-section-header">
          <div class="agenda-day-section-title">${FP.esc(dayLabel)}</div>
          ${daySub ? `<div class="agenda-day-section-badge">${daySub}</div>` : ''}
        </div>
        <div class="agenda-day-section-list card-list">
          ${events.map(renderAgendaEventCard).join('')}
        </div>
      </section>`;
    }).join('');

    listView.innerHTML = `<div class="agenda-day-list">${sectionsHtml}</div>`;

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

  // ── Event CRUD form ───────────────────────────────────────────
  async function openEventForm(id = null, prefillDate = null, prefillDatetime = null) {
    const controller = new EventFormController({
      templateId: 'tpl-event-form',
      formId: 'event-form',
      simplified: false,
      eventCache: events,
      onSave: () => {
        Cache.invalidate(/^agenda_events_/);
        loadEvents(false);
      },
    });

    await controller.open(id, prefillDate, prefillDatetime);
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

    // Check for URL parameter to jump to specific date (from search)
    const params = new URLSearchParams(window.location.search);
    const dateParam = params.get('date');
    if (dateParam) {
      const targetDate = new Date(dateParam);
      if (!isNaN(targetDate.getTime())) {
        curDate = targetDate;
      }
    }

    await loadEvents();

    // Check for URL parameter to open specific event modal (from search)
    const eventId = params.get('event');
    if (eventId) {
      openEventForm(parseInt(eventId));
    }

    // Clean URL without reload if there were params
    if (dateParam || eventId) {
      window.history.replaceState({}, '', '/agenda');
    }
  }

  document.addEventListener('DOMContentLoaded', init);
})();
