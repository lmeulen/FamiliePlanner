/* ================================================================
   birthdays.js – Birthday management page
   ================================================================ */
(function () {
  let birthdays = [];
  let editId = null;
  let sortMode = 'upcoming';  // 'upcoming' or 'alphabetical'
  let filterAgenda = false;

  // ── Loaders ───────────────────────────────────────────────────
  async function loadBirthdays() {
    try {
      birthdays = await API.get('/api/birthdays/');
      render();
    } catch {
      birthdays = [];
      Toast.show('Kon verjaardagen niet laden', 'error');
    }
  }

  // ── Render ────────────────────────────────────────────────────
  function render() {
    const list = document.getElementById('birthdays-list');
    const empty = document.getElementById('birthdays-empty');

    // Filter
    let filtered = birthdays;
    if (filterAgenda) {
      filtered = birthdays.filter(b => b.show_in_agenda);
    }

    // Sort
    if (sortMode === 'upcoming') {
      filtered.sort((a, b) => a.days_until_next - b.days_until_next);
    } else {
      filtered.sort((a, b) => a.name.localeCompare(b.name));
    }

    if (!filtered.length) {
      list.innerHTML = '';
      empty.classList.remove('hidden');
      return;
    }
    empty.classList.add('hidden');

    list.innerHTML = filtered.map(b => renderBirthdayCard(b)).join('');

    // Bind clicks
    list.querySelectorAll('.birthday-card').forEach(card => {
      card.addEventListener('click', () => openBirthdayForm(parseInt(card.dataset.id)));
    });
  }

  function renderBirthdayCard(b) {
    const emoji = b.year_type === 'death_year' ? '🕯️' : '🎂';
    const monthName = FP.NL_MONTHS[b.month - 1];
    const dateStr = `${b.day} ${monthName}`;

    let ageInfo = '';
    if (b.year_type === 'birth_year' && b.age !== null) {
      ageInfo = `<div class="birthday-age">Wordt ${b.age + 1} jaar</div>`;
    } else if (b.year_type === 'death_year' && b.years_since_death !== null) {
      ageInfo = `<div class="birthday-memorial">${b.years_since_death} jaar geleden</div>`;
    }

    const countdown = b.days_until_next === 0
      ? '<span class="birthday-today">Vandaag! 🎉</span>'
      : `Over ${b.days_until_next} ${b.days_until_next === 1 ? 'dag' : 'dagen'}`;

    return `
      <div class="birthday-card ${b.year_type === 'death_year' ? 'birthday-card--memorial' : ''}" data-id="${b.id}">
        <div class="birthday-emoji">${emoji}</div>
        <div class="birthday-info">
          <div class="birthday-name">${FP.esc(b.name)}</div>
          <div class="birthday-date">${dateStr}</div>
          ${ageInfo}
          <div class="birthday-countdown">${countdown}</div>
        </div>
        ${b.show_in_agenda ? '<div class="birthday-agenda-badge" title="In agenda">📅</div>' : ''}
      </div>`;
  }

  // ── Form handlers ─────────────────────────────────────────────
  function openBirthdayForm(id = null) {
    editId = id;
    Modal.open('tpl-birthday-form');
    const form = document.getElementById('birthday-form');
    const title = document.getElementById('birthday-form-title');
    const delBtn = document.getElementById('btn-delete-birthday');
    const yearField = form.querySelector('.birthday-year-field');

    // Toggle year field visibility based on year_type
    function toggleYearField() {
      const yearType = form.year_type.value;
      if (yearType === 'no_year') {
        yearField.style.display = 'none';
        form.year.value = '';
      } else {
        yearField.style.display = 'block';
      }
    }

    if (id) {
      title.textContent = 'Verjaardag bewerken';
      delBtn.classList.remove('hidden');
      const b = birthdays.find(x => x.id === id);
      if (b) {
        form.name.value = b.name;
        form.day.value = b.day;
        form.month.value = b.month;
        form.year.value = b.year || '';
        form.year_type.value = b.year_type;
        form.show_in_agenda.checked = b.show_in_agenda;
        form.notes.value = b.notes;
      }
    } else {
      title.textContent = 'Verjaardag toevoegen';
      delBtn.classList.add('hidden');
      form.reset();
      form.show_in_agenda.checked = true;
    }

    // Set initial visibility and add change listener
    toggleYearField();
    form.year_type.addEventListener('change', toggleYearField);

    form.addEventListener('submit', async e => {
      e.preventDefault();
      const data = {
        name: form.name.value.trim(),
        day: parseInt(form.day.value),
        month: parseInt(form.month.value),
        year: form.year.value ? parseInt(form.year.value) : null,
        year_type: form.year_type.value,
        show_in_agenda: form.show_in_agenda.checked,
        notes: form.notes.value.trim(),
      };

      try {
        if (editId) {
          await API.put(`/api/birthdays/${editId}`, data);
          Toast.show('Verjaardag bijgewerkt!');
        } else {
          await API.post('/api/birthdays/', data);
          Toast.show('Verjaardag toegevoegd!');
        }
        Modal.close();
        loadBirthdays();
      } catch (err) {
        Toast.show(err.message || 'Fout bij opslaan', 'error');
      }
    }, { once: true });

    delBtn.addEventListener('click', async () => {
      if (!confirm(`Verjaardag van ${birthdays.find(b => b.id === editId)?.name} verwijderen?`)) return;
      try {
        await API.delete(`/api/birthdays/${editId}`);
        Toast.show('Verwijderd', 'warning');
        Modal.close();
        loadBirthdays();
      } catch {
        Toast.show('Fout bij verwijderen', 'error');
      }
    }, { once: true });
  }

  // ── Init ───────────────────────────────────────────────────────
  async function init() {
    document.getElementById('btn-add-birthday')?.addEventListener('click', () => openBirthdayForm());

    // Sort mode
    document.querySelectorAll('input[name="sort"]').forEach(radio => {
      radio.addEventListener('change', e => {
        sortMode = e.target.value;
        render();
      });
    });

    // Filter
    document.getElementById('filter-agenda')?.addEventListener('change', e => {
      filterAgenda = e.target.checked;
      render();
    });

    await loadBirthdays();
  }

  document.addEventListener('DOMContentLoaded', init);
})();
