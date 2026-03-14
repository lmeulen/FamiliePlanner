/* ================================================================
   grocery.js – Smart grocery list with category learning
   ================================================================ */
(function () {
  let items = [];
  let categories = [];

  // ── Load ──────────────────────────────────────────────────
  async function loadCategories() {
    try {
      categories = await API.get('/api/grocery/categories');
    } catch {
      categories = [];
      Toast.show('Kon categorieën niet laden', 'error');
    }
  }

  async function loadItems() {
    try {
      items = await API.get('/api/grocery/items');
    } catch {
      items = [];
      Toast.show('Kon boodschappenlijst niet laden', 'error');
    }
    render();
  }

  // ── Render ────────────────────────────────────────────────
  function render() {
    const container = document.getElementById('grocery-list');
    const emptyState = document.getElementById('empty-state');
    const clearBtn = document.getElementById('btn-clear-done');

    if (!items.length) {
      container.innerHTML = '';
      emptyState.classList.remove('hidden');
      clearBtn.classList.add('hidden');
      return;
    }

    emptyState.classList.add('hidden');

    // Group items by category
    const grouped = new Map();
    const doneItems = [];

    items.forEach(item => {
      if (item.checked) {
        doneItems.push(item);
      } else {
        const catId = item.category_id;
        if (!grouped.has(catId)) grouped.set(catId, []);
        grouped.get(catId).push(item);
      }
    });

    let html = '';

    // Render categories in order
    categories.forEach(cat => {
      const catItems = grouped.get(cat.id) || [];
      if (!catItems.length) return;

      html += `
        <div class="grocery-category-group">
          <div class="grocery-category-header">
            <span class="grocery-category-icon">${cat.icon}</span>
            <span class="grocery-category-name">${FP.esc(cat.name)}</span>
            <span class="grocery-category-count">${catItems.length}</span>
          </div>
          <div class="grocery-items">
            ${catItems.map(renderItem).join('')}
          </div>
        </div>`;
    });

    // Render done items at bottom
    if (doneItems.length) {
      html += `
        <div class="grocery-category-group grocery-done-group">
          <div class="grocery-category-header">
            <span class="grocery-category-icon">✅</span>
            <span class="grocery-category-name">Klaar</span>
            <span class="grocery-category-count">${doneItems.length}</span>
          </div>
          <div class="grocery-items">
            ${doneItems.map(renderItem).join('')}
          </div>
        </div>`;

      clearBtn.classList.remove('hidden');
    } else {
      clearBtn.classList.add('hidden');
    }

    container.innerHTML = html;
    bindItemEvents();
  }

  function renderItem(item) {
    const quantityText = item.quantity && item.unit
      ? `${item.quantity} ${item.unit}`
      : item.quantity || '';

    return `
      <div class="grocery-item ${item.checked ? 'checked' : ''}" data-id="${item.id}">
        <button class="grocery-check" data-id="${item.id}" aria-label="Afvinken"></button>
        <div class="grocery-item-content">
          <div class="grocery-item-name">${FP.esc(item.display_name)}</div>
          ${quantityText ? `<div class="grocery-item-quantity">${FP.esc(quantityText)}</div>` : ''}
        </div>
        <button class="btn btn--icon btn--danger-ghost grocery-delete" data-id="${item.id}" title="Verwijderen" aria-label="Verwijderen">🗑️</button>
      </div>`;
  }

  function bindItemEvents() {
    // Check/uncheck
    document.querySelectorAll('.grocery-check').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = parseInt(btn.dataset.id);
        const item = items.find(i => i.id === id);
        if (!item) return;

        try {
          await API.patch(`/api/grocery/items/${id}`, { checked: !item.checked });
          await loadItems();
        } catch {
          Toast.show('Fout bij bijwerken', 'error');
        }
      });
    });

    // Delete
    document.querySelectorAll('.grocery-delete').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = parseInt(btn.dataset.id);
        if (!confirm('Item verwijderen?')) return;

        try {
          await API.delete(`/api/grocery/items/${id}`);
          Toast.show('Item verwijderd', 'warning');
          await loadItems();
        } catch {
          Toast.show('Fout bij verwijderen', 'error');
        }
      });
    });
  }

  // ── Add item ──────────────────────────────────────────────
  async function addItem(rawInput) {
    try {
      await API.post('/api/grocery/items', { raw_input: rawInput });
      Toast.show('Toegevoegd!');
      document.getElementById('item-input').value = '';
      document.getElementById('suggestion-hint').classList.add('hidden');
      await loadItems();
    } catch (err) {
      Toast.show(err.message || 'Fout bij toevoegen', 'error');
    }
  }

  // ── Category management ───────────────────────────────────
  async function openManageCategories() {
    Modal.open('tpl-manage-categories');
    renderCategoryOrder();

    const form = document.getElementById('category-order-form');
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      await saveCategoryOrder();
    }, { once: true });
  }

  function renderCategoryOrder() {
    const container = document.getElementById('category-order-list');
    let sortedCats = [...categories].sort((a, b) => a.sort_order - b.sort_order);

    container.innerHTML = sortedCats.map((cat, idx) => `
      <div class="manage-list-row" data-idx="${idx}">
        <span class="manage-list-dot" style="background:${cat.color}">${cat.icon}</span>
        <span class="manage-list-name">${FP.esc(cat.name)}</span>
        <div class="manage-list-btns">
          <button type="button" class="icon-btn cat-up" data-idx="${idx}" ${idx === 0 ? 'disabled' : ''} title="Omhoog">▲</button>
          <button type="button" class="icon-btn cat-down" data-idx="${idx}" ${idx === sortedCats.length - 1 ? 'disabled' : ''} title="Omlaag">▼</button>
        </div>
      </div>
    `).join('');

    // Bind up/down buttons
    container.querySelectorAll('.cat-up').forEach(btn => {
      btn.addEventListener('click', () => {
        const i = parseInt(btn.dataset.idx);
        if (i === 0) return;
        [sortedCats[i - 1], sortedCats[i]] = [sortedCats[i], sortedCats[i - 1]];
        renderCategoryOrder();
      });
    });

    container.querySelectorAll('.cat-down').forEach(btn => {
      btn.addEventListener('click', () => {
        const i = parseInt(btn.dataset.idx);
        if (i === sortedCats.length - 1) return;
        [sortedCats[i], sortedCats[i + 1]] = [sortedCats[i + 1], sortedCats[i]];
        renderCategoryOrder();
      });
    });

    // Store for save
    window._tempCategoryOrder = sortedCats;
  }

  async function saveCategoryOrder() {
    const sorted = window._tempCategoryOrder;
    const payload = sorted.map((cat, idx) => ({
      id: cat.id,
      sort_order: (idx + 1) * 10
    }));

    try {
      await API.put('/api/grocery/categories/reorder', payload);
      Toast.show('Volgorde opgeslagen!');
      Modal.close();
      await loadCategories();
      await loadItems();
    } catch {
      Toast.show('Fout bij opslaan', 'error');
    }
  }

  // ── Clear done ────────────────────────────────────────────
  async function clearDoneItems() {
    if (!confirm('Alle afgevinkte items verwijderen?')) return;

    try {
      await API.delete('/api/grocery/items/done');
      Toast.show('Afgevinkte items verwijderd', 'warning');
      await loadItems();
    } catch {
      Toast.show('Fout bij verwijderen', 'error');
    }
  }

  // ── Init ──────────────────────────────────────────────────
  async function init() {
    await loadCategories();
    await loadItems();

    // Add item form
    const form = document.getElementById('add-item-form');
    const input = document.getElementById('item-input');

    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const value = input.value.trim();
      if (value) addItem(value);
    });

    // Category management
    document.getElementById('btn-manage-categories')?.addEventListener('click', openManageCategories);

    // Clear done
    document.getElementById('btn-clear-done')?.addEventListener('click', clearDoneItems);
  }

  document.addEventListener('DOMContentLoaded', init);
})();
