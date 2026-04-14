"""v1.12 报价合同生成——模板系统与内容生成。

新增 templates 表，修改 quotations 和 contracts 表以支持内容生成和模板管理。

使用方法：
    cd backend
    python -m migrations.v1_12_migrate
"""
import sqlite3
import sys
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "shubiao.db")


def _column_exists(cur, table_name: str, column_name: str) -> bool:
    """检查表中是否存在指定列。"""
    cur.execute(f"PRAGMA table_info({table_name})")
    columns = {col[1] for col in cur.fetchall()}
    return column_name in columns


def _add_column_if_not_exists(cur, table: str, column: str, definition: str) -> bool:
    """如果列不存在则添加，返回是否执行了添加操作。"""
    if not _column_exists(cur, table, column):
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        print(f"  {table}.{column} 已添加")
        return True
    else:
        print(f"  {table}.{column} 已存在，跳过")
        return False


def _table_exists(cur, table_name: str) -> bool:
    """检查表是否存在。"""
    cur.execute(
        f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
    )
    return cur.fetchone() is not None


def _index_exists(cur, index_name: str) -> bool:
    """检查索引是否存在。"""
    cur.execute(
        f"SELECT name FROM sqlite_master WHERE type='index' AND name='{index_name}'"
    )
    return cur.fetchone() is not None


def _execute_sql_if_not_exists(cur, sql: str) -> bool:
    """如果 SQL 语句不存在则执行，返回是否执行。"""
    # 提取表名或唯一约束名
    if "CREATE TABLE IF NOT EXISTS" in sql:
        table_name = sql.split("CREATE TABLE IF NOT EXISTS")[1].split("(")[0].strip()
    elif "CREATE UNIQUE INDEX" in sql:
        index_name = sql.split("CREATE UNIQUE INDEX")[1].split()[1].strip()
        cur.execute(f"SELECT name FROM sqlite_master WHERE type='index' AND name='{index_name}'")
        return cur.fetchone() is not None
    else:
        return False

    cur.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
    return cur.fetchone() is None


def _insert_template_if_not_exists(cur, name: str, template_type: str, content: str, description: str) -> bool:
    """如果模板不存在则插入，返回是否执行了插入操作。"""
    cur.execute("SELECT id FROM templates WHERE template_type = ?", (template_type,))
    existing = cur.fetchone()
    if existing is None:
        cur.execute(
            "INSERT INTO templates (name, template_type, content, is_default, description) VALUES (?, ?, ?, 1, ?)",
            (name, template_type, content, description)
        )
        print(f"  templates: 插入默认模板 {name}")
        return True
    else:
        print(f"  templates: 模板 {name} 已存在，跳过")
        return False


# ── DDL 定义 ──────────────────────────────────────────────────────

NEW_TABLES = {
    "templates": """
        CREATE TABLE IF NOT EXISTS templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(200) NOT NULL,
            template_type VARCHAR(30) NOT NULL,
            content TEXT NOT NULL,
            is_default INTEGER NOT NULL DEFAULT 0,
            description TEXT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """,
}

ALL_INDEXES = [
    ("idx_templates_default_quotation",
     "CREATE UNIQUE INDEX IF NOT EXISTS idx_templates_default_quotation ON templates(template_type) WHERE is_default = 1 AND template_type = 'quotation'"),
    ("idx_templates_default_contract",
     "CREATE UNIQUE INDEX IF NOT EXISTS idx_templates_default_contract ON templates(template_type) WHERE is_default = 1 AND template_type = 'contract'"),
    ("idx_templates_template_type",
     "CREATE INDEX IF NOT EXISTS idx_templates_template_type ON templates(template_type)"),
]

DEFAULT_TEMPLATES = {
    "quotation": """
        INSERT OR IGNORE INTO templates (name, template_type, content, is_default, description) VALUES
        ('默认报价模板', 'quotation',
        '报价单

编号：{{ quotation_no }}
日期：{{ created_date }}

━━━━━━━━━━━━━━━━━━━━━━━━

客户：{{ customer_name }}
项目：{{ project_name }}

━━━━━━━━━━━━━━━━━━━━━━━━

一、服务内容

{{ requirement_summary }}

━━━━━━━━━━━━━━━━━━━━━━━━

二、费用明细

预计工期：{{ estimate_days }} 个工作日
{% if daily_rate %}日费率：¥{{ daily_rate }} / 天
{% endif %}{% if direct_cost %}直接成本：¥{{ direct_cost }}
{% endif %}{% if risk_buffer_rate %}风险缓冲：{{ (risk_buffer_rate * 100)|round(1) }}%
{% endif %}{% if discount_amount and discount_amount > 0 %}折扣：-¥{{ discount_amount }}
{% endif %}{% if tax_rate and tax_rate > 0 %}税额（{{ (tax_rate * 100)|round(1) }}%）：¥{{ tax_amount }}
{% endif %}
报价总额：¥{{ total_amount }}

━━━━━━━━━━━━━━━━━━━━━━━━

三、有效期

本报价有效期至：{{ valid_until }}

{% if payment_terms %}━━━━━━━━━━━━━━━━━━━━━━━━

四、付款方式

{{ payment_terms }}
{% endif %}{% if notes %}
备注：{{ notes }}
{% endif %}
本报价单由 {{ company_name if company_name else ''（乙方公司名称）'' }} 出具，仅供参考，最终以签署合同为准。
        ',
        1, '默认报价模板（使用标准变量）'
        )""",
    "contract": """
        INSERT OR IGNORE INTO templates (name, template_type, content, is_default, description) VALUES
        ('默认合同模板', 'contract',
        '软件开发服务合同

合同编号：{{ contract_no }}
签订日期：{{ sign_date }}

━━━━━━━━━━━━━━━━━━━━━━━━

甲方（委托方）：{{ customer_name }}
乙方（服务方）：{{ company_name if company_name else ''（乙方公司名称）'' }}

关联报价单：{{ quotation_no }}

━━━━━━━━━━━━━━━━━━━━━━━━

一、项目内容

项目名称：{{ project_name }}

项目范围：
{{ project_scope if project_scope else ''（请补充项目范围说明）'' }}

━━━━━━━━━━━━━━━━━━━━━━━━

二、交付内容

{{ deliverables_desc if deliverables_desc else ''（请补充交付内容说明）'' }}

━━━━━━━━━━━━━━━━━━━━━━━━

三、合同金额

合同总金额：¥{{ total_amount }}（人民币）

━━━━━━━━━━━━━━━━━━━━━━━━

四、付款方式

{{ payment_terms if payment_terms else ''（请补充付款条款）'' }}

━━━━━━━━━━━━━━━━━━━━━━━━

五、验收标准

{{ acceptance_criteria if acceptance_criteria else ''（请补充验收标准）'' }}

━━━━━━━━━━━━━━━━━━━━━━━━

六、违约责任

{{ liability_clause if liability_clause else ''任何一方违约，须向守约方赔偿因此造成的实际损失。双方协商不成，提交合同签订地有管辖权的人民法院诉讼解决。'' }}

{% if notes %}备注：{{ notes }}{% endif %}

甲方签字：_______________    乙方签字：_______________
日    期：_______________    日    期：_______________
        ',
        1, '默认合同模板（使用标准变量）'
        )""",
}


def migrate(db_path: str = DB_PATH) -> None:
    """执行 v1.12 迁移：templates 表 + 修改 quotations/contracts 表 + 默认模板。"""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    try:
        # ── 步骤 1：创建 templates 表 ──────────────────────────────
        print("步骤 1：创建 templates 表")
        for table_name, ddl in NEW_TABLES.items():
            if not _table_exists(cur, table_name):
                cur.execute(ddl)
                print(f"  {table_name} 表已创建")
            else:
                print(f"  {table_name} 表已存在，跳过")

        # ── 步骤 2：创建索引 ────────────────────────────────────
        print("\n步骤 2：创建索引:")
        for idx_name, idx_sql in ALL_INDEXES:
            if not _index_exists(cur, idx_name):
                cur.execute(idx_sql)
                print(f"  {idx_name} 索引已创建")
            else:
                print(f"  {idx_name} 索引已存在，跳过")

        # ── 步骤 3：扩展现有表 ─────────────────────────────────
        print("\n步骤 3：扩展现有表:")
        _add_column_if_not_exists(
            cur, "quotations", "generated_content", "TEXT NULL"
        )
        _add_column_if_not_exists(
            cur, "quotations", "template_id",
            "INTEGER NULL REFERENCES templates(id) ON DELETE SET NULL"
        )
        _add_column_if_not_exists(
            cur, "quotations", "content_generated_at", "TIMESTAMP NULL"
        )
        _add_column_if_not_exists(
            cur, "contracts", "generated_content", "TEXT NULL"
        )
        _add_column_if_not_exists(
            cur, "contracts", "template_id",
            "INTEGER NULL REFERENCES templates(id) ON DELETE SET NULL"
        )
        _add_column_if_not_exists(
            cur, "contracts", "content_generated_at", "TIMESTAMP NULL"
        )

        # ── 步骤 4：插入默认模板 ─────────────────────────────────
        print("\n步骤 4：插入默认模板:")

        # 报价单默认模板
        quotation_sql = """
            INSERT OR IGNORE INTO templates (name, template_type, content, is_default, description) VALUES
            ('默认报价模板', 'quotation',
            '报价单

编号：{{ quotation_no }}
日期：{{ created_date }}

━━━━━━━━━━━━━━━━━━━━━━━━

客户：{{ customer_name }}
项目：{{ project_name }}

━━━━━━━━━━━━━━━━━━━━━━━━

一、服务内容

{{ requirement_summary }}

━━━━━━━━━━━━━━━━━━━━━━━━

二、费用明细

预计工期：{{ estimate_days }} 个工作日
{% if daily_rate %}日费率：¥{{ daily_rate }} / 天
{% endif %}{% if direct_cost %}直接成本：¥{{ direct_cost }}
{% endif %}{% if risk_buffer_rate %}风险缓冲：{{ (risk_buffer_rate * 100)|round(1) }}%
{% endif %}{% if discount_amount and discount_amount > 0 %}折扣：-¥{{ discount_amount }}
{% endif %}{% if tax_rate and tax_rate > 0 %}税额（{{ (tax_rate * 100)|round(1) }}%）：¥{{ tax_amount }}
{% endif %}
报价总额：¥{{ total_amount }}

━━━━━━━━━━━━━━━━━━━━━━━━

三、有效期

本报价有效期至：{{ valid_until }}

{% if payment_terms %}━━━━━━━━━━━━━━━━━━━━━━━━

四、付款方式

{{ payment_terms }}
{% endif %}{% if notes %}
备注：{{ notes }}
{% endif %}
本报价单由 {{ company_name if company_name else ''（乙方公司名称）'' }} 出具，仅供参考，最终以签署合同为准。
            ',
            1, '默认报价模板（使用标准变量）'
            )"""
        cur.execute(quotation_sql)
        print("  报价单默认模板已插入")

        # 合同默认模板
        contract_sql = """
            INSERT OR IGNORE INTO templates (name, template_type, content, is_default, description) VALUES
            ('默认合同模板', 'contract',
            '软件开发服务合同

合同编号：{{ contract_no }}
签订日期：{{ sign_date }}

━━━━━━━━━━━━━━━━━━━━━━━━

甲方（委托方）：{{ customer_name }}
乙方（服务方）：{{ company_name if company_name else ''（乙方公司名称）'' }}

关联报价单：{{ quotation_no }}

━━━━━━━━━━━━━━━━━━━━━━━━

一、项目内容

项目名称：{{ project_name }}

项目范围：
{{ project_scope if project_scope else ''（请补充项目范围说明）'' }}

━━━━━━━━━━━━━━━━━━━━━━━━

二、交付内容

{{ deliverables_desc if deliverables_desc else ''（请补充交付内容说明）'' }}

━━━━━━━━━━━━━━━━━━━━━━━━

三、合同金额

合同总金额：¥{{ total_amount }}（人民币）

━━━━━━━━━━━━━━━━━━━━━━━━

四、付款方式

{{ payment_terms if payment_terms else ''（请补充付款条款）'' }}

━━━━━━━━━━━━━━━━━━━━━━━━

五、验收标准

{{ acceptance_criteria if acceptance_criteria else ''（请补充验收标准）'' }}

━━━━━━━━━━━━━━━━━━━━━━━━

六、违约责任

{{ liability_clause if liability_clause else ''任何一方违约，须向守约方赔偿因此造成的实际损失。双方协商不成，提交合同签订地有管辖权的人民法院诉讼解决。'' }}

{% if notes %}备注：{{ notes }}{% endif %}

甲方签字：_______________    乙方签字：_______________
日    期：_______________    日    期：_______________
            ',
            1, '默认合同模板（使用标准变量）'
            )"""
        cur.execute(contract_sql)
        print("  合同默认模板已插入")

        # ── 步骤 5：迁移后验证 ─────────────────────────────────
        print("\n步骤 5：迁移后验证:")

        # 验证 templates 表存在
        assert _table_exists(cur, "templates"), "templates 表不存在"
        print("  templates 表存在")

        # 验证索引
        expected_indexes = {idx[0] for idx in ALL_INDEXES}
        cur.execute("SELECT name FROM sqlite_master WHERE type='index'")
        existing_indexes = {row[0] for row in cur.fetchall()}
        missing = expected_indexes - existing_indexes
        assert not missing, f"索引缺失: {missing}"
        print(f"  所有 {len(expected_indexes)} 个索引已创建")

        # 验证 quotations 新增字段
        for field in ["generated_content", "template_id", "content_generated_at"]:
            assert _column_exists(cur, "quotations", field), f"quotations.{field} 不存在"
        print("  quotations 表新增字段全部存在")

        # 验证 contracts 新增字段
        for field in ["generated_content", "template_id", "content_generated_at"]:
            assert _column_exists(cur, "contracts", field), f"contracts.{field} 不存在"
        print("  contracts 表新增字段全部存在")

        # 验证默认模板
        cur.execute("SELECT id, name, template_type FROM templates WHERE is_default = 1")
        templates = cur.fetchall()
        assert len(templates) == 2, f"默认模板数量应为 2，实际为 {len(templates)}"
        print(f"  默认模板: {[t[1] for t in templates]}")

        # 验证唯一约束
        cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_templates_default_quotation'")
        assert cur.fetchone() is not None, "唯一约束 idx_templates_default_quotation 不存在"
        cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_templates_default_contract'")
        assert cur.fetchone() is not None, "唯一约束 idx_templates_default_contract 不存在"
        print("  唯一约束已创建")

        conn.commit()
        print(f"\nv1.12 迁移完成：1 张新表 + 6 个新字段 + 2 个默认模板")

    except Exception as e:
        conn.rollback()
        print(f"迁移失败: {e}", file=sys.stderr)
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()
