"""v1.9 进项发票模型——供应商成本票。"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Numeric, Date, Text, ForeignKey, DateTime,
)
from sqlalchemy.orm import relationship

from app.models.base import Base


class InputInvoice(Base):
    """进项发票表——与销项发票(invoices)完全独立。"""

    __tablename__ = "input_invoices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_no = Column(String(100), nullable=False, comment="发票编号")
    vendor_name = Column(String(200), nullable=False, comment="供应商名称")
    invoice_date = Column(Date, nullable=False, comment="发票日期")
    amount_excluding_tax = Column(Numeric(12, 2), nullable=False, comment="不含税金额")
    tax_rate = Column(Numeric(5, 4), nullable=False, default=0.13, comment="税率")
    tax_amount = Column(Numeric(12, 2), nullable=False, default=0, comment="税额")
    total_amount = Column(Numeric(12, 2), nullable=False, comment="价税合计")
    category = Column(String(50), nullable=False, default="other", comment="类别")
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
