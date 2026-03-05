/* ================================================================
   family.js – Family members management page
   ================================================================ */
(function () {
  let members = [];
  let editId  = null;

  async function loadMembers() {
    members = await FP.loadMembers();
    render();
  }

  function render() {
    const grid = document.getElementById('family-list');
    if (!members.length) {
      grid.innerHTML = '<p class="empty-state">Geen gezinsleden. Voeg de eerste toe! 👨‍👩‍👧‍👦</p>';
      return;
    }

    grid.innerHTML = members.map(m => `
      <div class="family-card" data-id="${m.id}" style="border-color:${m.color}20">
        <div class="family-color-dot" style="background:${m.color}"></div>
        <div class="family-avatar" style="background:${m.color}22">${m.avatar}</div>
        <div class="family-name">${FP.esc(m.name)}</div>
      </div>`).join('');

    grid.querySelectorAll('.family-card').forEach(card => {
      card.addEventListener('click', () => openMemberForm(parseInt(card.dataset.id)));
    });
  }

  function openMemberForm(id = null) {
    editId = id;
    Modal.open('tpl-member-form');
    const form   = document.getElementById('member-form');
    const title  = document.getElementById('member-form-title');
    const delBtn = document.getElementById('btn-delete-member');

    if (id) {
      title.textContent = 'Gezinslid bewerken';
      delBtn.classList.remove('hidden');
      const m = members.find(x => x.id === id);
      if (m) {
        form.name.value   = m.name;
        form.color.value  = m.color;
        form.avatar.value = m.avatar;
      }
    } else {
      title.textContent = 'Gezinslid toevoegen';
      delBtn.classList.add('hidden');
    }

    form.addEventListener('submit', async e => {
      e.preventDefault();
      const name   = form.name.value.trim();
      const avatar = form.avatar.value.trim();
      if (!name) { form.name.focus(); return; }
      if (!avatar) { form.avatar.focus(); return; }
      const data = { name, color: form.color.value, avatar };
      try {
        if (editId) {
          await API.put(`/api/family/${editId}`, data);
          Toast.show('Bijgewerkt!');
        } else {
          await API.post('/api/family/', data);
          Toast.show('Gezinslid toegevoegd!');
        }
        Modal.close();
        loadMembers();
      } catch (err) { Toast.show(err.message || 'Fout', 'error'); }
    }, { once: true });

    delBtn.addEventListener('click', async () => {
      if (!confirm('Gezinslid verwijderen? Alle gekoppelde items worden losgekoppeld.')) return;
      try {
        await API.delete(`/api/family/${editId}`);
        Toast.show('Verwijderd', 'warning');
        Modal.close();
        loadMembers();
      } catch { Toast.show('Fout', 'error'); }
    }, { once: true });
  }

  async function init() {
    document.getElementById('btn-add-member')?.addEventListener('click', () => openMemberForm());
    await loadMembers();
  }

  document.addEventListener('DOMContentLoaded', init);
})();
