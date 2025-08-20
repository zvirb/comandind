"""Router for Ollama model management."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
import httpx
import logging
import json
import asyncio
import uuid
from typing import Dict, Any, AsyncGenerator, Optional
from pydantic import BaseModel

from api.dependencies import get_current_user, verify_csrf_token
from shared.database.models import User, UserRole
from shared.utils.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()

# In-memory progress tracking for model downloads
download_progress = {}

class ModelRequest(BaseModel):
    model: str

@router.post("/pull/start", dependencies=[Depends(verify_csrf_token)])
async def start_model_pull(
    request: ModelRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Start downloading a new Ollama model and return a task ID for progress tracking.
    """
    # Only admins can manage models
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only administrators can manage models")
    
    ollama_url = settings.OLLAMA_API_BASE_URL
    if not ollama_url:
        raise HTTPException(status_code=503, detail="Ollama service is not configured")

    # Generate unique task ID
    task_id = str(uuid.uuid4())
    
    # Initialize progress tracking
    download_progress[task_id] = {
        "status": "starting",
        "percentage": 0,
        "model": request.model,
        "user_id": current_user.id
    }
    
    # Start background task
    asyncio.create_task(download_model_background(task_id, request.model, ollama_url))
    
    return {"task_id": task_id, "message": f"Started downloading model '{request.model}'"}

async def download_model_background(task_id: str, model_name: str, ollama_url: str):
    """Background task to download the model and update progress."""
    try:
        async with httpx.AsyncClient(timeout=600.0) as client:  # 10 minute timeout for large models
            logger.info(f"Pulling model '{model_name}' from Ollama (task {task_id})")
            
            download_progress[task_id]["status"] = "downloading"
            
            async with client.stream(
                "POST",
                f"{ollama_url}/api/pull",
                json={"name": model_name, "stream": True}
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line and task_id in download_progress:
                        try:
                            # Parse the JSON response from Ollama
                            progress_data = json.loads(line)
                            
                            # Calculate percentage if we have total and completed
                            if "total" in progress_data and "completed" in progress_data:
                                total = progress_data["total"]
                                completed = progress_data["completed"]
                                if total > 0:
                                    percentage = (completed / total) * 100
                                    download_progress[task_id]["percentage"] = round(percentage, 1)
                            
                            # Update status
                            if "status" in progress_data:
                                download_progress[task_id]["status"] = progress_data["status"]
                            
                            # Check if download is complete
                            if progress_data.get("status") == "success":
                                download_progress[task_id]["status"] = "completed"
                                download_progress[task_id]["percentage"] = 100
                                logger.info(f"Successfully completed downloading model '{model_name}' (task {task_id})")
                                break
                                
                        except json.JSONDecodeError:
                            # Skip invalid JSON lines
                            continue
                            
    except httpx.RequestError as e:
        logger.error(f"Failed to pull model from Ollama: {e}")
        if task_id in download_progress:
            download_progress[task_id]["status"] = "error"
            download_progress[task_id]["error"] = "Unable to connect to Ollama service"
    except httpx.HTTPStatusError as e:
        logger.error(f"Ollama returned error when pulling model: {e.response.status_code}")
        if task_id in download_progress:
            download_progress[task_id]["status"] = "error"
            download_progress[task_id]["error"] = f"Failed to pull model: {e.response.text}"
    except Exception as e:
        logger.error(f"Unexpected error pulling model: {e}")
        if task_id in download_progress:
            download_progress[task_id]["status"] = "error"
            download_progress[task_id]["error"] = "Internal server error"

@router.get("/pull/progress/{task_id}")
async def get_pull_progress(
    task_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get the progress of a model download task.
    """
    # Only admins can manage models
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only administrators can manage models")
    
    if task_id not in download_progress:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_info = download_progress[task_id]
    
    # Verify user owns this task
    if task_info["user_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Clean up completed/error tasks after returning status
    if task_info["status"] in ["completed", "error"]:
        # Schedule cleanup after response
        asyncio.create_task(cleanup_task(task_id))
    
    return task_info

async def cleanup_task(task_id: str):
    """Clean up completed task after a delay."""
    await asyncio.sleep(30)  # Keep for 30 seconds after completion
    if task_id in download_progress:
        del download_progress[task_id]

@router.post("/pull", dependencies=[Depends(verify_csrf_token)])
async def pull_model(
    request: ModelRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Download a new Ollama model (non-streaming version for compatibility).
    """
    # Only admins can manage models
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only administrators can manage models")
    
    ollama_url = settings.OLLAMA_API_BASE_URL
    if not ollama_url:
        raise HTTPException(status_code=503, detail="Ollama service is not configured")
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:  # 5 minute timeout for model downloads
            logger.info(f"Pulling model '{request.model}' from Ollama")
            response = await client.post(
                f"{ollama_url}/api/pull",
                json={"name": request.model}
            )
            response.raise_for_status()
            
            return {"message": f"Successfully started downloading model '{request.model}'"}
            
    except httpx.RequestError as e:
        logger.error(f"Failed to pull model from Ollama: {e}")
        raise HTTPException(status_code=503, detail="Unable to connect to Ollama service")
    except httpx.HTTPStatusError as e:
        logger.error(f"Ollama returned error when pulling model: {e.response.status_code}")
        raise HTTPException(status_code=400, detail=f"Failed to pull model: {e.response.text}")
    except Exception as e:
        logger.error(f"Unexpected error pulling model: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/delete", dependencies=[Depends(verify_csrf_token)])
async def delete_model(
    request: ModelRequest,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Delete an Ollama model.
    """
    # Only admins can manage models
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Only administrators can manage models")
    
    ollama_url = settings.OLLAMA_API_BASE_URL
    if not ollama_url:
        raise HTTPException(status_code=503, detail="Ollama service is not configured")
    
    try:
        async with httpx.AsyncClient() as client:
            logger.info(f"Deleting model '{request.model}' from Ollama")
            response = await client.delete(
                f"{ollama_url}/api/delete",
                json={"name": request.model}
            )
            response.raise_for_status()
            
            return {"message": f"Successfully deleted model '{request.model}'"}
            
    except httpx.RequestError as e:
        logger.error(f"Failed to delete model from Ollama: {e}")
        raise HTTPException(status_code=503, detail="Unable to connect to Ollama service")
    except httpx.HTTPStatusError as e:
        logger.error(f"Ollama returned error when deleting model: {e.response.status_code}")
        raise HTTPException(status_code=400, detail=f"Failed to delete model: {e.response.text}")
    except Exception as e:
        logger.error(f"Unexpected error deleting model: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")