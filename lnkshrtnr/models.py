import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from .database import db


class ShortenedLink(db.Model):
    code = Column(String, primary_key=True, nullable=False)
    default_parameter = Column(String, nullable=True)
    redirect_to = Column(String, nullable=False)
    clicks = Column(Integer, default=0)
    created_by = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    deleted_at = Column(DateTime, nullable=True)


class ShortenedLinkClick(db.Model):
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    link_id = Column(ForeignKey(ShortenedLink.code))
    clicked_at = Column(DateTime, default=func.now())
    client_ip = Column(String, nullable=False)
    referer = Column(String, nullable=False)
    user_agent = Column(String, nullable=False)
    source = Column(String, nullable=True)
    medium = Column(String, nullable=True)
    campaign = Column(String, nullable=True)
    term = Column(String, nullable=True)
    content = Column(String, nullable=True)
