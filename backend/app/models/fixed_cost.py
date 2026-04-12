"""v1.9 固定成本模型。"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Numeric, Date, Text, ForeignKey, DateTime,
)
from sqlalchemy.orm import relationship

from app.models.base import Base


class FixedCost(Base):
    """固定成本表——办公/云服务/软件/设备等。"""

    __tablename__ = "fixed_costs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, comment="名称")
    category = Column(String(30), nullable=False, default="other", comment="分类")
    amount = Column(Numeric(12, 2), nullable=False, comment="金额")
    period = Column(String(20), nullable=False, default="monthly", comment="周期")
    effective_date = Column(Date, nullable=False, comment="生效日期")
    end_date = Column(Date, nullable=True, comment="结束日期(NULL=持续)")
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True, comment="关联项目ID",
    )
    notes = Column(Text, nullable=True, comment="备注")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow,
    )

    project = relationship("Project", foreign_keys=[project_id])
