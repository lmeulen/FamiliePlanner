# Offline Security Model

This document explains how authentication and security work when FamiliePlanner is used offline.

## Overview

FamiliePlanner uses a **device-level security** model for offline access. This is a pragmatic approach that balances security with usability for a family app context.

## How It Works

### Initial Authentication

1. **First-time login requires internet connection**
   - User must log in online at least once
   - Server validates credentials (username + password)
   - Session is created with CSRF protection

2. **Offline access flag is set**
   - After successful online login, `wasAuthenticated` flag is stored in browser localStorage
   - This flag persists across browser sessions
   - Timestamp of last online access is recorded

### Offline Access

When the device is offline:

1. **Check authentication status**
   - If `wasAuthenticated` flag exists → grant access
   - If flag doesn't exist → show offline lock screen

2. **Offline lock screen**
   - Prevents access for users who haven't logged in online
   - Shows helpful message: "Log in online first to get offline access"
   - Disappears automatically when internet returns

3. **Full functionality offline**
   - All cached data accessible (agenda, tasks, meals, grocery)
   - All CRUD operations work (queued for sync)
   - No server roundtrips needed

### Logout Behavior

When user logs out:

1. **Authentication flag is cleared**
   - `wasAuthenticated` flag removed from localStorage
   - Offline access immediately revoked
   - Requires new online login to regain offline access

2. **Server session cleared**
   - Session cookie invalidated
   - CSRF token invalidated
   - User redirected to login page

## Security Considerations

### Strengths

✅ **Simple and reliable**
- No complex token refresh logic
- No token expiration headaches
- Works seamlessly offline

✅ **Device security reliant**
- Assumes device is physically secured (PIN, biometric, etc.)
- Appropriate for family context (trusted devices)

✅ **No credential storage**
- No passwords stored in browser
- No tokens that can be stolen
- Session-only authentication

### Limitations

⚠️ **Device theft = data access**
- If device is stolen and unlocked, offline data is accessible
- **Mitigation**: Users should enable device lock (PIN/biometric)
- **Mitigation**: Remote wipe capabilities (OS-level)

⚠️ **Browser data persistence**
- Clearing browser data removes offline access flag
- **Expected behavior**: User must re-login online
- localStorage data cleared = need to re-authenticate

⚠️ **Multi-device requirement**
- Each device needs separate online login
- No cross-device offline access sharing
- **Expected behavior**: Login once per device

⚠️ **No granular permissions**
- Once authenticated offline, full access granted
- No role-based access control
- **Acceptable for family app**: Single user account model

## Why Not JWT Tokens?

We chose device-level security over JWT tokens because:

| Aspect | Device-Level | JWT Tokens |
|--------|-------------|-----------|
| Implementation | ~12-16 hours | ~40+ hours |
| Complexity | Low | High |
| Token refresh | N/A | Complex offline |
| Token expiration | N/A | Requires handling |
| Offline reliability | 100% | Depends on token validity |
| Security model | Device trust | Token trust |
| Family app fit | Excellent | Overkill |

For a family organization app where:
- Users are trusted (family members)
- Devices are typically personal and secured
- Simplicity and reliability are priorities
- Development speed matters

The device-level security model is the right choice.

## Future Enhancements

If security requirements change, we could add:

### Short-term (can be added later)
- **Offline session timeout**: Require re-login after N days offline
- **Biometric re-authentication**: Prompt for device biometric before offline access
- **Data encryption**: Encrypt IndexedDB data at rest

### Long-term (major refactor)
- **JWT tokens**: Full token-based authentication with refresh
- **Role-based access**: Multiple user accounts with different permissions
- **Server-side encryption**: End-to-end encryption for sensitive data

## User Guidance

### For End Users

**Recommended device security:**
1. ✅ Enable device PIN/password
2. ✅ Enable biometric authentication (fingerprint/face)
3. ✅ Keep device updated
4. ✅ Don't share device with untrusted users
5. ✅ Use "Find My Device" for remote wipe capability

**What to expect:**
- First login must be online
- Logout requires re-login online
- Clearing browser data = offline access lost
- Each device needs separate login

### For Developers

**Authentication flow:**
```javascript
// 1. User loads authenticated page (online)
if (navigator.onLine && !loginPage) {
  AuthState.setAuthenticated(); // Set flag
}

// 2. User goes offline
if (!navigator.onLine) {
  const access = AuthState.checkOfflineAccess();
  if (!access.allowed) {
    AuthState.showOfflineLockScreen(access.reason);
  }
}

// 3. User logs out
function logout() {
  AuthState.clearAuthenticated(); // Clear flag
  window.location.href = '/logout';
}
```

**Testing offline access:**
1. Log in while online
2. Open DevTools → Network → Offline
3. Refresh page → should still work
4. Click logout → offline access revoked
5. Try to access while offline → lock screen shown

## Compliance & Privacy

**Data storage:**
- Authentication flag: localStorage (`fp_was_authenticated`)
- Last online timestamp: localStorage (`fp_last_online`)
- Cached app data: IndexedDB (groceries, meals, tasks, agenda)
- Session cookie: HTTP-only, same-site, secure (production)

**Data retention:**
- Cleared on explicit logout
- Cleared when browser data is cleared
- Not synced across devices
- Device-local only

**Privacy implications:**
- No third-party authentication
- No external data sharing
- Self-hosted deployment recommended
- Full data ownership

## Conclusion

The device-level security model provides:
- ✅ Excellent offline experience
- ✅ Simple and maintainable
- ✅ Appropriate for family context
- ✅ Future-extensible if needed

This approach prioritizes **usability** and **reliability** while maintaining reasonable security for a family organization app.
