# Azure AD Configuration Instructions

## Problem Found
Based on GitHub issue #2420, the main problem is that the **redirect URI must be configured EXACTLY** in Azure AD app registration.

## Required Azure AD Settings

### 1. Redirect URIs
In your Azure AD app registration, add these **exact** redirect URIs:

```
http://localhost:3000
http://localhost:3000/
```

**Note**: The `/login` route should NOT be added as redirect URI since it's where users START the login process, not where they return to.

### 2. Authentication Platform
- **Platform**: Single-page application (SPA)
- **DO NOT** check "Access tokens" or "ID tokens" in Implicit flow
- Use **Authorization code flow** (default for SPA)

### 3. Front-channel logout URL
**IMPORTANT**: Leave this field **EMPTY**.

According to Azure AD documentation: "This is where we send a request to have the application clear the user's session data. This is required for single sign-out to work correctly."

However, for SPA applications, this can cause redirect loops. Leave it empty to prevent logout issues.

### 4. API Permissions
Ensure these permissions are granted:
- `User.Read` (Microsoft Graph)
- `User.ReadBasic.All` (Microsoft Graph)
- `openid`
- `profile`
- `email`

### 5. Current Configuration
Your current app:
- **Client ID**: `630ad539-1ae7-495e-8921-03315f7618bf`
- **Tenant ID**: `0043f0fc-6fe9-49e5-87e2-b48fc293bf35`
- **Authority URL**: `https://login.microsoftonline.com/0043f0fc-6fe9-49e5-87e2-b48fc293bf35`

## Verification Steps

1. Go to Azure Portal → Azure Active Directory → App registrations
2. Find your app with Client ID `630ad539-1ae7-495e-8921-03315f7618bf`
3. Go to Authentication
4. Verify all redirect URIs listed above are added
5. Ensure platform is set to "Single-page application"

## Testing
After adding the redirect URIs, test the login flow:
1. Clear browser cache and localStorage
2. Go to `http://localhost:3000`
3. Click login
4. After Azure AD login, you should be redirected back with tokens

## Key Changes Made in Code
- **CRITICAL**: Set `navigateToLoginRequestUrl: true` (this was the main issue!)
- Added comprehensive redirect handling with retry mechanism
- Improved URL cleanup after authentication
- Added support for both URL parameters and hash fragments
- Implemented silent token acquisition fallback
- Added retry logic for timing issues with redirect handling

## Common Issues and Solutions

### Issue: `handleRedirectPromise` returns null
**Root Cause**: `navigateToLoginRequestUrl` was set to `false`
**Solution**: Must be set to `true` for redirect flow to work correctly

### Issue: Multiple MSAL initializations
**Root Cause**: React StrictMode causes multiple initialization
**Solution**: Moved MSAL initialization outside React component with promise caching

### Issue: Redirect loops or timing issues
**Root Cause**: MSAL needs time to process redirect response
**Solution**: Added retry mechanism with 1-second delay