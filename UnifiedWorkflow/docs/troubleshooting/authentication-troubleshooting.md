# Authentication Troubleshooting Guide

## Issue: Registration Works But Login Fails

### Problem Description
Users can register successfully, but when they try to log in with the same credentials, they receive "Incorrect email/username or password" errors.

### Root Cause Analysis
The issue was identified to be related to historical user accounts that were created with different passwords or different password hashing mechanisms before the current authentication system was fully stabilized.

### Investigation Results
1. ✅ **Registration endpoint** - Working correctly, creates users with proper password hashing
2. ✅ **Login endpoint** - Working correctly for newly registered users
3. ✅ **Password hashing/verification** - Working correctly with Argon2id algorithm
4. ❌ **Historical user accounts** - Some existing users have passwords that don't match expected values

### Solution
Added debug and admin endpoints to troubleshoot and resolve password issues for existing users.

## Debug Tools

### 1. Password Verification Debug Endpoint
**Endpoint:** `POST /api/v1/auth/debug/test-password`

**Purpose:** Test password verification for any user without affecting their account.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "testpassword"
}
```

**Response:**
```json
{
  "user_found": true,
  "user_id": 46,
  "email": "user@example.com",
  "is_active": true,
  "status": "active",
  "password_valid": false,
  "hashed_password_preview": "$argon2id$v=19$m=65536,t=3,p=4$...",
  "message": "Password verification failed"
}
```

### 2. Admin Password Reset Endpoint
**Endpoint:** `POST /api/v1/auth/admin/reset-password`

**Purpose:** Reset user passwords for troubleshooting (requires admin key).

**Request:**
```json
{
  "email": "user@example.com",
  "new_password": "newpassword123",
  "admin_key": "admin-reset-key-change-in-production"
}
```

**Response:**
```json
{
  "message": "Password reset successful for user@example.com",
  "user_id": 46
}
```

## Troubleshooting Steps

### Step 1: Verify the Issue
1. Test login with the user's expected credentials
2. If login fails, use the debug endpoint to verify:
   - User exists and is active
   - Password verification result

### Step 2: Reset Password (If Needed)
1. Use the admin reset endpoint to set a known password
2. Test login again with the new password
3. Verify with debug endpoint that password verification now succeeds

### Step 3: Test Production
1. Verify the fix works on production environment
2. Test both registration and login flows

## Example Troubleshooting Session

```bash
# 1. Test current login (fails)
curl -X POST "https://aiwfe.com/api/v1/auth/jwt/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "problem-user@example.com", "password": "expectedpassword"}'

# 2. Debug password verification
curl -X POST "https://aiwfe.com/api/v1/auth/debug/test-password" \
  -H "Content-Type: application/json" \
  -d '{"email": "problem-user@example.com", "password": "expectedpassword"}'

# 3. Reset password (if verification failed)
curl -X POST "https://aiwfe.com/api/v1/auth/admin/reset-password" \
  -H "Content-Type: application/json" \
  -d '{"email": "problem-user@example.com", "new_password": "expectedpassword", "admin_key": "admin-key"}'

# 4. Test login again (should now succeed)
curl -X POST "https://aiwfe.com/api/v1/auth/jwt/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "problem-user@example.com", "password": "expectedpassword"}'
```

## Security Considerations

1. **Admin Key**: Change the default admin key in production environment
2. **Debug Endpoint**: Consider disabling in production or adding additional security
3. **CSRF Exemption**: Debug and admin endpoints are exempted from CSRF protection for troubleshooting
4. **Logging**: All password reset operations are logged for audit purposes

## Environment Variables

Add to your `.env` file for production:
```bash
ADMIN_RESET_KEY=your-secure-admin-key-here
```

## Prevention

To prevent similar issues in the future:
1. Ensure consistent password hashing across all user creation methods
2. Add password verification tests to the test suite
3. Document any manual user creation procedures
4. Consider implementing password migration tools for future schema changes