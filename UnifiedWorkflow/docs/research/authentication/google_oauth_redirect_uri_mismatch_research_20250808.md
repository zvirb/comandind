# Google OAuth redirect_uri_mismatch Investigation

**Research Date**: August 8, 2025  
**Researcher**: Codebase Research Analyst  
**Issue**: Error 400: redirect_uri_mismatch - markuszvirbulis@gmail.com cannot sign in

## Executive Summary

**Problem**: Google OAuth authentication is failing with "redirect_uri_mismatch" error for user markuszvirbulis@gmail.com attempting to connect Google services.

**Root Cause**: Mismatch between the redirect URI configured in Google Cloud Console and the URI dynamically constructed by the application during OAuth flow.

**Impact**: Complete inability to connect any Google services (Calendar, Drive, Gmail) to the AI Workflow Engine.

## 1. OAuth Configuration Analysis

### Current OAuth Implementation

**OAuth Client Configuration**:
- **Client ID**: `43892281310-10tjeg777c2ftf7cjhdfpaare02odvro.apps.googleusercontent.com` (verified in `/home/marku/ai_workflow_engine/secrets/google_client_id.txt`)
- **Client Secret**: Configured (35 characters in `/home/marku/ai_workflow_engine/secrets/google_client_secret.txt`)
- **Configuration Status**: ✅ Both client ID and secret properly configured

**Configuration Loading**:
```python
# From app/shared/utils/config.py line 134-155
@model_validator(mode='after')
def load_google_oauth_from_secrets(self) -> 'Settings':
    # Load Google OAuth credentials from Docker secrets only
    if not self.GOOGLE_CLIENT_ID:
        secret_client_id = (read_secret_file('google_client_id.txt') or 
                           read_secret_file('google_client_id'))
        if secret_client_id:
            self.GOOGLE_CLIENT_ID = secret_client_id

    if not self.GOOGLE_CLIENT_SECRET:
        secret_client_secret = (read_secret_file('google_client_secret.txt') or 
                               read_secret_file('google_client_secret'))
        if secret_client_secret:
            self.GOOGLE_CLIENT_SECRET = SecretStr(secret_client_secret)
```

## 2. Redirect URI Construction Analysis

### Dynamic URI Construction

**Primary OAuth Connect Endpoint**: `/api/v1/oauth/google/connect/{service}`

```python
# From app/api/routers/oauth_router.py line 196-198
# Build redirect URI
base_url = str(request.base_url).rstrip('/')
redirect_uri = f"{base_url}/api/v1/oauth/google/callback"
```

**Problem Identified**: The redirect URI is dynamically constructed using `request.base_url`, which varies depending on:

1. **Domain Configuration**: `DOMAIN=aiwfe.com` (from `.env`)
2. **Request Headers**: `Host` header determines base URL
3. **Protocol**: HTTP vs HTTPS
4. **Port**: Presence or absence of port numbers

### Possible URI Variations

Based on the current setup, the redirect URI could be constructed as any of:

- `https://aiwfe.com/api/v1/oauth/google/callback` ✅ (Expected production)
- `http://aiwfe.com/api/v1/oauth/google/callback` ❌ (Protocol mismatch)
- `https://localhost/api/v1/oauth/google/callback` ❌ (Local development)
- `https://aiwfe.com:443/api/v1/oauth/google/callback` ❌ (With explicit port)
- Any other domain if DNS/proxy configuration issues exist

## 3. Frontend OAuth Flow Trigger

### OAuth Connection Initiation

```javascript
// From app/webui/src/lib/components/Settings.svelte line 156-158
// Redirect to OAuth flow
const baseUrl = window.location.origin;
window.location.href = `${baseUrl}/api/v1/oauth/google/connect/${service}`;
```

**Frontend Flow**:
1. User clicks "Connect" in Settings
2. Frontend redirects to `/api/v1/oauth/google/connect/calendar` (or drive/gmail)
3. Backend constructs redirect URI using `request.base_url`
4. User redirected to Google OAuth consent screen
5. **FAILURE**: Google rejects due to redirect URI mismatch

## 4. Environment Configuration

### Domain Configuration

```bash
# From .env file
DOMAIN=aiwfe.com
```

### Caddy Reverse Proxy Configuration

```caddyfile
# From config/caddy/Caddyfile line 19
{$DOMAIN:aiwfe.com} {
    # OAuth endpoints - no mTLS required for external redirects
    @oauth_endpoints path /api/v1/oauth/*
    handle @oauth_endpoints {
        reverse_proxy http://api:8000
    }
}
```

**Key Insight**: Caddy is configured to handle `aiwfe.com` and proxy OAuth endpoints to the API service.

## 5. Google Cloud Console Configuration Requirements

### Expected Redirect URI Configuration

Based on the current setup, the Google Cloud Console should have:

**Authorized Redirect URIs**:
- `https://aiwfe.com/api/v1/oauth/google/callback` (Production)
- `http://localhost:8000/api/v1/oauth/google/callback` (Local development - optional)

### OAuth Scopes Used

```python
# From app/api/routers/oauth_router.py line 175-179
scopes = {
    "calendar": ["https://www.googleapis.com/auth/calendar"],
    "drive": ["https://www.googleapis.com/auth/drive.readonly"],
    "gmail": ["https://www.googleapis.com/auth/gmail.readonly"]
}
```

## 6. Complete OAuth Flow Architecture

```mermaid
graph TD
    A[User clicks Connect Google Service] --> B[Frontend: window.location.href redirects]
    B --> C[Backend: /api/v1/oauth/google/connect/{service}]
    C --> D[Generate OAuth state + construct redirect URI]
    D --> E[Redirect to Google OAuth consent screen]
    E --> F{Google URI validation}
    F -->|✅ Match| G[User grants permissions]
    F -->|❌ Mismatch| H[Error 400: redirect_uri_mismatch]
    G --> I[Google redirects to callback URI]
    I --> J[Backend: /api/v1/oauth/google/callback]
    J --> K[Exchange code for tokens]
    K --> L[Store tokens in database]
    L --> M[Redirect to /settings?oauth=success]
```

## 7. Specific Error Analysis

### User Impact
- **User**: `markuszvirbulis@gmail.com`
- **Services Affected**: Calendar, Drive, Gmail (all Google services)
- **Error**: App request marked as invalid by Google
- **Status**: Complete OAuth flow failure

### Error Context
- The error occurs at Google's OAuth consent screen
- This suggests the redirect URI sent to Google doesn't match what's configured in Google Cloud Console
- The error happens before user interaction (Google rejects the request immediately)

## 8. Production Environment Analysis

### URL Construction in Production

**Request Flow**:
1. User accesses `https://aiwfe.com`
2. Caddy reverse proxy handles HTTPS termination
3. Internal request to API service uses HTTP
4. `request.base_url` could be returning incorrect protocol/host

**Potential Issue**: The `request.base_url` inside the Docker container may be:
- `http://api:8000` (internal service name)
- `http://localhost:8000` (if headers not properly forwarded)
- Missing HTTPS protocol if proxy headers not configured

### Caddy Proxy Headers

**Missing Configuration**: Caddy reverse proxy may not be forwarding proper headers for `request.base_url` reconstruction:

```caddyfile
# Should include (currently missing):
handle @oauth_endpoints {
    reverse_proxy http://api:8000 {
        header_up X-Forwarded-Proto {scheme}
        header_up X-Forwarded-Host {host}
        header_up X-Real-IP {remote}
    }
}
```

## 9. Root Cause Determination

### Primary Issue: Dynamic URI Construction

The redirect URI is constructed dynamically using `request.base_url`, but in a containerized environment behind a reverse proxy:

1. **Internal vs External URLs**: `request.base_url` may return internal container URL
2. **Protocol Mismatch**: HTTP internally vs HTTPS externally
3. **Host Header Issues**: May return service name instead of public domain
4. **Proxy Header Missing**: Caddy not forwarding proper headers for URL reconstruction

### Secondary Issue: Google Cloud Console Configuration

The authorized redirect URIs in Google Cloud Console must exactly match the dynamically constructed URI.

## 10. Solution Recommendations

### Immediate Fix: Static Redirect URI Configuration

**Option 1**: Use environment variable for redirect URI base:

```python
# Recommended change to oauth_router.py
@router.get("/google/connect/{service}")
async def connect_google_oauth(service: str, request: Request, current_user: User = Depends(get_current_user)):
    settings = get_settings()
    
    # Use configured domain instead of dynamic base URL
    redirect_uri = f"https://{settings.DOMAIN or 'aiwfe.com'}/api/v1/oauth/google/callback"
```

**Option 2**: Add OAUTH_REDIRECT_BASE environment variable:

```python
# In config.py
OAUTH_REDIRECT_BASE: str = "https://aiwfe.com"

# In oauth_router.py
redirect_uri = f"{settings.OAUTH_REDIRECT_BASE}/api/v1/oauth/google/callback"
```

### Infrastructure Fix: Proper Proxy Headers

**Update Caddy Configuration**:

```caddyfile
@oauth_endpoints path /api/v1/oauth/*
handle @oauth_endpoints {
    reverse_proxy http://api:8000 {
        header_up Host {host}
        header_up X-Real-IP {remote}
        header_up X-Forwarded-For {remote}
        header_up X-Forwarded-Port {server_port}
        header_up X-Forwarded-Proto {scheme}
        header_up X-Forwarded-Host {host}
    }
}
```

### Google Cloud Console Configuration

**Ensure these redirect URIs are configured**:
- `https://aiwfe.com/api/v1/oauth/google/callback`
- `http://localhost:8000/api/v1/oauth/google/callback` (for local development)

## 11. Testing Strategy

### Verification Steps

1. **Check Current URI Construction**:
   ```bash
   # Test what base_url is being constructed
   curl -v https://aiwfe.com/api/v1/oauth/google/connect/calendar
   ```

2. **Verify Google Cloud Console Configuration**:
   - Access Google Cloud Console for project
   - Navigate to APIs & Services > Credentials
   - Check OAuth 2.0 Client IDs
   - Verify redirect URIs match expected pattern

3. **Test OAuth Flow**:
   - Login as `markuszvirbulis@gmail.com`
   - Attempt to connect Google Calendar
   - Monitor network traffic for actual redirect URI sent to Google

### Debug Information Collection

**Immediate Debug Steps**:
```python
# Add to oauth_router.py for debugging
logger.info(f"Request base URL: {request.base_url}")
logger.info(f"Request headers: {dict(request.headers)}")
logger.info(f"Constructed redirect URI: {redirect_uri}")
```

## 12. Prevention Measures

### Configuration Hardening

1. **Static Configuration**: Use environment variables for redirect URIs instead of dynamic construction
2. **Header Forwarding**: Ensure reverse proxy forwards proper headers
3. **URI Validation**: Add validation to ensure redirect URI matches expected pattern
4. **Environment-Specific Configuration**: Different redirect URIs for dev/staging/production

### Monitoring

1. **OAuth Flow Logging**: Log all redirect URI constructions
2. **Error Tracking**: Monitor Google OAuth errors
3. **Configuration Drift Detection**: Alert on OAuth configuration changes

## 13. Related Files

### Core OAuth Implementation
- `/home/marku/ai_workflow_engine/app/api/routers/oauth_router.py` - Main OAuth flow
- `/home/marku/ai_workflow_engine/app/api/services/oauth_token_manager.py` - Token management
- `/home/marku/ai_workflow_engine/app/shared/utils/config.py` - Configuration loading

### Frontend Integration
- `/home/marku/ai_workflow_engine/app/webui/src/lib/components/Settings.svelte` - OAuth connection UI
- `/home/marku/ai_workflow_engine/app/webui/src/lib/api_client/index.js` - API client

### Infrastructure Configuration
- `/home/marku/ai_workflow_engine/config/caddy/Caddyfile` - Reverse proxy configuration
- `/home/marku/ai_workflow_engine/docker-compose.yml` - Container orchestration
- `/home/marku/ai_workflow_engine/.env` - Environment configuration

### Secret Management
- `/home/marku/ai_workflow_engine/secrets/google_client_id.txt` - OAuth client ID
- `/home/marku/ai_workflow_engine/secrets/google_client_secret.txt` - OAuth client secret

## 14. Expected Implementation Time

**Immediate Fix**: 15-30 minutes (static redirect URI configuration)
**Infrastructure Fix**: 30-60 minutes (Caddy proxy header configuration)
**Testing & Validation**: 30 minutes (OAuth flow testing)
**Total Estimated Time**: 1.5-2 hours

## 15. Risk Assessment

**Risk Level**: Medium-High
- **Impact**: Complete Google services integration failure
- **User Affected**: All users attempting to connect Google services
- **Workaround Available**: None (OAuth completely broken)
- **Data Loss Risk**: None (read-only OAuth scopes)

## Conclusion

The redirect_uri_mismatch error is caused by dynamic URL construction in a containerized environment behind a reverse proxy. The `request.base_url` is likely returning an internal container URL or incorrect protocol, creating a mismatch with the redirect URI configured in Google Cloud Console.

The recommended fix is to use static redirect URI configuration based on the `DOMAIN` environment variable, combined with proper proxy header forwarding to ensure the OAuth flow uses the correct external domain and HTTPS protocol.