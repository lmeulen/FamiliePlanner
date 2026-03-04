/* ================================================================
   meals.js – Weekly meal planner page
   ================================================================ */
(function () {
  let meals    = [];
  let curMonday = FP ? FP.startOfWeek(new Date()) : new Date();
  let editId   = null;
  let typeFilter = 'all';

  // ── Load ──────────────────────────────────────────────────────
  async function loadMeals() {
    const start = curMonday.toISOString().split('T')[0];
    const end   = FP.addDays(curMonday, 6).toISOString().split('T')[0];
    try {
      meals = await API.get(`/api/meals/?start=${start}&end=${end}`);
    } catch {
      meals = [];
      Toast.show('Kon maaltijden niet laden', 'error');
    }
    render();
  }

  // ── Render ────────────────────────────────────────────────────
  function filteredMeals() {
    return typeFilter === 'all' ? meals : meals.filter(m => m.meal_type === typeFilter);
  }

  function render() {
    updateTitle();
    const grid  = document.getElementById('meals-week-grid');
    const empty = document.getElementById('meals-empty');
    const fm = filteredMeals();

    if (!fm.length) {
      grid.innerHTML = '';
      empty.classList.remove('hidden');
      return;
    }
    empty.classList.add('hidden');

    let html = '';
    for (let i = 0; i < 7; i++) {
      const day = FP.addDays(curMonday, i);
      const dayStr = day.toISOString().split('T')[0];
      const dayMeals = fm.filter(m => m.date === dayStr);
      const isToday = FP.isToday(day);

      html += `<div class="meals-day-row">
        <div class="meals-day-header" data-date="${dayStr}">
          <span class="meals-day-name ${isToday ? 'meals-day-today' : ''}">${FP.dayNameFull(day)}</span>
          <span class="meals-day-date">${FP.formatDateShort(day)}</span>
        </div>
        <div class="meals-day-body">`;

      if (dayMeals.length) {
        dayMeals.forEach(meal => {
          const cook = meal.cook_member_id ? FP.getMember(meal.cook_member_id) : null;
          html += `
            <div class="meal-card" data-id="${meal.id}" style="flex:0 0 auto;max-width:160px">
              <span class="meal-type-badge ${meal.meal_type}">${FP.mealTypeLabel(meal.meal_type)}</span>
              <div class="meal-name-row">
                <div class="meal-name">${meal.name}</div>
                ${cook ? `<div class="meal-cook">${cook.avatar} ${cook.name}</div>` : ''}
              </div>
              ${meal.recipe_url ? `<a href="${meal.recipe_url}" target="_blank" rel="noopener" style="font-size:.72rem;color:var(--accent)" onclick="event.stopPropagation()">🔗 Recept</a>` : ''}
            </div>`;
        });
      } else {
        html += `<button class="btn btn--secondary" style="font-size:.8rem;flex:0 0 auto" data-add-date="${dayStr}">＋ Toevoegen</button>`;
      }

      html += `<button class="icon-btn" style="align-self:center" data-add-date="${dayStr}" title="Maaltijd toevoegen">＋</button>`;
      html += `</div></div>`;
    }

    grid.innerHTML = html;

    grid.querySelectorAll('.meal-card').forEach(card => {
      card.addEventListener('click', () => openMealForm(parseInt(card.dataset.id)));
    });
    grid.querySelectorAll('[data-add-date]').forEach(btn => {
      btn.addEventListener('click', () => openMealForm(null, btn.dataset.addDate));
    });
  }

  function updateTitle() {
    const el  = document.getElementById('meals-week-title');
    const end = FP.addDays(curMonday, 6);
    if (el) el.textContent = `${FP.formatDateShort(curMonday)} – ${FP.formatDateShort(end)} ${end.getFullYear()}`;
  }

  // ── Meal form ─────────────────────────────────────────────────
  async function openMealForm(id = null, prefillDate = null) {
    editId = id;
    Modal.open('tpl-meal-form');
    const form   = document.getElementById('meal-form');
    const title  = document.getElementById('meal-form-title');
    const delBtn = document.getElementById('btn-delete-meal');

    await FP.loadMembers();
    const cookSel = form.querySelector('[name="cook_member_id"]');
    if (cookSel) {
      FP.populateMemberSelect(cookSel, true);
      if (cookSel.options[0]) cookSel.options[0].textContent = '— Niemand —';
    }

    if (id) {
      title.textContent = 'Maaltijd bewerken';
      delBtn.classList.remove('hidden');
      const meal = meals.find(m => m.id === id);
      if (meal) {
        form.date.value       = meal.date;
        form.meal_type.value  = meal.meal_type;
        form.name.value       = meal.name;
        form.description.value = meal.description || '';
        form.recipe_url.value  = meal.recipe_url || '';
        if (cookSel) cookSel.value = meal.cook_member_id || '';
      }
    } else {
      title.textContent = 'Maaltijd toevoegen';
      delBtn.classList.add('hidden');
      if (prefillDate) form.date.value = prefillDate;
    }

    form.addEventListener('submit', async e => {
      e.preventDefault();
      const cookVal  = cookSel ? cookSel.value : '';
      const name     = form.name.value.trim();
      const recipeUrl = form.recipe_url.value.trim();

      if (!name) { form.name.focus(); return; }
      if (recipeUrl && !recipeUrl.startsWith('http://') && !recipeUrl.startsWith('https://')) {
        Toast.show('Recept URL moet beginnen met http:// of https://', 'error');
        form.recipe_url.focus();
        return;
      }

      const data = {
        date:           form.date.value,
        meal_type:      form.meal_type.value,
        name,
        description:    form.description.value.trim(),
        recipe_url:     recipeUrl,
        cook_member_id: cookVal ? parseInt(cookVal) : null,
      };
      try {
        if (editId) {
          await API.put(`/api/meals/${editId}`, data);
          Toast.show('Maaltijd bijgewerkt!');
        } else {
          await API.post('/api/meals/', data);
          Toast.show('Maaltijd toegevoegd!');
        }
        Modal.close();
        loadMeals();
      } catch (err) { Toast.show(err.message || 'Fout', 'error'); }
    }, { once: true });

    delBtn.addEventListener('click', async () => {
      if (!confirm('Maaltijd verwijderen?')) return;
      try {
        await API.delete(`/api/meals/${editId}`);
        Toast.show('Maaltijd verwijderd', 'warning');
        Modal.close();
        loadMeals();
      } catch { Toast.show('Fout', 'error'); }
    }, { once: true });
  }

  // ── Init ──────────────────────────────────────────────────────
  async function init() {
    // Wait for FP to initialise startOfWeek
    curMonday = FP.startOfWeek(new Date());

    document.getElementById('meals-prev')?.addEventListener('click', () => {
      curMonday = FP.addDays(curMonday, -7);
      loadMeals();
    });
    document.getElementById('meals-next')?.addEventListener('click', () => {
      curMonday = FP.addDays(curMonday, 7);
      loadMeals();
    });

    document.querySelectorAll('.view-btn[data-type]').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.view-btn[data-type]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        typeFilter = btn.dataset.type;
        render();
      });
    });

    document.getElementById('btn-add-meal')?.addEventListener('click', () => openMealForm());

    loadMeals();
  }

  document.addEventListener('DOMContentLoaded', init);
})();
