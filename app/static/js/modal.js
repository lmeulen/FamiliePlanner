/* ================================================================
   modal.js – Generic modal / bottom-sheet controller
   Usage:
     Modal.open(htmlString | templateId);   // open with content
     Modal.close();
   ================================================================ */
window.Modal = (() => {
  const overlay = document.getElementById('modal-overlay');
  const box     = document.getElementById('modal-box');
  const content = document.getElementById('modal-content');
  const closeBtn = document.getElementById('modal-close');

  function open(source) {
    if (typeof source === 'string' && source.startsWith('tpl-')) {
      const tpl = document.getElementById(source);
      content.innerHTML = '';
      content.appendChild(tpl.content.cloneNode(true));
    } else {
      content.innerHTML = source;
    }
    overlay.classList.remove('hidden');
    // Focus first input for accessibility
    const first = content.querySelector('input,select,textarea');
    if (first) setTimeout(() => first.focus(), 100);
  }

  function close() {
    overlay.classList.add('hidden');
    content.innerHTML = '';
  }

  closeBtn.addEventListener('click', close);
  overlay.addEventListener('click', e => { if (e.target === overlay) close(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });

  return { open, close, content: () => content };
})();
