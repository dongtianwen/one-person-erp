from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.crud.base import CRUDBase
from app.models.quotation import Quotation
from app.models.project import Project
from app.schemas.quotation import QuotationCreate, QuotationUpdate
from app.core.template_utils import (
    render_template,
    build_quotation_context,
    can_regenerate_content,
)
from app.core.error_codes import ERROR_CODES
from app.core.exception_handlers import BusinessException
from app.core.constants import (
    TEMPLATE_TYPE_QUOTATION,
    QUOTATION_CONTENT_FROZEN_STATUS,
    QUOTATION_REQUIRED_VARS,
)


class CRUDQuotation(CRUDBase[Quotation, QuotationCreate, QuotationUpdate]):
    async def generate_quote_no(self, db: AsyncSession) -> str:
        """生成报价单编号：BJ-YYYYMMDD-序号。"""
        today = date.today()
        prefix = f"BJ-{today.strftime('%Y%m%d')}"
        result = await db.execute(
            select(Quotation.quote_no)
            .where(Quotation.quote_no.like(f"{prefix}%"))
            .order_by(Quotation.quote_no.desc())
        )
        existing = result.scalars().first()
        if existing:
            seq = int(existing.split("-")[-1]) + 1
        else:
            seq = 1
        return f"{prefix}-{seq:03d}"

    async def list(
        self, db: AsyncSession, skip: int = 0, limit: int = 20,
        filters: Optional[Dict[str, Any]] = None, search: Optional[str] = None,
    ) -> tuple[List[Quotation], int]:
        query = select(Quotation).where(Quotation.is_deleted == False)
        count_query = select(func.count()).select_from(Quotation).where(Quotation.is_deleted == False)

        if filters:
            for key, value in filters.items():
                if value is not None:
                    query = query.where(getattr(Quotation, key) == value)
                    count_query = count_query.where(getattr(Quotation, key) == value)

        if search:
            pattern = f"%{search}%"
            query = query.where(Quotation.title.ilike(pattern))
            count_query = count_query.where(Quotation.title.ilike(pattern))

        count_result = await db.execute(count_query)
        total = count_result.scalar()

        query = query.offset(skip).limit(limit).order_by(Quotation.created_at.desc())
        result = await db.execute(query)
        items = result.scalars().all()
        return list(items), total

    async def generate_quotation_content(
        self,
        db: AsyncSession,
        quotation_id: int,
        force: bool = False,
    ) -> Tuple[str, Optional[str]]:
        """生成报价单内容。

        Args:
            db: 数据库会话
            quotation_id: 报价单 ID
            force: 是否强制覆盖（默认 false，如果内容已存在则返回 409）

        Returns:
            (generated_content, error_msg) tuple

        Raises:
            ValueError: 如果报价单不存在
            BusinessException: 如果冻结、内容已存在、渲染失败等
        """
        # 获取报价单（包含关联的项目和模板）
        result = await db.execute(
            select(Quotation)
            .options(
                selectinload(Quotation.customer),
                selectinload(Quotation.project),
                selectinload(Quotation.template),
            )
            .where(Quotation.id == quotation_id)
        )
        quotation = result.scalars().first()

        if not quotation:
            raise ValueError(f"报价单不存在 (ID={quotation_id})")

        # 检查是否可以重新生成
        can_regenerate, error_code = can_regenerate_content(
            status=quotation.status,
            template_type=TEMPLATE_TYPE_QUOTATION,
            has_content=bool(quotation.generated_content),
            force=force,
        )
        if not can_regenerate:
            status_code = 409
            if error_code == ERROR_CODES["CONTENT_FROZEN"]:
                status_code = 400
            raise BusinessException(
                status_code=status_code,
                detail=error_code,
                code=error_code,
            )

        # 获取默认模板
        from app.crud.template import get_default_template
        template = await get_default_template(db, template_type=TEMPLATE_TYPE_QUOTATION)
        if not template:
            raise BusinessException(
                status_code=404,
                detail=ERROR_CODES["TEMPLATE_NOT_FOUND"],
                code="TEMPLATE_NOT_FOUND",
            )

        # 构建模板上下文
        quotation_data = _quotation_to_dict(quotation)

        # 获取公司设置（乙方信息）
        from app.crud.setting import get_company_settings
        company_data = await get_company_settings(db)

        context = build_quotation_context(quotation_data, company_data)

        # 渲染模板
        generated_content, render_error = render_template(
            template_content=template.content,
            context=context,
            required_vars=QUOTATION_REQUIRED_VARS,
        )

        if render_error:
            raise BusinessException(
                status_code=500,
                detail=ERROR_CODES["TEMPLATE_RENDER_FAILED"],
                code="TEMPLATE_RENDER_FAILED",
            )

        # 更新生成时间和内容
        quotation.generated_content = generated_content
        quotation.template_id = template.id
        quotation.content_generated_at = datetime.now()
        await db.commit()

        return generated_content, None

    async def update_quotation_generated_content(
        self,
        db: AsyncSession,
        quotation_id: int,
        content: str,
    ) -> bool:
        """手工编辑报价单内容。

        content_generated_at 不更新（保留最后生成时间）。

        Args:
            db: 数据库会话
            quotation_id: 报价单 ID
            content: 新的内容

        Returns:
            是否更新成功

        Raises:
            ValueError: 如果报价单不存在
            BusinessException: 如果冻结状态
        """
        result = await db.execute(
            select(Quotation).where(Quotation.id == quotation_id)
        )
        quotation = result.scalars().first()

        if not quotation:
            raise ValueError(f"报价单不存在 (ID={quotation_id})")

        # 检查是否可编辑（冻结状态不允许手工编辑）
        can_edit, error_code = can_regenerate_content(
            status=quotation.status,
            template_type=TEMPLATE_TYPE_QUOTATION,
            has_content=bool(quotation.generated_content),
            force=True,  # 手工编辑不关心 force，只看冻结
        )
        if not can_edit:
            raise BusinessException(
                status_code=400,
                detail=error_code,
                code=error_code,
            )

        # 更新内容（不更新 content_generated_at）
        quotation.generated_content = content
        await db.commit()

        return True

    async def has_generated_draft_quotation(
        self,
        db: AsyncSession,
        project_id: int,
    ) -> Optional[Quotation]:
        """检查项目是否已有草稿报价单。

        一个项目同一时间只允许一份 status=draft 且 template_id IS NOT NULL 的报价单。

        Args:
            db: 数据库会话
            project_id: 项目 ID

        Returns:
            已存在的草稿报价单，如果不存在返回 None
        """
        result = await db.execute(
            select(Quotation)
            .where(
                Quotation.project_id == project_id,
                Quotation.status == "draft",
                Quotation.is_deleted == False,
                Quotation.template_id.isnot(None),
            )
        )
        return result.scalars().first()

    async def create_quotation_from_project(
        self,
        db: AsyncSession,
        project_id: int,
    ) -> Quotation:
        """从项目创建草稿报价单（带草稿去重检查）。

        Args:
            db: 数据库会话
            project_id: 项目 ID

        Returns:
            创建的报价单

        Raises:
            BusinessException: 如果项目已有草稿报价单
        """
        # 检查草稿是否存在
        existing_draft = await self.has_generated_draft_quotation(
            db, project_id=project_id
        )
        if existing_draft:
            raise BusinessException(
                status_code=409,
                detail=ERROR_CODES["DRAFT_ALREADY_EXISTS"],
                code="DRAFT_ALREADY_EXISTS",
                extra={"quotation_id": existing_draft.id, "quote_no": existing_draft.quote_no},
            )

        # 获取项目信息
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalars().first()
        if not project:
            raise ValueError(f"项目不存在 (ID={project_id})")

        # 获取默认报价单模板
        from app.crud.template import get_default_template

        template = await get_default_template(db, template_type=TEMPLATE_TYPE_QUOTATION)
        if not template:
            raise ValueError("默认报价单模板不存在")

        # 创建报价单
        from datetime import timedelta
        quotation = Quotation(
            project_id=project_id,
            customer_id=project.customer_id,
            quote_no=f"BJ-{datetime.now().strftime('%Y%m%d')}-001",
            title=project.name,
            requirement_summary=project.description or "",
            estimate_days=project.estimated_hours or 30,
            status="draft",
            valid_until=(datetime.now() + timedelta(days=30)).date(),
            generated_content=None,
            template_id=template.id,
            content_generated_at=None,
        )

        db.add(quotation)
        await db.commit()
        await db.refresh(quotation)

        return quotation


def _quotation_to_dict(q: Quotation) -> dict:
    """将报价单对象转为字典，供模板上下文使用。"""
    return {
        "quote_no": q.quote_no,
        "title": q.title,
        "customer_name": q.customer.name if q.customer else "",
        "project_name": q.project.name if q.project else q.title,
        "requirement_summary": q.requirement_summary or "",
        "estimate_days": q.estimate_days or 0,
        "total_amount": float(q.total_amount) if q.total_amount else 0,
        "valid_until": q.valid_until,
        "created_at": q.created_at,
        "daily_rate": q.daily_rate,
        "direct_cost": q.direct_cost,
        "risk_buffer_rate": q.risk_buffer_rate,
        "tax_rate": q.tax_rate,
        "tax_amount": q.tax_amount,
        "discount_amount": q.discount_amount,
        "subtotal_amount": q.subtotal_amount,
        "notes": q.notes,
    }


quotation = CRUDQuotation(Quotation)
