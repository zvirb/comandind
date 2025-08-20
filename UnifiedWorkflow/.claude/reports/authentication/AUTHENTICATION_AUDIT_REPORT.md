# Authentication System Audit Report
## Session Timeout Issue Analysis

Generated: 2025-08-06

---

### 🚨 Finding: Token Format Mismatch Between Creation and Validation
- **Severity:** Critical
- **Category:** API Contract (Python/JS)
- **File(s):** `/home/marku/ai_workflow_engine/app/api/routers/custom_auth_router.py`, `/home/marku/ai_workflow_engine/app/api/dependencies.py`
- **Line(s):** `custom_auth_router.py:156-160`, `dependencies.py:79-95`

#### Description
The login endpoint creates JWT tokens with format `{"sub": email, "id": user_id, "role": role}` but the validation logic in dependencies.py first attempts to parse an "enhanced" format where `sub` should be the user_id as a string. This causes initial validation to fail, forcing fallback to legacy validation on every request, adding latency and potential failure points.

#### Current Mismatch (Code Example)
```python
# custom_auth_router.py:156-160 - Token Creation
token_data = {
    "sub": user.email,  # Email as subject
    "id": user.id,      # User ID as separate field
    "role": user.role.value
}
```

```python
# dependencies.py:79-86 - Token Validation (Enhanced Format First)
if "email" in payload and "sub" in payload:
    try:
        user_id = int(payload.get("sub"))  # Expects sub to be user_id!
        email = payload.get("email")       # Expects email field
        role = payload.get("role")
        logger.info(f"Using enhanced token format for user {user_id}")
    except (ValueError, TypeError):
        logger.warning("Failed to parse enhanced token format")
```

#### Recommended Mediation (Code Example)
```python
# custom_auth_router.py - Align token creation with validation expectations
token_data = {
    "sub": str(user.id),    # User ID as string (enhanced format)
    "email": user.email,     # Add email field for enhanced format
    "id": user.id,           # Keep for backward compatibility
    "role": user.role.value
}
```

#### Justification
Aligning token creation with the enhanced format that validation expects first will eliminate unnecessary fallback logic, reduce latency, and prevent potential authentication failures when the fallback mechanism fails.

---

### 🚨 Finding: Activity Timeout Disabled But Still Checked
- **Severity:** High
- **Category:** Data Serialization
- **File(s):** `/home/marku/ai_workflow_engine/app/api/auth.py`, `/home/marku/ai_workflow_engine/app/api/dependencies.py`
- **Line(s):** `auth.py:144-164`, `dependencies.py:102-107`

#### Description
The `is_token_activity_expired` function is hardcoded to return `False` (line 149) with a comment stating it's "TEMPORARILY DISABLED" due to being "too strict". However, dependencies.py still calls this function (line 102), adding unnecessary overhead and creating confusion about whether activity timeout is actually enforced.

#### Current Mismatch (Code Example)
```python
# auth.py:144-149
def is_token_activity_expired(token_payload: dict) -> bool:
    """Check if token has exceeded activity timeout."""
    # TEMPORARILY DISABLED: Activity timeout is too strict and causing session issues
    # The JWT token expiration (15 minutes) is sufficient for security
    # TODO: Implement proper activity timeout refresh mechanism
    return False  # Always returns False!
```

```python
# dependencies.py:102-107
# Still checking activity timeout even though it's disabled
if is_token_activity_expired(payload):
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session expired due to inactivity",
        headers={"WWW-Authenticate": "Bearer"},
    )
```

#### Recommended Mediation (Code Example)
```python
# dependencies.py - Skip activity timeout check until properly implemented
# Comment out or remove the activity timeout check
# if is_token_activity_expired(payload):
#     raise HTTPException(...)

# OR implement proper activity refresh in auth.py
def is_token_activity_expired(token_payload: dict) -> bool:
    """Check if token has exceeded activity timeout with grace period."""
    activity_timeout_str = token_payload.get("activity_timeout")
    if not activity_timeout_str:
        return False
    
    try:
        activity_timeout = datetime.fromisoformat(activity_timeout_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        # Add 5-minute grace period for active sessions
        grace_period = timedelta(minutes=5)
        return now > (activity_timeout + grace_period)
    except (ValueError, TypeError):
        return False  # Don't expire on parse errors
```

#### Justification
Either properly implement activity timeout with a grace period or completely remove the check to avoid confusion and unnecessary processing.

---

### 🚨 Finding: Multiple Authentication Routers Creating Confusion
- **Severity:** Medium
- **Category:** API Contract (Python/JS)
- **File(s):** `/home/marku/ai_workflow_engine/app/api/main.py`, `/home/marku/ai_workflow_engine/app/api/routers/`
- **Line(s):** `main.py:74-81, 411-421`

#### Description
The codebase has multiple authentication routers (custom_auth_router, enhanced_auth_router, native_auth_router, oauth_router) all imported but only custom_auth_router is mounted. This creates confusion about which authentication system is actually in use and may lead to inconsistent authentication behavior.

#### Current Mismatch (Code Example)
```python
# main.py:74-81 - Multiple auth routers imported
from api.routers.custom_auth_router import router as custom_auth_router
from api.routers.oauth_router import router as oauth_router
from api.routers.native_auth_router import router as native_auth_router
from api.routers.enhanced_auth_router import router as enhanced_auth_router

# main.py:411-421 - Only custom_auth_router is mounted
app.include_router(
    custom_auth_router,
    prefix="/api/v1/auth",
    tags=["Authentication"],
)
```

#### Recommended Mediation (Code Example)
```python
# main.py - Clean up unused imports and clarify authentication strategy
# Only import the router that's actually being used
from api.routers.custom_auth_router import router as auth_router

# Mount with clear documentation
app.include_router(
    auth_router,
    prefix="/api/v1/auth",
    tags=["Authentication"],
)
# Document: Using custom_auth_router as primary authentication system
# enhanced_auth_router and native_auth_router are deprecated
```

#### Justification
Removing unused authentication routers reduces confusion and prevents accidental use of incompatible authentication systems.

---

### 🚨 Finding: Enhanced JWT Service Fallback Creates Unnecessary Complexity
- **Severity:** High  
- **Category:** API Contract (Python/JS)
- **File(s):** `/home/marku/ai_workflow_engine/app/api/dependencies.py`, `/home/marku/ai_workflow_engine/app/api/auth_compatibility.py`
- **Line(s):** `dependencies.py:145-176`, `auth_compatibility.py:98-138`

#### Description
The get_current_user function attempts enhanced JWT validation first, then falls back to legacy validation through auth_compatibility.py, which then tries legacy validation first and enhanced second. This circular and redundant validation pattern creates unnecessary complexity and potential infinite loops.

#### Current Mismatch (Code Example)
```python
# dependencies.py:145-176
async def get_current_user(request: Request, db: AsyncSession = Depends(get_async_session)) -> User:
    try:
        # Try enhanced JWT service validation first
        token_data = await enhanced_jwt_service.verify_token(...)
        if token_data["valid"]:
            # Get user from database
            ...
    except Exception as e:
        logger.debug(f"Enhanced JWT validation failed: {e}")
        
    # Fallback to legacy authentication (compatibility layer)
    from api.auth_compatibility import enhanced_get_current_user
    return await enhanced_get_current_user(request, db)  # This tries legacy first!
```

#### Recommended Mediation (Code Example)
```python
# dependencies.py - Simplify to single validation path
async def get_current_user(request: Request, db: AsyncSession = Depends(get_async_session)) -> User:
    # Use the standard token validation that matches login token format
    token_data = get_current_user_payload(request)
    
    # Get user from database
    from sqlalchemy import select
    result = await db.execute(select(User).where(User.id == token_data.id))
    user = result.scalar_one_or_none()
    
    if not user or not user.is_active:
        raise credentials_exception
    
    return user
```

#### Justification
A single, clear validation path that matches the token format created during login eliminates confusion and reduces failure points.

---

### 🚨 Finding: CSRF Token Format Inconsistency
- **Severity:** Medium
- **Category:** Network & Transport
- **File(s):** `/home/marku/ai_workflow_engine/app/api/auth.py`, `/home/marku/ai_workflow_engine/app/api/routers/custom_auth_router.py`
- **Line(s):** `auth.py:43-67`, `custom_auth_router.py:301-366`

#### Description
CSRF token generation is duplicated in multiple places with slight variations. The auth.py generate_csrf_token and the /csrf-token endpoint in custom_auth_router.py both generate tokens, potentially with different formats or secrets, leading to validation failures.

#### Current Mismatch (Code Example)
```python
# auth.py:43-67 - One CSRF generation method
def generate_csrf_token() -> str:
    csrf_secret = settings.CSRF_SECRET_KEY
    if hasattr(csrf_secret, 'get_secret_value'):
        csrf_secret = csrf_secret.get_secret_value()
    ...

# custom_auth_router.py:316-330 - Different CSRF generation
csrf_secret = os.getenv("CSRF_SECRET_KEY", SECRET_KEY)  # Different fallback!
if hasattr(csrf_secret, 'get_secret_value'):
    csrf_secret = csrf_secret.get_secret_value()
```

#### Recommended Mediation (Code Example)
```python
# custom_auth_router.py - Use the centralized CSRF generation
from api.auth import generate_csrf_token

@router.get("/csrf-token")
async def get_csrf_token(request: Request, response: Response):
    csrf_token = generate_csrf_token()  # Use centralized function
    
    # Set cookie and return token
    ...
```

#### Justification
Using a single CSRF token generation function ensures consistency across the application and prevents validation failures due to format mismatches.

---

### 🚨 Finding: Cookie Domain Configuration Inconsistency
- **Severity:** High
- **Category:** Network & Transport
- **File(s):** `/home/marku/ai_workflow_engine/app/api/auth.py`
- **Line(s):** `auth.py:180-192`

#### Description
Cookie domain is set to `.aiwfe.com` in production, which may not match the actual deployment domain. This can cause cookies to not be sent with requests, leading to authentication failures.

#### Current Mismatch (Code Example)
```python
# auth.py:180-192
domain_name = os.getenv('DOMAIN', 'aiwfe.com')  # Hardcoded default
cookie_domain = f".{domain_name}" if is_production and domain_name not in ['localhost', '127.0.0.1'] else None
```

#### Recommended Mediation (Code Example)
```python
# auth.py - Make domain configuration more robust
domain_name = os.getenv('DOMAIN', None)
if is_production and domain_name:
    # Only set explicit domain if properly configured
    cookie_domain = f".{domain_name}" if not domain_name.startswith('.') else domain_name
else:
    # Let browser handle domain for development
    cookie_domain = None
```

#### Justification
Proper domain configuration ensures cookies are sent with requests across all deployment environments.

---

## Summary and Immediate Actions

### Root Cause
The session timeout issue is primarily caused by:
1. **Token format mismatch** between creation (legacy format) and validation (expects enhanced format first)
2. **Complex fallback chains** that may fail under certain conditions
3. **Disabled activity timeout** still being checked in validation

### Immediate Fix Required
1. **Restart the backend service** to apply any recent changes:
   ```bash
   docker-compose restart api
   ```

2. **Align token formats** - Update custom_auth_router.py to create tokens in the enhanced format that validation expects

3. **Simplify validation** - Remove unnecessary fallback logic in dependencies.py

4. **Fix CSRF token generation** - Use a single, consistent CSRF token generation method

### Testing
Use the provided test scripts to verify the fixes:
```bash
python test_token_format_validation.py
python test_live_authentication_flow.py
```

These changes will eliminate the 401 errors appearing after successful login and ensure stable session management.