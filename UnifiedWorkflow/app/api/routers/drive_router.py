"""
Google Drive router for browsing and importing files.
"""

import logging
import pathlib
import aiofiles
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel

from shared.utils.database_setup import get_db
from shared.database.models import User, UserOAuthToken, GoogleService
from api.dependencies import get_current_user, verify_csrf_token
from api.services.google_drive_service import GoogleDriveService
from shared.services.document_service import create_document, delete_document as delete_db_document_record

logger = logging.getLogger(__name__)

router = APIRouter()

class DriveFileImportRequest(BaseModel):
    """Request model for importing a file from Google Drive."""
    file_id: str
    file_name: str

@router.get("/files")
async def list_drive_files(
    folder_id: Optional[str] = Query(None, description="Folder ID to list files from"),
    page_size: int = Query(20, description="Number of files per page"),
    page_token: Optional[str] = Query(None, description="Pagination token"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """List files from user's Google Drive."""
    
    # Check if user has Google Drive connected
    oauth_token = db.query(UserOAuthToken).filter(
        UserOAuthToken.user_id == current_user.id,
        UserOAuthToken.service == GoogleService.DRIVE
    ).first()
    
    if not oauth_token:
        raise HTTPException(
            status_code=400,
            detail="Google Drive is not connected. Please connect your Google Drive first."
        )
    
    try:
        # Initialize Google Drive service
        drive_service = GoogleDriveService(oauth_token, db)
        
        # List files
        result = await drive_service.list_files(
            folder_id=folder_id,
            page_size=page_size,
            page_token=page_token
        )
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to list Drive files for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list Drive files: {str(e)}"
        )

@router.post("/import", dependencies=[Depends(verify_csrf_token)])
async def import_drive_file(
    file_request: DriveFileImportRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Import a file from Google Drive to the document library."""
    
    # Check if user has Google Drive connected
    oauth_token = db.query(UserOAuthToken).filter(
        UserOAuthToken.user_id == current_user.id,
        UserOAuthToken.service == GoogleService.DRIVE
    ).first()
    
    if not oauth_token:
        raise HTTPException(
            status_code=400,
            detail="Google Drive is not connected. Please connect your Google Drive first."
        )
    
    try:
        # Initialize Google Drive service
        drive_service = GoogleDriveService(oauth_token, db)
        
        # Download file content
        file_content, file_metadata = await drive_service.get_file_content(file_request.file_id)
        
        # Create document record in database first
        db_document = create_document(
            db=db,
            filename=file_metadata.get('name', file_request.file_name),
            user_id=current_user.id
        )
        
        # Save file to documents directory
        workspace_path = pathlib.Path("/app/documents")
        workspace_path.mkdir(exist_ok=True)
        
        # Create safe filename
        safe_filename = f"{db_document.id}_{pathlib.Path(file_metadata.get('name', file_request.file_name)).name}"
        file_path = workspace_path / safe_filename
        
        try:
            # Save file content to disk
            async with aiofiles.open(file_path, "wb") as buffer:
                await buffer.write(file_content)
            logger.info(f"Saved Drive file '{file_metadata.get('name')}' to '{file_path}'")
        except Exception as e:
            logger.error(f"Could not save Drive file: {e}")
            # Rollback database record
            delete_db_document_record(db, document_id=db_document.id, user_id=current_user.id)
            raise HTTPException(status_code=500, detail="Could not save file.") from e
        
        # Queue processing task (similar to upload endpoint)
        task_params = {
            "document_id": str(db_document.id),
            "user_id": current_user.id,
            "file_path": str(file_path),
            "original_filename": file_metadata.get('name', file_request.file_name)
        }
        
        # Get celery instance and send task (use same pattern as main API)
        celery_app = request.app.state.celery_app
        celery_app.send_task("tasks.process_document_wrapper", args=[task_params])
        
        logger.info(f"Successfully queued Drive file processing for '{file_metadata.get('name')}'")
        
        return {
            "message": "File imported successfully from Google Drive",
            "document_id": str(db_document.id),
            "filename": db_document.filename,
            "size": len(file_content)
        }
        
    except Exception as e:
        logger.error(f"Failed to import Drive file for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to import file from Drive: {str(e)}"
        )

@router.get("/connection-status")
async def get_drive_connection_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get the status of Google Drive connection."""
    
    # Check if user has Google Drive connected
    oauth_token = db.query(UserOAuthToken).filter(
        UserOAuthToken.user_id == current_user.id,
        UserOAuthToken.service == GoogleService.DRIVE
    ).first()
    
    if not oauth_token:
        return {
            "connected": False,
            "message": "Google Drive not connected"
        }
    
    return {
        "connected": True,
        "message": "Google Drive connected",
        "connected_at": oauth_token.created_at.isoformat() if oauth_token.created_at else None
    }