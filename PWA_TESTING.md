# PWA Testing Guide

## ✅ PWA Implementation Complete!

FamiliePlanner is now a fully functional Progressive Web App with offline support.

---

## 📱 Testing the PWA Installation

### On Android (Chrome/Edge)

1. **Access the app on mobile:**
   - Open Chrome or Edge browser
   - Navigate to your FamiliePlanner URL (e.g., `http://your-server:8000`)

2. **Install the app:**
   - You should see a custom install banner at the bottom
   - Tap "Installeren" to install
   - OR tap the browser menu (⋮) → "App installeren" / "Add to Home Screen"

3. **Verify installation:**
   - App icon appears on home screen with 🏠 emoji
   - Tap icon to open in standalone mode (no browser chrome)
   - App shortcuts work: long-press icon → see Agenda, Taken, Maaltijden shortcuts

### On iOS (Safari)

1. **Access the app:**
   - Open Safari browser
   - Navigate to your FamiliePlanner URL

2. **Install to Home Screen:**
   - Tap the Share button (square with arrow pointing up)
   - Scroll and tap "Add to Home Screen"
   - Edit name if desired → tap "Add"

3. **Verify installation:**
   - App icon appears on home screen
   - Tap to open in fullscreen mode
   - Status bar color matches theme (#6C5CE7)

### On Desktop (Chrome/Edge)

1. **Access the app:**
   - Open Chrome or Edge
   - Navigate to your FamiliePlanner URL

2. **Install the app:**
   - Look for install icon (⊕) in address bar
   - Click it and confirm installation
   - OR go to Settings → "Install FamiliePlanner..."

3. **Verify installation:**
   - App opens in separate window (like a desktop app)
   - App appears in Start Menu / Applications folder
   - Can pin to taskbar

---

## 🔌 Testing Offline Functionality

### Test Offline Mode

1. **Load the app while online:**
   - Visit a few pages (Dashboard, Agenda, Tasks, Meals)
   - This caches the pages and data

2. **Go offline:**
   - **Mobile:** Enable Airplane Mode
   - **Desktop:** DevTools → Network tab → Check "Offline"

3. **Verify offline behavior:**
   - Navigate between pages → Should work (cached)
   - View previously loaded data → Should display
   - Try to add new item → Should show offline message
   - Toast notification: "Offline modus - sommige functies niet beschikbaar"

4. **Return online:**
   - Disable Airplane Mode / Offline checkbox
   - Toast notification: "Verbinding hersteld"
   - Try adding/editing → Should work normally

### Test Cache Updates

1. **Check service worker:**
   - Open DevTools → Application tab → Service Workers
   - Should see "activated and running"
   - Cache Storage → Should see 3 caches:
     - `familieplanner-static-v1` (CSS, JS files)
     - `familieplanner-dynamic-v1` (HTML pages)
     - `familieplanner-api-v1` (API responses)

2. **Test update mechanism:**
   - Make a code change (e.g., edit CSS)
   - Refresh page
   - Should see toast: "Nieuwe versie beschikbaar! Ververs de pagina."

---

## 🎯 Testing PWA Features

### App Shortcuts (Android/Desktop)

1. **Android:** Long-press app icon
2. **Desktop:** Right-click app icon in taskbar
3. **Verify shortcuts:**
   - 📅 Agenda → Opens `/agenda`
   - ✅ Taken → Opens `/taken`
   - 🍽️ Maaltijden → Opens `/maaltijden`

### Standalone Mode Detection

1. **Open browser DevTools console**
2. **Check for logs:**
   ```
   [PWA] Service Worker registered: /static/
   [PWA] Running in standalone mode
   ```

3. **Verify UI adjustments:**
   - Safe area padding on notched phones
   - No browser chrome visible
   - Status bar color matches theme

### Install Prompt Behavior

1. **First visit (not installed):**
   - Should see custom install banner after page load
   - Can dismiss with "Later"

2. **After dismissal:**
   - Prompt won't show again for 7 days
   - Can manually clear: `localStorage.removeItem('pwa-install-dismissed')`

3. **After installation:**
   - No install prompt (already installed)
   - Console: `[PWA] Running as installed app`

---

## 🐛 Debugging PWA Issues

### Check Service Worker Status

**Chrome/Edge DevTools:**
```
Application → Service Workers
- Should show "activated and running"
- Check for errors in console
```

**View cached resources:**
```
Application → Cache Storage → Expand caches
- familieplanner-static-v1: CSS, JS files
- familieplanner-dynamic-v1: HTML pages
- familieplanner-api-v1: API responses
```

### Force Update Service Worker

1. **DevTools → Application → Service Workers**
2. **Check "Update on reload"**
3. **Refresh page**
4. **OR click "Unregister" then refresh**

### Clear All Caches

**Via DevTools:**
```
Application → Storage → Clear site data
```

**Via Code:**
```javascript
// In browser console
caches.keys().then(names => {
  names.forEach(name => caches.delete(name));
});
navigator.serviceWorker.getRegistrations().then(regs => {
  regs.forEach(reg => reg.unregister());
});
location.reload();
```

### Common Issues

**Issue:** Service worker not registering
- **Fix:** Check browser console for errors
- **Fix:** Ensure app is served over HTTPS (or localhost)
- **Fix:** Check `/static/sw.js` is accessible

**Issue:** Install prompt not showing
- **Fix:** Check browser supports PWA (Chrome, Edge, Safari)
- **Fix:** Verify `manifest.json` is valid
- **Fix:** Clear `localStorage` item: `pwa-install-dismissed`

**Issue:** Offline mode not working
- **Fix:** Visit pages while online first (to cache them)
- **Fix:** Check service worker is activated
- **Fix:** Check cache strategy in DevTools

---

## 📊 PWA Metrics

### Lighthouse Audit

Run Chrome Lighthouse to verify PWA quality:

1. **DevTools → Lighthouse tab**
2. **Select "Progressive Web App"**
3. **Click "Analyze page load"**

**Expected scores:**
- ✅ Installable: Yes
- ✅ PWA Optimized: Yes
- ✅ Offline functionality: Yes
- ✅ Service worker registered: Yes
- ✅ Manifest valid: Yes

---

## 🚀 Next Steps (Future Enhancements)

### Planned PWA Features:

1. **Background Sync:**
   - Queue offline changes
   - Auto-sync when connection restored

2. **Push Notifications:**
   - Reminders for upcoming events/tasks
   - Daily digest notifications

3. **Share Target:**
   - Share photos/links to FamiliePlanner from other apps

4. **Periodic Background Sync:**
   - Auto-refresh data in background
   - Update calendar/tasks while app is closed

---

## 📝 Technical Details

### Cache Strategy Summary:

| Resource Type | Strategy | Purpose |
|--------------|----------|---------|
| API calls (`/api/*`) | Network First | Fresh data when online, cached fallback |
| Static assets (`/static/*`) | Cache First | Fast loading, network fallback |
| HTML pages | Network First | Fresh content, cached fallback |
| Other requests | Network Only | No caching |

### Cache Versioning:

- **Version:** `v1` (defined in `sw.js`)
- **Update process:** Change version → old caches deleted → new caches created
- **Manual update:** Users notified with toast message

### Browser Support:

| Browser | Installation | Offline | Shortcuts |
|---------|-------------|---------|-----------|
| Chrome (Android) | ✅ | ✅ | ✅ |
| Chrome (Desktop) | ✅ | ✅ | ✅ |
| Edge | ✅ | ✅ | ✅ |
| Safari (iOS 14+) | ✅ | ✅ | ❌ |
| Firefox | ⚠️ (limited) | ✅ | ❌ |

---

**Enjoy your new Progressive Web App! 🎉**

For questions or issues, check the browser console for PWA-related logs.
