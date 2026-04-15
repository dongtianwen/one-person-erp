"""v2.0 AI Agent 闭环——动作模型。"""
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class AgentAction(Base, TimestampMixin):
    """Agent 动作表。

    确认建议后自动创建并执行的动作。
    """
    __tablename__ = "agent_actions"

    suggestion_id = Column(Integer, ForeignKey("agent_suggestions.id"), nullable=False, index=True)
    action_type = Column(String(50), nullable=False)  # create_todo / create_reminder / generate_report
    action_params = Column(Text, nullable=True)  # 动作参数 JSON 字符串
    status = Column(String(20), nullable=False, default="pending")  # pending / executed / failed
    result = Column(Text, nullable=True)  # 执行结果
    error_message = Column(Text, nullable=True)
    executed_at = Column(DateTime, nullable=True)

    # 关联
    suggestion = relationship("AgentSuggestion", back_populates="actions")
