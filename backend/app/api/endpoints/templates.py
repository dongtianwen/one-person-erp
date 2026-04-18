"""v1.12 模板管理 API 端点。"""
import logging
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.constants import TEMPLATE_TYPE_CONTRACT, TEMPLATE_TYPE_QUOTATION, TEMPLATE_TYPE_WHITELIST
from app.core.error_codes import ERROR_CODES
from app.core.template_utils import validate_template_syntax
from app.crud import template as template_crud
from app.database import get_db
from app.models.template import Template

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=None)
async def get_templates(
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    template_type: Optional[str] = Query(None, enum=list(TEMPLATE_TYPE_WHITELIST))
):
    """
    获取模板列表。

    支持 template_type 参数筛选指定类型的模板。
    """
    templates = await template_crud.get_templates(db, skip=skip, limit=limit, template_type=template_type)

    return templates


@router.get("/{template_id}", response_model=None)
async def get_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    获取单个模板详情。
    """
    template = await template_crud.get_template_by_id(db, template_id)
    if not template:
        raise HTTPException(
            status_code=404,
            detail=ERROR_CODES["TEMPLATE_NOT_FOUND"]
        )
    return template


@router.post("/", response_model=None)
async def create_template(
    name: str,
    content: str,
    template_type: str = Query(..., enum=list(TEMPLATE_TYPE_WHITELIST)),
    description: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    创建新模板。

    - 校验模板类型
    - 校验模板语法
    - 创建模板
    """
    # 校验模板类型
    if template_type not in TEMPLATE_TYPE_WHITELIST:
        raise HTTPException(
            status_code=422,
            detail=ERROR_CODES["VALIDATION_ERROR"]
        )

    # 校验模板语法
    is_valid, error_msg = validate_template_syntax(content)
    if not is_valid:
        raise HTTPException(
            status_code=400,
            detail=f"模板语法错误: {error_msg}"
        )

    try:
        template = await template_crud.create_template(
            db=db,
            name=name,
            template_type=template_type,
            content=content,
            description=description
        )
        from app.services.snapshot_service import create_snapshot
        await create_snapshot(
            db=db,
            entity_type="template",
            entity_id=template.id,
            snapshot_json={"name": template.name, "content": template.content, "template_type": template.template_type},
        )
        return template
    except Exception as e:
        logger.error(f"创建模板失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="创建模板失败"
        )


@router.put("/{template_id}", response_model=None)
async def update_template(
    template_id: int,
    name: Optional[str] = None,
    content: Optional[str] = None,
    description: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    更新模板。

    - 校验模板是否存在
    - 校验模板语法（如果提供 content）
    - 更新模板
    """
    # 校验模板是否存在
    template = await template_crud.get_template_by_id(db, template_id)
    if not template:
        raise HTTPException(
            status_code=404,
            detail=ERROR_CODES["TEMPLATE_NOT_FOUND"]
        )

    # 校验模板语法（如果提供 content）
    if content:
        is_valid, error_msg = validate_template_syntax(content)
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"模板语法错误: {error_msg}"
            )

    try:
        updated_template = await template_crud.update_template(
            db=db,
            template_id=template_id,
            name=name,
            content=content,
            description=description
        )
        if not updated_template:
            raise HTTPException(
                status_code=500,
                detail="更新模板失败"
            )
        return updated_template
    except Exception as e:
        logger.error(f"更新模板失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="更新模板失败"
        )


@router.delete("/{template_id}", response_model=dict)
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    删除模板。

    - 校验模板是否存在
    - 保护默认模板不可删除
    - 删除模板
    """
    # 校验模板是否存在
    template = await template_crud.get_template_by_id(db, template_id)
    if not template:
        raise HTTPException(
            status_code=404,
            detail=ERROR_CODES["TEMPLATE_NOT_FOUND"]
        )

    # 保护默认模板不可删除
    if template.is_default == 1:
        raise HTTPException(
            status_code=400,
            detail=ERROR_CODES["TEMPLATE_IS_DEFAULT"]
        )

    try:
        success = await template_crud.delete_template(db, template_id)
        if not success:
            raise HTTPException(
                status_code=500,
                detail="删除模板失败"
            )
        return {"message": "删除成功"}
    except Exception as e:
        logger.error(f"删除模板失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="删除模板失败"
        )


@router.patch("/set-default", response_model=None)
async def set_default_template(
    template_id: int = Query(..., ge=1),
    template_type: str = Query(..., enum=list(TEMPLATE_TYPE_WHITELIST)),
    db: AsyncSession = Depends(get_db)
):
    """
    设置指定类型的默认模板（原子操作）。

    - 校验模板是否存在
    - 校验模板类型匹配
    - 原子操作：先清除同类型的默认，再设置新的默认
    """
    # 校验模板是否存在
    template = await template_crud.get_template_by_id(db, template_id)
    if not template:
        raise HTTPException(
            status_code=404,
            detail=ERROR_CODES["TEMPLATE_NOT_FOUND"]
        )

    # 校验模板类型匹配
    if template.template_type != template_type:
        raise HTTPException(
            status_code=400,
            detail=f"模板类型不匹配，期望 {template_type}，实际 {template.template_type}"
        )

    try:
        success = await template_crud.set_default_template(db, template_id, template_type)
        if not success:
            raise HTTPException(
                status_code=500,
                detail="设置默认模板失败"
            )
        await db.refresh(template)
        return template
    except Exception as e:
        logger.error(f"设置默认模板失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="设置默认模板失败"
        )


@router.get("/default/{template_type}")
async def get_default_template_by_type(
    template_type: str = Path(..., enum=list(TEMPLATE_TYPE_WHITELIST)),
    db: AsyncSession = Depends(get_db)
):
    """
    获取指定类型的默认模板。
    """
    template = await template_crud.get_default_template(db, template_type)

    if not template:
        raise HTTPException(
            status_code=404,
            detail=ERROR_CODES["TEMPLATE_NOT_FOUND"]
        )

    return template
