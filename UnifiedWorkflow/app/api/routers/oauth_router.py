"""
OAuth router for handling Google OAuth authentication and token management.
Provides endpoints for connecting and managing Google services.
"""

import logging
import secrets
import urllib.parse
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, HTTPException, status, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import httpx

from api.dependencies import get_current_user
from shared.utils.database_setup import get_db
from shared.database.models import User, UserOAuthToken, GoogleService
from shared.utils.config import get_settings
from api.services.oauth_token_manager import get_oauth_token_manager


def get_public_base_url(request: Request) -> str:
    """Get the public base URL from request, with production domain override.
    
    For production OAuth callbacks, always use https://aiwfe.com to ensure
    Google OAuth redirect URI consistency. Only falls back to dynamic
    construction in development environments.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        str: Public base URL (always 'https://aiwfe.com' in production,
             dynamic construction for development)
    """
    # Check for proxy headers indicating production environment
    forwarded_host = request.headers.get("x-forwarded-host")
    forwarded_proto = request.headers.get("x-forwarded-proto")
    
    # Production: Always use static aiwfe.com domain for OAuth consistency
    if forwarded_host == "aiwfe.com" or forwarded_host == "www.aiwfe.com":
        public_url = "https://aiwfe.com"
        logger.debug(f"Production environment detected, using static domain: {public_url}")
        return public_url
    
    # Development: Use proxy headers if available
    if forwarded_host and forwarded_proto:
        public_url = f"{forwarded_proto}://{forwarded_host}"
        logger.debug(f"Development environment with proxy headers: {public_url}")
        return public_url
    
    # Local development fallback
    base_url = str(request.base_url).rstrip('/')
    logger.debug(f"Local development fallback: {base_url}")
    return base_url

logger = logging.getLogger(__name__)
router = APIRouter()


class OAuthStatus(BaseModel):
    """OAuth connection status response."""
    connected: bool
    email: Optional[str] = None
    status: str


class OAuthConfig(BaseModel):
    """OAuth configuration check response."""
    enabled: bool
    configured: bool
    client_id: Optional[str] = None


@router.get("/google/status")
async def get_google_oauth_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get Google OAuth connection status for all services.
    """
    try:
        # Query all OAuth tokens for the current user
        oauth_tokens = db.query(UserOAuthToken).filter(
            UserOAuthToken.user_id == current_user.id
        ).all()
        
        # Create a mapping of service to token
        token_map = {token.service: token for token in oauth_tokens}
        
        result = {}
        for service in GoogleService:
            token = token_map.get(service)
            if token:
                result[service.value] = {
                    "connected": True,
                    "email": token.service_email,
                    "connected_at": token.created_at.isoformat() if token.created_at else None,
                    "expires_at": token.token_expiry.isoformat() if token.token_expiry else None
                }
            else:
                result[service.value] = {
                    "connected": False,
                    "email": None
                }
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting Google OAuth status: {e}", exc_info=True)
        # Return safe default
        return {
            "calendar": {"connected": False, "email": None},
            "drive": {"connected": False, "email": None},
            "gmail": {"connected": False, "email": None}
        }


@router.get("/google/config/check")
async def check_google_oauth_config():
    """
    Check Google OAuth configuration status.
    """
    try:
        settings = get_settings()
        settings.load_google_oauth_from_secrets()
        
        has_client_id = bool(settings.GOOGLE_CLIENT_ID)
        has_client_secret = bool(settings.GOOGLE_CLIENT_SECRET)
        
        configured = has_client_id and has_client_secret
        
        return {
            "google_oauth_configured": configured,
            "configured": configured,
            "client_id": settings.GOOGLE_CLIENT_ID[:10] + "..." if settings.GOOGLE_CLIENT_ID else None,
            "client_id_present": has_client_id,
            "client_secret_present": has_client_secret,
            "issues": [issue for issue in [
                "Client ID: ❌ Missing" if not has_client_id else None,
                "Client Secret: ❌ Missing" if not has_client_secret else None
            ] if issue is not None]
        }
        
    except Exception as e:
        logger.error(f"Error checking Google OAuth configuration: {e}", exc_info=True)
        return {
            "google_oauth_configured": False,
            "configured": False,
            "client_id": None,
            "client_id_present": False,
            "client_secret_present": False,
            "issues": [f"Configuration error: {str(e)}"]
        }


# Store OAuth state temporarily (in production, use Redis or database)
# Enhanced to support PKCE security parameters
oauth_states: Dict[str, Dict[str, Any]] = {}

def cleanup_expired_states():
    """Clean up expired OAuth states (older than 10 minutes)"""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
    expired_states = [
        state for state, data in oauth_states.items()
        if data.get("created_at", cutoff) < cutoff
    ]
    for state in expired_states:
        del oauth_states[state]
    
    if expired_states:
        logger.info(f"Cleaned up {len(expired_states)} expired OAuth states")

@router.post("/google/connect/{service}")
async def connect_google_oauth(
    service: str,
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """
    Initiate Google OAuth connection for a specific service with PKCE security.
    """
    try:
        # Parse request body for PKCE parameters
        body = await request.json() if request.headers.get("content-type") == "application/json" else {}
        code_challenge = body.get("code_challenge")
        code_challenge_method = body.get("code_challenge_method", "S256")
        
        # Validate PKCE parameters
        if not code_challenge:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PKCE code_challenge is required for enhanced security"
            )
        
        if code_challenge_method != "S256":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only S256 code_challenge_method is supported"
            )
        
        # Validate service
        if service not in [s.value for s in GoogleService]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid service: {service}. Must be one of: calendar, drive, gmail"
            )
        
        # Check configuration
        settings = get_settings()
        settings.load_google_oauth_from_secrets()
        
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth is not configured. Please contact administrator."
            )
        
        # Clean up expired states first
        cleanup_expired_states()
        
        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)
        
        # Define scopes based on service
        scopes = {
            "calendar": ["https://www.googleapis.com/auth/calendar"],
            "drive": ["https://www.googleapis.com/auth/drive.readonly"],
            "gmail": ["https://www.googleapis.com/auth/gmail.readonly"]
        }
        
        service_scopes = scopes.get(service, [])
        if not service_scopes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No scopes defined for service: {service}"
            )
        
        # Store state information with PKCE parameters
        oauth_states[state] = {
            "user_id": current_user.id,
            "service": service,
            "created_at": datetime.now(timezone.utc),
            "scopes": service_scopes,
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method
        }
        
        # Build redirect URI using public base URL
        base_url = get_public_base_url(request)
        redirect_uri = f"{base_url}/api/v1/oauth/google/callback"
        logger.info(f"OAuth connect redirect URI: {redirect_uri}")
        
        # Build authorization URL with PKCE parameters
        auth_params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "scope": " ".join(service_scopes),
            "response_type": "code",
            "state": state,
            "access_type": "offline",  # Get refresh token
            "prompt": "consent",  # Force consent to get refresh token
            "code_challenge": code_challenge,
            "code_challenge_method": code_challenge_method
        }
        
        auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(auth_params)
        
        logger.info(f"Redirecting user {current_user.id} to Google OAuth for {service}")
        return RedirectResponse(url=auth_url, status_code=302)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initiating Google OAuth for {service}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate Google OAuth connection"
        )


@router.post("/google/callback")
async def google_oauth_callback(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle Google OAuth callback and store tokens with PKCE verification.
    """
    try:
        # Parse request body
        body = await request.json()
        code = body.get("code")
        state = body.get("state")
        code_verifier = body.get("code_verifier")
        
        if not code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing authorization code"
            )
        
        if not state:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing state parameter"
            )
        
        if not code_verifier:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing PKCE code verifier"
            )
        
        # Validate state and retrieve PKCE parameters
        if state not in oauth_states:
            logger.warning(f"Invalid OAuth state: {state}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OAuth state"
            )
        
        state_data = oauth_states[state]
        user_id = state_data["user_id"]
        service = state_data["service"]
        scopes = state_data["scopes"]
        stored_code_challenge = state_data.get("code_challenge")
        
        # Verify PKCE code challenge
        import hashlib
        import base64
        
        if stored_code_challenge:
            # Compute code challenge from verifier
            computed_challenge = base64.urlsafe_b64encode(
                hashlib.sha256(code_verifier.encode()).digest()
            ).decode().rstrip('=')
            
            if computed_challenge != stored_code_challenge:
                logger.error(f"PKCE verification failed for user {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="PKCE verification failed"
                )
        
        # Clean up state
        del oauth_states[state]
        
        # Get settings
        settings = get_settings()
        settings.load_google_oauth_from_secrets()
        
        # Build redirect URI using public base URL
        base_url = get_public_base_url(request)
        redirect_uri = f"{base_url}/api/v1/oauth/google/callback"
        logger.info(f"OAuth callback redirect URI: {redirect_uri}")
        
        # Exchange code for tokens with PKCE
        token_params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET.get_secret_value(),
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier
        }
        
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data=token_params
            )
            
            if token_response.status_code != 200:
                logger.error(f"Token exchange failed: {token_response.status_code} - {token_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to exchange authorization code for tokens"
                )
            
            token_data = token_response.json()
        
        # Get user info to get email
        user_info = None
        if "access_token" in token_data:
            async with httpx.AsyncClient() as client:
                user_response = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {token_data['access_token']}"}
                )
                if user_response.status_code == 200:
                    user_info = user_response.json()
        
        # Calculate token expiry
        expires_in = token_data.get("expires_in", 3600)
        token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        
        # Store or update OAuth token
        service_enum = GoogleService(service)
        existing_token = db.query(UserOAuthToken).filter(
            UserOAuthToken.user_id == user_id,
            UserOAuthToken.service == service_enum
        ).first()
        
        if existing_token:
            # Update existing token
            existing_token.access_token = token_data["access_token"]
            existing_token.refresh_token = token_data.get("refresh_token", existing_token.refresh_token)
            existing_token.token_expiry = token_expiry
            existing_token.scope = ",".join(scopes)
            existing_token.service_email = user_info.get("email") if user_info else existing_token.service_email
            existing_token.updated_at = datetime.now(timezone.utc)
        else:
            # Create new token
            new_token = UserOAuthToken(
                user_id=user_id,
                service=service_enum,
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                token_expiry=token_expiry,
                scope=",".join(scopes),
                service_email=user_info.get("email") if user_info else None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.add(new_token)
        
        db.commit()
        
        logger.info(f"Successfully stored OAuth token for user {user_id}, service {service} with PKCE")
        
        return {
            "success": True,
            "message": f"Successfully connected {service}",
            "service": service
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling Google OAuth callback with PKCE: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process OAuth callback"
        )
        
@router.get("/google/callback")
async def google_oauth_callback_legacy(
    code: str,
    state: str,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Handle Google OAuth callback and store tokens.
    """
    try:
        # Validate state
        if state not in oauth_states:
            logger.warning(f"Invalid OAuth state: {state}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OAuth state"
            )
        
        state_data = oauth_states[state]
        user_id = state_data["user_id"]
        service = state_data["service"]
        scopes = state_data["scopes"]
        
        # Clean up state
        del oauth_states[state]
        
        # Get settings
        settings = get_settings()
        settings.load_google_oauth_from_secrets()
        
        # Build redirect URI using public base URL
        base_url = get_public_base_url(request)
        redirect_uri = f"{base_url}/api/v1/oauth/google/callback"
        logger.info(f"OAuth callback redirect URI: {redirect_uri}")
        
        # Exchange code for tokens
        token_params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET.get_secret_value(),
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri
        }
        
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data=token_params
            )
            
            if token_response.status_code != 200:
                logger.error(f"Token exchange failed: {token_response.status_code} - {token_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to exchange authorization code for tokens"
                )
            
            token_data = token_response.json()
        
        # Get user info to get email
        user_info = None
        if "access_token" in token_data:
            async with httpx.AsyncClient() as client:
                user_response = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {token_data['access_token']}"}
                )
                if user_response.status_code == 200:
                    user_info = user_response.json()
        
        # Calculate token expiry
        expires_in = token_data.get("expires_in", 3600)
        token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        
        # Store or update OAuth token
        service_enum = GoogleService(service)
        existing_token = db.query(UserOAuthToken).filter(
            UserOAuthToken.user_id == user_id,
            UserOAuthToken.service == service_enum
        ).first()
        
        if existing_token:
            # Update existing token
            existing_token.access_token = token_data["access_token"]
            existing_token.refresh_token = token_data.get("refresh_token", existing_token.refresh_token)
            existing_token.token_expiry = token_expiry
            existing_token.scope = ",".join(scopes)
            existing_token.service_email = user_info.get("email") if user_info else existing_token.service_email
            existing_token.updated_at = datetime.now(timezone.utc)
        else:
            # Create new token
            new_token = UserOAuthToken(
                user_id=user_id,
                service=service_enum,
                access_token=token_data["access_token"],
                refresh_token=token_data.get("refresh_token"),
                token_expiry=token_expiry,
                scope=",".join(scopes),
                service_email=user_info.get("email") if user_info else None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.add(new_token)
        
        db.commit()
        
        logger.info(f"Successfully stored OAuth token for user {user_id}, service {service}")
        
        # Redirect back to settings page with success message
        return RedirectResponse(url="/settings?oauth=success", status_code=302)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error handling Google OAuth callback: {e}", exc_info=True)
        return RedirectResponse(url="/settings?oauth=error", status_code=302)


@router.post("/google/refresh-tokens")
async def refresh_google_oauth_tokens(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Proactively refresh Google OAuth tokens that are expiring soon.
    """
    try:
        # Use OAuth token manager for enhanced refresh logic with circuit breaker
        token_manager = get_oauth_token_manager(db)
        
        result = await token_manager.refresh_expiring_tokens(current_user.id)
        
        return {
            "status": "success" if result["tokens_refreshed"] > 0 else "no_refresh_needed",
            "message": f"Refreshed {result['tokens_refreshed']} of {result.get('total_tokens', 0)} tokens",
            "tokens_refreshed": result["tokens_refreshed"],
            "errors": result.get("errors")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing OAuth tokens: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to refresh OAuth tokens"
        )


@router.get("/google/health-check")
async def google_services_health_check(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check the health and validity of Google service connections.
    """
    try:
        # Use OAuth token manager for comprehensive health checking
        token_manager = get_oauth_token_manager(db)
        
        # Get token status for all services
        token_statuses = await token_manager.check_all_user_tokens(current_user.id)
        
        if not token_statuses:
            return {
                "status": "no_connections",
                "message": "No Google services connected",
                "services": {}
            }
        
        service_health = {}
        overall_healthy = True
        
        settings = get_settings()
        settings.load_google_oauth_from_secrets()
        
        # Convert token statuses to API response format
        for service_name, status in token_statuses.items():
            service_health[service_name] = {
                "healthy": status.health.value in ["healthy", "expires_soon"],
                "status": status.health.value,
                "expires_at": status.expires_at.isoformat() if status.expires_at else None,
                "needs_refresh": status.needs_refresh,
                "error": status.error_message
            }
            
            if not service_health[service_name]["healthy"]:
                overall_healthy = False
        
        return {
            "status": "healthy" if overall_healthy else "degraded", 
            "message": f"Checked {len(token_statuses)} service(s)",
            "services": service_health,
            "oauth_configured": bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)
        }
        
    except Exception as e:
        logger.error(f"Error checking Google services health: {e}", exc_info=True)
        return {
            "status": "error",
            "message": "Health check failed",
            "services": {},
            "error": str(e)
        }


@router.delete("/google/disconnect/{service}")
async def disconnect_google_oauth(
    service: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Disconnect Google OAuth for a specific service.
    """
    try:
        # Validate service
        if service not in [s.value for s in GoogleService]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid service: {service}. Must be one of: calendar, drive, gmail"
            )
        
        service_enum = GoogleService(service)
        
        # Find and delete the OAuth token
        oauth_token = db.query(UserOAuthToken).filter(
            UserOAuthToken.user_id == current_user.id,
            UserOAuthToken.service == service_enum
        ).first()
        
        if not oauth_token:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Google {service} is not connected"
            )
        
        db.delete(oauth_token)
        db.commit()
        
        logger.info(f"Successfully disconnected Google {service} for user {current_user.id}")
        
        return {
            "message": f"Successfully disconnected Google {service}",
            "service": service
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting Google {service}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disconnect Google {service}"
        )