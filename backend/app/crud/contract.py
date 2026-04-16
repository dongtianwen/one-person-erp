from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.crud.base import CRUDBase
from app.models.contract import Contract
from app.models.quotation import Quotation
from app.models.project import Project
from app.schemas.contract import ContractCreate, ContractUpdate
from app.core.template_utils import (
    render_template,
    build_contract_context,
    can_regenerate_content,
)
from app.core.error_codes import ERROR_CODES
from app.core.exception_handlers import BusinessException
from app.core.constants import (
    TEMPLATE_TYPE_CONTRACT,
    CONTRACT_CONTENT_FROZEN_STATUS,
    CONTRACT_REQUIRED_VARS,
)


class CRUDContract(CRUDBase[Contract, ContractCreate, ContractUpdate]):
    async def generate_contract_no(self, db: AsyncSession) -> str:
        today = date.today()
        prefix = f"HT-{today.strftime('%Y%m%d')}"
        result = await db.execute(
            select(Contract.contract_no)
            .where(Contract.contract_no.like(f"{prefix}%"))
            .order_by(Contract.contract_no.desc())
        )
        existing = result.scalars().first()
        if existing:
            seq = int(existing.split("-")[-1]) + 1
        else:
            seq = 1
        return f"{prefix}-{seq:03d}"

    async def sync_amount_to_project(self, db: AsyncSession, contract: Contract) -> None:
        if contract.project_id:
            from app.models.project import Project

            result = await db.execute(select(Project).where(Project.id == contract.project_id))
            proj = result.scalar_one_or_none()
            if proj:
                proj.budget = contract.amount
                db.add(proj)
                await db.commit()

    async def generate_contract_content(
        self,
        db: AsyncSession,
        contract_id: int,
        force: bool = False,
    ) -> Tuple[str, Optional[str]]:
        """生成合同内容。

        Args:
            db: 数据库会话
            contract_id: 合同 ID
            force: 是否强制覆盖（默认 false，如果内容已存在则返回 409）

        Returns:
            (generated_content, error_msg) tuple

        Raises:
            ValueError: 如果合同不存在
            BusinessException: 如果冻结、内容已存在、渲染失败等
        """
        # 获取合同（包含关联的报价单和模板）
        result = await db.execute(
            select(Contract)
            .options(
                selectinload(Contract.customer),
                selectinload(Contract.project),
                selectinload(Contract.quotation),
                selectinload(Contract.template),
            )
            .where(Contract.id == contract_id)
        )
        contract = result.scalars().first()

        if not contract:
            raise ValueError(f"合同不存在 (ID={contract_id})")

        # 检查 quotation_id 是否为空
        if not contract.quotation_id:
            raise BusinessException(
                status_code=422,
                detail=ERROR_CODES["QUOTE_NO_QUOTATION_ID"],
                code="QUOTE_NO_QUOTATION_ID",
            )

        # 检查是否可以重新生成
        can_regenerate, error_code = can_regenerate_content(
            status=contract.status,
            template_type=TEMPLATE_TYPE_CONTRACT,
            has_content=bool(contract.generated_content),
            force=force,
        )
        if not can_regenerate:
            status_code = 409 if error_code == ERROR_CODES["CONTENT_ALREADY_EXISTS"] else 400
            raise BusinessException(
                status_code=status_code,
                detail=error_code,
                code=error_code,
            )

        # 获取默认模板
        from app.crud.template import get_default_template
        template = await get_default_template(db, template_type=TEMPLATE_TYPE_CONTRACT)
        if not template:
            raise BusinessException(
                status_code=404,
                detail=ERROR_CODES["TEMPLATE_NOT_FOUND"],
                code="TEMPLATE_NOT_FOUND",
            )

        # 构建模板上下文
        contract_data = _contract_to_dict(contract)
        quotation_data = _quotation_to_dict(contract.quotation) if contract.quotation else {}

        # 查询项目描述（用于自动填充 project_scope）
        project_data = None
        if contract.project:
            project_data = {
                "description": contract.project.description or "",
            }

        # 查询交付物列表（用于自动填充 deliverables_desc）
        deliverables_data = None
        if contract.project_id:
            from app.models.deliverable import Deliverable
            del_stmt = (
                select(Deliverable)
                .where(Deliverable.project_id == contract.project_id)
                .order_by(Deliverable.delivery_date)
            )
            del_result = await db.execute(del_stmt)
            deliverables_data = [
                {
                    "name": d.name,
                    "description": d.description or "",
                    "version_no": d.version_no or "",
                    "delivery_date": d.delivery_date,
                }
                for d in del_result.scalars().all()
            ] or None

        # 获取公司设置（乙方信息）
        from app.crud.setting import get_company_settings
        company_data = await get_company_settings(db)

        context = build_contract_context(
            contract_data, quotation_data, project_data, deliverables_data, company_data
        )

        # 渲染模板
        generated_content, render_error = render_template(
            template_content=template.content,
            context=context,
            required_vars=CONTRACT_REQUIRED_VARS,
        )

        if render_error:
            raise BusinessException(
                status_code=500,
                detail=ERROR_CODES["TEMPLATE_RENDER_FAILED"],
                code="TEMPLATE_RENDER_FAILED",
            )

        # 更新生成时间和内容
        contract.generated_content = generated_content
        contract.template_id = template.id
        contract.content_generated_at = datetime.now()
        await db.commit()

        return generated_content, None

    async def update_contract_generated_content(
        self,
        db: AsyncSession,
        contract_id: int,
        content: str,
    ) -> bool:
        """手工编辑合同内容。

        content_generated_at 不更新（保留最后生成时间）。

        Args:
            db: 数据库会话
            contract_id: 合同 ID
            content: 新的内容

        Returns:
            是否更新成功

        Raises:
            ValueError: 如果合同不存在
            BusinessException: 如果冻结状态
        """
        result = await db.execute(
            select(Contract).where(Contract.id == contract_id)
        )
        contract = result.scalars().first()

        if not contract:
            raise ValueError(f"合同不存在 (ID={contract_id})")

        # 检查是否可编辑（冻结状态不允许手工编辑）
        can_edit, error_code = can_regenerate_content(
            status=contract.status,
            template_type=TEMPLATE_TYPE_CONTRACT,
            has_content=bool(contract.generated_content),
            force=True,
        )
        if not can_edit:
            raise BusinessException(
                status_code=400,
                detail=error_code,
                code=error_code,
            )

        # 更新内容（不更新 content_generated_at）
        contract.generated_content = content
        await db.commit()

        return True

    async def create_contract_from_quotation(
        self,
        db: AsyncSession,
        quotation_id: int,
    ) -> Contract:
        """从报价单创建合同（仅创建，不 commit，由调用方统一提交）。

        deliverables_desc 传空字符串，不从 deliverables 表取。

        Args:
            db: 数据库会话
            quotation_id: 报价单 ID

        Returns:
            创建的合同（未 commit）

        Raises:
            ValueError: 如果报价单不存在
            BusinessException: 如果报价单不是 accepted 状态或已经转成合同
        """
        # 获取报价单（包含关联的项目）
        result = await db.execute(
            select(Quotation)
            .options(selectinload(Quotation.customer), selectinload(Quotation.project))
            .where(Quotation.id == quotation_id)
        )
        quotation = result.scalars().first()

        if not quotation:
            raise ValueError(f"报价单不存在 (ID={quotation_id})")

        # 检查报价单是否为 accepted 状态
        if quotation.status != "accepted":
            raise BusinessException(
                status_code=400,
                detail="仅已接受的报价单可转为合同",
                code="QUOTE_NOT_ACCEPTED",
            )

        # 检查是否已经转成合同
        if quotation.converted_contract_id:
            raise BusinessException(
                status_code=409,
                detail="该报价单已转成合同",
                code="QUOTE_ALREADY_CONVERTED",
            )

        # 获取项目
        project = quotation.project
        if not project:
            raise ValueError("报价单未关联项目")

        # 获取默认合同模板
        from app.crud.template import get_default_template

        template = await get_default_template(db, template_type=TEMPLATE_TYPE_CONTRACT)
        if not template:
            raise ValueError("默认合同模板不存在")

        # 创建合同
        contract_no = await self.generate_contract_no(db)
        contract = Contract(
            project_id=project.id,
            customer_id=quotation.customer_id,
            contract_no=contract_no,
            title=project.name or quotation.title,
            amount=float(quotation.total_amount) if quotation.total_amount else 0,
            status="draft",
            generated_content=None,
            template_id=template.id,
            content_generated_at=None,
            quotation_id=quotation_id,
            terms=quotation.requirement_summary,
        )

        db.add(contract)
        await db.flush()

        # 更新报价单的 converted_contract_id
        quotation.converted_contract_id = contract.id
        db.add(quotation)

        await db.refresh(contract)
        return contract


def _contract_to_dict(c: Contract) -> dict:
    """将合同对象转为字典，供模板上下文使用。"""
    return {
        "contract_no": c.contract_no,
        "title": c.title,
        "customer_name": c.customer.name if c.customer else "",
        "project_name": c.project.name if hasattr(c, "project") and c.project else c.title,
        "amount": c.amount or 0,
        "signed_date": c.signed_date,
        "notes": c.terms or "",
    }


def _quotation_to_dict(q: Quotation) -> dict:
    """将报价单对象转为字典，供合同模板上下文使用。"""
    return {
        "quote_no": q.quote_no,
        "total_amount": float(q.total_amount) if q.total_amount else 0,
        "estimate_days": q.estimate_days or 0,
        "notes": q.notes or "",
    }


contract = CRUDContract(Contract)
