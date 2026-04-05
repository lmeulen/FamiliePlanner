# Android APK Build Guide

Complete guide for building and distributing the FamiliePlanner Android APK.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Initial Setup](#initial-setup)
4. [Building the APK](#building-the-apk)
5. [Distribution](#distribution)
6. [Updating](#updating)
7. [Troubleshooting](#troubleshooting)

## Overview

FamiliePlanner uses **Trusted Web Activities (TWA)** to package the PWA as an Android APK. This provides:

✅ **Native app experience** - No browser chrome, full-screen
✅ **Auto-updates** - Web changes deploy instantly, no APK rebuild needed
✅ **Small size** - 15-25 MB (PWA wrapper only, content from server)
✅ **Offline support** - Full IndexedDB caching for all modules
✅ **App shortcuts** - Quick access to Agenda, Tasks, Grocery
✅ **No Play Store required** - Direct distribution to family

## Prerequisites

### System Requirements

- **Operating System**: Linux, macOS, or Windows with WSL
- **Node.js**: Version 16 or higher
- **Java JDK**: Version 11 or higher
- **npm**: Comes with Node.js

### FamiliePlanner Requirements

- **HTTPS server**: Valid SSL certificate (Let's Encrypt recommended)
- **Domain name**: Fully qualified domain (e.g., `familieplanner.example.com`)
- **Deployed app**: FamiliePlanner running on HTTPS

### Optional Tools

- **ImageMagick**: For icon generation (can use pre-generated icons)
- **Android Debug Bridge (ADB)**: For installing via USB

## Initial Setup

### Step 1: Install Prerequisites

#### Install Node.js

```bash
# Ubuntu/Debian
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# macOS
brew install node

# Windows (PowerShell as Admin)
choco install nodejs

# Verify
node --version  # Should be 16+
npm --version
```

#### Install Java JDK

```bash
# Ubuntu/Debian
sudo apt-get install openjdk-11-jdk

# macOS
brew install openjdk@11

# Windows
# Download from https://adoptium.net/

# Verify
java -version  # Should be 11+
```

#### Install Bubblewrap CLI

```bash
# Install globally
npm install -g @bubblewrap/cli

# Verify
bubblewrap --version
```

#### Install ImageMagick (Optional)

```bash
# Ubuntu/Debian
sudo apt-get install imagemagick

# macOS
brew install imagemagick

# Windows
# Download from https://imagemagick.org/
```

### Step 2: Deploy to HTTPS

Before building the APK, deploy FamiliePlanner to your HTTPS server:

```bash
# From project root
cd /path/to/FamiliePlanner

# Configure environment
cp .env.example .env
# Edit .env with your domain and credentials

# Deploy with Docker
docker-compose -f docker-compose.production.yml up -d

# Or follow the HTTPS setup guide
# See: docs/HTTPS_SETUP.md
```

**Verify deployment:**
- [ ] App accessible via HTTPS
- [ ] SSL certificate valid
- [ ] Service Worker registered
- [ ] PWA installable

### Step 3: Configure TWA Manifest

Edit `android/twa-manifest.json`:

```json
{
  "host": "familieplanner.yourdomain.com",  // ← Your actual domain
  "iconUrl": "https://familieplanner.yourdomain.com/static/icon-512.png",
  "maskableIconUrl": "https://familieplanner.yourdomain.com/static/icon-maskable-512.png",
  "shortcuts": [
    {
      "url": "/agenda",
      "icon": "https://familieplanner.yourdomain.com/static/shortcut-agenda.png"
    }
    // ... update all URLs with your domain
  ]
}
```

### Step 4: Generate Icons

If you don't have icons yet:

```bash
# 1. Create or download a source icon (1024x1024 recommended)
# Save as: app/static/icon-source.png

# 2. Generate all sizes
./scripts/generate-icons.sh

# This creates:
# - icon-{72,96,128,144,152,192,384,512}.png
# - icon-maskable-512.png
# - icon-monochrome-512.png
# - shortcut-{agenda,tasks,grocery}.png
# - favicon.png, favicon.ico
```

**Using an emoji as icon** (quick option):
1. Visit https://emojipedia.org/house/
2. Download a high-resolution emoji image
3. Save as `app/static/icon-source.png`
4. Run `./scripts/generate-icons.sh`

### Step 5: Generate Android Keystore

```bash
./scripts/generate-keystore.sh
```

Answer the prompts:
- **Name**: Your name or "FamiliePlanner Developer"
- **Organization**: "FamiliePlanner" or your family name
- **City/State/Country**: Optional (can leave as defaults)
- **Password**: Choose a strong password (min 6 characters)

**⚠️ CRITICAL**: Save the password and backup the keystore!

The script generates:
- `android/familieplanner.keystore` - Android signing key
- `android/keystore-credentials.txt` - Password and fingerprint
- SHA-256 fingerprint - Needed for Digital Asset Links

### Step 6: Update Digital Asset Links

Copy the SHA-256 fingerprint from the keystore generation output:

```bash
# Edit this file
app/static/.well-known/assetlinks.json
```

Replace `REPLACE_WITH_YOUR_SHA256_FINGERPRINT` with your fingerprint:

```json
[
  {
    "relation": ["delegate_permission/common.handle_all_urls"],
    "target": {
      "namespace": "android_app",
      "package_name": "com.familieplanner.app",
      "sha256_cert_fingerprints": [
        "AB:CD:EF:12:34:56:78:90:AB:CD:EF:12:34:56:78:90:AB:CD:EF:12:34:56:78:90:AB:CD:EF:12:34:56:78:90"
      ]
    }
  }
]
```

**Redeploy** to make the updated `assetlinks.json` available:

```bash
docker-compose -f docker-compose.production.yml restart
```

**Verify**:
```bash
curl https://familieplanner.yourdomain.com/.well-known/assetlinks.json
```

## Building the APK

### Automated Build (Recommended)

```bash
cd android
./build.sh
```

The script:
1. ✅ Validates TWA manifest
2. ✅ Checks Digital Asset Links accessibility
3. ✅ Initializes TWA project (first time)
4. ✅ Builds and signs the APK
5. ✅ Shows build summary and next steps

### Manual Build

If you prefer manual control:

```bash
cd android

# Initialize (first time only)
bubblewrap init --manifest=./twa-manifest.json

# Or update existing project
bubblewrap update --manifest=./twa-manifest.json

# Build
bubblewrap build

# Find the APK
ls -lh app/build/outputs/apk/release/*.apk
```

### Build Output

Successful build produces:

```
app/build/outputs/apk/release/app-release-signed.apk
```

**Expected size**: 15-25 MB

**What's included**:
- Bubblewrap TWA wrapper (~5 MB)
- Android support libraries (~8 MB)
- Icons and assets (~2 MB)
- Minimal native code (~5 MB)

**What's NOT included** (loaded from server):
- HTML/CSS/JavaScript
- Service Worker
- Cached data
- Images and photos

This keeps the APK small and enables instant updates.

## Distribution

### Option 1: Direct Distribution (Family Recommended)

**Best for**: Family members, small groups, testing

**Steps**:

1. **Share the APK file**:
   ```bash
   # Via cloud storage
   cp app/build/outputs/apk/release/app-release-signed.apk ~/Dropbox/FamiliePlanner.apk
   
   # Via email
   # Attach app-release-signed.apk to email
   
   # Via USB transfer
   adb push app/build/outputs/apk/release/app-release-signed.apk /sdcard/Download/
   ```

2. **Recipient installs**:
   - Open APK file on Android device
   - Android prompts "Install unknown app?"
   - Enable "Allow from this source"
   - Tap "Install"
   - Tap "Open"

**Pros**:
- ✅ Free (no Google Play fees)
- ✅ Instant distribution
- ✅ Full control
- ✅ No review process
- ✅ Updates happen automatically via web

**Cons**:
- ⚠️ Manual installation required
- ⚠️ Users must enable "Install unknown apps"
- ⚠️ No auto-update for APK itself (only web content)

### Option 2: Google Play Store

**Best for**: Public release, large audience

**Steps**:

1. **Create Google Play Developer account** ($25 one-time)
2. **Build App Bundle** (AAB format):
   ```bash
   bubblewrap build --bundletool
   ```
3. **Create store listing**:
   - App name, description
   - Screenshots
   - Privacy policy
4. **Upload AAB** to Play Console
5. **Submit for review** (typically 1-3 days)

**Pros**:
- ✅ Easy distribution (Play Store)
- ✅ Automatic installs
- ✅ User trust (Play Store badge)
- ✅ Better discovery

**Cons**:
- ⚠️ $25 one-time fee
- ⚠️ Review process (1-3 days)
- ⚠️ Must follow Play Store policies
- ⚠️ More complex process

### Option 3: ADB Installation (Development)

**Best for**: Testing, development devices

```bash
# Connect device via USB
# Enable USB debugging in Developer Options

# Install
adb install app/build/outputs/apk/release/app-release-signed.apk

# Or upgrade existing install
adb install -r app/build/outputs/apk/release/app-release-signed.apk

# Check installation
adb shell pm list packages | grep familieplanner
```

## Updating

### Updating Web Content Only

If you only change HTML/CSS/JavaScript:

```bash
# Just deploy the updated web app
docker-compose -f docker-compose.production.yml restart

# Users get updates automatically via Service Worker
# No APK rebuild needed!
```

**What updates automatically**:
- ✅ HTML/CSS/JavaScript
- ✅ Images and assets
- ✅ Service Worker
- ✅ API responses
- ✅ Database schema (via migrations)

### Updating APK Configuration

If you change app manifest, icons, or TWA configuration:

1. **Update `twa-manifest.json`**:
   ```json
   {
     "appVersionName": "1.1.0",  // User-visible version
     "appVersionCode": 2          // Must increment
   }
   ```

2. **Rebuild APK**:
   ```bash
   cd android
   ./build.sh
   ```

3. **Redistribute APK** to users

**When to rebuild APK**:
- ❌ HTML/CSS/JavaScript changes → No rebuild needed
- ❌ Adding features → No rebuild needed
- ❌ Bug fixes → No rebuild needed
- ✅ Changing app name → Rebuild needed
- ✅ Updating icons → Rebuild needed
- ✅ Changing theme colors → Rebuild needed
- ✅ Adding/removing shortcuts → Rebuild needed

## Troubleshooting

### Browser Bar Appears

**Symptom**: App shows Chrome address bar at top

**Cause**: Digital Asset Links not verified

**Solutions**:

1. **Verify assetlinks.json is accessible**:
   ```bash
   curl https://yourdomain.com/.well-known/assetlinks.json
   # Should return valid JSON
   ```

2. **Check fingerprint matches**:
   ```bash
   # Extract fingerprint from keystore
   keytool -list -v -keystore android/familieplanner.keystore -alias familieplanner
   
   # Compare with assetlinks.json
   ```

3. **Wait 24-48 hours** for Google verification
   - Google caches verification results
   - First verification takes time
   - Subsequent updates are faster

4. **Verify with Google's tool**:
   ```bash
   curl "https://digitalassetlinks.googleapis.com/v1/statements:list?source.web.site=https://yourdomain.com"
   ```

5. **Force re-verification**:
   - Clear app data on device
   - Uninstall and reinstall APK
   - Wait a few minutes

### APK Won't Install

**Error: "App not installed"**

**Solutions**:

1. **Enable "Install unknown apps"**:
   - Settings → Apps → Special access → Install unknown apps
   - Select your file manager or browser
   - Enable "Allow from this source"

2. **Check Android version**:
   - Minimum: Android 5.0 (API 21)
   - Recommended: Android 8.0+ (API 26)

3. **Uninstall old version**:
   ```bash
   adb uninstall com.familieplanner.app
   ```

4. **Check APK signature**:
   ```bash
   jarsigner -verify -verbose app-release-signed.apk
   ```

### Build Fails

**Error: "Java not found"**

```bash
# Check Java installation
java -version

# Install if missing
sudo apt-get install openjdk-11-jdk
```

**Error: "Bubblewrap command not found"**

```bash
# Install Bubblewrap
npm install -g @bubblewrap/cli

# Verify
bubblewrap --version
```

**Error: "Keystore not found"**

```bash
# Generate keystore
./scripts/generate-keystore.sh
```

**Error: "Manifest validation failed"**

```bash
# Validate manifest
cd android
bubblewrap validate

# Check for:
# - Invalid JSON syntax
# - Missing required fields
# - Invalid URLs
```

### Icons Not Loading

**Solutions**:

1. **Verify icon URLs are HTTPS**:
   ```bash
   curl -I https://yourdomain.com/static/icon-512.png
   # Should return 200 OK
   ```

2. **Check icon sizes**:
   ```bash
   identify app/static/icon-512.png
   # Should be 512x512
   ```

3. **Regenerate icons**:
   ```bash
   ./scripts/generate-icons.sh
   ```

4. **Clear cache and rebuild**:
   ```bash
   rm -rf android/app
   cd android && ./build.sh
   ```

### App Crashes on Startup

**Check logs**:

```bash
# Connect device via USB
adb logcat | grep FamiliePlanner

# Look for errors related to:
# - URL accessibility
# - SSL certificate
# - Service Worker
```

**Common causes**:
- HTTPS server down
- Invalid SSL certificate
- Service Worker errors
- JavaScript errors

### Offline Mode Not Working

**Verify**:

1. **Service Worker registered**:
   - Open app in Chrome (web version)
   - DevTools → Application → Service Workers
   - Should show "activated and running"

2. **IndexedDB populated**:
   - DevTools → Application → IndexedDB
   - Should see databases for meals, tasks, agenda

3. **Authentication flag set**:
   - DevTools → Application → Local Storage
   - Should see `fp_was_authenticated: true`

4. **Test offline**:
   - DevTools → Network → Offline
   - Reload app → should still work

## Performance & Best Practices

### APK Size Optimization

Current size: **15-25 MB**

If you need to reduce further:

1. **Optimize icons** (minimal impact):
   ```bash
   # Use pngquant for compression
   pngquant --quality=65-80 app/static/icon-*.png
   ```

2. **Remove unused shortcuts**:
   - Edit `twa-manifest.json`
   - Remove shortcuts you don't need

3. **Use minimal dependencies**:
   - Bubblewrap already includes only essential libraries

### Load Time Optimization

App startup time: **< 2 seconds** (typical)

To improve:

1. **Optimize Service Worker**:
   - Cache critical resources first
   - Use `stale-while-revalidate` for assets

2. **Minimize initial payload**:
   - Defer non-critical JavaScript
   - Lazy-load images

3. **Enable compression**:
   - Nginx gzip/brotli for text assets
   - See `nginx.conf` configuration

### Update Strategy

**Web updates** (instant):
- Deploy changes to HTTPS server
- Service Worker auto-updates within 24 hours
- Users see changes on next visit

**APK updates** (manual):
- Only when manifest changes
- Distribute new APK file
- Users must reinstall

**Recommended approach**:
- Ship features via web (no APK rebuild)
- Update APK only for branding/config changes
- Keep APK version stable

## Security Checklist

Before distribution:

- [ ] HTTPS enabled with valid certificate
- [ ] Digital Asset Links configured correctly
- [ ] Keystore backed up securely
- [ ] Password stored in password manager
- [ ] assetlinks.json accessible publicly
- [ ] Icons optimized and accessible
- [ ] Service Worker properly configured
- [ ] Authentication working offline
- [ ] Tested on real Android device
- [ ] Verified no console errors
- [ ] Checked app works offline

## References

- [TWA Quick Start](https://developer.chrome.com/docs/android/trusted-web-activity/quick-start/)
- [Bubblewrap GitHub](https://github.com/GoogleChromeLabs/bubblewrap)
- [Digital Asset Links](https://developers.google.com/digital-asset-links)
- [Android Icon Guidelines](https://developer.android.com/distribute/google-play/resources/icon-design-specifications)
- [PWA Offline Guide](https://web.dev/offline-cookbook/)

## Getting Help

If you encounter issues:

1. **Check this guide** - Most issues covered above
2. **Check logs** - `adb logcat` shows errors
3. **Verify prerequisites** - Java, Node, Bubblewrap
4. **Test web version** - Ensure PWA works first
5. **File an issue** - Include error messages and logs

---

**Next Steps**: See [android/README.md](../android/README.md) for ongoing maintenance and updates.
