from sqlalchemy import Column, DateTime, Integer, String
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
