# AI Workflow Engine - Complete User Authentication Guide

## 🚀 Quick Start Authentication

### Standard Login Process

1. **Navigate to Login**: Visit `https://localhost/` and click "Login"
2. **Enter Credentials**: Provide your email and password
3. **Multi-Factor Authentication** (if enabled): Enter your 2FA code
4. **Access Dashboard**: You'll be redirected to the main dashboard

### Supported Authentication Methods

- **🔐 JWT Token Authentication** (Primary)
- **🔑 Two-Factor Authentication (2FA)**
- **🛡️ WebAuthn/Passwordless**
- **🔒 Google OAuth Integration**
- **📱 Native Device Authentication**

---

## 🔐 Authentication Methods

### 1. JWT Token Authentication

**Primary authentication method** using JSON Web Tokens with enhanced security features.

#### Login Flow
```http
POST /api/v1/auth/jwt/login
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "your_secure_password"
}
```

**Successful Response**:
```json
{
  "success": true,
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user_id": "uuid-string",
  "role": "user",
  "session_id": "session-uuid"
}
```

#### Token Usage
Include the token in all authenticated requests:
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### Token Refresh
Tokens expire after 1 hour. Refresh using:
```http
POST /api/v1/auth/refresh
Authorization: Bearer your_current_token
```

### 2. Two-Factor Authentication (2FA)

#### Enable 2FA
1. **Login** to your account
2. **Navigate** to Settings > Security
3. **Click** "Enable Two-Factor Authentication"
4. **Scan QR Code** with your authenticator app
5. **Enter** the 6-digit code to verify
6. **Save backup codes** securely

#### 2FA Login Process
1. **Standard Login**: Enter username/password
2. **2FA Prompt**: System requests 2FA code
3. **Enter Code**: Provide 6-digit authenticator code
4. **Access Granted**: Complete authentication

```http
POST /api/v1/2fa/verify
Content-Type: application/json
Authorization: Bearer partial_token

{
  "code": "123456"
}
```

#### Backup Codes
- **Generated** during 2FA setup
- **Single-use** codes for emergency access
- **Store securely** offline
- **Regenerate** after use

### 3. WebAuthn/Passwordless Authentication

#### Register WebAuthn Device
```http
POST /api/v1/webauthn/register/begin
Authorization: Bearer your_token
```

**Browser Integration**:
```javascript
// Register new credential
const credential = await navigator.credentials.create({
  publicKey: registrationOptions
});

// Complete registration
await fetch('/api/v1/webauthn/register/complete', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ credential })
});
```

#### WebAuthn Login
```javascript
// Begin authentication
const authOptions = await fetch('/api/v1/webauthn/authenticate/begin');

// Authenticate with device
const credential = await navigator.credentials.get({
  publicKey: await authOptions.json()
});

// Complete authentication
const response = await fetch('/api/v1/webauthn/authenticate/complete', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ credential })
});
```

### 4. Google OAuth Integration

#### OAuth Flow
1. **Click** "Login with Google"
2. **Redirect** to Google authorization
3. **Grant permissions** to AI Workflow Engine
4. **Automatic** account creation/linking
5. **Return** to dashboard with active session

```http
GET /api/v1/oauth/google/authorize
```

#### OAuth Status Check
```http
GET /api/v1/oauth/status
Authorization: Bearer your_token
```

**Response**:
```json
{
  "google_connected": true,
  "connected_at": "2025-08-06T14:30:22Z",
  "scopes": ["profile", "email", "calendar", "drive"]
}
```

### 5. Native Device Authentication

For mobile and desktop applications:

#### Device Registration
```http
POST /native/auth/register
Content-Type: application/json

{
  "device_name": "iPhone 12",
  "device_type": "mobile",
  "platform": "iOS"
}
```

#### Native Login
```http
POST /native/auth/login
Content-Type: application/json

{
  "device_id": "device-uuid",
  "credentials": "hashed_credentials"
}
```

---

## 🛡️ Security Features

### Password Security
- **Minimum 8 characters**
- **Mix of uppercase, lowercase, numbers**
- **Special characters recommended**
- **Common passwords blocked**
- **Breach database checking**

### Session Security
- **Automatic logout** after inactivity (30 minutes)
- **Session regeneration** after login
- **Concurrent session limits**
- **Device tracking and management**

### Account Protection
- **Failed login attempt limiting** (5 attempts per 15 minutes)
- **Account lockout** after multiple failures
- **Suspicious activity detection**
- **Login notification emails**

### CSRF Protection
- **Double-submit cookie pattern**
- **Required for state-changing operations**
- **Automatic token generation**
- **Token validation on server**

---

## 🚨 Troubleshooting Guide

### Common Login Issues

#### 1. "Invalid Credentials" Error

**Symptoms**: Login fails with "Invalid credentials" message

**Possible Causes**:
- Incorrect email or password
- Account not activated
- Account temporarily locked
- Server authentication issues

**Solutions**:
```bash
# Check if account exists and is active
curl -X POST https://localhost/api/v1/auth/jwt/login-debug \
  -H "Content-Type: application/json" \
  -d '{"username":"user@example.com","password":"test"}'
```

**Resolution Steps**:
1. **Verify credentials** - Double-check email and password
2. **Check caps lock** - Ensure correct capitalization
3. **Password reset** - Use "Forgot Password" if needed
4. **Account activation** - Check email for activation link
5. **Contact support** - If issue persists

#### 2. "Account Locked" Error

**Symptoms**: "Account temporarily locked due to multiple failed attempts"

**Causes**:
- 5+ failed login attempts within 15 minutes
- Automated security protection
- Suspicious login patterns

**Solutions**:
1. **Wait 15 minutes** - Lockout expires automatically
2. **Use backup method** - Try 2FA backup codes
3. **Reset password** - If compromised password suspected
4. **Contact administrator** - For manual unlock

#### 3. "Token Expired" Error

**Symptoms**: "Authentication token has expired" during session

**Causes**:
- Session exceeded 1-hour limit
- Token refresh failed
- Server time synchronization

**Solutions**:
```javascript
// Automatic token refresh
if (response.status === 401 && response.data.error.code === 'TOKEN_EXPIRED') {
  const refreshResponse = await fetch('/api/v1/auth/refresh', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${currentToken}` }
  });
  
  if (refreshResponse.ok) {
    const { access_token } = await refreshResponse.json();
    // Update token and retry request
  } else {
    // Redirect to login
    window.location.href = '/login';
  }
}
```

#### 4. "CSRF Token Invalid" Error

**Symptoms**: Form submissions fail with CSRF error

**Causes**:
- Missing CSRF token
- Expired CSRF token
- Token mismatch

**Solutions**:
```javascript
// Get fresh CSRF token
const csrfResponse = await fetch('/api/v1/auth/csrf-token');
const { csrf_token } = await csrfResponse.json();

// Include in request
await fetch('/api/v1/protected-endpoint', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRF-TOKEN': csrf_token
  },
  body: JSON.stringify(data)
});
```

#### 5. "2FA Code Invalid" Error

**Symptoms**: Two-factor authentication code rejected

**Causes**:
- Incorrect 6-digit code
- Time synchronization issues
- Used backup code already consumed

**Solutions**:
1. **Check time sync** - Ensure device time is accurate
2. **Wait for new code** - TOTP codes refresh every 30 seconds
3. **Use backup code** - Try single-use emergency codes
4. **Reset 2FA** - Contact support if device lost

#### 6. "WebAuthn Not Supported" Error

**Symptoms**: Passwordless login unavailable

**Causes**:
- Browser doesn't support WebAuthn
- No HTTPS connection
- No biometric/security key available

**Solutions**:
1. **Use supported browser** - Chrome 67+, Firefox 60+, Safari 14+
2. **Ensure HTTPS** - WebAuthn requires secure connection
3. **Enable biometrics** - Set up fingerprint/face unlock
4. **Use alternative** - Fall back to password + 2FA

### Advanced Troubleshooting

#### Debug Login Endpoint

For detailed error analysis:
```http
POST /api/v1/auth/jwt/login-debug
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "test_password"
}
```

**Debug Response**:
```json
{
  "success": false,
  "error": {
    "code": "ERR_401_INVALID_CREDENTIALS",
    "message": "Invalid credentials provided",
    "debug_info": {
      "user_exists": true,
      "account_active": true,
      "password_check": false,
      "last_login": "2025-08-05T10:30:00Z",
      "failed_attempts": 2
    }
  }
}
```

#### Session Information

Check current session details:
```http
GET /api/v1/enhanced/session/info
Authorization: Bearer your_token
```

**Response**:
```json
{
  "session_id": "uuid-string",
  "user_id": "user-uuid",
  "created_at": "2025-08-06T14:00:00Z",
  "expires_at": "2025-08-06T15:00:00Z",
  "device_info": {
    "browser": "Chrome 91.0",
    "os": "Windows 10",
    "ip": "192.168.1.100"
  },
  "security_flags": {
    "mfa_verified": true,
    "device_trusted": true
  }
}
```

#### Account Security Status

Monitor account security:
```http
GET /api/v1/enhanced-auth/security/status
Authorization: Bearer your_token
```

**Response**:
```json
{
  "account_status": "active",
  "security_score": 95,
  "enabled_features": {
    "two_factor": true,
    "webauthn": true,
    "oauth_google": false
  },
  "recent_activity": [
    {
      "action": "login",
      "timestamp": "2025-08-06T14:00:00Z",
      "ip": "192.168.1.100",
      "device": "Chrome/Windows"
    }
  ],
  "security_alerts": []
}
```

---

## ⚙️ Account Management

### Profile Management

#### View Profile
```http
GET /api/v1/profile/
Authorization: Bearer your_token
```

#### Update Profile
```http
PUT /api/v1/profile/
Content-Type: application/json
Authorization: Bearer your_token

{
  "display_name": "John Doe",
  "timezone": "America/New_York",
  "preferences": {
    "theme": "dark",
    "notifications": true
  }
}
```

### Password Management

#### Change Password
```http
POST /api/v1/auth/change-password
Content-Type: application/json
Authorization: Bearer your_token
X-CSRF-TOKEN: csrf_token

{
  "current_password": "current_password",
  "new_password": "new_secure_password"
}
```

#### Reset Password
1. **Request Reset**:
```http
POST /api/v1/auth/forgot-password
Content-Type: application/json

{
  "email": "user@example.com"
}
```

2. **Complete Reset** (from email link):
```http
POST /api/v1/auth/reset-password
Content-Type: application/json

{
  "token": "reset_token_from_email",
  "new_password": "new_secure_password"
}
```

### Device Management

#### List Connected Devices
```http
GET /native/devices
Authorization: Bearer your_token
```

#### Remove Device
```http
DELETE /native/devices/{device_id}
Authorization: Bearer your_token
X-CSRF-TOKEN: csrf_token
```

---

## 📱 Mobile App Authentication

### iOS/Android Setup

1. **Download App** from App Store/Play Store
2. **Open App** and tap "Sign In"
3. **Choose Method**:
   - Email/Password
   - Biometric (if available)
   - QR Code login from web

### Biometric Authentication

#### Enable Touch/Face ID
```javascript
// React Native example
import TouchID from 'react-native-touch-id';

const authenticateWithBiometric = async () => {
  try {
    const biometryType = await TouchID.isSupported();
    if (biometryType) {
      const isAuthenticated = await TouchID.authenticate('Authenticate to access your account');
      if (isAuthenticated) {
        // Proceed with app login
        return await loginWithStoredCredentials();
      }
    }
  } catch (error) {
    console.log('Biometric authentication failed', error);
    // Fall back to password login
  }
};
```

---

## 🔧 Developer Integration

### Authentication Middleware

#### Custom Authentication Check
```python
from fastapi import HTTPException, Depends
from api.dependencies import get_current_user

@app.get("/protected-route")
async def protected_route(current_user = Depends(get_current_user)):
    return {"user_id": current_user.id, "message": "Access granted"}
```

#### WebSocket Authentication
```python
from fastapi import WebSocket, WebSocketDisconnect
from api.dependencies import get_websocket_user

@app.websocket("/ws/secure")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        # Authenticate WebSocket connection
        user = await get_websocket_user(websocket)
        
        while True:
            data = await websocket.receive_text()
            # Process authenticated WebSocket messages
            
    except WebSocketDisconnect:
        pass
```

### Frontend Authentication

#### JavaScript/TypeScript Integration
```typescript
class AuthService {
  private token: string | null = null;
  
  async login(username: string, password: string): Promise<boolean> {
    try {
      const response = await fetch('/api/v1/auth/jwt/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      
      if (response.ok) {
        const data = await response.json();
        this.token = data.access_token;
        localStorage.setItem('auth_token', this.token);
        return true;
      }
      return false;
    } catch (error) {
      console.error('Login failed:', error);
      return false;
    }
  }
  
  async makeAuthenticatedRequest(url: string, options: RequestInit = {}) {
    const headers = {
      ...options.headers,
      'Authorization': `Bearer ${this.token}`
    };
    
    return fetch(url, { ...options, headers });
  }
  
  logout() {
    this.token = null;
    localStorage.removeItem('auth_token');
    window.location.href = '/login';
  }
}
```

---

## 📊 Authentication Analytics

### Login Metrics

#### Track Login Attempts
```http
GET /api/v1/analytics/login-metrics
Authorization: Bearer admin_token

# Response
{
  "successful_logins": 1250,
  "failed_attempts": 45,
  "unique_users": 89,
  "peak_hours": ["09:00", "14:00", "20:00"],
  "authentication_methods": {
    "password": 70,
    "oauth_google": 20,
    "webauthn": 10
  }
}
```

#### Security Events
```http
GET /api/v1/security-metrics/incidents
Authorization: Bearer admin_token

# Response
{
  "incidents": [
    {
      "type": "brute_force_attempt",
      "ip": "192.168.1.100",
      "timestamp": "2025-08-06T14:30:22Z",
      "user_account": "user@example.com",
      "status": "blocked"
    }
  ]
}
```

---

## 🎯 Best Practices

### For Users

1. **Strong Passwords**
   - Use unique passwords for AI Workflow Engine
   - Include uppercase, lowercase, numbers, symbols
   - Avoid personal information

2. **Enable 2FA**
   - Set up two-factor authentication
   - Keep backup codes secure and accessible
   - Use authenticator apps (not SMS)

3. **Device Security**
   - Log out from shared devices
   - Monitor connected devices regularly
   - Remove unused device connections

4. **Stay Updated**
   - Keep browsers updated for WebAuthn support
   - Update mobile apps regularly
   - Monitor account activity

### For Developers

1. **Token Management**
   - Store tokens securely (not in localStorage for sensitive apps)
   - Implement automatic token refresh
   - Handle token expiration gracefully

2. **Error Handling**
   - Provide clear error messages
   - Log authentication failures
   - Implement retry mechanisms with backoff

3. **Security Headers**
   - Always include CSRF tokens
   - Use HTTPS for all authentication
   - Implement proper CORS policies

4. **Testing**
   - Test all authentication flows
   - Verify token expiration handling
   - Test error scenarios

---

## 🆘 Support & Contact

### Self-Help Resources
- **Documentation**: This guide covers most scenarios
- **API Documentation**: `/docs` endpoint for technical details
- **Debug Endpoints**: Use login-debug for detailed error analysis

### Contact Support

For issues not resolved by this guide:

1. **Check System Status**: Visit `/public/status` for service availability
2. **Bug Reports**: Submit via `/api/v1/bug-reports/submit`
3. **Security Issues**: Contact security team immediately
4. **Account Recovery**: Use automated password reset first

### Emergency Access

If locked out completely:
1. **Use backup codes** (if 2FA enabled)
2. **Reset password** via email
3. **Contact administrator** for manual account unlock
4. **Security review** may be required for suspicious activity

---

This comprehensive guide covers all authentication methods, troubleshooting procedures, and best practices for the AI Workflow Engine authentication system.