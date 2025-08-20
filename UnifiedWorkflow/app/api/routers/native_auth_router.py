
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from api.auth import authenticate_user, create_access_token, create_refresh_token
from shared.database.models import User
from shared.utils.database_setup import get_db
from shared.services.totp_service import TOTPService

router = APIRouter()

class NativeLoginRequest(BaseModel):
    username: str
    password: str

class NativeLoginResponse(BaseModel):
    access_token: str | None = None
    token_type: str = "bearer"
    message: str | None = None
    two_factor_required: bool = False

class NativeTwoFactorRequest(BaseModel):
    username: str
    totp_code: str

@router.post("/login", response_model=NativeLoginResponse)
async def native_login(
    request: NativeLoginRequest,
    db: Session = Depends(get_db)
):
    print(f"[DEBUG] Native login endpoint hit!")
    print(f"[DEBUG] Login attempt for username: {request.username}")
    print(f"[DEBUG] Password length: {len(request.password) if request.password else 0}")
    user = authenticate_user(db, request.username, request.password)
    if not user:
        print(f"[DEBUG] Authentication failed for user: {request.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    if user.status.value != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active"
        )

    if user.two_factor_auth is not None:
        print(f"[DEBUG] 2FA required for user: {request.username}")
        return NativeLoginResponse(two_factor_required=True, message="Two-factor authentication required.")
    
    print(f"[DEBUG] Login successful for user: {request.username}")

    token_data = {
        "sub": user.email,
        "id": user.id,
        "role": user.role.value if hasattr(user.role, 'value') else str(user.role)
    }
    access_token = create_access_token(token_data)
    create_refresh_token(token_data) # This creates and stores the refresh token, but doesn't return it directly

    return NativeLoginResponse(access_token=access_token)

@router.post("/verify-2fa", response_model=NativeLoginResponse)
async def native_verify_2fa(
    request: NativeTwoFactorRequest,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == request.username).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.two_factor_auth is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Two-factor authentication not enabled for this user.")

    totp_service = TOTPService()
    is_valid, error_msg = totp_service.authenticate_with_totp(db, user, request.totp_code)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid 2FA code.")

    token_data = {
        "sub": user.email,
        "id": user.id,
        "role": user.role.value if hasattr(user.role, 'value') else str(user.role)
    }
    access_token = create_access_token(token_data)
    create_refresh_token(token_data)

    return NativeLoginResponse(access_token=access_token)
