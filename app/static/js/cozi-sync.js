/* ================================================================
   cozi-sync.js – Cozi synchronisation review page
   ================================================================ */
(function () {
  let _items = [];     // all CoziPreviewItem objects
  let _selected = new Set();  // UIDs that are checked
  let _linkItem = null;  // Current item being linked

  const elLoading      = document.getElementById('cozi-loading');
  const elError        = document.getElementById('cozi-error');
  const elErrorMsg     = document.getElementById('cozi-error-msg');
  const elResults      = document.getElementById('cozi-results');
  const elEmpty        = document.getElementById('cozi-empty');
  const elImportResult = document.getElementById('cozi-import-result');

  const elBadgeNew     = document.getElementById('badge-new');
  const elBadgeChanged = document.getElementById('badge-changed');
  const elBadgeLikely  = document.getElementById('badge-likely');
  const elBadgeExists  = document.getElementById('badge-exists');
  const elSelectedCount = document.getElementById('selected-count');
  const elBtnImport    = document.getElementById('btn-import');
  const elBtnSelectNew     = document.getElementById('btn-select-new');
  const elBtnSelectChanged = document.getElementById('btn-select-changed');
  const elBtnLinkAllLikely = document.getElementById('btn-link-all-likely');
  const elBtnRetry     = document.getElementById('btn-retry');
  const elBtnSyncAgain = document.getElementById('btn-sync-again');
  const elBtnLinkConfirm = document.getElementById('btn-link-confirm');

  // ── Load ──────────────────────────────────────────────────────
  async function loadPreview() {
    show(elLoading);
    hide(elError);
    hide(elResults);
    hide(elImportResult);

    try {
      _items = await API.get('/api/cozi/preview');
      renderResults();
    } catch (err) {
      elErrorMsg.textContent = err.message || 'Onbekende fout';
      show(elError);
    } finally {
      hide(elLoading);
    }
  }

  // ── Render ────────────────────────────────────────────────────
  function renderResults() {
    const newItems      = _items.filter(i => i.status === 'new');
    const changedItems  = _items.filter(i => i.status === 'changed');
    const likelyItems   = _items.filter(i => i.status === 'likely_exists');
    const existsItems   = _items.filter(i => i.status === 'exists');

    // Summary badges
    elBadgeNew.textContent     = `${newItems.length} nieuw`;
    elBadgeChanged.textContent = `${changedItems.length} gewijzigd`;
    elBadgeLikely.textContent  = `${likelyItems.length} mogelijk aanwezig`;
    elBadgeExists.textContent  = `${existsItems.length} al aanwezig`;
    if (elBtnLinkAllLikely) {
      elBtnLinkAllLikely.disabled = likelyItems.length === 0;
    }

    // Pre-select recommended items (new + changed)
    _selected.clear();
    [...newItems, ...changedItems].forEach(i => _selected.add(i.uid));

    // Requested order: Nieuw, Gewijzigd, Mogelijk aanwezig, Al aanwezig
    renderSection('section-new',     'list-new',     newItems);
    renderSection('section-changed', 'list-changed', changedItems);
    renderSection('section-likely',  'list-likely',  likelyItems);
    renderSection('section-exists',  'list-exists',  existsItems);

    updateImportButton();
    show(elResults);

    if (!_items.length) {
      show(elEmpty);
    } else {
      hide(elEmpty);
    }
  }

  function renderSection(sectionId, listId, items) {
    const section = document.getElementById(sectionId);
    const list    = document.getElementById(listId);
    list.innerHTML = '';

    if (!items.length) {
      hide(section);
      return;
    }
    show(section);
    items.forEach(item => list.appendChild(buildItemCard(item)));
  }

  function buildItemCard(item) {
    const tpl  = document.getElementById('tpl-cozi-item');
    const node = tpl.content.cloneNode(true);
    const card = node.querySelector('.cozi-item-card');
    const cb   = node.querySelector('.cozi-item-cb');

    cb.checked = _selected.has(item.uid);
    cb.dataset.uid = item.uid;

    cb.addEventListener('change', () => {
      if (cb.checked) {
        _selected.add(item.uid);
      } else {
        _selected.delete(item.uid);
      }
      updateImportButton();
    });

    // Title
    node.querySelector('.cozi-item-title').textContent = item.title;

    // Type badge
    const typeBadge = node.querySelector('.cozi-item-type-badge');
    const typeLabels = { event: 'afspraak', series: 'reeks', meal: 'maaltijd' };
    typeBadge.textContent = typeLabels[item.event_type] || item.event_type;

    // Status badge
    const statusBadge = node.querySelector('.cozi-item-status-badge');
    const statusLabels = {
      new: 'nieuw',
      changed: 'gewijzigd',
      likely_exists: 'mogelijk aanwezig',
      exists: 'al aanwezig',
    };
    statusBadge.textContent = statusLabels[item.status] || item.status;
    statusBadge.classList.add(`badge--${item.status}`);

    // Meta line: date + time + recurrence + location + members
    const metaParts = [];
    if (item.start_date) {
      const d = new Date(item.start_date + 'T00:00:00');
      metaParts.push(FP.formatDate(d));
    }
    if (item.start_time) {
      metaParts.push(`${item.start_time}${item.end_time ? '–' + item.end_time : ''}`);
    } else if (item.all_day) {
      metaParts.push('hele dag');
    }
    if (item.recurrence_type) {
      const recLabels = {
        daily: 'dagelijks', weekly: 'wekelijks', biweekly: 'tweewekelijks',
        monthly: 'maandelijks', yearly: 'jaarlijks',
        weekdays: 'werkdagen', every_other_day: 'om de dag',
      };
      metaParts.push(`↻ ${recLabels[item.recurrence_type] || item.recurrence_type}`);
    }
    if (item.location) metaParts.push(`📍 ${item.location}`);
    if (item.member_names && item.member_names.length) {
      metaParts.push(`👤 ${item.member_names.join(', ')}`);
    }
    node.querySelector('.cozi-item-meta').textContent = metaParts.join('  ·  ');

    // Recommendation reason
    node.querySelector('.cozi-item-reason').textContent = item.recommendation_reason;

    // Changes (for changed items)
    if (item.changes && item.changes.length) {
      const changesEl = node.querySelector('.cozi-item-changes');
      changesEl.innerHTML = '<strong>Wijzigingen:</strong> ' +
        item.changes.map(c =>
          `<span><em>${FP.esc(c.field)}:</em> "${FP.esc(c.old)}" → "${FP.esc(c.new)}"</span>`
        ).join(' · ');
      changesEl.classList.remove('hidden');
    }

    // Matched FP item with link button
    if (item.matched_fp_title) {
      const matchEl = node.querySelector('.cozi-item-match');
      const matchTypeLabels = { event: 'afspraak', series: 'reeks', meal: 'maaltijd' };
      const linkButtonHtml = item.status === 'likely_exists'
        ? `<button type="button" class="btn btn--sm btn--secondary" data-link-uid="${item.uid}" style="margin-left:0.5rem;">🔗 Koppel</button>`
        : '';
      matchEl.innerHTML =
        `Overeenkomst in FamiliePlanner: ${matchTypeLabels[item.matched_fp_type] || ''} "${item.matched_fp_title}" ${linkButtonHtml}`;
      matchEl.classList.remove('hidden');

      const linkBtn = matchEl.querySelector('[data-link-uid]');
      if (linkBtn) {
        linkBtn.addEventListener('click', (e) => {
          e.preventDefault();
          e.stopPropagation();
          openLinkModal(item);
        });
      }
    }

    return node;
  }

  function updateImportButton() {
    const count = _selected.size;
    elSelectedCount.textContent = count;
    elBtnImport.disabled = count === 0;
  }

  // ── Select helpers ────────────────────────────────────────────
  function selectGroup(predicate) {
    _items.forEach(item => {
      if (predicate(item)) {
        _selected.add(item.uid);
      }
    });
    // Sync checkboxes
    document.querySelectorAll('.cozi-item-cb').forEach(cb => {
      if (_selected.has(cb.dataset.uid)) cb.checked = true;
    });
    updateImportButton();
  }

  elBtnSelectNew?.addEventListener('click', () => {
    selectGroup(i => i.status === 'new');
  });

  elBtnSelectChanged?.addEventListener('click', () => {
    selectGroup(i => i.status === 'changed');
  });

  elBtnLinkAllLikely?.addEventListener('click', async () => {
    const likelyItems = _items.filter(i => i.status === 'likely_exists' && i.matched_fp_id && i.matched_fp_type);
    if (!likelyItems.length) return;

    elBtnLinkAllLikely.disabled = true;
    const originalLabel = elBtnLinkAllLikely.textContent;
    elBtnLinkAllLikely.textContent = 'Koppelen…';

    let linkedCount = 0;
    let failedCount = 0;

    try {
      for (const item of likelyItems) {
        try {
          await API.post('/api/cozi/link', {
            cozi_uid: item.uid,
            item_type: item.matched_fp_type,
            item_id: item.matched_fp_id,
          });
          linkedCount += 1;
        } catch (err) {
          failedCount += 1;
        }
      }

      if (failedCount === 0) {
        Toast.show(`✅ ${linkedCount} mogelijk aanwezige items gekoppeld.`, 'success');
      } else {
        Toast.show(`⚠️ ${linkedCount} gekoppeld, ${failedCount} mislukt.`, 'warning');
      }

      await loadPreview();
    } finally {
      elBtnLinkAllLikely.textContent = originalLabel;
      elBtnLinkAllLikely.disabled = _items.filter(i => i.status === 'likely_exists').length === 0;
    }
  });

  // ── Link Modal ────────────────────────────────────────────────
  function resetLinkConfirmButton() {
    if (!elBtnLinkConfirm) return;
    elBtnLinkConfirm.disabled = false;
    elBtnLinkConfirm.textContent = 'Koppel nu';
  }

  function openLinkModal(item) {
    _linkItem = item;
    resetLinkConfirmButton();
    const typeLabels = { event: 'afspraak', series: 'reeks', meal: 'maaltijd' };
    const msg = document.getElementById('link-modal-msg');
    msg.textContent = `Weet je zeker dat je deze Cozi-${typeLabels[item.event_type]} wilt koppelen aan de FamiliePlanner-${typeLabels[item.matched_fp_type]}: "${item.matched_fp_title}"?`;
    
    const modal = document.getElementById('cozi-link-modal');
    modal.classList.remove('hidden');
  }

  function closeLinkModal() {
    const modal = document.getElementById('cozi-link-modal');
    modal.classList.add('hidden');
    _linkItem = null;
    resetLinkConfirmButton();
  }

  document.getElementById('btn-link-cancel')?.addEventListener('click', closeLinkModal);

  document.getElementById('btn-link-confirm')?.addEventListener('click', async () => {
    if (!_linkItem) return;

    if (!elBtnLinkConfirm) return;
    elBtnLinkConfirm.disabled = true;
    elBtnLinkConfirm.textContent = 'Bezig…';

    try {
      await API.post('/api/cozi/link', {
        cozi_uid: _linkItem.uid,
        item_type: _linkItem.matched_fp_type,
        item_id: _linkItem.matched_fp_id,
      });
      Toast.show(`✅ Gekoppeld! "${_linkItem.matched_fp_title}" is nu aan Cozi gekoppeld.`, 'success');
      closeLinkModal();
      // Reload preview to update status
      setTimeout(() => loadPreview(), 1000);
    } catch (err) {
      Toast.show(`❌ Koppeling mislukt: ${err.message}`, 'error');
    } finally {
      resetLinkConfirmButton();
    }
  });

  // Close modal when clicking outside
  document.getElementById('cozi-link-modal')?.addEventListener('click', (e) => {
    if (e.target.id === 'cozi-link-modal') {
      closeLinkModal();
    }
  });

  // ── Import ────────────────────────────────────────────────────
  elBtnImport?.addEventListener('click', async () => {
    const selectedUids = [..._selected];
    if (!selectedUids.length) return;

    elBtnImport.disabled = true;
    elBtnImport.textContent = 'Importeren…';

    try {
      const result = await API.post('/api/cozi/import', {
        selected_uids: selectedUids,
        default_series_count: 60,
      });

      // Invalidate caches so updates are visible immediately
      const invalidatedAgenda = Cache.invalidate(/^agenda_events_/);
      const invalidatedMeals = Cache.invalidate(/^meals_/);
      const invalidatedTasks = Cache.invalidate(/^tasks_/);
      if (invalidatedAgenda || invalidatedMeals || invalidatedTasks) {
        console.log('[Cozi] Cache invalidated after import:', { invalidatedAgenda, invalidatedMeals, invalidatedTasks });
      }

      // Show result panel
      hide(elResults);
      renderImportResult(result);
      show(elImportResult);
    } catch (err) {
      Toast.show(`Importeren mislukt: ${err.message}`, 'error');
      elBtnImport.disabled = false;
      elBtnImport.innerHTML = `Importeer geselecteerde (<span id="selected-count">${selectedUids.length}</span>)`;
    }
  });

  function renderImportResult(r) {
    const newCount = r.imported_events + r.imported_series + r.imported_meals;
    const updCount = r.updated_events + r.updated_series + r.updated_meals;
    const lines = [];

    if (newCount > 0) {
      const parts = [];
      if (r.imported_events)  parts.push(`${r.imported_events} afspraak/afspraken`);
      if (r.imported_series)  parts.push(`${r.imported_series} reeks/reeksen`);
      if (r.imported_meals)   parts.push(`${r.imported_meals} maaltijd/maaltijden`);
      lines.push(`<div>✨ Nieuw geïmporteerd: ${parts.join(', ')}</div>`);
    }
    if (updCount > 0) {
      const parts = [];
      if (r.updated_events)  parts.push(`${r.updated_events} afspraak/afspraken`);
      if (r.updated_series)  parts.push(`${r.updated_series} reeks/reeksen`);
      if (r.updated_meals)   parts.push(`${r.updated_meals} maaltijd/maaltijden`);
      lines.push(`<div>✏️ Bijgewerkt: ${parts.join(', ')}</div>`);
    }
    if (newCount === 0 && updCount === 0) {
      lines.push('<div>Niets geïmporteerd (alle geselecteerde items zijn al geskipt of mislukt).</div>');
    }

    document.getElementById('import-result-details').innerHTML = lines.join('');
  }

  // ── Retry / Sync again ────────────────────────────────────────
  elBtnRetry?.addEventListener('click', loadPreview);
  elBtnSyncAgain?.addEventListener('click', () => {
    hide(elImportResult);
    loadPreview();
  });

  // ── Helpers ───────────────────────────────────────────────────
  function show(el) { el?.classList.remove('hidden'); }
  function hide(el) { el?.classList.add('hidden'); }

  // ── Init ─────────────────────────────────────────────────────
  loadPreview();
})();
