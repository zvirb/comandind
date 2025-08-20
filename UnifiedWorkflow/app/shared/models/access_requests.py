
from sqlalchemy import Column, Integer, String, DateTime, text
from sqlalchemy.ext.declarative import declarative_base
import datetime

Base = declarative_base()

class AccessRequest(Base):
    __tablename__ = 'access_requests'

    id = Column(Integer, primary_key=True)
    email = Column(String, nullable=False)
    status = Column(String, nullable=False, default='pending')
    token = Column(String, unique=True)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, server_default=text('CURRENT_TIMESTAMP'))

    def __repr__(self):
        return f"<AccessRequest(id={self.id}, email='{self.email}', status='{self.status}')>"
