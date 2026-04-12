"""v1.11 数据集与数据集版本模型。"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, DateTime, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.models.base import Base


class Dataset(Base):
    """数据集台账——关联项目，管理数据集元信息。"""

    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False, comment="所属项目ID",
    )
    name = Column(String(200), nullable=False, comment="数据集名称")
    dataset_type = Column(
        String(30), nullable=False, default="other", comment="数据集类型",
    )
    description = Column(Text, nullable=True, comment="描述")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow,
    )

    versions = relationship(
        "DatasetVersion", back_populates="dataset", lazy="selectin",
    )


class DatasetVersion(Base):
    """数据集版本——支持 draft/ready/in_use/archived 状态流转与字段冻结。"""

    __tablename__ = "dataset_versions"
    __table_args__ = (
        UniqueConstraint("dataset_id", "version_no", name="uq_dataset_version"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(
        Integer, ForeignKey("datasets.id", ondelete="RESTRICT"),
        nullable=False, comment="所属数据集ID",
    )
    version_no = Column(String(20), nullable=False, comment="版本号，如 v1.0")
    status = Column(
        String(20), nullable=False, default="draft", comment="状态",
    )
    sample_count = Column(Integer, nullable=True, comment="样本数")
    file_path = Column(Text, nullable=True, comment="文件路径")
    data_source = Column(Text, nullable=True, comment="数据来源描述")
    label_schema_version = Column(
        String(50), nullable=True, comment="标注规范版本号",
    )
    change_summary = Column(Text, nullable=True, comment="与上一版本的变更说明")
    notes = Column(Text, nullable=True, comment="备注")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow,
    )

    dataset = relationship("Dataset", back_populates="versions")
