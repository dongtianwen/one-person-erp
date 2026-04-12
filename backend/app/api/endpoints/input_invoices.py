"""v1.9 进项发票 CRUD API 路由。"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.input_invoice import InputInvoice
from app.core.input_invoice_utils import (
    calculate_input_invoice_amount,
    get_input_invoice_summary,
)

router = APIRouter()


@router.post("")
async def create_input_invoice(
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建进项发票。"""
    vendor_name = data.get("vendor_name")
    invoice_no = data.get("invoice_no")
    if not vendor_name:
        raise HTTPException(status_code=422, detail="供应商名称必填")
    if not invoice_no:
        raise HTTPException(status_code=422, detail="发票编号必填")

    amt_ex = Decimal(str(data.get("amount_excluding_tax", 0)))
    tax_rate = Decimal(str(data.get("tax_rate", 0.13)))
    if amt_ex <= 0:
        raise HTTPException(status_code=422, detail="金额必须大于 0")

    amounts = calculate_input_invoice_amount(amt_ex, tax_rate)

    inv = InputInvoice(
        invoice_no=invoice_no,
        vendor_name=vendor_name,
        invoice_date=date.fromisoformat(data["invoice_date"]),
        amount_excluding_tax=amt_ex,
        tax_rate=tax_rate,
        tax_amount=amounts["tax_amount"],
        total_amount=amounts["total_amount"],
        category=data.get("category", "other"),
        project_id=data.get("project_id"),
        notes=data.get("notes"),
    )
    db.add(inv)
    await db.commit()
    await db.refresh(inv)
    return {"id": inv.id, "message": "创建成功"}


@router.get("")
async def list_input_invoices(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取所有进项发票。"""
    stmt = select(InputInvoice).order_by(InputInvoice.invoice_date.desc())
    result = await db.execute(stmt)
    invoices = result.scalars().all()
    return [
        {
            "id": i.id,
            "invoice_no": i.invoice_no,
            "vendor_name": i.vendor_name,
            "invoice_date": i.invoice_date.isoformat(),
            "amount_excluding_tax": float(i.amount_excluding_tax),
            "tax_rate": float(i.tax_rate),
            "tax_amount": float(i.tax_amount),
            "total_amount": float(i.total_amount),
            "category": i.category,
            "project_id": i.project_id,
            "notes": i.notes,
        }
        for i in invoices
    ]


@router.get("/summary")
async def get_summary(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """进项发票汇总（按类别）。"""
    return await get_input_invoice_summary(db, start_date, end_date)


@router.get("/{invoice_id}")
async def get_input_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取单个进项发票详情。"""
    stmt = select(InputInvoice).where(InputInvoice.id == invoice_id)
    result = await db.execute(stmt)
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="进项发票不存在")
    return {
        "id": inv.id,
        "invoice_no": inv.invoice_no,
        "vendor_name": inv.vendor_name,
        "invoice_date": inv.invoice_date.isoformat(),
        "amount_excluding_tax": float(inv.amount_excluding_tax),
        "tax_rate": float(inv.tax_rate),
        "tax_amount": float(inv.tax_amount),
        "total_amount": float(inv.total_amount),
        "category": inv.category,
        "project_id": inv.project_id,
        "notes": inv.notes,
    }


@router.put("/{invoice_id}")
async def update_input_invoice(
    invoice_id: int,
    data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新进项发票。"""
    stmt = select(InputInvoice).where(InputInvoice.id == invoice_id)
    result = await db.execute(stmt)
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="进项发票不存在")

    for field in ("invoice_no", "vendor_name", "category", "notes"):
        if field in data:
            setattr(inv, field, data[field])

    if "invoice_date" in data:
        inv.invoice_date = date.fromisoformat(data["invoice_date"])

    if any(k in data for k in ("amount_excluding_tax", "tax_rate")):
        amt_ex = Decimal(str(data.get("amount_excluding_tax", inv.amount_excluding_tax)))
        tax_rate = Decimal(str(data.get("tax_rate", inv.tax_rate)))
        amounts = calculate_input_invoice_amount(amt_ex, tax_rate)
        inv.amount_excluding_tax = amt_ex
        inv.tax_rate = tax_rate
        inv.tax_amount = amounts["tax_amount"]
        inv.total_amount = amounts["total_amount"]

    if "project_id" in data:
        inv.project_id = data["project_id"]

    await db.commit()
    return {"message": "更新成功"}


@router.delete("/{invoice_id}")
async def delete_input_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除进项发票。"""
    stmt = select(InputInvoice).where(InputInvoice.id == invoice_id)
    result = await db.execute(stmt)
    inv = result.scalar_one_or_none()
    if not inv:
        raise HTTPException(status_code=404, detail="进项发票不存在")
    await db.delete(inv)
    await db.commit()
    return {"message": "删除成功"}
