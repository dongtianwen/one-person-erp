"""v2.0/v2.2 AI Agent 闭环——建议模型。"""
from sqlalchemy import Column, String, Text, Integer, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class AgentSuggestion(Base, TimestampMixin):
    """Agent 建议表。

    一条运行产生多条建议。
    """
    __tablename__ = "agent_suggestions"

    agent_run_id = Column(Integer, ForeignKey("agent_runs.id"), nullable=False, index=True)
    decision_type = Column(String(50), nullable=False)  # overdue_payment / profit_anomaly / milestone_risk 等
    suggestion_type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String(20), nullable=False, default="medium")  # high / medium / low
    status = Column(String(20), nullable=False, default="pending")  # pending / confirmed / rejected
    suggested_action = Column(String(50), nullable=False, default="none")  # create_todo / create_reminder / generate_report / none
    action_params = Column(Text, nullable=True)  # 动作参数 JSON 字符串
    source_rule = Column(String(100), nullable=True)  # 来源规则名称
    llm_enhanced = Column(Integer, default=0, nullable=False)  # 是否经 LLM 增强
    risk_score = Column(Integer, default=0, nullable=False)  # v2.2 风险评分（0-100）
    strategy_code = Column(String(50), default="", nullable=False)  # v2.2 策略码
    score_breakdown = Column(Text, nullable=True)  # v2.2 评分拆解 JSON

    # 关联
    agent_run = relationship("AgentRun", back_populates="suggestions")
    actions = relationship("AgentAction", back_populates="suggestion", cascade="all, delete-orphan")
    confirmations = relationship("HumanConfirmation", back_populates="suggestion", cascade="all, delete-orphan")
