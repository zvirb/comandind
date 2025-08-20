"""
This service handles the processing and embedding of documents.
It's designed to be called as a background task from the worker.
"""
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List
from tenacity import retry, stop_after_attempt, wait_exponential
from qdrant_client.http.models import PointStruct
# Use absolute imports for modules within the same package
from shared.schemas import Document
from worker.utils.embeddings import get_embeddings
from .qdrant_service import QdrantService
# --- Path Correction ---
# This corrects the path to allow absolute imports from the project root
project_root = Path(__file__).resolve().parents[4]
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))




logger = logging.getLogger(__name__)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
async def process_and_embed_document_task(document_data: Dict[str, Any]) -> None:
    """
    Background task to process a document, generate embeddings, and upsert to Qdrant.
    """
    doc_id = document_data.get('id')
    try:
        logger.info("Starting background task for document ID: %s", doc_id)
        document = Document.model_validate(document_data)

        embeddings: List[List[float]] = await get_embeddings([document.content])
        if not embeddings:
            raise ValueError("Embedding generation failed.")
        embedding_vector: List[float] = embeddings[0]

        payload = document.model_dump()

        point = PointStruct(
            id=str(document.id),
            vector=embedding_vector,
            payload=payload
        )

        qdrant_service = QdrantService()
        await qdrant_service.initialize()
        await qdrant_service.upsert_points(points=[point])

        logger.info("Successfully processed and upserted document ID: %s", document.id)

    except Exception as e:
        logger.error(
            "Error in background task for document ID %s: %s",
            doc_id, e, exc_info=True
        )
        raise
