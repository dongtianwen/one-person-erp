"""v1.11 交付包模型。"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, DateTime, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.models.base import Base


class DeliveryPackage(Base):
    """交付包——聚合模型版本和数据集版本，支持交付与验收流程。"""

    __tablename__ = "delivery_packages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(
        Integer, ForeignKey("projects.id", ondelete="RESTRICT"),
        nullable=False, comment="所属项目ID",
    )
    name = Column(String(200), nullable=False, comment="包名称")
    status = Column(
        String(20), nullable=False, default="draft", comment="状态",
    )
    description = Column(Text, nullable=True, comment="描述")
    delivered_at = Column(DateTime, nullable=True, comment="交付时间")
    notes = Column(Text, nullable=True, comment="备注")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow,
    )

    model_versions = relationship(
        "PackageModelVersion", back_populates="package", lazy="selectin",
    )
    dataset_versions = relationship(
        "PackageDatasetVersion", back_populates="package", lazy="selectin",
    )


class PackageModelVersion(Base):
    """交付包-模型版本关联。"""

    __tablename__ = "package_model_versions"
    __table_args__ = (
        UniqueConstraint("package_id", "model_version_id", name="uq_pkg_mv"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    package_id = Column(
        Integer, ForeignKey("delivery_packages.id", ondelete="CASCADE"),
        nullable=False, comment="交付包ID",
    )
    model_version_id = Column(
        Integer, ForeignKey("model_versions.id", ondelete="RESTRICT"),
        nullable=False, comment="模型版本ID",
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    package = relationship("DeliveryPackage", back_populates="model_versions")


class PackageDatasetVersion(Base):
    """交付包-数据集版本关联。"""

    __tablename__ = "package_dataset_versions"
    __table_args__ = (
        UniqueConstraint("package_id", "dataset_version_id", name="uq_pkg_dv"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    package_id = Column(
        Integer, ForeignKey("delivery_packages.id", ondelete="CASCADE"),
        nullable=False, comment="交付包ID",
    )
    dataset_version_id = Column(
        Integer, ForeignKey("dataset_versions.id", ondelete="RESTRICT"),
        nullable=False, comment="数据集版本ID",
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    package = relationship("DeliveryPackage", back_populates="dataset_versions")
