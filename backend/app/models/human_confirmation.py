"""v2.0 AI Agent 闭环——人工确认模型。"""
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class HumanConfirmation(Base, TimestampMixin):
    """人工确认记录表。"""
    __tablename__ = "human_confirmations"

    suggestion_id = Column(Integer, ForeignKey("agent_suggestions.id"), nullable=False, index=True)
    decision_type = Column(String(20), nullable=False)  # accepted / rejected / modified
    reason_code = Column(String(50), nullable=True)
    free_text_reason = Column(Text, nullable=True)
    corrected_fields = Column(Text, nullable=True)  # 修改字段 JSON 字符串
    user_priority_override = Column(String(20), nullable=True)  # 用户覆盖的优先级
    inject_to_next_run = Column(Boolean, default=True, nullable=False)
    next_review_at = Column(DateTime, nullable=True)

    # 关联
    suggestion = relationship("AgentSuggestion", back_populates="confirmations")
