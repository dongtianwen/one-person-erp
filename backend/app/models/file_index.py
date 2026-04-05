import uuid

from sqlalchemy import Column, String, Text, Boolean, Integer, Date
from app.models.base import Base, TimestampMixin


class FileIndex(Base, TimestampMixin):
    __tablename__ = "file_indexes"

    file_group_id = Column(String(36), nullable=False, index=True)
    file_name = Column(String(200), nullable=False)
    file_type = Column(String(30), nullable=False)
    version = Column(String(50), nullable=True)
    is_current = Column(Boolean, default=True, nullable=False)
    issue_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    storage_location = Column(String(500), nullable=True)
    entity_type = Column(String(30), nullable=True)
    entity_id = Column(Integer, nullable=True)
    issuing_authority = Column(String(200), nullable=True)
    note = Column(Text, nullable=True)

    @staticmethod
    def generate_group_id() -> str:
        return str(uuid.uuid4())
