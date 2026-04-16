from sqlalchemy import Column, String, Text, ForeignKey, Integer, Date, Float, DateTime
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Contract(Base, TimestampMixin):
    # v1.12 模板和内容生成相关字段
    generated_content = Column(Text, nullable=True)  # 生成的完整内容
    template_id = Column(Integer, ForeignKey("templates.id", ondelete="SET NULL"), nullable=True)  # 使用的模板ID
    content_generated_at = Column(DateTime, nullable=True)  # 内容生成时间
    """
    合同：与客户签订的正式服务协议。
    合同金额是收款和发票的核对基准，不等同于实收金额。
    一份合同通常对应一个项目（1:1），特殊情况可扩展。
    合同是发票开具的前提，发票必须关联已存在的合同。
    """
    __tablename__ = "contracts"

    contract_no = Column(String(50), unique=True, nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    title = Column(String(200), nullable=False)
    amount = Column(Float, nullable=False)
    signed_date = Column(Date, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    status = Column(String(20), default="draft")
    terms = Column(Text, default="")
    termination_reason = Column(Text, nullable=True)

    # v1.3 现金流预测字段
    expected_payment_date = Column(Date, nullable=True)
    payment_stage_note = Column(String(200), nullable=True)

    # v1.6 报价转合同反查
    quotation_id = Column(Integer, ForeignKey("quotations.id", ondelete="SET NULL"), nullable=True)

    customer = relationship("Customer", back_populates="contracts")
    project = relationship("Project", back_populates="contracts")
    finance_records = relationship("FinanceRecord", back_populates="contract", cascade="all, delete-orphan")
    change_orders = relationship("ChangeOrder", back_populates="contract")
    invoices = relationship("Invoice", back_populates="contract", cascade="all, delete-orphan")
    quotation = relationship("Quotation", foreign_keys=[quotation_id])
    template = relationship("Template", foreign_keys=[template_id])
