"""v2.0 AI Agent 闭环——待办模型。"""
from sqlalchemy import Column, String, Text, Integer, Boolean, Date, DateTime, ForeignKey
from app.models.base import Base, TimestampMixin


class Todo(Base, TimestampMixin):
    """待办事项表。"""
    __tablename__ = "todos"

    title = Column(String(200), nullable=False)
    description = Column(Text, default="")
    priority = Column(String(20), default="medium")  # high / medium / low
    status = Column(String(20), default="pending")  # pending / in_progress / completed / cancelled
    due_date = Column(Date, nullable=True)
    is_completed = Column(Boolean, default=False, nullable=False)
    source = Column(String(50), nullable=True)  # agent_action / manual
    source_id = Column(Integer, nullable=True)  # 来源记录 ID
