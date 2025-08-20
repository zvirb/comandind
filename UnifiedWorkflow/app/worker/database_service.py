"""Provides database service functions for interacting with the application's models."""

import logging
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session  # Keep this import
from shared.database.models import Document, DocumentChunk, DocumentStatus, SessionState

logger = logging.getLogger(__name__)


def get_all_documents(db: Session, user_id: int) -> List[Document]:
    """
    Retrieves all documents for a specific user from the database,
    ordered by most recent.
    """
    try:
        # Filter documents by the user_id and order by most recent
        documents = (
            db.query(Document).filter(Document.user_id == user_id)
            .order_by(Document.created_at.desc()).all()
        )
        logger.info("Successfully retrieved %d documents from the database.", len(documents))
        return documents
    except SQLAlchemyError as e:
        logger.error("Error retrieving documents from the database: %s", e, exc_info=True)
        # In case of an error, return an empty list to prevent the application from crashing.
        return []


def create_document(db: Session, filename: str, user_id: int) -> Document:
    """
    Creates a new document record in the database.

    Args:
        db: The database session.
        filename: The name of the uploaded file.
        user_id: The ID of the user who uploaded the file.

    Returns:
        The newly created Document object.
    """
    try:
        new_document = Document(filename=filename, user_id=user_id)
        db.add(new_document)
        db.commit()
        db.refresh(new_document)
        logger.info("Created document record for '%s' with ID: %s", filename, new_document.id)
        return new_document
    except SQLAlchemyError as e:
        logger.error(
            "Error creating document record for filename %s: %s", filename, e, exc_info=True
        )
        db.rollback()
        raise  # Re-raise the exception to be handled by the caller


def get_document_by_id_and_user(
    db: Session, document_id: uuid.UUID, user_id: int
) -> Optional[Document]:
    """
    Retrieves a single document by its ID, but only if it belongs to the specified user.
    This is useful for authorization checks before performing an action.

    Args:
        db: The database session.
        document_id: The UUID of the document to retrieve.
        user_id: The ID of the user who must own the document.

    Returns:
        The Document object if found and owned by the user, otherwise None.
    """
    try:
        return db.query(Document).filter(
            Document.id == document_id, Document.user_id == user_id
        ).first()
    except SQLAlchemyError as e:
        logger.error(
            "Error retrieving document %s for user %s: %s", document_id, user_id, e, exc_info=True
        )
        return None


def update_document_status(db: Session, document_id: uuid.UUID, status: DocumentStatus):
    """Updates the status of a document in the database."""
    try:
        document = db.query(Document).filter(Document.id == document_id).first()
        if document:
            document.status = status
            db.commit()
            logger.info("Updated status for document %s to %s", document_id, status.value)
        else:
            logger.warning(
                "Could not find document %s to update status to %s", document_id, status.value
            )
    except SQLAlchemyError as e:
        logger.error(
            "Error updating document status for ID %s: %s", document_id, e, exc_info=True
        )
        db.rollback()
        raise


def create_document_chunks(db: Session, document_id: uuid.UUID, chunks_data: List[Dict[str, Any]]):
    """
    Creates document chunk records in the database in a single transaction.

    Args:
        db: The database session.
        document_id: The UUID of the parent document.
        chunks_data: A list of dictionaries, where each dict contains
                     'chunk_index', 'content', and optionally 'vector_id'.
    """
    try:
        new_chunks = [
            DocumentChunk(
                document_id=document_id,
                chunk_index=chunk['chunk_index'],
                content=chunk['content'],
                vector_id=chunk.get('vector_id')  # vector_id might be optional initially
            )
            for chunk in chunks_data
        ]
        db.add_all(new_chunks)
        db.commit()
        logger.info(
            "Successfully created %d chunks for document ID: %s", len(new_chunks), document_id
        )
    except SQLAlchemyError as e:
        logger.error(
            "Error creating document chunks for document ID %s: %s", document_id, e, exc_info=True
        )
        db.rollback()
        raise  # Re-raise the exception to be handled by the caller


def delete_document(db: Session, document_id: uuid.UUID, user_id: int) -> bool:
    """
    Deletes a document and its associated chunks from the database.
    Ensures that the user owns the document before deleting.

    Args:
        db: The database session.
        document_id: The UUID of the document to delete.
        user_id: The ID of the user requesting the deletion.

    Returns:
        True if the document was deleted, False otherwise.
    """
    try:
        document = db.query(Document).filter(
            Document.id == document_id, Document.user_id == user_id
        ).first()
        if document:
            db.delete(document)
            db.commit()
            logger.info("Successfully deleted document with ID: %s", document_id)
            return True
        logger.warning(
            "Attempted to delete a document that does not exist. ID: %s", document_id
        )
        return False
    except SQLAlchemyError as e:
        logger.error("Error deleting document with ID %s: %s", document_id, e, exc_info=True)
        db.rollback()
        return False


def get_session_state(db: Session, session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves session state from the database."""
    try:
        session_record = db.query(SessionState).filter(
            SessionState.session_id == session_id
        ).first()
        if session_record:
            logger.debug("Retrieved session state for session_id %s", session_id)
            return session_record.state
        logger.debug("No session state found for session_id %s", session_id)
    except SQLAlchemyError as e:
        logger.error(
            "Error retrieving session state for session_id %s: %s", session_id, e, exc_info=True
        )
    return None


def save_session_state(db: Session, session_id: str, state_data: Dict[str, Any]):
    """Saves or updates session state in the database."""
    try:
        session_record = db.query(SessionState).filter(
            SessionState.session_id == session_id
        ).first()
        if session_record:
            session_record.state = state_data
            # The 'updated_at' field is handled automatically by the database via onupdate.
        else:
            session_record = SessionState(session_id=session_id, state=state_data)
            db.add(session_record)
        db.commit()
        logger.debug("Saved session state for session_id %s", session_id)
    except SQLAlchemyError as e:
        logger.error(
            "Error saving session state for session_id %s: %s", session_id, e, exc_info=True
        )
        db.rollback()
        raise
