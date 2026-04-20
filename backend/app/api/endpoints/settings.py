"""公司设置 API 端点。"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.crud.setting import (
    get_company_settings, update_company_settings,
    COMPANY_KEYS, TAX_CONFIG_KEYS,
    get_setting, set_setting,
)

router = APIRouter()


@router.get("/company")
async def api_get_company_settings(
    db: AsyncSession = Depends(get_db),
):
    """获取公司设置（乙方信息）。"""
    settings = await get_company_settings(db)
    result = {key: settings.get(key, "") for key in COMPANY_KEYS}
    return {"success": True, "data": result}


@router.put("/company")
async def api_update_company_settings(
    data: dict[str, str],
    db: AsyncSession = Depends(get_db),
):
    """更新公司设置（乙方信息）。"""
    filtered = {k: v for k, v in data.items() if k in COMPANY_KEYS}
    await update_company_settings(db, filtered)
    await db.commit()
    return {"success": True, "message": "公司设置已更新"}


@router.get("/tax-config")
async def api_get_tax_config(
    db: AsyncSession = Depends(get_db),
):
    """获取税务配置。"""
    from app.core.tax_calculator import TaxConfig
    config = await TaxConfig.load_from_db(db)
    return {"success": True, "data": config.as_dict()}


@router.put("/tax-config")
async def api_update_tax_config(
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """更新税务配置。"""
    allowed = set(TAX_CONFIG_KEYS)
    filtered = {k: str(v) for k, v in data.items() if k in allowed}
    for key, value in filtered.items():
        await set_setting(db, key, value)
    await db.commit()
    return {"success": True, "message": "税务配置已更新"}
