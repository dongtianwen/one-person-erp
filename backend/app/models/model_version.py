"""v1.11 模型版本模型。"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, DateTime, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.models.base import Base


class ModelVersion(Base):
    """模型版本——支持 training/ready/delivered/deprecated 状态流转与字段冻结。"""

    __tablename__ = "model_versions"
    __table_args__ = (
        UniqueConstraint("project_id", "name", "version_no", name="uq_model_ver"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False, comment="所属项目ID",
    )
    experiment_id = Column(
        Integer, ForeignKey("training_experiments.id", ondelete="RESTRICT"),
        nullable=False, comment="所属实验ID",
    )
    name = Column(String(200), nullable=False, comment="模型名称")
    version_no = Column(String(30), nullable=False, comment="版本号，如 v1.0.0")
    status = Column(
        String(20), nullable=False, default="training", comment="状态",
    )
    metrics = Column(Text, nullable=True, comment="评估指标JSON")
    file_path = Column(Text, nullable=True, comment="模型文件路径")
    notes = Column(Text, nullable=True, comment="备注")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow,
    )

    experiment = relationship("TrainingExperiment", back_populates="model_versions")
