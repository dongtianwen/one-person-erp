from sqlalchemy import Column, String, Text, ForeignKey, Integer, Date, Numeric, Boolean
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


class RdExpense(Base, TimestampMixin):
    """
    研发费用台账——科技型中小企业认定/加计扣除专用。
    按税法六大类归集研发费用，与 FinanceRecord 松耦合关联。
    """
    __tablename__ = "rd_expenses"

    rd_no = Column(String(30), unique=True, nullable=False, index=True, comment="研发费用编号")

    project_id = Column(Integer, ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True, comment="所属研发项目")
    finance_record_id = Column(Integer, ForeignKey("finance_records.id", ondelete="SET NULL"), nullable=True, comment="关联原始支出记录")
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="SET NULL"), nullable=True, comment="关联合同")

    rd_category = Column(String(30), nullable=False, index=True, comment="费用大类（税法六大类）")
    rd_sub_category = Column(String(50), nullable=True, comment="子分类（细粒度）")

    amount = Column(Numeric(12, 2), nullable=False, comment="费用金额（不含税）")
    tax_amount = Column(Numeric(12, 2), nullable=True, default=0, comment="税额")
    total_amount = Column(Numeric(12, 2), nullable=True, comment="价税合计")

    expense_date = Column(Date, nullable=False, index=True, comment="费用发生日期")
    accounting_period = Column(String(7), nullable=True, index=True, comment="会计期间 YYYY-MM")

    description = Column(Text, default="", comment="费用说明")
    vendor_name = Column(String(200), nullable=True, comment="供应商/收款方名称")
    invoice_no = Column(String(50), nullable=True, comment="凭证号/发票号")
    has_invoice = Column(Boolean, nullable=True, default=None, comment="是否取得有效凭证")
    invoice_type = Column(String(20), nullable=True, comment="凭证类型")

    status = Column(String(20), nullable=False, default="draft", index=True, comment="审核状态")
    notes = Column(Text, nullable=True, comment="备注信息")

    project = relationship("Project", foreign_keys=[project_id])
    finance_record = relationship("FinanceRecord", foreign_keys=[finance_record_id], back_populates="rd_expenses")
    contract = relationship("Contract", foreign_keys=[contract_id])
