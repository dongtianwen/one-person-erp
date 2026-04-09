"""v1.8 发票台账模型——发票完整生命周期管理。"""

from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Date, Text, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base


class Invoice(Base):
    """发票台账模型。

    状态流转: draft → issued → received → verified
             └────────→ cancelled (任意状态可作废)
    """

    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_no = Column(String(30), nullable=False, unique=True, comment="发票编号 INV-YYYYMMDD-序号")
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="RESTRICT"), nullable=False, comment="关联合同ID")

    # 发票基本信息
    invoice_type = Column(String(20), nullable=False, default="standard", comment="发票类型: standard/ordinary/electronic/small_scale")
    invoice_date = Column(Date, nullable=False, comment="发票日期")
    amount_excluding_tax = Column(Numeric(12, 2), nullable=False, comment="不含税金额")
    tax_rate = Column(Numeric(5, 4), nullable=False, default=Decimal("0.13"), comment="税率")
    tax_amount = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"), comment="税额")
    total_amount = Column(Numeric(12, 2), nullable=False, comment="价税合计")

    # 状态管理
    status = Column(String(20), nullable=False, default="draft", comment="状态: draft/issued/received/verified/cancelled")
    issued_at = Column(DateTime, nullable=True, comment="开具时间")
    received_at = Column(DateTime, nullable=True, comment="收票时间")
    received_by = Column(String(100), nullable=True, comment="收票人")
    verified_at = Column(DateTime, nullable=True, comment="核销时间")

    # 备注
    notes = Column(Text, nullable=True, comment="备注")

    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    # 关系
    contract = relationship("Contract", back_populates="invoices")
