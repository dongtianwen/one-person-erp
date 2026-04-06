"""v1.4 迁移验证测试——确认 related_project_id 字段存在、索引存在、数据完整性。"""
import pytest
import pytest_asyncio
from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import FinanceRecord
from app.models.project import Project


@pytest.mark.asyncio
async def test_index_finance_records_related_project_id_exists(db_session: AsyncSession):
    """NFR-401: related_project_id 索引存在"""
    result = await db_session.execute(text("PRAGMA index_list('finance_records')"))
    indexes = {row[1] for row in result.fetchall()}
    # SQLAlchemy 生成的索引名前缀为 ix_，迁移脚本手动创建的为 idx_
    has_index = any("related_project_id" in idx for idx in indexes)
    assert has_index, f"未找到 related_project_id 相关索引，现有索引: {indexes}"


@pytest.mark.asyncio
async def test_finance_records_related_project_id_default_null(db_session: AsyncSession):
    """NFR-401: related_project_id 字段存在且允许 NULL"""
    result = await db_session.execute(text("PRAGMA table_info('finance_records')"))
    columns = {row[1]: row for row in result.fetchall()}
    assert "related_project_id" in columns, "字段 related_project_id 不存在"
    assert columns["related_project_id"][3] == 0, "字段 related_project_id 应允许 NULL"


@pytest.mark.asyncio
async def test_finance_records_total_count_unchanged(db_session: AsyncSession):
    """NFR-401: 迁移后 finance_records 行数验证（测试环境空表）"""
    result = await db_session.execute(select(func.count()).select_from(FinanceRecord))
    assert result.scalar() == 0


@pytest.mark.asyncio
async def test_finance_records_existing_fields_unchanged(db_session: AsyncSession):
    """NFR-401: 原有字段仍然存在"""
    result = await db_session.execute(text("PRAGMA table_info('finance_records')"))
    columns = {row[1] for row in result.fetchall()}

    legacy_fields = [
        "id", "type", "amount", "category", "description", "date",
        "invoice_no", "status", "funding_source", "business_note",
        "related_record_id", "related_note", "settlement_status",
        "outsource_name", "has_invoice", "tax_treatment",
        "invoice_direction", "invoice_type", "tax_rate", "tax_amount",
    ]
    for field in legacy_fields:
        assert field in columns, f"原有字段 {field} 丢失"


@pytest.mark.asyncio
async def test_related_project_id_foreign_key_constraint(db_session: AsyncSession):
    """NFR-401: related_project_id 外键约束验证——关联不存在的项目应失败"""
    result = await db_session.execute(text("PRAGMA foreign_key_list('finance_records')"))
    fks = result.fetchall()
    fk_found = any(
        "projects" in str(fk) and "related_project_id" in str(fk)
        for fk in fks
    )
    assert fk_found, "未找到 related_project_id → projects(id) 的外键约束"


@pytest.mark.asyncio
async def test_related_project_id_set_null_on_project_delete(db_session: AsyncSession):
    """NFR-401: 项目删除后 related_project_id 置 NULL"""
    from datetime import date as date_type
    from app.models.customer import Customer
    from app.models.contract import Contract

    # 启用外键约束（SQLite 默认关闭）
    await db_session.execute(text("PRAGMA foreign_keys = ON"))

    # 用 ORM 创建测试数据
    customer = Customer(name="测试客户", contact_person="张三", phone="13800000000")
    db_session.add(customer)
    await db_session.commit()
    await db_session.refresh(customer)

    project = Project(name="测试项目", customer_id=customer.id, status="requirements")
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    record = FinanceRecord(
        type="expense", amount=1000, date=date_type(2026, 4, 1),
        status="pending", related_project_id=project.id,
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)

    # 删除项目（ON DELETE SET NULL）
    await db_session.delete(project)
    await db_session.commit()

    # 验证 related_project_id 被置为 NULL
    await db_session.refresh(record)
    assert record.related_project_id is None, "项目删除后 related_project_id 应为 NULL"
