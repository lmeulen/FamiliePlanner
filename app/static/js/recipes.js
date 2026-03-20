/* global API, Modal, Toast, FP */
(function () {
  let recipes = [];
  let currentPage = 1;
  let totalPages = 1;
  let searchQuery = '';
  let categoryFilter = '';
  let tagFilter = '';
  let editSlug = null;

  // ── Duration utilities ──────────────────────────────────────
  function parseDuration(iso8601) {
    if (!iso8601) return null;
    // PT30M → "30 min", PT1H30M → "1u 30m", PT45S → "45 sec"
    const match = iso8601.match(/PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?/);
    if (!match) return null;
    const hours = parseInt(match[1] || 0);
    const minutes = parseInt(match[2] || 0);
    const seconds = parseInt(match[3] || 0);

    if (hours > 0 && minutes > 0) return `${hours}u ${minutes}m`;
    if (hours > 0) return `${hours}u`;
    if (minutes > 0) return `${minutes} min`;
    if (seconds > 0) return `${seconds} sec`;
    return null;
  }

  function toDuration(minutes) {
    if (!minutes || minutes === 0) return null;
    const hrs = Math.floor(minutes / 60);
    const mins = minutes % 60;
    let str = 'PT';
    if (hrs > 0) str += `${hrs}H`;
    if (mins > 0) str += `${mins}M`;
    return str === 'PT' ? null : str;
  }

  // ── Load recipes ────────────────────────────────────────────
  async function loadRecipes() {
    const grid = document.getElementById('recipes-grid');
    const emptyState = document.getElementById('recipes-empty');
    const configError = document.getElementById('config-error');
    const pagination = document.getElementById('pagination');

    try {
      // Hide states
      emptyState.classList.add('hidden');
      configError.classList.add('hidden');

      // Build query params
      const params = new URLSearchParams({
        page: currentPage,
        per_page: 50,
      });
      if (searchQuery) params.set('search', searchQuery);
      if (categoryFilter) params.set('categories', categoryFilter);
      if (tagFilter) params.set('tags', tagFilter);

      const data = await API.get(`/api/recipes/?${params}`);
      recipes = data.items || [];
      totalPages = data.total_pages || 1;

      if (recipes.length === 0) {
        emptyState.classList.remove('hidden');
        pagination.classList.add('hidden');
      } else {
        pagination.classList.remove('hidden');
      }

      renderGrid();
      updatePagination();
    } catch (err) {
      if (err.status === 503) {
        // Config error
        configError.classList.remove('hidden');
        grid.innerHTML = '';
        pagination.classList.add('hidden');
      } else {
        Toast.show('Fout bij laden recepten: ' + (err.detail || err.message), 'error');
        grid.innerHTML = '';
      }
    }
  }

  // ── Render grid ─────────────────────────────────────────────
  function renderGrid() {
    const grid = document.getElementById('recipes-grid');

    if (recipes.length === 0) {
      grid.innerHTML = '';
      return;
    }

    grid.innerHTML = recipes.map(recipe => {
      const categories = (recipe.recipeCategory || []).slice(0, 3).map(cat =>
        `<span style="padding: 0.25rem 0.6rem; background: var(--accent-bg); color: var(--accent); border-radius: 4px; font-size: 0.8rem;">${FP.esc(cat)}</span>`
      ).join('');

      const tags = (recipe.tags || []).slice(0, 3).map(tag =>
        `<span style="padding: 0.25rem 0.6rem; background: var(--bg-secondary); color: var(--text-muted); border-radius: 4px; font-size: 0.8rem;">#${FP.esc(tag)}</span>`
      ).join('');

      const description = recipe.description ? FP.esc(recipe.description.substring(0, 150)) + (recipe.description.length > 150 ? '...' : '') : '';

      const rating = recipe.rating ? '⭐'.repeat(Math.round(recipe.rating)) : '';

      return `<div class="card recipe-card" data-slug="${FP.esc(recipe.slug)}" style="cursor: pointer; display: flex; flex-direction: row; align-items: center; padding: 1rem 1.25rem; margin-bottom: 0.75rem; border-radius: 8px; transition: background 0.15s;">
        <div style="flex: 1; min-width: 0;">
          <h4 style="font-size: 1.1rem; margin: 0 0 0.4rem 0; font-weight: 600;">${FP.esc(recipe.name)} ${rating ? `<span style="margin-left: 0.5rem; font-size: 0.9rem;">${rating}</span>` : ''}</h4>
          ${description ? `<p style="font-size: 0.9rem; color: var(--text-muted); margin: 0 0 0.5rem 0;">${description}</p>` : ''}
          <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center;">
            ${categories}
            ${tags}
          </div>
        </div>
      </div>`;
    }).join('');

    grid.querySelectorAll('.recipe-card').forEach(card => {
      card.addEventListener('click', () => openRecipeDetail(card.dataset.slug));
    });
  }

  // ── Update pagination ───────────────────────────────────────
  function updatePagination() {
    const pageInfo = document.getElementById('page-info');
    const prevBtn = document.getElementById('prev-page');
    const nextBtn = document.getElementById('next-page');

    pageInfo.textContent = `Pagina ${currentPage} van ${totalPages}`;
    prevBtn.disabled = currentPage === 1;
    nextBtn.disabled = currentPage === totalPages;
  }

  // ── Open recipe detail ──────────────────────────────────────
  async function openRecipeDetail(slug) {
    try {
      const recipe = await API.get(`/api/recipes/${slug}`);

      Modal.open('tpl-recipe-detail');

      // Populate detail modal
      document.getElementById('recipe-name').textContent = recipe.name;
      document.getElementById('recipe-description').textContent = recipe.description || '';

      const image = document.getElementById('recipe-image');
      if (recipe.image) {
        image.src = recipe.image;
        image.style.display = 'block';
      } else {
        image.style.display = 'none';
      }

      // Recipe info
      const prepTime = parseDuration(recipe.prepTime);
      const cookTime = parseDuration(recipe.cookTime);
      const recipeInfo = document.querySelector('.recipe-info');
      let infoHtml = '';
      if (prepTime) infoHtml += `<span>⏱️ Bereidingstijd: ${prepTime}</span>`;
      if (cookTime) infoHtml += `<span>🔥 Kooktijd: ${cookTime}</span>`;
      if (recipe.recipeYield) infoHtml += `<span>🍽️ ${FP.esc(recipe.recipeYield)}</span>`;
      if (recipe.rating) infoHtml += `<span>${'⭐'.repeat(recipe.rating)}</span>`;
      recipeInfo.innerHTML = infoHtml;

      // Categories and tags
      const categoriesEl = document.getElementById('recipe-categories');
      categoriesEl.innerHTML = (recipe.recipeCategory || []).map(cat =>
        `<span style="padding: 0.25rem 0.75rem; background: var(--accent-bg); color: var(--accent); border-radius: 6px; font-size: 0.85rem;">${FP.esc(cat)}</span>`
      ).join('');

      const tagsEl = document.getElementById('recipe-tags');
      tagsEl.innerHTML = (recipe.tags || []).map(tag =>
        `<span style="padding: 0.25rem 0.75rem; background: var(--bg-secondary); color: var(--text-muted); border-radius: 6px; font-size: 0.85rem;">#${FP.esc(tag)}</span>`
      ).join('');

      // Ingredients
      const ingredientsList = document.getElementById('ingredients-list');
      ingredientsList.innerHTML = (recipe.recipeIngredient || []).map(ing => {
        const display = ing.display || `${ing.quantity || ''} ${ing.unit || ''} ${ing.food || ''}`.trim();
        return `<li style="padding: 0.35rem 0; border-bottom: 1px solid var(--border);">${FP.esc(display)}</li>`;
      }).join('');

      // Instructions
      const instructionsList = document.getElementById('instructions-list');
      instructionsList.innerHTML = (recipe.recipeInstructions || []).map(inst => {
        const title = inst.title ? `<strong>${FP.esc(inst.title)}:</strong> ` : '';
        return `<li style="padding: 0.5rem 0; line-height: 1.6;">${title}${FP.esc(inst.text)}</li>`;
      }).join('');

      // Original URL link
      const originalLink = document.getElementById('btn-view-original');
      if (recipe.orgURL) {
        originalLink.href = recipe.orgURL;
        originalLink.style.display = '';
      } else {
        originalLink.style.display = 'none';
      }

      // Edit and delete buttons removed - recipes are read-only
      // document.getElementById('btn-edit-recipe').onclick = () => {
      //   Modal.close();
      //   openRecipeForm(slug);
      // };
      // document.getElementById('btn-delete-recipe').onclick = () => deleteRecipe(slug);

    } catch (err) {
      Toast.show('Fout bij laden recept: ' + (err.detail || err.message), 'error');
    }
  }

  // ── Open recipe form (create/edit) ──────────────────────────
  async function openRecipeForm(slug = null) {
    editSlug = slug;
    Modal.open('tpl-recipe-form');

    const form = document.getElementById('recipe-form');
    const title = document.getElementById('recipe-form-title');

    if (slug) {
      title.textContent = 'Recept bewerken';

      try {
        const recipe = await API.get(`/api/recipes/${slug}`);

        form.elements.name.value = recipe.name || '';
        form.elements.description.value = recipe.description || '';

        const prepMinutes = parseDuration(recipe.prepTime);
        const cookMinutes = parseDuration(recipe.cookTime);
        form.elements.prepTime.value = prepMinutes ? parseInt(prepMinutes) : '';
        form.elements.cookTime.value = cookMinutes ? parseInt(cookMinutes) : '';

        form.elements.recipeYield.value = recipe.recipeYield || '';
        form.elements.categories.value = (recipe.recipeCategory || []).join(', ');
        form.elements.tags.value = (recipe.tags || []).join(', ');

        // Ingredients - one per line
        form.elements.ingredients.value = (recipe.recipeIngredient || []).map(ing => ing.display).join('\n');

        // Instructions - one per line
        form.elements.instructions.value = (recipe.recipeInstructions || []).map(inst => inst.text).join('\n\n');

        form.elements.orgURL.value = recipe.orgURL || '';
      } catch (err) {
        Toast.show('Fout bij laden recept: ' + (err.detail || err.message), 'error');
      }
    } else {
      title.textContent = 'Recept toevoegen';
      form.reset();
    }

    // Wire up form submit
    form.onsubmit = async (e) => {
      e.preventDefault();
      await saveRecipe();
    };
  }

  // ── Save recipe ─────────────────────────────────────────────
  async function saveRecipe() {
    const form = document.getElementById('recipe-form');

    const name = form.elements.name.value.trim();
    if (!name) {
      Toast.show('Naam is verplicht', 'error');
      return;
    }

    const prepMinutes = parseInt(form.elements.prepTime.value) || 0;
    const cookMinutes = parseInt(form.elements.cookTime.value) || 0;

    const categories = form.elements.categories.value.split(',').map(c => c.trim()).filter(Boolean);
    const tags = form.elements.tags.value.split(',').map(t => t.trim()).filter(Boolean);

    // Parse ingredients
    const ingredientsText = form.elements.ingredients.value.trim();
    const recipeIngredient = ingredientsText
      .split('\n')
      .map(line => line.trim())
      .filter(Boolean)
      .map(line => ({ display: line }));

    // Parse instructions
    const instructionsText = form.elements.instructions.value.trim();
    const recipeInstructions = instructionsText
      .split('\n\n')
      .map(text => text.trim())
      .filter(Boolean)
      .map(text => ({ text }));

    const payload = {
      name,
      description: form.elements.description.value.trim(),
      prepTime: toDuration(prepMinutes),
      cookTime: toDuration(cookMinutes),
      recipeYield: form.elements.recipeYield.value.trim(),
      recipeCategory: categories,
      tags: tags,
      recipeIngredient,
      recipeInstructions,
      orgURL: form.elements.orgURL.value.trim(),
    };

    try {
      let slug = editSlug;

      if (editSlug) {
        // Update existing recipe
        await API.put(`/api/recipes/${editSlug}`, payload);
        Toast.show('Recept bijgewerkt', 'success');
      } else {
        // Create new recipe
        const stub = await API.post('/api/recipes/', { name });
        slug = stub.slug;
        await API.put(`/api/recipes/${slug}`, payload);
        Toast.show('Recept aangemaakt', 'success');
      }

      // Handle image upload if present
      const imageFile = form.elements.image.files[0];
      if (imageFile && slug) {
        const formData = new FormData();
        formData.append('file', imageFile);

        await fetch(`/api/recipes/${slug}/image`, {
          method: 'PUT',
          headers: {
            'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]')?.content,
          },
          body: formData,
        });
      }

      Modal.close();
      await loadRecipes();
    } catch (err) {
      Toast.show('Fout bij opslaan: ' + (err.detail || err.message), 'error');
    }
  }

  // ── Delete recipe ───────────────────────────────────────────
  async function deleteRecipe(slug) {
    if (!confirm('Weet je zeker dat je dit recept wilt verwijderen?')) {
      return;
    }

    try {
      await API.delete(`/api/recipes/${slug}`);
      Toast.show('Recept verwijderd', 'success');
      Modal.close();
      await loadRecipes();
    } catch (err) {
      Toast.show('Fout bij verwijderen: ' + (err.detail || err.message), 'error');
    }
  }

  // ── Load categories and tags for filters ────────────────────
  async function loadFilters() {
    try {
      const categories = await API.get('/api/recipes/categories/all');
      const categorySelect = document.getElementById('category-filter');
      categorySelect.innerHTML = '<option value="">Alle categorieën</option>' +
        categories.map(cat => `<option value="${FP.esc(cat.slug)}">${FP.esc(cat.name)}</option>`).join('');

      const tags = await API.get('/api/recipes/tags/all');
      const tagSelect = document.getElementById('tag-filter');
      tagSelect.innerHTML = '<option value="">Alle tags</option>' +
        tags.map(tag => `<option value="${FP.esc(tag.slug)}">${FP.esc(tag.name)}</option>`).join('');
    } catch (err) {
      // Silently fail if filters can't be loaded
      console.warn('Could not load filters:', err);
    }
  }

  // ── Init ────────────────────────────────────────────────────
  function init() {
    // Search
    const searchInput = document.getElementById('recipe-search');
    searchInput.addEventListener('input', (e) => {
      searchQuery = e.target.value.trim();
      currentPage = 1;
      loadRecipes();
    });

    // Filters
    const categorySelect = document.getElementById('category-filter');
    categorySelect.addEventListener('change', (e) => {
      categoryFilter = e.target.value;
      currentPage = 1;
      loadRecipes();
    });

    const tagSelect = document.getElementById('tag-filter');
    tagSelect.addEventListener('change', (e) => {
      tagFilter = e.target.value;
      currentPage = 1;
      loadRecipes();
    });

    // Pagination
    document.getElementById('prev-page').addEventListener('click', () => {
      if (currentPage > 1) {
        currentPage--;
        loadRecipes();
      }
    });

    document.getElementById('next-page').addEventListener('click', () => {
      if (currentPage < totalPages) {
        currentPage++;
        loadRecipes();
      }
    });

    // Add recipe button disabled - recipes are read-only
    // const addBtn = document.getElementById('btn-add-recipe');
    // if (addBtn) {
    //   addBtn.addEventListener('click', () => openRecipeForm());
    // }

    // Initial load
    loadRecipes();
    loadFilters();
  }

  document.addEventListener('DOMContentLoaded', init);
})();
