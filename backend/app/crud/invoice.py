"""v1.8 发票 CRUD 操作——包含业务逻辑。"""

from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exception_handlers import BusinessException

from app.models.invoice import Invoice
from app.models.contract import Contract
from app.schemas.invoice import InvoiceCreate, InvoiceUpdate
from app.crud.invoice_utils import (
    generate_invoice_no,
    calculate_invoice_amount,
    validate_invoice_amount,
    validate_invoice_transition,
    get_invoice_summary,
)


class CRUDInvoice:
    """发票 CRUD 操作。"""

    async def get(self, db: AsyncSession, id: int) -> Optional[Invoice]:
        """获取单个发票（含关联信息）。"""
        result = await db.execute(
            select(Invoice)
            .options(selectinload(Invoice.contract))
            .where(Invoice.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by_no(self, db: AsyncSession, invoice_no: str) -> Optional[Invoice]:
        """根据发票编号获取。"""
        result = await db.execute(
            select(Invoice).where(Invoice.invoice_no == invoice_no)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 20,
        contract_id: Optional[int] = None,
        invoice_status: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Tuple[List[Invoice], int]:
        """列表查询（支持筛选）。"""
        query = select(Invoice).options(selectinload(Invoice.contract))
        count_query = select(func.count()).select_from(Invoice)

        conditions = []
        if contract_id:
            conditions.append(Invoice.contract_id == contract_id)
        if invoice_status:
            conditions.append(Invoice.status == invoice_status)
        if start_date:
            conditions.append(Invoice.invoice_date >= start_date)
        if end_date:
            conditions.append(Invoice.invoice_date <= end_date)

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        # 统计总数
        count_result = await db.execute(count_query)
        total = count_result.scalar()

        # 分页查询，按发票日期倒序
        query = query.order_by(Invoice.invoice_date.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def create(
        self, db: AsyncSession, obj_in: InvoiceCreate
    ) -> Invoice:
        """创建发票（原子事务：生成编号 + 校验金额 + 计算）。"""
        # 1. 验证合同存在
        result = await db.execute(
            select(Contract).where(Contract.id == obj_in.contract_id)
        )
        contract = result.scalar_one_or_none()
        if not contract:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="发票必须关联合同"
            )

        # 2. 生成发票编号
        invoice_no = await generate_invoice_no(db, obj_in.invoice_date)

        # 3. 计算税额和价税合计
        calc_result = calculate_invoice_amount(
            obj_in.amount_excluding_tax, obj_in.tax_rate
        )

        # 4. 校验累计金额不超合同
        total_amount = calc_result["total_amount"]
        if not await validate_invoice_amount(
            db, obj_in.contract_id, total_amount
        ):
            raise BusinessException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="开票金额已超合同金额",
                code="INVOICE_AMOUNT_EXCEEDS_CONTRACT",
            )

        # 5. 创建发票记录
        db_obj = Invoice(
            invoice_no=invoice_no,
            contract_id=obj_in.contract_id,
            invoice_type=obj_in.invoice_type,
            invoice_date=obj_in.invoice_date,
            amount_excluding_tax=obj_in.amount_excluding_tax,
            tax_rate=obj_in.tax_rate or Decimal("0.13"),
            tax_amount=calc_result["tax_amount"],
            total_amount=total_amount,
            status="draft",
            notes=obj_in.notes,
        )
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db: AsyncSession,
        db_obj: Invoice,
        obj_in: InvoiceUpdate,
    ) -> Invoice:
        """更新发票（带状态约束校验）。"""
        update_data = obj_in.model_dump(exclude_unset=True)

        # 状态约束校验
        if db_obj.status == "verified":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="已核销发票不可修改"
            )
        if db_obj.status == "cancelled":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="已作废发票不可修改"
            )
        if db_obj.status == "issued" and update_data:
            # 已开具只能修改 notes
            non_notes_fields = {k for k in update_data if k != "notes"}
            if non_notes_fields:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="已开具发票只能修改备注"
                )

        # 金额变更需重新计算和校验
        if "amount_excluding_tax" in update_data or "tax_rate" in update_data:
            new_amount = update_data.get(
                "amount_excluding_tax", db_obj.amount_excluding_tax
            )
            new_tax_rate = update_data.get("tax_rate", db_obj.tax_rate)
            calc_result = calculate_invoice_amount(new_amount, new_tax_rate)

            update_data["tax_amount"] = calc_result["tax_amount"]
            update_data["total_amount"] = calc_result["total_amount"]

            # 校验累计金额
            if not await validate_invoice_amount(
                db,
                db_obj.contract_id,
                calc_result["total_amount"],
                exclude_invoice_id=db_obj.id,
            ):
                raise BusinessException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="开票金额已超合同金额",
                    code="INVOICE_AMOUNT_EXCEEDS_CONTRACT",
                )

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def delete(self, db: AsyncSession, db_obj: Invoice) -> None:
        """删除发票（仅允许 draft 状态）。"""
        if db_obj.status != "draft":
            status_msg = {
                "issued": "已开具发票不可删除",
                "received": "已收票发票不可删除",
                "verified": "已核销发票不可删除",
                "cancelled": "已作废发票不可删除",
            }
            detail = status_msg.get(db_obj.status, "当前状态不可删除")
            if db_obj.status in ("verified", "cancelled"):
                raise BusinessException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=detail,
                    code="INVOICE_CANNOT_DELETE",
                )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=detail,
            )
        await db.delete(db_obj)
        await db.commit()

    async def issue(self, db: AsyncSession, db_obj: Invoice) -> Invoice:
        """开具发票。"""
        if not validate_invoice_transition(db_obj.status, "issued"):
            if db_obj.status == "verified":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="发票已核销，不可变更"
                )
            if db_obj.status == "cancelled":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="已作废发票不可开具"
                )
            raise BusinessException(
                status_code=status.HTTP_409_CONFLICT,
                detail="非法状态流转",
                code="INVOICE_STATUS_INVALID_TRANSITION",
            )

        db_obj.status = "issued"
        db_obj.issued_at = datetime.utcnow()
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def receive(
        self, db: AsyncSession, db_obj: Invoice, received_by: Optional[str] = None
    ) -> Invoice:
        """确认收票。"""
        if not validate_invoice_transition(db_obj.status, "received"):
            if db_obj.status == "verified":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="发票已核销，不可变更"
                )
            if db_obj.status == "cancelled":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="已作废发票不可收票"
                )
            raise BusinessException(
                status_code=status.HTTP_409_CONFLICT,
                detail="非法状态流转",
                code="INVOICE_STATUS_INVALID_TRANSITION",
            )

        db_obj.status = "received"
        db_obj.received_at = datetime.utcnow()
        db_obj.received_by = received_by
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def verify(self, db: AsyncSession, db_obj: Invoice) -> Invoice:
        """核销发票。"""
        if not validate_invoice_transition(db_obj.status, "verified"):
            if db_obj.status == "cancelled":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="已作废发票不可核销"
                )
            raise BusinessException(
                status_code=status.HTTP_409_CONFLICT,
                detail="非法状态流转",
                code="INVOICE_STATUS_INVALID_TRANSITION",
            )

        db_obj.status = "verified"
        db_obj.verified_at = datetime.utcnow()
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def cancel(self, db: AsyncSession, db_obj: Invoice) -> Invoice:
        """作废发票。"""
        if not validate_invoice_transition(db_obj.status, "cancelled"):
            if db_obj.status == "verified":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="已核销发票不可作废"
                )
            raise BusinessException(
                status_code=status.HTTP_409_CONFLICT,
                detail="非法状态流转",
                code="INVOICE_STATUS_INVALID_TRANSITION",
            )

        db_obj.status = "cancelled"
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_summary(
        self,
        db: AsyncSession,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict:
        """获取汇总统计（按状态分组）。"""
        return await get_invoice_summary(db, start_date, end_date)


invoice = CRUDInvoice()
