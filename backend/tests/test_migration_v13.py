"""v1.3 迁移验证测试——确认新字段存在、默认 NULL、数据完整性。"""

import os
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finance import FinanceRecord
from app.models.contract import Contract


@pytest.mark.asyncio
async def test_alembic_migration_file_exists():
    """v1.3 Alembic 迁移文件存在"""
    version_dir = os.path.join(os.path.dirname(__file__), "..", "alembic", "versions")
    files = os.listdir(version_dir)
    v13_files = [f for f in files if "v1_3" in f or "outsource_invoice_cashflow" in f]
    assert len(v13_files) > 0, "v1.3 迁移文件不存在"


@pytest.mark.asyncio
async def test_migration_contains_index_definitions():
    """迁移文件包含三个索引定义"""
    version_dir = os.path.join(os.path.dirname(__file__), "..", "alembic", "versions")
    files = os.listdir(version_dir)
    v13_files = [f for f in files if "v1_3" in f or "outsource_invoice_cashflow" in f]
    assert len(v13_files) > 0, "未找到 v1.3 迁移文件"
    content = open(os.path.join(version_dir, v13_files[0]), encoding="utf-8").read()
    assert "idx_contracts_expected_payment_date" in content
    assert "idx_finance_records_invoice_direction" in content
    assert "idx_finance_records_invoice_no" in content


@pytest.mark.asyncio
async def test_contracts_new_fields_all_null_by_default(db_session: AsyncSession):
    """contracts 新增字段默认为 NULL"""
    result = await db_session.execute(text("PRAGMA table_info('contracts')"))
    columns = {row[1]: row for row in result.fetchall()}

    new_fields = ["expected_payment_date", "payment_stage_note"]
    for field in new_fields:
        assert field in columns, f"字段 {field} 不存在"
        assert columns[field][3] == 0, f"字段 {field} 应允许 NULL"


@pytest.mark.asyncio
async def test_finance_records_new_fields_all_null_by_default(db_session: AsyncSession):
    """finance_records 新增字段默认为 NULL"""
    result = await db_session.execute(text("PRAGMA table_info('finance_records')"))
    columns = {row[1]: row for row in result.fetchall()}

    new_fields = [
        "outsource_name", "has_invoice", "tax_treatment",
        "invoice_direction", "invoice_type", "tax_rate", "tax_amount",
    ]
    for field in new_fields:
        assert field in columns, f"字段 {field} 不存在"
        assert columns[field][3] == 0, f"字段 {field} 应允许 NULL"


@pytest.mark.asyncio
async def test_finance_records_existing_fields_unchanged(db_session: AsyncSession):
    """finance_records 原有字段仍然存在"""
    result = await db_session.execute(text("PRAGMA table_info('finance_records')"))
    columns = {row[1] for row in result.fetchall()}

    legacy_fields = [
        "id", "type", "amount", "category", "description", "date",
        "invoice_no", "status", "funding_source", "business_note",
        "related_record_id", "related_note", "settlement_status",
    ]
    for field in legacy_fields:
        assert field in columns, f"原有字段 {field} 丢失"


@pytest.mark.asyncio
async def test_finance_records_total_count_unchanged(db_session: AsyncSession):
    """迁移后表行数验证（空表）"""
    from sqlalchemy import select, func
    result = await db_session.execute(select(func.count()).select_from(FinanceRecord))
    assert result.scalar() == 0


@pytest.mark.asyncio
async def test_contracts_total_count_unchanged(db_session: AsyncSession):
    """迁移后 contracts 表行数验证（空表）"""
    from sqlalchemy import select, func
    result = await db_session.execute(select(func.count()).select_from(Contract))
    assert result.scalar() == 0
