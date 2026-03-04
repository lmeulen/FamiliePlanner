/* ================================================================
   theme.js – Light / dark theme toggle with localStorage persistence
   ================================================================ */
(function () {
  const KEY = 'fp-theme';
  const html = document.documentElement;
  const btn  = document.getElementById('theme-toggle');
  const icon = document.getElementById('theme-icon');

  function applyTheme(t) {
    html.setAttribute('data-theme', t);
    icon.textContent = t === 'dark' ? '☀️' : '🌙';
    localStorage.setItem(KEY, t);
  }

  // Apply saved or system preference on load
  const saved = localStorage.getItem(KEY);
  if (saved) {
    applyTheme(saved);
  } else if (window.matchMedia?.('(prefers-color-scheme: dark)').matches) {
    applyTheme('dark');
  }

  btn?.addEventListener('click', () => {
    applyTheme(html.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
  });

  // Sync across tabs
  window.addEventListener('storage', e => {
    if (e.key === KEY && e.newValue) applyTheme(e.newValue);
  });
})();
