/* ================================================================
   grocery.js – Smart grocery list with offline PWA support
   ================================================================ */
(function () {
  let items = [];
  let categories = [];
  let isOnline = navigator.onLine;
  let db = window.GroceryDB;

  // ── Offline/Online detection ──────────────────────────────────
  function updateOnlineStatus() {
    isOnline = navigator.onLine;
    const indicator = document.getElementById('offline-indicator');

    if (isOnline) {
      if (indicator) indicator.remove();
      syncPendingChanges();
    } else {
      if (!indicator) {
        const banner = document.createElement('div');
        banner.id = 'offline-indicator';
        banner.className = 'offline-indicator';
        banner.textContent = '📡 Offline modus - wijzigingen worden gesynchroniseerd wanneer je weer online bent';
        document.body.prepend(banner);
      }
    }
  }

  window.addEventListener('online', updateOnlineStatus);
  window.addEventListener('offline', updateOnlineStatus);

  // ── Load ──────────────────────────────────────────────────────
  async function loadCategories() {
    try {
      if (isOnline) {
        categories = await API.get('/api/grocery/categories');
        // Save to IndexedDB for offline use
        await db.saveCategories(categories);
      } else {
        // Load from IndexedDB when offline
        categories = await db.getCategories();
      }
    } catch (err) {
      console.error('Failed to load categories:', err);
      // Try loading from IndexedDB as fallback
      try {
        categories = await db.getCategories();
      } catch {
        categories = [];
      }
      if (!categories.length) {
        Toast.show('Kon categorieën niet laden', 'error');
      }
    }
  }

  async function loadItems() {
    try {
      if (isOnline) {
        items = await API.get('/api/grocery/items');
        // Save to IndexedDB for offline use
        await db.saveItems(items);
      } else {
        // Load from IndexedDB when offline
        items = await db.getItems();
      }
    } catch (err) {
      console.error('Failed to load items:', err);
      // Try loading from IndexedDB as fallback
      try {
        items = await db.getItems();
      } catch {
        items = [];
      }
      if (!items.length && isOnline) {
        Toast.show('Kon boodschappenlijst niet laden', 'error');
      }
    }
    render();
  }

  // ── Sync pending changes ──────────────────────────────────────
  async function syncPendingChanges() {
    if (!isOnline) return;

    try {
      const pending = await db.getPendingSync();
      if (!pending || !pending.length) return;

      console.log(`[Grocery] Syncing ${pending.length} pending changes...`);

      for (const action of pending) {
        try {
          switch (action.type) {
            case 'add':
              await API.post('/api/grocery/items', action.payload);
              break;
            case 'update':
              await API.patch(`/api/grocery/items/${action.itemId}`, action.payload);
              break;
            case 'delete':
              await API.delete(`/api/grocery/items/${action.itemId}`);
              break;
            case 'clear_done':
              await API.delete('/api/grocery/items/done');
              break;
          }
        } catch (err) {
          console.error('Failed to sync action:', action, err);
        }
      }

      // Clear sync queue after successful sync
      await db.clearSyncQueue();

      // Reload from server
      await loadCategories();
      await loadItems();

      Toast.show('Wijzigingen gesynchroniseerd!', 'success');
    } catch (err) {
      console.error('Sync failed:', err);
    }
  }

  // ── Render ────────────────────────────────────────────────────
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
        <div class="grocery-item-actions">
          <button class="btn btn--icon btn--ghost grocery-edit" data-id="${item.id}" title="Categorie wijzigen" aria-label="Categorie wijzigen">✏️</button>
          <button class="btn btn--icon btn--danger-ghost grocery-delete" data-id="${item.id}" title="Verwijderen" aria-label="Verwijderen">🗑️</button>
        </div>
      </div>`;
  }

  function bindItemEvents() {
    // Check/uncheck
    document.querySelectorAll('.grocery-check').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = parseInt(btn.dataset.id);
        const item = items.find(i => i.id === id);
        if (!item) return;

        const newChecked = !item.checked;

        try {
          if (isOnline) {
            await API.patch(`/api/grocery/items/${id}`, { checked: newChecked });
          } else {
            // Update locally and queue sync
            await db.updateItemOffline(id, {
              checked: newChecked,
              checked_at: newChecked ? new Date().toISOString() : null
            });
            await db.queueSync({
              type: 'update',
              itemId: id,
              payload: { checked: newChecked }
            });
          }
          await loadItems();
        } catch (err) {
          console.error('Failed to update item:', err);
          Toast.show('Fout bij bijwerken', 'error');
        }
      });
    });

    // Edit category
    document.querySelectorAll('.grocery-edit').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = parseInt(btn.dataset.id);
        const item = items.find(i => i.id === id);
        if (!item) return;

        openCategoryPicker(item);
      });
    });

    // Delete
    document.querySelectorAll('.grocery-delete').forEach(btn => {
      btn.addEventListener('click', async () => {
        const id = parseInt(btn.dataset.id);
        if (!confirm('Item verwijderen?')) return;

        try {
          if (isOnline) {
            await API.delete(`/api/grocery/items/${id}`);
          } else {
            // Delete locally and queue sync
            await db.deleteItemOffline(id);
            await db.queueSync({ type: 'delete', itemId: id });
          }
          Toast.show('Item verwijderd', 'warning');
          await loadItems();
        } catch (err) {
          console.error('Failed to delete item:', err);
          Toast.show('Fout bij verwijderen', 'error');
        }
      });
    });
  }

  // ── Add item ──────────────────────────────────────────────────
  async function addItem(rawInput) {
    try {
      if (isOnline) {
        await API.post('/api/grocery/items', { raw_input: rawInput });
      } else {
        // Add locally and queue sync (simplified offline parsing)
        const parts = rawInput.trim().split(' ');
        const displayName = rawInput.charAt(0).toUpperCase() + rawInput.slice(1).toLowerCase();
        const productName = rawInput.toLowerCase();

        // Get default category (last one = "Overig")
        const defaultCat = categories[categories.length - 1];

        const newItem = {
          product_name: productName,
          display_name: displayName,
          quantity: null,
          unit: null,
          category_id: defaultCat?.id || 1,
          checked: false,
          sort_order: 0,
          created_at: new Date().toISOString(),
          checked_at: null
        };

        await db.addItemOffline(newItem);
        await db.queueSync({ type: 'add', payload: { raw_input: rawInput } });
      }

      Toast.show('Toegevoegd!');
      document.getElementById('item-input').value = '';
      document.getElementById('suggestion-hint').classList.add('hidden');
      await loadItems();
    } catch (err) {
      console.error('Failed to add item:', err);
      Toast.show(err.message || 'Fout bij toevoegen', 'error');
    }
  }

  // ── Edit item category ────────────────────────────────────────
  async function openCategoryPicker(item) {
    if (!isOnline) {
      Toast.show('Categorie wijzigen is alleen online mogelijk', 'warning');
      return;
    }

    Modal.open('tpl-category-picker');

    // Set item info
    document.getElementById('picker-item-name').textContent = item.display_name;

    // Render category options
    const container = document.getElementById('category-picker-list');
    container.innerHTML = categories.map(cat => `
      <button
        type="button"
        class="category-picker-option ${cat.id === item.category_id ? 'active' : ''}"
        data-category-id="${cat.id}"
      >
        <span class="category-picker-icon">${cat.icon}</span>
        <span class="category-picker-name">${FP.esc(cat.name)}</span>
        ${cat.id === item.category_id ? '<span class="category-picker-check">✓</span>' : ''}
      </button>
    `).join('');

    // Bind click events
    container.querySelectorAll('.category-picker-option').forEach(btn => {
      btn.addEventListener('click', async () => {
        const newCategoryId = parseInt(btn.dataset.categoryId);
        await updateItemCategory(item.id, newCategoryId);
      });
    });
  }

  async function updateItemCategory(itemId, categoryId) {
    try {
      await API.patch(`/api/grocery/items/${itemId}`, { category_id: categoryId });
      Toast.show('Categorie gewijzigd!');
      Modal.close();
      await loadItems();
    } catch (err) {
      console.error('Failed to update category:', err);
      Toast.show('Fout bij wijzigen categorie', 'error');
    }
  }

  // ── Category management ───────────────────────────────────────
  async function openManageCategories() {
    if (!isOnline) {
      Toast.show('Categorieën aanpassen is alleen online mogelijk', 'warning');
      return;
    }

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
    } catch (err) {
      console.error('Failed to save category order:', err);
      Toast.show('Fout bij opslaan', 'error');
    }
  }

  // ── Clear done ────────────────────────────────────────────────
  async function clearDoneItems() {
    if (!confirm('Alle afgevinkte items verwijderen?')) return;

    try {
      if (isOnline) {
        await API.delete('/api/grocery/items/done');
      } else {
        // Delete all checked items locally and queue sync
        const checkedItems = items.filter(i => i.checked);
        for (const item of checkedItems) {
          await db.deleteItemOffline(item.id);
        }
        await db.queueSync({ type: 'clear_done' });
      }

      Toast.show('Afgevinkte items verwijderd', 'warning');
      await loadItems();
    } catch (err) {
      console.error('Failed to clear done items:', err);
      Toast.show('Fout bij verwijderen', 'error');
    }
  }

  // ── Init ──────────────────────────────────────────────────────
  async function init() {
    // Initialize IndexedDB
    await db.open();

    // Check initial online status
    updateOnlineStatus();

    // Load data
    await loadCategories();
    await loadItems();

    // Try to sync any pending changes from previous offline session
    if (isOnline) {
      syncPendingChanges();
    }

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
