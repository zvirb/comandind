"""
Service responsible for the document processing pipeline (RAG).
"""
import logging
import uuid
from typing import Any, Dict

from langchain.text_splitter import RecursiveCharacterTextSplitter
from sqlalchemy.orm import Session

from shared.database.models import DocumentStatus
from worker.database_service import create_document_chunks, update_document_status
from worker.services.qdrant_service import QdrantService
from worker.utils.embeddings import get_embeddings

logger = logging.getLogger(__name__)


def _read_file_content(file_path: str) -> str:
    """Reads the content of a file, raising an error if it fails."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error("Failed to read file %s: %s", file_path, e, exc_info=True)
        raise IOError(f"Could not read file at {file_path}") from e


async def process_document(
    db: Session,
    document_id: str,
    user_id: int,
    file_path: str,
    original_filename: str,
):
    """
    The main RAG pipeline for processing an uploaded document.
    1. Chunks the document text.
    2. Generates embeddings for each chunk.
    3. Upserts the vectors into Qdrant.
    4. Saves chunk metadata to PostgreSQL.
    5. Updates the document status throughout the process.
    """
    doc_uuid = uuid.UUID(document_id)
    logger.info("Starting processing for document_id: %s", document_id)

    try:
        # 1. Update status to PROCESSING
        update_document_status(db, doc_uuid, DocumentStatus.PROCESSING)

        # 2. Read file content
        content = _read_file_content(file_path)

        # 3. Chunk the text using LangChain for better results
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_text(content)
        logger.info("Split document %s into %d chunks.", document_id, len(chunks))

        if not chunks:
            logger.warning("Document %s resulted in 0 chunks. Marking as completed.", document_id)
            update_document_status(db, doc_uuid, DocumentStatus.COMPLETED)
            return

        # 4. Generate embeddings and prepare data for storage
        embeddings = await get_embeddings(chunks)
        qdrant_service = QdrantService()
        vector_ids = [str(uuid.uuid4()) for _ in chunks]
        db_chunks_data: list[dict[str, Any]] = []

        for i, chunk_text in enumerate(chunks):
            payload = {"document_id": document_id, "user_id": user_id, "content": chunk_text, "original_filename": original_filename, "chunk_index": i}
            db_chunks_data.append({"chunk_index": i, "content": chunk_text, "vector_id": vector_ids[i]})
            qdrant_service.add_to_batch(vector_id=vector_ids[i], vector=embeddings[i], payload=payload)

        # 5. Upsert to Qdrant and save to PostgreSQL
        await qdrant_service.upsert_batch()
        create_document_chunks(db, document_id=doc_uuid, chunks_data=db_chunks_data)

        # 6. Update status to COMPLETED
        update_document_status(db, doc_uuid, DocumentStatus.COMPLETED)
        logger.info("Successfully processed document_id: %s", document_id)

    except Exception as e:
        logger.error("Failed to process document %s: %s", document_id, e, exc_info=True)
        update_document_status(db, doc_uuid, DocumentStatus.FAILED)
        raise  # Re-raise to let Celery know the task failed