/* ================================================================
   mobile-menu.js – Mobile hamburger menu toggle + active states
   ================================================================ */
(function() {
  const toggle = document.getElementById('mobile-menu-toggle');
  const overlay = document.getElementById('mobile-menu-overlay');
  const close = document.getElementById('mobile-menu-close');

  if (!toggle || !overlay || !close) return;

  function openMenu() {
    overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function closeMenu() {
    overlay.classList.remove('active');
    document.body.style.overflow = '';
  }

  toggle.addEventListener('click', openMenu);
  close.addEventListener('click', closeMenu);

  // Close on overlay click (outside menu)
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) {
      closeMenu();
    }
  });

  // Close on menu item click
  overlay.querySelectorAll('.mobile-menu-item').forEach(item => {
    item.addEventListener('click', closeMenu);
  });

  // Set active state based on current URL
  const currentPath = window.location.pathname;

  // Mobile top nav items
  document.querySelectorAll('.mobile-nav-item').forEach(item => {
    const href = item.getAttribute('href');
    if (href && currentPath === href) {
      item.classList.add('active');
    }
  });

  // Mobile menu items
  overlay.querySelectorAll('.mobile-menu-item').forEach(item => {
    const href = item.getAttribute('href');
    if (href && currentPath === href) {
      item.classList.add('active');
    }
  });
})();
