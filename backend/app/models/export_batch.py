"""v1.8 导出批次模型——记录财务数据导出历史。"""

from datetime import date
from sqlalchemy import Column, String, Integer, Date, Text
from app.models.base import Base, TimestampMixin


class ExportBatch(Base, TimestampMixin):
    """导出批次记录表。"""
    __tablename__ = "export_batches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String(50), nullable=False, unique=True)  # EXP-YYYYMMDD-HHMMSS-随机6位
    export_type = Column(String(30), nullable=False)  # contracts, payments, invoices
    target_format = Column(String(20), nullable=False, default="generic")
    accounting_period = Column(String(7), nullable=True)  # YYYY-MM
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    record_count = Column(Integer, nullable=False, default=0)
    file_path = Column(Text, nullable=True)
