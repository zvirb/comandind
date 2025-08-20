"""
Emergency API main entry point - minimal authentication service.
This bypasses complex imports to get authentication working quickly.
"""
import logging
from fastapi import FastAPI, HTTPException, Depends, Form, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pwdlib.hashers.argon2 import Argon2Hasher
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
import asyncpg
import os
from pydantic import BaseModel

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI Workflow Engine API (Emergency Mode)",
    description="Minimal authentication service with bcrypt support",
    version="1.0.0-emergency"
)

# Setup CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Argon2 hasher
hasher = Argon2Hasher()
security = HTTPBearer()

# JWT configuration
SECRET_KEY = "test_secret_key_for_development"  # Use env var in production
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str

async def get_db_connection():
    return await asyncpg.connect(
        host='postgres',
        port=5432,
        user='postgres', 
        password='OVie0GVt2jSUi9aLrh9swS64KGraIZyHLprAEimLwKc=',
        database='ai_workflow_engine'
    )

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "api-emergency",
        "argon2_available": True,
        "message": "API container is running with Argon2 support"
    }

@app.get("/api/v1/health")
async def v1_health():
    """API v1 health check endpoint for Caddy proxy."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "api-emergency",
        "version": "v1",
        "argon2_available": True
    }

@app.get("/api/v1/health/integration")
async def health_integration():
    """Integration health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "api-emergency", 
        "version": "v1",
        "argon2_available": True
    }

@app.get("/api/v1/auth/health")
async def auth_health():
    """Authentication service health check."""
    try:
        # Test Argon2 functionality
        test_password = "test123"
        test_hash = hasher.hash(test_password)
        is_valid = hasher.verify(test_password, test_hash)
        
        return {
            "status": "healthy", 
            "argon2_working": is_valid,
            "hasher_type": "Argon2Hasher",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Authentication health check failed: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@app.post("/api/v1/auth/test-argon2")
async def test_argon2(password: str = "testpassword"):
    """Test Argon2 hashing functionality."""
    try:
        # Test Argon2 hashing and verification
        hash_result = hasher.hash(password)
        verify_result = hasher.verify(password, hash_result)
        
        return {
            "success": True,
            "password_tested": password,
            "hash_created": bool(hash_result),
            "verification_passed": verify_result,
            "argon2_available": True,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Argon2 test failed: {e}")
        raise HTTPException(status_code=500, detail=f"Argon2 test failed: {str(e)}")

def create_access_token(data: dict) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def set_auth_cookies(response: Response, access_token: str):
    """Set authentication cookies."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        secure=False,  # localhost development
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/"
    )

@app.post("/api/v1/auth/jwt/login")
async def jwt_login(login_data: LoginRequest, response: Response):
    """JWT login endpoint."""
    try:
        conn = await get_db_connection()
        try:
            # Get user from database
            row = await conn.fetchrow(
                "SELECT id, email, hashed_password, role, is_active FROM users WHERE email = $1",
                login_data.email
            )
            
            if not row:
                raise HTTPException(status_code=401, detail="Invalid credentials")
            
            if not row['is_active']:
                raise HTTPException(status_code=401, detail="Account disabled")
            
            # Verify password
            if not hasher.verify(login_data.password, row['hashed_password']):
                raise HTTPException(status_code=401, detail="Invalid credentials")
            
            # Create JWT token
            token_data = {
                "sub": row['email'],
                "id": row['id'],
                "role": row['role']
            }
            access_token = create_access_token(token_data)
            
            # Set cookies
            set_auth_cookies(response, access_token)
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "id": row['id'],
                    "email": row['email'],
                    "role": row['role']
                }
            }
            
        finally:
            await conn.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """Verify JWT token."""
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/api/v1/auth/register")
async def register_user(register_data: RegisterRequest, response: Response):
    """User registration endpoint."""
    try:
        conn = await get_db_connection()
        try:
            # Check if user exists
            existing_user = await conn.fetchrow(
                "SELECT id FROM users WHERE email = $1",
                register_data.email
            )
            
            if existing_user:
                raise HTTPException(status_code=400, detail="Email already registered")
            
            # Hash password
            hashed_password = hasher.hash(register_data.password)
            
            # Insert new user
            new_user = await conn.fetchrow(
                """INSERT INTO users (email, hashed_password, role, is_active) 
                   VALUES ($1, $2, $3, $4) 
                   RETURNING id, email, role""",
                register_data.email, hashed_password, "user", True
            )
            
            # Create JWT token
            token_data = {
                "sub": new_user['email'],
                "id": new_user['id'],
                "role": new_user['role']
            }
            access_token = create_access_token(token_data)
            
            # Set cookies
            set_auth_cookies(response, access_token)
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "id": new_user['id'],
                    "email": new_user['email'],
                    "role": new_user['role']
                },
                "message": "Registration successful"
            }
            
        finally:
            await conn.close()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

@app.get("/api/v1/session/validate")
async def validate_session(request: Request):
    """Validate session from cookie."""
    try:
        # Get token from cookie
        token = request.cookies.get("access_token")
        if not token:
            raise HTTPException(status_code=401, detail="No token")
        
        # Verify token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        return {
            "valid": True,
            "user": {
                "id": payload.get("id"),
                "email": payload.get("sub"),
                "role": payload.get("role")
            }
        }
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Session validation error: {e}")
        raise HTTPException(status_code=401, detail="Session validation failed")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)