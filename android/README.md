# FamiliePlanner Android APK

This directory contains the configuration and build scripts for packaging FamiliePlanner as an Android APK using Trusted Web Activities (TWA).

## What is TWA?

Trusted Web Activities (TWA) allows you to wrap your Progressive Web App (PWA) in an Android APK that:
- Runs without browser chrome (looks like a native app)
- Updates automatically when you update the web app (no APK rebuild needed)
- Is small in size (15-25 MB)
- Uses the user's Chrome browser engine
- Requires HTTPS and Digital Asset Links verification

## Prerequisites

### Required
- **Node.js 16+** and npm
- **Java JDK 11+** (for Android build tools)
- **HTTPS domain** with valid SSL certificate
- **FamiliePlanner deployed** on HTTPS server

### Optional (for icon generation)
- **ImageMagick** (for generating icon sizes)

### Installation

```bash
# Install Bubblewrap CLI globally
npm install -g @bubblewrap/cli

# Verify installation
bubblewrap --version

# Install Java (if not already installed)
# Ubuntu/Debian:
sudo apt-get install openjdk-11-jdk

# macOS:
brew install openjdk@11

# Windows: Download from https://adoptium.net/
```

## Quick Start

### 1. Configure Your Domain

Edit `twa-manifest.json` and update:
```json
{
  "host": "familieplanner.yourdomain.com",
  "iconUrl": "https://familieplanner.yourdomain.com/static/icon-512.png",
  ...
}
```

### 2. Generate Icons

```bash
# From project root
cd scripts
./generate-icons.sh
```

This creates all required icon sizes from a source image.

### 3. Generate Android Keystore

```bash
# From project root
./scripts/generate-keystore.sh
```

Follow the prompts to create a keystore. **Save the credentials securely!**

### 4. Update Digital Asset Links

Copy the SHA-256 fingerprint from the keystore generation and update:
```bash
# Edit this file
../app/static/.well-known/assetlinks.json
```

Replace `REPLACE_WITH_YOUR_SHA256_FINGERPRINT` with your actual fingerprint.

### 5. Deploy to HTTPS Server

```bash
# From project root
docker-compose -f docker-compose.production.yml up -d
```

Verify that:
- App is accessible via HTTPS
- `/.well-known/assetlinks.json` is accessible
- Icons are loading correctly

### 6. Build the APK

```bash
# From android/ directory
./build.sh
```

The script will:
1. Validate the TWA manifest
2. Check Digital Asset Links accessibility
3. Initialize/update the TWA project
4. Build and sign the APK

### 7. Install on Android Device

```bash
# Via ADB (device connected via USB)
adb install app/build/outputs/apk/release/app-release-signed.apk

# Or transfer the APK to your device and install manually
```

## Configuration

### twa-manifest.json

Key fields to configure:

| Field | Description | Example |
|-------|-------------|---------|
| `packageId` | Android package name | `com.familieplanner.app` |
| `host` | Your HTTPS domain | `familieplanner.yourdomain.com` |
| `name` | App name (full) | `FamiliePlanner` |
| `launcherName` | App name (short) | `FamiliePlanner` |
| `themeColor` | Theme color | `#6C5CE7` |
| `startUrl` | Initial route | `/` |
| `iconUrl` | Main icon URL | `https://.../icon-512.png` |
| `minSdkVersion` | Minimum Android version | `21` (Android 5.0+) |

### App Shortcuts

The manifest includes 3 app shortcuts:
- **Agenda** - Jump to calendar view
- **Taken** - Jump to tasks view
- **Boodschappen** - Jump to grocery list

Long-press the app icon on Android to access these.

## Troubleshooting

### Browser Bar Shows Up

**Symptom**: App shows Chrome browser bar at the top

**Cause**: Digital Asset Links not verified yet

**Solution**:
1. Verify `assetlinks.json` is accessible at `https://yourdomain.com/.well-known/assetlinks.json`
2. Check fingerprint matches your keystore
3. Wait 24-48 hours for Google's verification
4. Clear app data and reinstall

**Verify with Google's tool**:
```bash
curl "https://digitalassetlinks.googleapis.com/v1/statements:list?source.web.site=https://yourdomain.com&relation=delegate_permission/common.handle_all_urls"
```

### APK Won't Install

**Symptom**: "App not installed" error

**Solutions**:
- Enable "Install unknown apps" in Android settings
- Check minimum Android version (API 21 = Android 5.0)
- Uninstall previous version if exists
- Check APK signature is valid

### Build Fails

**Common issues**:

1. **Java not found**
   ```bash
   # Verify Java installation
   java -version
   # Should show Java 11 or higher
   ```

2. **Bubblewrap not installed**
   ```bash
   npm install -g @bubblewrap/cli
   ```

3. **Keystore not found**
   ```bash
   # Generate keystore first
   cd .. && ./scripts/generate-keystore.sh
   ```

4. **Invalid manifest**
   ```bash
   # Validate manifest
   bubblewrap validate
   ```

### Icons Not Showing

**Solutions**:
- Verify icon URLs are HTTPS
- Check icons are accessible (try opening in browser)
- Ensure icons are correct size (512x512 for main icon)
- Regenerate icons with `scripts/generate-icons.sh`

## Version Management

### Updating the App

To release a new version:

1. **Update version in twa-manifest.json**:
   ```json
   {
     "appVersionName": "1.1.0",
     "appVersionCode": 2
   }
   ```

2. **Rebuild APK**:
   ```bash
   ./build.sh
   ```

3. **Install updated APK** on devices

**Note**: If you only change web content (HTML/CSS/JS), users get updates automatically without reinstalling the APK. Only rebuild the APK when changing:
- App name
- Icons
- Theme colors
- Shortcuts
- Manifest configuration

### Version Codes

- `appVersionName`: User-visible version (e.g., "1.0.0")
- `appVersionCode`: Integer that must increase with each release

## File Structure

```
android/
├── twa-manifest.json       # TWA configuration
├── build.sh                # Build automation script
├── .gitignore              # Ignore build artifacts
├── README.md               # This file
├── familieplanner.keystore # Android signing key (not in git)
└── app/                    # Generated by Bubblewrap (not in git)
    └── build/
        └── outputs/
            └── apk/
                └── release/
                    └── app-release-signed.apk  # Final APK
```

## APK Size

Expected APK size: **15-25 MB**

Breakdown:
- Bubblewrap wrapper: ~5 MB
- Android support libraries: ~8 MB
- Icons and assets: ~2 MB
- Service worker cache: ~5 MB

The web content (HTML/CSS/JS) is not bundled in the APK - it's loaded from your HTTPS server. This keeps the APK small and allows instant updates.

## Distribution

### Option 1: Direct Distribution (Recommended for Family)

1. Build APK using `./build.sh`
2. Share APK file directly with family members
3. They install it manually (enable "Install unknown apps")
4. Updates happen automatically via web

**Pros**: No Google Play fees, instant updates, full control
**Cons**: Manual installation required

### Option 2: Google Play Store

To publish on Google Play:

1. Create a Google Play Developer account ($25 one-time fee)
2. Build a signed APK bundle (AAB format):
   ```bash
   bubblewrap build --bundletool
   ```
3. Upload to Play Console
4. Complete store listing
5. Submit for review

**Pros**: Easy distribution, automatic installs
**Cons**: $25 fee, review process, policies to follow

For a family app, **direct distribution** is usually simpler and faster.

## Security Notes

### Keystore Security

⚠️ **CRITICAL**: Keep your keystore and password secure!

- **Backup the keystore** - If lost, you cannot update the app
- **Never commit to git** - Already in `.gitignore`
- **Store password securely** - Use a password manager

If you lose the keystore, users must:
1. Uninstall the old app (loses data)
2. Install the new app with a different keystore

### Digital Asset Links

The `assetlinks.json` file proves you own both the domain and the app. This prevents:
- Impersonation attacks
- Unauthorized APK wrapping
- Browser bar spoofing

Always verify the fingerprint matches your keystore.

## Performance

TWA apps are **as fast as the web app** because they use:
- Chrome's rendering engine (not WebView)
- Service Worker caching
- Same performance optimizations as PWA

Offline functionality works identically to the PWA.

## Updating This Guide

When making changes to the TWA configuration:

1. Update `twa-manifest.json`
2. Update this README with changes
3. Rebuild APK
4. Test on real device
5. Update documentation

## Support

For issues with:
- **Bubblewrap**: https://github.com/GoogleChromeLabs/bubblewrap
- **TWA**: https://developer.chrome.com/docs/android/trusted-web-activity
- **FamiliePlanner**: File an issue in the repository

## References

- [Trusted Web Activities Guide](https://developer.chrome.com/docs/android/trusted-web-activity/)
- [Bubblewrap Documentation](https://github.com/GoogleChromeLabs/bubblewrap)
- [Digital Asset Links](https://developers.google.com/digital-asset-links/v1/getting-started)
- [Android Icon Guidelines](https://developer.android.com/distribute/google-play/resources/icon-design-specifications)
