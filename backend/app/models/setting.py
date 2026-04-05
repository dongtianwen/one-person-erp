from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, Boolean
from app.models.base import Base


class SystemSetting(Base):
    __tablename__ = "settings"

    key = Column(String(100), unique=True, nullable=False, primary_key=True)
    value = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
