"""v1.11 训练实验模型。"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, DateTime, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.models.base import Base


class TrainingExperiment(Base):
    """训练实验——记录训练配置、关联数据集版本。"""

    __tablename__ = "training_experiments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False, comment="所属项目ID",
    )
    name = Column(String(200), nullable=False, comment="实验名称")
    description = Column(Text, nullable=True, comment="描述")
    framework = Column(String(100), nullable=True, comment="训练框架")
    hyperparameters = Column(Text, nullable=True, comment="超参数JSON")
    metrics = Column(Text, nullable=True, comment="评估指标JSON")
    status = Column(String(20), nullable=True, comment="状态: draft, running, completed, failed")
    started_at = Column(DateTime, nullable=True, comment="开始时间")
    finished_at = Column(DateTime, nullable=True, comment="结束时间")
    notes = Column(Text, nullable=True, comment="备注")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow,
    )

    dataset_versions = relationship(
        "ExperimentDatasetVersion", back_populates="experiment", lazy="selectin",
    )
    model_versions = relationship(
        "ModelVersion", back_populates="experiment", lazy="selectin",
    )


class ExperimentDatasetVersion(Base):
    """实验-数据集版本关联表——关联时自动设置 in_use。"""

    __tablename__ = "experiment_dataset_versions"
    __table_args__ = (
        UniqueConstraint("experiment_id", "dataset_version_id", name="uq_exp_dv"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    experiment_id = Column(
        Integer, ForeignKey("training_experiments.id", ondelete="CASCADE"),
        nullable=False, comment="实验ID",
    )
    dataset_version_id = Column(
        Integer, ForeignKey("dataset_versions.id", ondelete="RESTRICT"),
        nullable=False, comment="数据集版本ID",
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    experiment = relationship("TrainingExperiment", back_populates="dataset_versions")
