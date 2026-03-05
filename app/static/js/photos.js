/* global FP, API */
(function () {
const grid      = document.getElementById('photos-grid');
const countEl   = document.getElementById('photo-count');
const emptyEl   = document.getElementById('photos-empty');
const dropZone  = document.getElementById('drop-zone');
const fileInput = document.getElementById('photo-file-input');
const progress  = document.getElementById('upload-progress');
const statusEl  = document.getElementById('upload-status');

// ── Delete modal ──────────────────────────────────────────────────
const deleteOverlay = document.getElementById('delete-modal-overlay');
const deleteNameEl  = document.getElementById('delete-modal-name');
const confirmBtn    = document.getElementById('delete-confirm-btn');
const cancelBtn     = document.getElementById('delete-cancel-btn');
let pendingDeleteId = null;

function openDeleteModal(id, name) {
  pendingDeleteId = id;
  deleteNameEl.textContent = name || 'Onbekend';
  deleteOverlay.classList.remove('hidden');
}
cancelBtn.addEventListener('click', () => { deleteOverlay.classList.add('hidden'); pendingDeleteId = null; });
deleteOverlay.addEventListener('click', e => { if (e.target === deleteOverlay) cancelBtn.click(); });
confirmBtn.addEventListener('click', async () => {
  if (!pendingDeleteId) return;
  deleteOverlay.classList.add('hidden');
  await API.delete(`/api/photos/${pendingDeleteId}`);
  await loadPhotos();
  pendingDeleteId = null;
});

// ── Render ────────────────────────────────────────────────────────
function renderPhotos(photos) {
  countEl.textContent = photos.length;
  if (!photos.length) {
    grid.innerHTML = '';
    emptyEl.classList.remove('hidden');
    return;
  }
  emptyEl.classList.add('hidden');
  grid.innerHTML = photos.map(p => `
    <div class="photo-card" data-id="${p.id}">
      <div class="photo-card-img-wrap">
        <img src="${FP.esc(p.url)}" alt="${FP.esc(p.display_name || p.filename)}" loading="lazy" />
      </div>
      <div class="photo-card-footer">
        <span class="photo-card-name" title="${FP.esc(p.display_name || p.filename)}">${FP.esc(p.display_name || p.filename)}</span>
        <button class="btn btn--icon btn--danger-ghost photo-delete-btn" data-id="${p.id}" data-name="${FP.esc(p.display_name || p.filename)}" title="Verwijderen" aria-label="Verwijderen">🗑️</button>
      </div>
    </div>
  `).join('');

  grid.querySelectorAll('.photo-delete-btn').forEach(btn => {
    btn.addEventListener('click', () => openDeleteModal(+btn.dataset.id, btn.dataset.name));
  });
}

async function loadPhotos() {
  const photos = await API.get('/api/photos/');
  renderPhotos(photos || []);
}

// ── Upload ────────────────────────────────────────────────────────
const MAX_BYTES = 10 * 1024 * 1024;
const ALLOWED_MIME = new Set(['image/jpeg', 'image/png']);

function validateFile(file) {
  if (!ALLOWED_MIME.has(file.type)) return 'Alleen JPG en PNG bestanden zijn toegestaan.';
  if (file.size > MAX_BYTES) return `Bestand te groot (max 10 MB, dit bestand is ${(file.size / 1024 / 1024).toFixed(1)} MB).`;
  return null;
}

async function uploadFile(file) {
  const err = validateFile(file);
  if (err) { statusEl.textContent = err; progress.classList.remove('hidden'); return; }
  progress.classList.remove('hidden');
  statusEl.textContent = `Uploaden: ${file.name}…`;
  const form = new FormData();
  form.append('file', file);
  try {
    const result = await API.post('/api/photos/', form);
    if (result) {
      statusEl.textContent = 'Geüpload!';
      fileInput.value = '';
      await loadPhotos();
    }
  } catch (err) {
    statusEl.textContent = `Fout: ${err.message}`;
  } finally {
    progress.classList.remove('hidden');
  }
}

dropZone.addEventListener('click', () => fileInput.click());
dropZone.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') fileInput.click(); });
fileInput.addEventListener('change', () => { if (fileInput.files[0]) uploadFile(fileInput.files[0]); });

dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault();
  dropZone.classList.remove('drag-over');
  const file = e.dataTransfer.files[0];
  if (file) uploadFile(file);
});

// ── Init ──────────────────────────────────────────────────────────
loadPhotos();
}());
