/* ================================================================
   agenda.js – Full agenda page: week/month/list views + CRUD
   ================================================================ */
(function () {
  let events   = [];
  let members  = [];
  let curView  = 'week';
  let curDate  = new Date();    // anchor date for current view
  let editId   = null;
  let activeMember = null;

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
    if (curView === 'week')  renderWeekView();
    else if (curView === 'month') renderMonthView();
    else renderListView();
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

  const HOUR_HEIGHT = 32;   // px per hour
  const START_HOUR  = 7;
  const END_HOUR    = 22;

  // Assigns a lane (column index) to each event so overlapping events sit side-by-side.
  // Returns an array of { ev, lane, totalCols } objects in the same order.
  function computeEventLayout(events) {
    if (!events.length) return [];
    const sorted = [...events].sort((a, b) => new Date(a.start_time) - new Date(b.start_time));

    // lanes[i] = end time of the last event placed in lane i
    const laneEnds = [];
    const items = sorted.map(ev => {
      const start = new Date(ev.start_time);
      const end   = new Date(ev.end_time);
      let lane = laneEnds.findIndex(laneEnd => laneEnd <= start);
      if (lane === -1) { lane = laneEnds.length; }
      laneEnds[lane] = end;
      return { ev, lane };
    });

    // For each event, count how many total lanes are active at the same time.
    return items.map(item => {
      const start = new Date(item.ev.start_time);
      const end   = new Date(item.ev.end_time);
      const concurrent = items.filter(other => {
        const os = new Date(other.ev.start_time);
        const oe = new Date(other.ev.end_time);
        return os < end && oe > start;
      });
      const totalCols = Math.max(...concurrent.map(c => c.lane)) + 1;
      return { ev: item.ev, lane: item.lane, totalCols };
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

    // Split all-day vs timed
    const allDayEvents = fe.filter(e => e.all_day);
    const timedEvents  = fe.filter(e => !e.all_day);

    // ── Sticky header ─────────────────────────────────────────
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

    // ── All-day row ──────────────────────────────────────────
    html += '<div class="cal-week-allday">';
    html += '<div class="cal-allday-label">Hele<br>dag</div>';
    days.forEach(d => {
      const chips = allDayEvents.filter(e => FP.isSameDay(new Date(e.start_time), d));
      html += '<div class="cal-allday-cell">';
      chips.forEach(ev => {
        const m = FP.getMember(ev.member_id);
        html += `<div class="cal-event-chip" style="background:${ev.color}" data-id="${ev.id}">${m ? m.avatar + ' ' : ''}${ev.title}</div>`;
      });
      html += '</div>';
    });
    html += '</div>';

    // ── Scrollable time grid ─────────────────────────────────
    html += '<div class="cal-week-scroll">';
    html += '<div class="cal-week-timegrid">';

    // Time label column
    html += '<div class="cal-time-labels">';
    for (let h = START_HOUR; h <= END_HOUR; h++) {
      html += `<div class="cal-time-slot">${FP.pad(h)}:00</div>`;
    }
    html += '</div>';

    // One column per day
    days.forEach(day => {
      const dateStr = `${day.getFullYear()}-${FP.pad(day.getMonth()+1)}-${FP.pad(day.getDate())}`;
      const isToday = FP.isToday(day);
      const dayTimed = timedEvents.filter(e => FP.isSameDay(new Date(e.start_time), day));

      html += `<div class="cal-day-col ${isToday ? 'cal-day-col--today' : ''}" data-date="${dateStr}">`;

      // Hourly background lines
      for (let h = START_HOUR; h <= END_HOUR; h++) {
        html += `<div class="cal-hour-line"></div>`;
      }

      // Current-time indicator
      if (isToday) {
        const now    = new Date();
        const nowPx  = (now.getHours() + now.getMinutes() / 60 - START_HOUR) * HOUR_HEIGHT;
        if (nowPx >= 0 && nowPx <= (END_HOUR - START_HOUR) * HOUR_HEIGHT) {
          html += `<div class="cal-now-line" style="top:${nowPx}px"></div>`;
        }
      }

      // Compute overlap layout (lanes) for this day's events
      const layout = computeEventLayout(dayTimed);

      // Positioned event blocks
      layout.forEach(({ ev, lane, totalCols }) => {
        const start   = new Date(ev.start_time);
        const end     = new Date(ev.end_time);
        const topPx   = Math.max(0, (start.getHours() + start.getMinutes() / 60 - START_HOUR) * HOUR_HEIGHT);
        const botPx   = Math.min((end.getHours() + end.getMinutes() / 60 - START_HOUR) * HOUR_HEIGHT,
                                 (END_HOUR - START_HOUR) * HOUR_HEIGHT);
        const h       = Math.max(26, botPx - topPx);
        const isShort = h < 46;
        const m       = FP.getMember(ev.member_id);
        const colW    = 100 / totalCols;
        const leftPct = lane * colW;
        html += `<div class="cal-event-block" style="top:${topPx}px;height:${h}px;background:${ev.color};left:calc(${leftPct}% + 2px);width:calc(${colW}% - 4px);right:auto" data-id="${ev.id}" title="${ev.title}">
          <div class="cal-event-block-title">${ev.title}</div>
          ${!isShort && m ? `<div class="cal-event-block-member">${m.avatar} ${m.name}</div>` : ''}
        </div>`;
      });

      html += '</div>';
    });

    html += '</div>'; // cal-week-timegrid
    html += '</div>'; // cal-week-scroll
    html += '</div>'; // cal-week-wrapper

    calView.innerHTML = html;

    // Click on day column → new event at that time
    calView.querySelectorAll('.cal-day-col').forEach(col => {
      col.addEventListener('click', e => {
        if (e.target.closest('.cal-event-block')) return;
        const scroll  = calView.querySelector('.cal-week-scroll');
        const colRect = col.getBoundingClientRect();
        const scrollRect = scroll.getBoundingClientRect();
        const y = e.clientY - colRect.top;
        const rawHour = y / HOUR_HEIGHT + START_HOUR;
        const hour    = Math.min(Math.max(Math.floor(rawHour), START_HOUR), END_HOUR - 1);
        const mins    = Math.round((rawHour - Math.floor(rawHour)) * 60 / 15) * 15;
        const dt = `${col.dataset.date}T${FP.pad(hour)}:${FP.pad(mins === 60 ? 0 : mins)}`;
        openEventForm(null, col.dataset.date, dt);
      });
    });
    calView.querySelectorAll('.cal-event-block').forEach(block => {
      block.addEventListener('click', e => { e.stopPropagation(); openEventForm(parseInt(block.dataset.id)); });
    });
    calView.querySelectorAll('.cal-event-chip').forEach(chip => {
      chip.addEventListener('click', () => openEventForm(parseInt(chip.dataset.id)));
    });

    // Auto-scroll to current hour (or 07:00)
    const scroll = calView.querySelector('.cal-week-scroll');
    if (scroll) {
      const now = new Date();
      const target = Math.max(0, (now.getHours() - START_HOUR - 1)) * HOUR_HEIGHT;
      scroll.scrollTop = target;
    }
  }

  function renderMonthView() {
    const calView = document.getElementById('cal-view');
    const listView = document.getElementById('events-list-view');
    calView.classList.remove('hidden');
    listView.classList.add('hidden');

    const year  = curDate.getFullYear();
    const month = curDate.getMonth();
    const first = new Date(year, month, 1);
    const last  = new Date(year, month + 1, 0);
    // Start grid on Monday
    const startDay = (first.getDay() + 6) % 7;   // 0=Mon
    const fe = filteredEvents();

    let html = '<div class="cal-month-grid">';
    ['Ma','Di','Wo','Do','Vr','Za','Zo'].forEach(d => {
      html += `<div class="cal-month-header">${d}</div>`;
    });

    // Leading blanks
    for (let i = 0; i < startDay; i++) {
      const prev = new Date(year, month, 1 - startDay + i);
      html += `<div class="cal-month-day cal-day--other-month">
        <div class="cal-month-day-num">${prev.getDate()}</div>
      </div>`;
    }

    for (let d = 1; d <= last.getDate(); d++) {
      const day = new Date(year, month, d);
      const dayEvents = fe.filter(e => FP.isSameDay(new Date(e.start_time), day));
      const isToday   = FP.isToday(day);
      const dayStr = `${day.getFullYear()}-${FP.pad(day.getMonth()+1)}-${FP.pad(day.getDate())}`;
      html += `<div class="cal-month-day ${isToday ? 'cal-day--today' : ''}" data-date="${dayStr}">
        <div class="cal-month-day-num">${d}</div>
        <div class="cal-month-events">
          ${dayEvents.slice(0,3).map(ev => `<div class="cal-event-chip" style="background:${ev.color}" data-id="${ev.id}">${ev.title}</div>`).join('')}
          ${dayEvents.length > 3 ? `<div style="font-size:.65rem;color:var(--text-muted);padding:.1rem .2rem">+${dayEvents.length-3}</div>` : ''}
        </div>
      </div>`;
    }

    // Trailing blanks
    const used = startDay + last.getDate();
    const trailing = (7 - (used % 7)) % 7;
    for (let i = 1; i <= trailing; i++) {
      html += `<div class="cal-month-day cal-day--other-month">
        <div class="cal-month-day-num">${i}</div>
      </div>`;
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
      .sort((a,b) => new Date(a.start_time) - new Date(b.start_time));

    if (!fe.length) {
      listView.innerHTML = '<p class="empty-state">Geen aankomende afspraken</p>';
      return;
    }

    listView.innerHTML = fe.map(ev => {
      const start = new Date(ev.start_time);
      const end   = new Date(ev.end_time);
      const m = FP.getMember(ev.member_id);
      return `
        <div class="card event-card" data-id="${ev.id}" style="cursor:pointer">
          <div class="event-color-bar" style="background:${ev.color}"></div>
          <div class="event-body">
            <div class="event-title">${ev.title}</div>
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
    if (curView === 'week')  curDate = FP.addDays(curDate, dir * 7);
    else if (curView === 'month') {
      curDate = new Date(curDate.getFullYear(), curDate.getMonth() + dir, 1);
    }
    loadEvents();
  }

  // ── Event CRUD form ───────────────────────────────────────────
  async function openEventForm(id = null, prefillDate = null, prefillDatetime = null) {
    editId = id;
    Modal.open('tpl-event-form');
    const form   = document.getElementById('event-form');
    const title  = document.getElementById('event-form-title');
    const delBtn = document.getElementById('btn-delete-event');

    // Populate member select
    FP.populateMemberSelect(form.querySelector('select[name="member_id"]'));

    if (id) {
      title.textContent = 'Afspraak bewerken';
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
      }
    } else {
      title.textContent = 'Afspraak toevoegen';
      delBtn.classList.add('hidden');
      if (prefillDatetime) {
        // Exact datetime from clicking the time grid
        const dStart = new Date(prefillDatetime);
        form.start_time.value = FP.toLocalDatetimeInput(dStart);
        const dEnd = new Date(dStart);
        dEnd.setHours(dEnd.getHours() + 1);
        form.end_time.value = FP.toLocalDatetimeInput(dEnd);
      } else if (prefillDate) {
        const d = new Date(prefillDate + 'T09:00');
        form.start_time.value = FP.toLocalDatetimeInput(d);
        d.setHours(d.getHours() + 1);
        form.end_time.value = FP.toLocalDatetimeInput(d);
      }
    }

    form.addEventListener('submit', async e => {
      e.preventDefault();
      const data = {
        title:       form.title.value,
        description: form.description.value,
        location:    form.location.value,
        start_time:  new Date(form.start_time.value).toISOString(),
        end_time:    new Date(form.end_time.value).toISOString(),
        all_day:     form.all_day.checked,
        color:       form.color.value,
        member_id:   form.querySelector('select[name="member_id"]').value
                       ? parseInt(form.querySelector('select[name="member_id"]').value) : null,
      };
      try {
        if (editId) {
          await API.put(`/api/agenda/${editId}`, data);
          Toast.show('Afspraak bijgewerkt!');
        } else {
          await API.post('/api/agenda/', data);
          Toast.show('Afspraak toegevoegd!');
        }
        Modal.close();
        loadEvents();
      } catch (err) {
        Toast.show(err.message || 'Fout bij opslaan', 'error');
      }
    }, { once: true });

    delBtn.addEventListener('click', async () => {
      if (!confirm('Afspraak verwijderen?')) return;
      try {
        await API.delete(`/api/agenda/${editId}`);
        Toast.show('Afspraak verwijderd', 'warning');
        Modal.close();
        loadEvents();
      } catch { Toast.show('Fout bij verwijderen', 'error'); }
    }, { once: true });
  }

  // ── Init ──────────────────────────────────────────────────────
  async function init() {
    await FP.loadMembers();

    // View buttons
    document.querySelectorAll('.view-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.view-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        curView = btn.dataset.view;
        render();
      });
    });

    // Navigation
    document.getElementById('cal-prev')?.addEventListener('click', () => navigate(-1));
    document.getElementById('cal-next')?.addEventListener('click', () => navigate(1));

    // FAB
    document.getElementById('btn-add-event')?.addEventListener('click', () => openEventForm());

    // Member filter
    await FP.buildMemberChips('agenda-member-chips', m => {
      activeMember = m;
      render();
    });

    loadEvents();
  }

  document.addEventListener('DOMContentLoaded', init);
})();
