"""v1.12 模板管理模型。"""
from sqlalchemy import Column, String, Text, Integer
from app.models.base import Base, TimestampMixin


class Template(Base, TimestampMixin):
    """模板表：存储报价单和合同的 Jinja2 模板。"""
    __tablename__ = "templates"

    name = Column(String(200), nullable=False, comment="模板名称")
    template_type = Column(String(30), nullable=False, comment="模板类型: quotation/contract")
    content = Column(Text, nullable=False, comment="模板内容（Jinja2）")
    is_default = Column(Integer, nullable=False, default=0, comment="是否默认模板")
    description = Column(Text, nullable=True, comment="模板描述")

    # 关联关系（暂未定义 relationship，因为不是每个模块都使用模板）
