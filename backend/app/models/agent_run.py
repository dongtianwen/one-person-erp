"""v2.0 AI Agent 闭环——Agent 运行记录模型。"""
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, JSON, Numeric
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class AgentRun(Base, TimestampMixin):
    """Agent 运行记录表。

    一次运行产生多条建议。
    """
    __tablename__ = "agent_runs"

    agent_type = Column(String(50), nullable=False, index=True)  # business_decision / project_management
    trigger_type = Column(String(20), nullable=False, default="manual")  # manual / scheduled
    status = Column(String(20), nullable=False, default="running")  # running / completed / failed
    llm_provider = Column(String(20), nullable=True)  # none / local / api
    llm_enhanced = Column(Boolean, default=False, nullable=False)
    llm_model = Column(String(100), nullable=True)
    rule_output = Column(Text, nullable=True)  # 规则引擎输出 JSON
    context_snapshot = Column(JSON, nullable=True)  # 运行时的上下文快照
    error_message = Column(Text, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # 关联
    suggestions = relationship("AgentSuggestion", back_populates="agent_run", cascade="all, delete-orphan")
