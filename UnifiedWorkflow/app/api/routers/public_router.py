from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import logging

from shared.database.models import AccessRequest
from shared.utils.database_setup import get_db
from shared.schemas.access_request import AccessRequestCreate
from shared.services.certificate_service import create_certificate_package
from shared.services.email_service import send_email

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/request-access")
async def request_access(
    request_data: AccessRequestCreate, 
    db: Session = Depends(get_db)
):
    """
    Submit a request for client certificate access.
    """
    try:
        # Check if email already has a pending or approved request
        existing_request = db.query(AccessRequest).filter(
            AccessRequest.email == request_data.email,
            AccessRequest.status.in_(["pending", "approved"])
        ).first()
        
        if existing_request:
            return {
                "message": "A request for this email already exists. Please wait for approval or check your email for the download link.",
                "status": existing_request.status
            }
        
        # Create new access request
        new_request = AccessRequest(
            email=request_data.email,
            status="pending"
        )
        db.add(new_request)
        db.commit()
        db.refresh(new_request)
        
        logger.info(f"New access request created for email: {request_data.email}")
        
        return {
            "message": "Access request submitted successfully. An administrator will review your request and send you a download link if approved.",
            "request_id": str(new_request.id)
        }
        
    except Exception as e:
        logger.error(f"Error processing access request: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/download-certs/{token}")
async def download_certs(
    token: str, 
    platform: str = Query(..., regex="^(windows|macos|linux)$"),
    db: Session = Depends(get_db)
):
    """
    Download client certificates using an approved access token.
    Platform must be one of: windows, macos, linux
    """
    try:
        # Find the request by token
        request = db.query(AccessRequest).filter(
            AccessRequest.token == token,
            AccessRequest.status == "approved"
        ).first()
        
        if not request:
            raise HTTPException(status_code=404, detail="Token not found or not approved")
        
        # Check if token has expired
        if request.expires_at and request.expires_at < datetime.now(timezone.utc):
            logger.warning(f"Expired token used: {token}")
            raise HTTPException(status_code=410, detail="Download link has expired")
        
        # Create platform-specific certificate package
        try:
            package_path = create_certificate_package(request.email, platform)
            logger.info(f"Certificate package created for {request.email} on {platform}")
            
            # Return the file as a download
            filename = f"ai-workflow-client-certs-{platform}.{'pfx' if platform == 'windows' else 'p12' if platform == 'macos' else 'zip'}"
            
            return FileResponse(
                path=package_path,
                filename=filename,
                media_type="application/octet-stream"
            )
            
        except Exception as e:
            logger.error(f"Error creating certificate package: {str(e)}")
            raise HTTPException(status_code=500, detail="Error generating certificate package")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in download_certs: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")