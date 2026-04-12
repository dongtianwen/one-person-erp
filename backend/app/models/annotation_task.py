"""v1.11 标注任务模型。"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, DateTime,
)
from sqlalchemy.orm import relationship

from app.models.base import Base


class AnnotationTask(Base):
    """标注任务——关联项目与数据集版本，追踪标注进度与质检。"""

    __tablename__ = "annotation_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False, comment="所属项目ID",
    )
    dataset_version_id = Column(
        Integer, ForeignKey("dataset_versions.id", ondelete="RESTRICT"),
        nullable=False, comment="关联数据集版本ID",
    )
    name = Column(String(200), nullable=False, comment="任务名称")
    status = Column(
        String(30), nullable=False, default="pending", comment="状态",
    )
    batch_no = Column(String(50), nullable=True, comment="批次号")
    sample_count = Column(Integer, nullable=True, comment="样本数")
    annotator_count = Column(Integer, nullable=True, comment="标注人数")
    assignee = Column(String(100), nullable=True, comment="负责人")
    deadline = Column(DateTime, nullable=True, comment="截止日期")
    progress = Column(Integer, nullable=True, comment="进度(%)")
    quality_check_result = Column(Text, nullable=True, comment="质检结果")
    rework_reason = Column(Text, nullable=True, comment="返工原因")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")
    notes = Column(Text, nullable=True, comment="备注")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow,
    )
