"""Seed default data on first startup with system_initialized lock."""

import json
import logging
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reminder import ReminderSetting
from app.models.file_index import FileIndex
from app.models.setting import SystemSetting
from app.models.template import Template
from app.crud import setting as setting_crud

logger = logging.getLogger(__name__)

DEFAULT_REMINDER_SETTINGS = [
    {
        "reminder_type": "annual_audit",
        "config": json.dumps({"month": 3, "day": 31}),
        "is_active": True,
    },
    {
        "reminder_type": "tax_filing",
        "config": json.dumps({"day": 15}),
        "is_active": True,
    },
]

DEFAULT_FILE_INDEXES = [
    {
        "file_name": "营业执照正本",
        "file_type": "business_license",
        "version": "1",
        "is_current": True,
        "note": "公司营业执照正本，需年检更新",
    },
    {
        "file_name": "公司章程",
        "file_type": "company_charter",
        "version": "1",
        "is_current": True,
        "note": "公司章程及修正案",
    },
    {
        "file_name": "数标园入驻协议",
        "file_type": "lease_agreement",
        "version": "1",
        "is_current": True,
        "note": "办公场地租赁/入驻协议",
    },
    {
        "file_name": "税务备案回执",
        "file_type": "tax_registration",
        "version": "1",
        "is_current": True,
        "note": "税务机关登记备案回执",
    },
    {
        "file_name": "首次审计报告",
        "file_type": "audit_report",
        "version": "1",
        "is_current": True,
        "note": "首次年度审计报告",
    },
]

DEFAULT_REPORT_TEMPLATES = [
    {
        "name": "项目复盘报告",
        "template_type": "report_project",
        "content": """项目复盘报告

项目名称：{{ project_name }}
客户：{{ customer_name }}
报告生成日期：{{ generated_date }}

━━━━━━━━━━━━━━━━━━━━━━━━

一、项目概况

项目周期：{{ start_date }} 至 {{ end_date }}（共 {{ duration_days }} 天）
合同金额：¥{{ "%.2f"|format(contract_amount) }}
实际收款：¥{{ "%.2f"|format(received_amount) }}
{% if pending_amount and pending_amount > 0 %}待收款：¥{{ "%.2f"|format(pending_amount) }}
{% endif %}

━━━━━━━━━━━━━━━━━━━━━━━━

二、执行情况

累计工时：{{ total_hours }} 小时
里程碑完成率：{{ "%.1f"|format(milestone_completion_rate) }}%
变更单数量：{{ change_count }} 个
验收通过：{{ acceptance_passed }}

━━━━━━━━━━━━━━━━━━━━━━━━

三、财务表现

毛利率：{{ "%.1f"|format(gross_margin_rate) }}%
直接成本：¥{{ "%.2f"|format(direct_cost) }}
{% if outsource_cost and outsource_cost > 0 %}外包成本：¥{{ "%.2f"|format(outsource_cost) }}
{% endif %}

━━━━━━━━━━━━━━━━━━━━━━━━

四、综合分析

{{ analysis_summary }}

━━━━━━━━━━━━━━━━━━━━━━━━

五、风险复盘

{{ risk_retrospective }}

━━━━━━━━━━━━━━━━━━━━━━━━

六、改进建议

{{ improvement_suggestions }}""",
        "is_default": 1,
        "description": "项目复盘报告默认模板",
    },
    {
        "name": "客户分析报告",
        "template_type": "report_customer",
        "content": """客户分析报告

客户名称：{{ customer_name }}
报告生成日期：{{ generated_date }}

━━━━━━━━━━━━━━━━━━━━━━━━

一、合作概况

合作项目数：{{ project_count }}
累计合同金额：¥{{ total_contract_amount }}
累计收款金额：¥{{ total_received_amount }}
{% if total_pending > 0 %}当前待收款：¥{{ total_pending }}
{% endif %}首次合作：{{ first_project_date }}
最近合作：{{ last_project_date }}

━━━━━━━━━━━━━━━━━━━━━━━━

二、客户价值

LTV 估算：¥{{ ltv_estimate }}
平均项目金额：¥{{ avg_project_amount }}
回款准时率：{{ payment_on_time_rate }}%

━━━━━━━━━━━━━━━━━━━━━━━━

三、价值评估

{{ value_assessment }}

━━━━━━━━━━━━━━━━━━━━━━━━

四、关系摘要

{{ relationship_summary }}

━━━━━━━━━━━━━━━━━━━━━━━━

五、下一步建议

{{ next_action_suggestions }}""",
        "is_default": 1,
        "description": "客户分析报告默认模板",
    },
]


async def seed_default_data(db: AsyncSession) -> None:
    """Seed default data only if system is not yet initialized."""
    initialized = await setting_crud.get_setting(db, "system_initialized")
    if initialized == "true":
        logger.info("System already initialized, skipping seed")
        return

    # Seed reminder settings
    result = await db.execute(select(func.count(ReminderSetting.id)))
    setting_count = result.scalar() or 0
    if setting_count == 0:
        for setting_data in DEFAULT_REMINDER_SETTINGS:
            setting = ReminderSetting(**setting_data)
            db.add(setting)
        logger.info("Seeded %d default reminder settings", len(DEFAULT_REMINDER_SETTINGS))

    # Seed file indexes with unique file_group_id per entry
    result = await db.execute(select(func.count(FileIndex.id)))
    file_count = result.scalar() or 0
    if file_count == 0:
        for file_data in DEFAULT_FILE_INDEXES:
            file_index = FileIndex(
                file_group_id=str(uuid.uuid4()),
                **file_data,
            )
            db.add(file_index)
        logger.info("Seeded %d default file indexes", len(DEFAULT_FILE_INDEXES))

    # Seed default report templates (idempotent: skip if already exists)
    for tpl_data in DEFAULT_REPORT_TEMPLATES:
        result = await db.execute(
            select(Template).where(
                Template.template_type == tpl_data["template_type"],
                Template.is_default == 1,
            )
        )
        existing = result.scalar_one_or_none()
        if not existing:
            template = Template(**tpl_data)
            db.add(template)
            logger.info("Seeded default template: %s", tpl_data["template_type"])

    # Mark system as initialized
    await setting_crud.set_setting(db, "system_initialized", "true")
    await db.commit()
    logger.info("System initialization complete")
