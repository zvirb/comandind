"""WebAuthn/FIDO2 endpoints for hardware security key registration and authentication."""

import base64
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import logging

from shared.utils.database_setup import get_async_session
from shared.services.enhanced_jwt_service import enhanced_jwt_service
from shared.database.models import User
from api.dependencies import get_current_user
from shared.database.models.security_models import CertificateRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webauthn", tags=["WebAuthn"])
security = HTTPBearer()


class WebAuthnRegistrationBeginRequest(BaseModel):
    """Request model for beginning WebAuthn registration."""
    authenticator_type: str = "cross-platform"
    user_verification: str = "required"


class WebAuthnRegistrationCompleteRequest(BaseModel):
    """Request model for completing WebAuthn registration."""
    credential_id: str
    attestation_object: str
    client_data_json: str
    registration_id: str


class WebAuthnAuthenticationBeginRequest(BaseModel):
    """Request model for beginning WebAuthn authentication."""
    user_verification: str = "required"


class WebAuthnAuthenticationCompleteRequest(BaseModel):
    """Request model for completing WebAuthn authentication."""
    credential_id: str
    authenticator_data: str
    client_data_json: str
    signature: str
    challenge_id: str




# In-memory storage for challenges (in production, use Redis or database)
_active_challenges = {}


@router.post("/register/begin")
async def begin_webauthn_registration(
    request: WebAuthnRegistrationBeginRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Begin WebAuthn registration process."""
    try:
        # Generate a random challenge
        challenge = base64.urlsafe_b64encode(uuid.uuid4().bytes).decode('utf-8').rstrip('=')
        registration_id = str(uuid.uuid4())
        
        # Store challenge temporarily
        _active_challenges[registration_id] = {
            'challenge': challenge,
            'user_id': current_user.id,
            'created_at': datetime.utcnow(),
            'type': 'registration'
        }
        
        # Clean up old challenges (older than 5 minutes)
        cutoff_time = datetime.utcnow() - timedelta(minutes=5)
        _active_challenges = {
            k: v for k, v in _active_challenges.items() 
            if v['created_at'] > cutoff_time
        }
        
        return {
            "challenge": challenge,
            "registration_id": registration_id,
            "rp": {
                "name": "AI Workflow Engine",
                "id": "localhost"  # Should be your domain in production
            },
            "user": {
                "id": base64.urlsafe_b64encode(str(current_user.id).encode()).decode('utf-8').rstrip('='),
                "name": current_user.email,
                "displayName": current_user.full_name or current_user.email
            },
            "pubKeyCredParams": [
                {"alg": -7, "type": "public-key"},   # ES256
                {"alg": -257, "type": "public-key"}, # RS256
                {"alg": -8, "type": "public-key"}    # EdDSA
            ],
            "timeout": 60000
        }
        
    except Exception as e:
        logger.error(f"Failed to begin WebAuthn registration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate WebAuthn registration"
        )


@router.post("/register/complete")
async def complete_webauthn_registration(
    request: WebAuthnRegistrationCompleteRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Complete WebAuthn registration process."""
    try:
        # Verify registration_id and challenge
        if request.registration_id not in _active_challenges:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired registration challenge"
            )
        
        challenge_data = _active_challenges[request.registration_id]
        
        if challenge_data['user_id'] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Challenge does not belong to current user"
            )
        
        # In a real implementation, you would:
        # 1. Verify the attestation object
        # 2. Check the client data JSON
        # 3. Validate the signature
        # 4. Store the credential public key
        
        # For this demo, we'll do basic validation
        try:
            client_data = json.loads(base64.b64decode(request.client_data_json + '=='))
            
            if client_data.get('challenge') != challenge_data['challenge']:
                raise ValueError("Challenge mismatch")
                
            if client_data.get('type') != 'webauthn.create':
                raise ValueError("Invalid client data type")
                
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid client data: {str(e)}"
            )
        
        # Store the credential (simplified - in production, store the public key properly)
        # Here we'll create a certificate request to track the hardware key registration
        hardware_key_record = CertificateRequest(
            user_id=current_user.id,
            request_type='HARDWARE_KEY',
            platform='webauthn',
            certificate_cn=f"Hardware Key - {current_user.email}",
            status='READY',
            generated_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=365 * 5),  # 5 years for hardware keys
            certificate_path=request.credential_id  # Store credential ID here
        )
        
        session.add(hardware_key_record)
        await session.commit()
        
        # Clean up challenge
        del _active_challenges[request.registration_id]
        
        return {
            "status": "success",
            "credential_id": request.credential_id,
            "message": "Hardware security key registered successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to complete WebAuthn registration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete WebAuthn registration"
        )


@router.post("/authenticate/begin")
async def begin_webauthn_authentication(
    request: WebAuthnAuthenticationBeginRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Begin WebAuthn authentication process."""
    try:
        # Generate a random challenge
        challenge = base64.urlsafe_b64encode(uuid.uuid4().bytes).decode('utf-8').rstrip('=')
        challenge_id = str(uuid.uuid4())
        
        # Store challenge temporarily
        _active_challenges[challenge_id] = {
            'challenge': challenge,
            'user_id': current_user.id,
            'created_at': datetime.utcnow(),
            'type': 'authentication'
        }
        
        # Get user's registered credentials
        from sqlalchemy import select
        stmt = select(CertificateRequest).where(
            CertificateRequest.user_id == current_user.id,
            CertificateRequest.request_type == 'HARDWARE_KEY',
            CertificateRequest.status == 'READY'
        )
        result = await session.execute(stmt)
        credentials = result.scalars().all()
        
        allowed_credentials = [
            {
                "id": cred.certificate_path,  # credential_id stored here
                "type": "public-key"
            }
            for cred in credentials
        ]
        
        return {
            "challenge": challenge,
            "challenge_id": challenge_id,
            "allowCredentials": allowed_credentials,
            "userVerification": request.user_verification,
            "timeout": 60000
        }
        
    except Exception as e:
        logger.error(f"Failed to begin WebAuthn authentication: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate WebAuthn authentication"
        )


@router.post("/authenticate/complete")
async def complete_webauthn_authentication(
    request: WebAuthnAuthenticationCompleteRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Complete WebAuthn authentication process."""
    try:
        # Verify challenge_id and challenge
        if request.challenge_id not in _active_challenges:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired authentication challenge"
            )
        
        challenge_data = _active_challenges[request.challenge_id]
        
        if challenge_data['user_id'] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Challenge does not belong to current user"
            )
        
        # In a real implementation, you would:
        # 1. Verify the authenticator data
        # 2. Check the client data JSON
        # 3. Validate the signature using the stored public key
        
        # For this demo, we'll do basic validation
        try:
            client_data = json.loads(base64.b64decode(request.client_data_json + '=='))
            
            if client_data.get('challenge') != challenge_data['challenge']:
                raise ValueError("Challenge mismatch")
                
            if client_data.get('type') != 'webauthn.get':
                raise ValueError("Invalid client data type")
                
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid client data: {str(e)}"
            )
        
        # Verify the credential belongs to the user
        from sqlalchemy import select
        stmt = select(CertificateRequest).where(
            CertificateRequest.user_id == current_user.id,
            CertificateRequest.request_type == 'HARDWARE_KEY',
            CertificateRequest.certificate_path == request.credential_id,
            CertificateRequest.status == 'READY'
        )
        result = await session.execute(stmt)
        credential = result.scalar_one_or_none()
        
        if not credential:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Credential not found or not registered to this user"
            )
        
        # Clean up challenge
        del _active_challenges[request.challenge_id]
        
        return {
            "status": "success",
            "verified": True,
            "message": "Hardware security key authentication successful"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to complete WebAuthn authentication: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete WebAuthn authentication"
        )


@router.get("/credentials")
async def list_user_credentials(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """List user's registered WebAuthn credentials."""
    try:
        from sqlalchemy import select
        stmt = select(CertificateRequest).where(
            CertificateRequest.user_id == current_user.id,
            CertificateRequest.request_type == 'HARDWARE_KEY'
        )
        result = await session.execute(stmt)
        credentials = result.scalars().all()
        
        return {
            "credentials": [
                {
                    "id": cred.id,
                    "credential_id": cred.certificate_path,
                    "name": cred.certificate_cn,
                    "status": cred.status,
                    "registered_at": cred.generated_at.isoformat() if cred.generated_at else None,
                    "expires_at": cred.expires_at.isoformat() if cred.expires_at else None
                }
                for cred in credentials
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to list WebAuthn credentials: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list credentials"
        )


@router.delete("/credentials/{credential_id}")
async def revoke_credential(
    credential_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Revoke a WebAuthn credential."""
    try:
        from sqlalchemy import select, update
        
        # Find the credential
        stmt = select(CertificateRequest).where(
            CertificateRequest.user_id == current_user.id,
            CertificateRequest.request_type == 'HARDWARE_KEY',
            CertificateRequest.certificate_path == credential_id
        )
        result = await session.execute(stmt)
        credential = result.scalar_one_or_none()
        
        if not credential:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Credential not found"
            )
        
        # Update status to revoked
        credential.status = 'REVOKED'
        credential.revoked_at = datetime.utcnow()
        
        await session.commit()
        
        return {
            "status": "success",
            "message": "Credential revoked successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to revoke WebAuthn credential: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke credential"
        )