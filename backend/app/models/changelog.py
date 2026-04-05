from sqlalchemy import Column, String, Text, Integer
from app.models.base import Base, TimestampMixin


class ChangeLog(Base, TimestampMixin):
    __tablename__ = "change_logs"

    entity_type = Column(String(50), nullable=False, index=True)
    entity_id = Column(Integer, nullable=False, index=True)
    field = Column(String(100), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    changed_by = Column(Integer, nullable=True)
