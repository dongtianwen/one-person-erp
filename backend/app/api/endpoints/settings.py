"""公司设置 API 端点。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.crud.setting import get_company_settings, update_company_settings, COMPANY_KEYS

router = APIRouter()


@router.get("/company")
async def api_get_company_settings(
    db: AsyncSession = Depends(get_db),
):
    """获取公司设置（乙方信息）。"""
    settings = await get_company_settings(db)
    # 确保所有 key 都返回，即使为空
    result = {key: settings.get(key, "") for key in COMPANY_KEYS}
    return {"success": True, "data": result}


@router.put("/company")
async def api_update_company_settings(
    data: dict[str, str],
    db: AsyncSession = Depends(get_db),
):
    """更新公司设置（乙方信息）。"""
    # 只接受已知的 key
    filtered = {k: v for k, v in data.items() if k in COMPANY_KEYS}
    await update_company_settings(db, filtered)
    await db.commit()
    return {"success": True, "message": "公司设置已更新"}
