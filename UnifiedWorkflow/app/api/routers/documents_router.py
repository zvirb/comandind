"""
Documents API Router - Comprehensive document management endpoints.
Handles document upload, retrieval, deletion, and management operations.
"""

import logging
import os
import pathlib
import shutil
import uuid
import aiofiles
from datetime import datetime
from typing import List, Dict, Any, Optional

from fastapi import (
    APIRouter, Depends, HTTPException, status, UploadFile, File, Request, Query
)
from fastapi.responses import JSONResponse
from celery import Celery
from sqlalchemy.ext.asyncio import AsyncSession

from shared.utils.database_setup import get_async_session
from shared.services.document_service import (
    create_document_async,
    delete_document_async as delete_db_document_record,
    get_all_documents_async,
    get_document_by_id_and_user_async
)
from shared.schemas import DocumentResponse, DocumentUploadResponse
from api.dependencies import get_current_user, verify_csrf_token
from shared.database.models import User, Document

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(verify_csrf_token)],
)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Accepts a document upload, creates a record in the database,
    and queues a task for the worker to process it. Returns immediately
    with the document ID.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file name provided.")
    
    # Validate file size (10MB limit)
    if file.size and file.size > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File too large. Maximum size is 10MB.")
    
    # Validate file type
    allowed_extensions = {'.txt', '.pdf', '.doc', '.docx', '.md', '.json', '.csv'}
    file_extension = pathlib.Path(file.filename).suffix.lower()
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"File type not supported. Allowed types: {', '.join(allowed_extensions)}"
        )
    
    # 1. Create the document record in PostgreSQL first.
    # This gives us a unique ID to name the stored file, preventing conflicts.
    db_document = await create_document_async(db, filename=file.filename, user_id=current_user.id)

    # 2. Save the file to a shared volume instead of passing its content in Redis.
    # This is more memory-efficient and robust for large files.
    # The workspace is defined as /app/documents, which is a mounted volume.
    workspace_path = pathlib.Path("/app/documents")
    workspace_path.mkdir(exist_ok=True)  # Ensure the directory exists

    # Sanitize filename and create a unique path to avoid collisions and traversal attacks.
    safe_filename = f"{db_document.id}_{pathlib.Path(file.filename).name}"
    file_path = workspace_path / safe_filename

    try:
        # Asynchronously stream the file to disk to avoid blocking the event loop
        # and to handle large files efficiently without high memory usage.
        async with aiofiles.open(file_path, "wb") as buffer:
            while content := await file.read(1024 * 1024):  # Read in 1MB chunks
                await buffer.write(content)
        logger.info("Saved uploaded file '%s' to '%s'", file.filename, file_path)
    except Exception as e:
        logger.error(
            "Could not save uploaded file: %s. Rolling back database entry.", e, exc_info=True
        )
        # --- Transactional Rollback ---
        # If saving the file fails, explicitly delete the orphaned database record.
        # The database service function handles its own commit.
        await delete_db_document_record(db, document_id=db_document.id, user_id=current_user.id)
        raise HTTPException(status_code=500, detail="Could not save file.") from e

    # 3. Prepare and publish the task for the worker.
    # The worker will now receive the path to the file, not its content.
    task_params: Dict[str, Any] = {
        "document_id": str(db_document.id),
        "user_id": current_user.id,
        "file_path": str(file_path),  # Pass the absolute path inside the container
        "original_filename": file.filename,
    }    
    celery_app: Celery = request.app.state.celery_app
    celery_app.send_task("tasks.process_document_wrapper", args=[task_params])

    # The response remains the same, providing immediate feedback to the user.
    return DocumentUploadResponse(
        message="File upload successful. Processing has been queued via Celery.",
        document_id=db_document.id,
    )


@router.get(
    "/",
    response_model=List[DocumentResponse],
)
async def list_documents(
    current_user: User = Depends(get_current_user), 
    db: AsyncSession = Depends(get_async_session)
):
    """Lists all documents owned by the current user."""
    documents = await get_all_documents_async(db, user_id=current_user.id)
    return documents


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
)
async def get_document(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Get a specific document by ID."""
    document = await get_document_by_id_and_user_async(
        db, document_id=document_id, user_id=current_user.id
    )
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or you do not have permission to access it.",
        )
    return document


@router.get(
    "/{document_id}/content",
)
async def get_document_content_endpoint(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Get document content."""
    document = await get_document_by_id_and_user_async(
        db, document_id=document_id, user_id=current_user.id
    )
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or you do not have permission to access it.",
        )
    
    try:
        # Basic implementation - would connect to vector store in production
        return {
            "document_id": document_id,
            "filename": document.filename,
            "content": "Document content retrieval not yet implemented",
            "content_type": "text/plain",
            "status": document.status or "uploaded"
        }
    except Exception as e:
        logger.error(f"Error retrieving document content: {e}")
        raise HTTPException(
            status_code=500, detail="Could not retrieve document content."
        )


@router.get(
    "/search",
    response_model=List[DocumentResponse],
)
async def search_documents_endpoint(
    q: str = Query(..., description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Search documents by content or filename."""
    try:
        # Basic filename search implementation
        from sqlalchemy import select
        result = await db.execute(
            select(Document).filter(
                Document.user_id == current_user.id,
                Document.filename.ilike(f"%{q}%")
            ).limit(limit)
        )
        documents = result.scalars().all()
        return documents
    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        raise HTTPException(
            status_code=500, detail="Could not search documents."
        )


@router.put(
    "/{document_id}/metadata",
    dependencies=[Depends(verify_csrf_token)],
)
async def update_document_metadata_endpoint(
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Update document metadata."""
    document = await get_document_by_id_and_user_async(
        db, document_id=document_id, user_id=current_user.id
    )
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or you do not have permission to access it.",
        )
    
    try:
        # Basic implementation - would update metadata in production
        return {
            "message": "Document metadata update not yet implemented",
            "document_id": document_id,
            "current_metadata": {
                "filename": document.filename,
                "status": document.status,
                "created_at": document.created_at.isoformat() if document.created_at else None
            }
        }
    except Exception as e:
        logger.error(f"Error updating document metadata: {e}")
        raise HTTPException(
            status_code=500, detail="Could not update document metadata."
        )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(verify_csrf_token)],
)
async def delete_user_document(
    request: Request,
    document_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Verifies document ownership and queues a task for the worker to delete
    the document from the database and vector store.
    """
    # 1. Verify the document exists and belongs to the user before queueing deletion.
    document = await get_document_by_id_and_user_async(
        db, document_id=document_id, user_id=current_user.id
    )
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or you do not have permission to delete it.",
        )

    # Construct the full path to the physical file that needs to be deleted.
    # This makes the interface with the worker explicit, removing the need for
    # the worker to reconstruct the path itself.
    workspace_path = pathlib.Path("/app/documents")
    safe_filename = f"{document.id}_{pathlib.Path(document.filename).name}"
    file_path = workspace_path / safe_filename

    # 2. Publish the deletion task to the worker.
    task_params: Dict[str, Any] = {
        "document_id": str(document_id),
        "user_id": current_user.id,
        "file_path": str(file_path),  # Pass the explicit path to the worker
    }
    celery_app: Celery = request.app.state.celery_app
    celery_app.send_task("tasks.delete_document", kwargs=task_params)

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={"message": "Document deletion request accepted via Celery."},
    )


@router.get(
    "/stats",
)
async def get_document_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session)
):
    """Get document statistics for the current user."""
    try:
        documents = await get_all_documents_async(db, user_id=current_user.id)
        
        total_count = len(documents)
        total_size = sum(doc.file_size or 0 for doc in documents)
        
        # Group by status
        by_status = {}
        for doc in documents:
            status_val = doc.status or "unknown"
            by_status[status_val] = by_status.get(status_val, 0) + 1
        
        # Group by file type
        by_type = {}
        for doc in documents:
            extension = pathlib.Path(doc.filename).suffix.lower()
            by_type[extension or "no_extension"] = by_type.get(extension or "no_extension", 0) + 1
        
        return {
            "total_documents": total_count,
            "total_size_bytes": total_size,
            "by_status": by_status,
            "by_file_type": by_type,
            "recent_uploads": [
                {
                    "id": doc.id,
                    "filename": doc.filename,
                    "created_at": doc.created_at.isoformat() if doc.created_at else None
                }
                for doc in sorted(documents, key=lambda x: x.created_at or datetime.min, reverse=True)[:5]
            ]
        }
    except Exception as e:
        logger.error(f"Error retrieving document stats: {e}")
        raise HTTPException(
            status_code=500, detail="Could not retrieve document statistics."
        )