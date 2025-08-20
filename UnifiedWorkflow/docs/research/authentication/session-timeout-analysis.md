# Session Timeout Analysis: 15-Second Logout Issue

**Date:** August 6, 2025  
**Analyst:** codebase-research-analyst  
**Issue:** Users experiencing automatic logout after 15 seconds with error "Failed to load settings: Authentication required. Please log in again."

## Executive Summary

The 15-second logout issue is **NOT caused by JWT token expiration** (tokens are valid for 60 minutes), but by a **compatibility mismatch between legacy and enhanced authentication systems** that causes immediate validation failures.

## Root Cause Analysis

### 1. Token Generation vs Validation Mismatch

**Problem**: The login endpoint creates legacy JWT tokens, but the settings endpoint tries enhanced JWT validation first, which fails for legacy tokens.

**Login Token Generation** (`/app/api/auth.py:101-115`):
```python
def create_access_token(data: dict[str, Any]) -> str:
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)  # 60 minutes
    
    to_encode.update({
        "exp": expire,
        "iat": now,
        "last_activity": now.isoformat(),
        "activity_timeout": (now + timedelta(minutes=ACTIVITY_TIMEOUT_MINUTES)).isoformat()
    })
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

**Token Format Created**:
```json
{
    "sub": "user@example.com",
    "id": 3,
    "role": "user", 
    "exp": 1754487306,
    "iat": 1754483706,
    "last_activity": "2025-08-06T12:35:06.907466+00:00",
    "activity_timeout": "2025-08-06T13:05:06.907466+00:00"
}
```

### 2. Enhanced JWT Service Expectation Mismatch

**Settings Endpoint Validation** (`/app/api/dependencies.py:145-158`):
```python
token_data = await enhanced_jwt_service.verify_token(
    session=db,
    token=token,
    required_scopes=["read"],
    ip_address=request.client.host if request.client else None,
    user_agent=request.headers.get("user-agent")
)
```

**Enhanced JWT Service Expected Format** (`/app/shared/services/enhanced_jwt_service.py:275-278`):
```python
# Enhanced format: sub=user_id, email=email
if "email" in payload and payload.get("sub"):
    try:
        user_id = int(payload["sub"])  # Expects numeric user ID
    except (ValueError, TypeError):
        # Falls back to legacy, but fails
```

**Issue**: Legacy token has `sub="user@example.com"` (email) but enhanced service expects `sub="3"` (user_id).

### 3. Compatibility Layer Failure

**Authentication Flow** (`/app/api/dependencies.py:170-176`):
```python
except Exception as e:
    logger.debug(f"Enhanced JWT validation failed: {e}")
    # Continue to legacy validation

# Fallback to legacy authentication (compatibility layer)
from api.auth_compatibility import enhanced_get_current_user
return await enhanced_get_current_user(request, db)
```

**Root Problem**: The enhanced JWT service fails to parse the legacy token correctly, but the compatibility layer also has issues with the database session or security audit service calls.

## Configuration Analysis

### JWT Token Settings
- **Access Token Expiration**: 60 minutes (`ACCESS_TOKEN_EXPIRE_MINUTES = 60`)
- **Refresh Token Expiration**: 7 days (`REFRESH_TOKEN_EXPIRE_DAYS = 7`)
- **Activity Timeout**: 30 minutes (`ACTIVITY_TIMEOUT_MINUTES = 30`) - **DISABLED**

### Redis Cache TTL Settings (`/app/shared/services/redis_cache_service.py:46-50`)
- **Session TTL**: 30 minutes (`session_ttl = 1800`)
- **Auth TTL**: 15 minutes (`auth_ttl = 900`)
- **Default TTL**: 1 hour (`default_ttl = 3600`)

## Test Evidence

**Debug Script Results** (`/debug_15_second_logout.py`):
```
Token expires at: 2025-08-06 13:35:06+00:00
Current time: 2025-08-06 12:35:06.918903+00:00
Time until expiration: 0:59:59.081097
Time until expiration (seconds): 3599.081097

❌ Settings endpoint FAILED at 5.0s - 401 Unauthorized
Response: {"success":false,"error":{"code":"ERR_401_A3454935","message":"Could not validate credentials",...
```

**Conclusion**: Token is valid for almost 60 minutes but authentication fails within 5 seconds.

## File Locations & Configurations

### Authentication Files
- **Legacy JWT Service**: `/app/api/auth.py`
  - `ACCESS_TOKEN_EXPIRE_MINUTES = 60`
  - `ACTIVITY_TIMEOUT_MINUTES = 30` (disabled)
  - Creates legacy token format

- **Enhanced JWT Service**: `/app/shared/services/enhanced_jwt_service.py`
  - `access_token_expire_minutes = 60`
  - Expects enhanced token format
  - Fails on legacy tokens

- **Authentication Dependencies**: `/app/api/dependencies.py`
  - `get_current_user()` function (line 119)
  - Tries enhanced validation first, falls back to legacy

- **Compatibility Layer**: `/app/api/auth_compatibility.py`
  - `enhanced_get_current_user()` function (line 80)
  - Handles transition between systems

### Settings Endpoint
- **Settings Router**: `/app/api/routers/settings_router.py`
  - Line 20: `get_user_settings()` endpoint
  - Depends on: `Depends(get_current_user)`

## Solution Recommendations

### 1. Immediate Fix: Force Legacy Token Validation
**File**: `/app/api/dependencies.py`
**Action**: Skip enhanced JWT validation for legacy tokens
```python
# In get_current_user function, prioritize legacy validation
try:
    # First try legacy/simple token validation (what login creates)
    from api.auth_compatibility import get_user_from_legacy_token
    user = await get_user_from_legacy_token(request, db)
    if user:
        return user
    
    # Only try enhanced if legacy fails
    # ... enhanced JWT validation
```

### 2. Long-term Fix: Standardize Token Format
**File**: `/app/api/routers/enhanced_auth_router.py`
**Action**: Update login endpoint to create enhanced format tokens
```python
# Use enhanced JWT service for token creation
token_data = await enhanced_jwt_service.create_access_token(
    session=db,
    user_id=user.id,
    scopes=["read", "write"],
    ip_address=request.client.host
)
```

### 3. Configuration Review: Redis Cache
**File**: `/app/shared/services/redis_cache_service.py`
**Issue**: `auth_ttl = 900` (15 minutes) might be affecting session persistence
**Action**: Increase auth TTL to match JWT expiration:
```python
auth_ttl = 3600  # Match 60-minute JWT expiration
```

## Technical Analysis Summary

| Component | Configuration | Status | Issue |
|-----------|--------------|--------|-------|
| JWT Token Expiration | 60 minutes | ✅ Correct | None |
| Token Validation | Enhanced + Legacy | ❌ Failing | Format mismatch |
| Redis Auth TTL | 15 minutes | ⚠️ Suspicious | May cause issues |
| Settings Endpoint | Depends on auth | ❌ Failing | Validation failure |
| Compatibility Layer | Fallback system | ❌ Failing | Database/audit issues |

## Action Items

1. **Priority 1**: Fix token format compatibility in `get_current_user()`
2. **Priority 2**: Review and increase Redis auth TTL from 15 to 60 minutes  
3. **Priority 3**: Standardize all endpoints to use same token validation approach
4. **Priority 4**: Add comprehensive logging to identify specific validation failure points
5. **Priority 5**: Consider deprecating dual authentication systems for single approach

The 15-second logout is caused by authentication validation failure, not token expiration. The fix involves resolving the compatibility between legacy and enhanced JWT systems.