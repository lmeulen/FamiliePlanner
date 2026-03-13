/* ================================================================
   PWA Install Prompt
   Shows a custom install banner when PWA is installable
   ================================================================ */

(function() {
  let deferredPrompt = null;

  // Listen for beforeinstallprompt event
  window.addEventListener('beforeinstallprompt', (e) => {
    console.log('[PWA] Install prompt available');

    // Prevent default browser install prompt
    e.preventDefault();

    // Store the event for later use
    deferredPrompt = e;

    // Check if user has previously dismissed the prompt
    const dismissed = localStorage.getItem('pwa-install-dismissed');
    if (dismissed) {
      const dismissedDate = new Date(dismissed);
      const daysSinceDismissed = (Date.now() - dismissedDate) / (1000 * 60 * 60 * 24);

      // Show again after 7 days
      if (daysSinceDismissed < 7) {
        return;
      }
    }

    // Show custom install prompt
    showInstallPrompt();
  });

  function showInstallPrompt() {
    // Create prompt element
    const prompt = document.createElement('div');
    prompt.className = 'pwa-install-prompt';
    prompt.innerHTML = `
      <div class="pwa-install-prompt-icon">📱</div>
      <div class="pwa-install-prompt-text">
        <div class="pwa-install-prompt-title">Installeer FamiliePlanner</div>
        <div class="pwa-install-prompt-desc">Gebruik de app als native app op je telefoon</div>
      </div>
      <div class="pwa-install-prompt-actions">
        <button class="btn btn--secondary btn--sm" id="pwa-dismiss">Later</button>
        <button class="btn btn--primary btn--sm" id="pwa-install">Installeren</button>
      </div>
    `;

    document.body.appendChild(prompt);

    // Handle install button
    document.getElementById('pwa-install').addEventListener('click', async () => {
      if (!deferredPrompt) return;

      // Show browser's install prompt
      deferredPrompt.prompt();

      // Wait for user choice
      const { outcome } = await deferredPrompt.userChoice;
      console.log('[PWA] User choice:', outcome);

      if (outcome === 'accepted') {
        console.log('[PWA] User accepted install');
        if (window.Toast) {
          Toast.show('App wordt geïnstalleerd...', 'success');
        }
      }

      // Clear the prompt
      deferredPrompt = null;
      prompt.remove();
    });

    // Handle dismiss button
    document.getElementById('pwa-dismiss').addEventListener('click', () => {
      localStorage.setItem('pwa-install-dismissed', new Date().toISOString());
      prompt.remove();
    });
  }

  // Listen for successful installation
  window.addEventListener('appinstalled', () => {
    console.log('[PWA] App installed successfully');
    if (window.Toast) {
      Toast.show('App succesvol geïnstalleerd! 🎉', 'success');
    }
    deferredPrompt = null;
  });

  // Detect if running as installed PWA
  if (window.matchMedia('(display-mode: standalone)').matches ||
      window.navigator.standalone === true) {
    console.log('[PWA] Running as installed app');
  }
})();
