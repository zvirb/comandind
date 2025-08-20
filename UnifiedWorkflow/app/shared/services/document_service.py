"""
Service layer for document-related database operations.

This module provides a set of functions to interact with the Document model
in the database. It is placed in the 'shared' directory as these functions
are used by both the API and the Celery worker.
"""
import logging
import uuid
from typing import List, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import overload, Union

from shared.database.models import Document

logger = logging.getLogger(__name__)


def create_document(db: Session, filename: str, user_id: int) -> Document:
    """
    Creates a new document record in the database.
    A unique ID is generated for the document.
    """
    db_document = Document(
        id=uuid.uuid4(), filename=filename, user_id=user_id  # Content will be added by the worker as chunks
    )
    try:
        db.add(db_document)
        db.commit()
        db.refresh(db_document)
        logger.info("Created document record with ID: %s for user: %s", db_document.id, user_id)
        return db_document
    except SQLAlchemyError as e:
        db.rollback()
        logger.error("Database error while creating document: %s", e, exc_info=True)
        raise


async def create_document_async(db: AsyncSession, filename: str, user_id: int) -> Document:
    """
    Creates a new document record in the database asynchronously.
    A unique ID is generated for the document.
    """
    db_document = Document(
        id=uuid.uuid4(), filename=filename, user_id=user_id  # Content will be added by the worker as chunks
    )
    try:
        db.add(db_document)
        await db.commit()
        await db.refresh(db_document)
        logger.info("Created document record with ID: %s for user: %s", db_document.id, user_id)
        return db_document
    except SQLAlchemyError as e:
        await db.rollback()
        logger.error("Database error while creating document: %s", e, exc_info=True)
        raise


def get_all_documents(db: Session, user_id: int) -> List[Document]:
    """Retrieves all documents for a given user."""
    return db.query(Document).filter(Document.user_id == user_id).order_by(Document.created_at.desc()).all()


async def get_all_documents_async(db: AsyncSession, user_id: int) -> List[Document]:
    """Retrieves all documents for a given user asynchronously."""
    result = await db.execute(
        select(Document)
        .filter(Document.user_id == user_id)
        .order_by(Document.created_at.desc())
    )
    return result.scalars().all()


def get_document_by_id_and_user(db: Session, document_id: uuid.UUID, user_id: int) -> Optional[Document]:
    """
    Retrieves a single document by its ID, ensuring it belongs to the specified user.
    """
    return db.query(Document).filter(Document.id == document_id, Document.user_id == user_id).first()


async def get_document_by_id_and_user_async(db: AsyncSession, document_id: uuid.UUID, user_id: int) -> Optional[Document]:
    """
    Retrieves a single document by its ID, ensuring it belongs to the specified user asynchronously.
    """
    result = await db.execute(
        select(Document).filter(Document.id == document_id, Document.user_id == user_id)
    )
    return result.scalar_one_or_none()


def delete_document(db: Session, document_id: uuid.UUID, user_id: int) -> bool:
    """
    Deletes a document record from the database, verifying ownership first.
    Returns True if a document was deleted, False otherwise.
    """
    document = get_document_by_id_and_user(db, document_id=document_id, user_id=user_id)
    if document:
        try:
            db.delete(document)
            db.commit()
            logger.info("Deleted document record with ID: %s for user: %s", document_id, user_id)
            return True
        except SQLAlchemyError as e:
            db.rollback()
            logger.error("Database error while deleting document %s: %s", document_id, e, exc_info=True)
            raise
    return False


async def delete_document_async(db: AsyncSession, document_id: uuid.UUID, user_id: int) -> bool:
    """
    Deletes a document record from the database, verifying ownership first asynchronously.
    Returns True if a document was deleted, False otherwise.
    """
    document = await get_document_by_id_and_user_async(db, document_id=document_id, user_id=user_id)
    if document:
        try:
            await db.delete(document)
            await db.commit()
            logger.info("Deleted document record with ID: %s for user: %s", document_id, user_id)
            return True
        except SQLAlchemyError as e:
            await db.rollback()
            logger.error("Database error while deleting document %s: %s", document_id, e, exc_info=True)
            raise
    return False