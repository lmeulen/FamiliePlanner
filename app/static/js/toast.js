/* ================================================================
   toast.js – Lightweight toast notifications
   Usage: Toast.show('Opgeslagen!');  Toast.show('Fout!', 'error');
   ================================================================ */
window.Toast = (() => {
  const container = document.getElementById('toast-container');

  function show(message, type = 'success', duration = 3000) {
    const el = document.createElement('div');
    el.className = `toast toast--${type}`;
    el.textContent = message;
    container.appendChild(el);

    setTimeout(() => {
      el.classList.add('leaving');
      el.addEventListener('animationend', () => el.remove());
    }, duration);
  }

  return { show };
})();
