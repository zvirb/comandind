"""
SQLAlchemy model for access_requests table.
"""
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import Column, String, DateTime, func, Enum
from sqlalchemy.dialects.postgresql import UUID
from shared.utils.database_setup import Base

class AccessRequest(Base):
    """
    Represents an access request for client certificates.
    """
    __tablename__ = 'access_requests'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False)
    status = Column(Enum('pending', 'approved', 'rejected', name='access_request_status'), nullable=False, default='pending')
    token = Column(String, unique=True, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<AccessRequest(id={self.id}, email='{self.email}', status='{self.status}')>"

    def set_token(self, session):
        """
        Generates a secure token for the access request.
        """
        self.token = str(uuid.uuid4())
        self.expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        session.add(self)
        session.commit()
