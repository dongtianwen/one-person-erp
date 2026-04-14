"""v1.12 模板管理 CRUD 操作。"""
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.template import Template


async def get_templates(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    template_type: Optional[str] = None
) -> List[Template]:
    """
    获取模板列表。

    Args:
        db: 数据库会话
        skip: 跳过条数
        limit: 限制条数
        template_type: 模板类型筛选

    Returns:
        模板列表
    """
    stmt = select(Template)
    if template_type:
        stmt = stmt.where(Template.template_type == template_type)
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_template_by_id(db: AsyncSession, template_id: int) -> Optional[Template]:
    """
    根据 ID 获取模板。

    Args:
        db: 数据库会话
        template_id: 模板 ID

    Returns:
        模块对象或 None
    """
    stmt = select(Template).where(Template.id == template_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_default_template(db: AsyncSession, template_type: str) -> Optional[Template]:
    """
    获取指定类型的默认模板。

    Args:
        db: 数据库会话
        template_type: 模板类型

    Returns:
        模块对象或 None
    """
    stmt = select(Template).where(
        Template.template_type == template_type,
        Template.is_default == 1
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create_template(
    db: AsyncSession,
    name: str,
    template_type: str,
    content: str,
    description: Optional[str] = None
) -> Template:
    """
    创建新模板。

    Args:
        db: 数据库会话
        name: 模板名称
        template_type: 模板类型
        content: 模板内容
        description: 模板描述

    Returns:
        创建的模板对象
    """
    template = Template(
        name=name,
        template_type=template_type,
        content=content,
        description=description,
        is_default=0
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


async def update_template(
    db: AsyncSession,
    template_id: int,
    name: Optional[str] = None,
    content: Optional[str] = None,
    description: Optional[str] = None
) -> Optional[Template]:
    """
    更新模板。

    Args:
        db: 数据库会话
        template_id: 模板 ID
        name: 新的模板名称
        content: 新的模板内容
        description: 新的模板描述

    Returns:
        更新后的模板对象或 None
    """
    template = await get_template_by_id(db, template_id)
    if not template:
        return None

    if name is not None:
        template.name = name
    if content is not None:
        template.content = content
    if description is not None:
        template.description = description

    await db.commit()
    await db.refresh(template)
    return template


async def delete_template(db: AsyncSession, template_id: int) -> bool:
    """
    删除模板。

    Args:
        db: 数据库会话
        template_id: 模板 ID

    Returns:
        是否删除成功
    """
    template = await get_template_by_id(db, template_id)
    if not template:
        return False

    # 默认模板不可删除
    if template.is_default == 1:
        return False

    await db.delete(template)
    await db.commit()
    return True


async def set_default_template(
    db: AsyncSession,
    template_id: int,
    template_type: str
) -> bool:
    """
    设置指定类型的默认模板（原子操作）。

    Args:
        db: 数据库会话
        template_id: 模板 ID
        template_type: 模板类型

    Returns:
        是否设置成功
    """
    from sqlalchemy import update

    # 先将同类型的默认模板设为非默认
    await db.execute(
        update(Template)
        .where(
            Template.template_type == template_type,
            Template.is_default == 1
        )
        .values(is_default=0)
    )

    # 再将指定模板设为默认
    await db.execute(
        update(Template)
        .where(Template.id == template_id)
        .values(is_default=1)
    )

    await db.commit()
    return True
