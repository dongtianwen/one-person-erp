"""
Golden Path 测试数据完整填充脚本
- 清理所有项目相关测试数据
- 创建一个完整的golden path项目，确保每个tab每个字段都有数据
"""

import sqlite3
import os
from datetime import date, datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "shubiao.db")

# ── 工具函数 ──────────────────────────────────────────────────────────

def now_iso():
    return datetime.utcnow().isoformat()

def today():
    return date.today().isoformat()

def days_ago(n):
    return (date.today() - timedelta(days=n)).isoformat()

def days_later(n):
    return (date.today() + timedelta(days=n)).isoformat()


# ── 阶段1: 清理所有项目相关数据 ──────────────────────────────────────

def clean_all(cur):
    """删除所有业务数据，保留 users 和 settings"""
    # 按依赖关系倒序删除
    tables_to_clean = [
        "package_dataset_versions",
        "package_model_versions",
        "experiment_dataset_versions",
        "delivery_packages",
        "model_versions",
        "training_experiments",
        "annotation_tasks",
        "dataset_versions",
        "datasets",
        "input_invoices",
        "fixed_costs",
        "work_hour_logs",
        "account_handovers",
        "deliverables",
        "acceptances",
        "releases",
        "requirement_changes",
        "requirements",
        "change_orders",
        "maintenance_periods",
        "change_logs",
        "invoices",
        "finance_records",
        "quotation_items",
        "quotation_changes",
        "quotations",
        "contracts",
        "milestones",
        "tasks",
        "reminders",
        "reminder_settings",
        "customer_assets",
        "customers",
        "projects",
        "export_batches",
        "file_indexes",
    ]
    for t in tables_to_clean:
        try:
            cur.execute(f"DELETE FROM {t}")
        except Exception as e:
            print(f"  skip {t}: {e}")


# ── 阶段2: 创建完整golden path数据 ──────────────────────────────────

def seed(cur):
    now = now_iso()

    # ━━ 客户 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    cur.execute("""
        INSERT INTO customers (name, contact_person, phone, email, company, source, status, notes,
                               lost_reason, overdue_milestone_count, overdue_amount, risk_level,
                               created_at, updated_at, is_deleted)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    """, ("数标智政科技有限公司", "张伟", "138-0013-8000", "zhangwei@shubiao-gov.cn",
          "数标智政科技有限公司", "referral", "active", "长期政府项目合作伙伴，年度框架协议",
          None, 0, 0, "low", now, now))
    customer_id = cur.lastrowid

    # ━━ 项目 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    cur.execute("""
        INSERT INTO projects (name, customer_id, description, status, budget,
                             start_date, end_date, progress,
                             estimated_hours, actual_hours,
                             cached_revenue, cached_labor_cost, cached_fixed_cost,
                             cached_input_cost, cached_gross_profit, cached_gross_margin,
                             profit_cache_updated_at, close_checklist, closed_at,
                             created_at, updated_at, is_deleted)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    """, ("智能政务多模态交互系统", customer_id,
          "基于Llama3-8B的政务问答AI系统，包含数据标注、模型训练、系统集成及验收交付全流程",
          "development", 800000.0,
          "2026-01-10", "2026-07-30", 35,
          480, 6,
          200000.0, 2625.0, 50000.0, 15000.0, 132375.0, 0.6619,
          now, None, None, now, now))
    project_id = cur.lastrowid

    # ━━ 报价单 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    cur.execute("""
        INSERT INTO quotations (quote_no, customer_id, project_id, title, requirement_summary,
                               estimate_days, estimate_hours, daily_rate, direct_cost,
                               risk_buffer_rate, discount_amount, tax_rate,
                               subtotal_amount, tax_amount, total_amount,
                               valid_until, status, notes,
                               sent_at, accepted_at, rejected_at, expired_at,
                               converted_contract_id, is_deleted, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
    """, ("QT-2026-001", customer_id, project_id,
          "智能政务多模态交互系统报价", "政务问答AI系统开发，含数据标注、模型精调、系统集成",
          120, 480, 3500.0, 200000.0, 10.0, 30000.0, 0.06,
          720000.0, 43200.0, 763200.0,
          "2026-03-31", "accepted", "客户确认接受报价方案",
          days_ago(90), days_ago(80), None, None,
          None, now, now))
    quotation_id = cur.lastrowid

    # 报价单明细
    items = [
        ("需求分析与方案设计", "service", 1, 50000, 50000, "含业务流程梳理", 1),
        ("数据集构建与标注", "service", 1, 120000, 120000, "含5000条政务问答对标注", 2),
        ("模型精调与训练", "service", 1, 200000, 200000, "Llama3-8B政务领域精调", 3),
        ("系统集成开发", "service", 1, 180000, 180000, "含API开发与前端集成", 4),
        ("测试与部署", "service", 1, 100000, 100000, "含压力测试与灰度部署", 5),
        ("培训与交付", "service", 1, 70000, 70000, "含操作手册与现场培训", 6),
    ]
    for item in items:
        cur.execute("""
            INSERT INTO quotation_items (quotation_id, item_name, item_type, quantity, unit_price,
                                        amount, notes, sort_order, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (quotation_id, *item, now))

    # ━━ 合同 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    cur.execute("""
        INSERT INTO contracts (contract_no, project_id, customer_id, title, amount,
                              signed_date, start_date, end_date, status, terms,
                              termination_reason, expected_payment_date, payment_stage_note,
                              quotation_id, created_at, updated_at, is_deleted)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    """, ("HT-2026-GOV-001", project_id, customer_id,
          "智能政务多模态交互系统开发合同", 800000.0,
          "2026-01-15", "2026-01-20", "2026-08-31", "active",
          "合同总金额¥800,000，分三期付款：30%/40%/30%",
          None, "2026-02-28", "第一期：合同签订后15个工作日",
          quotation_id, now, now))
    contract_id = cur.lastrowid

    # ━━ 财务记录 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 收入
    finance_income = [
        (contract_id, "income", 240000.0, "progress_payment", "第一期进度款（30%）",
         "2026-02-10", "FP-2026-001", "received",
         "contract", "首期款项", None, None, "settled",
         None, True, "out", "special", 0.06, 13584.91,
         project_id, None, "2026-02", None, "reconciled"),
        (contract_id, "income", 320000.0, "progress_payment", "第二期进度款（40%）",
         "2026-04-15", "FP-2026-002", "pending",
         "contract", "二期款项待到账", None, None, "pending",
         None, False, "out", "special", 0.06, 18113.21,
         project_id, None, "2026-04", None, "pending"),
    ]
    for f in finance_income:
        cur.execute("""
            INSERT INTO finance_records (contract_id, type, amount, category, description,
                                        date, invoice_no, status,
                                        funding_source, business_note, related_record_id, related_note,
                                        settlement_status, outsource_name, has_invoice,
                                        invoice_direction, invoice_type, tax_rate, tax_amount,
                                        related_project_id, invoice_id, accounting_period,
                                        export_batch_id, reconciliation_status,
                                        created_at, updated_at, is_deleted)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (*f, now, now))

    # 支出
    expense_records = [
        (contract_id, "expense", 15000.0, "server", "GPU服务器租赁费（2×A100）",
         "2026-03-01", "EX-2026-001", "confirmed",
         "own", "模型训练用GPU服务器", None, None, "settled",
         "阿里云", True, "in", "special", 0.06, 849.06,
         project_id, None, "2026-03", None, "reconciled"),
        (contract_id, "expense", 8000.0, "software", "数据标注工具授权费",
         "2026-02-20", "EX-2026-002", "confirmed",
         "own", "Label Studio企业版", None, None, "settled",
         None, True, "in", "special", 0.06, 452.83,
         project_id, None, "2026-02", None, "reconciled"),
        (contract_id, "expense", 5000.0, "outsourcing", "外部数据采购（政务语料库）",
         "2026-02-15", "EX-2026-003", "confirmed",
         "outsource", "购买政务公开数据语料", None, None, "settled",
         "数据供应商A", True, "in", "special", 0.06, 283.02,
         project_id, None, "2026-02", None, "reconciled"),
    ]
    for f in expense_records:
        cur.execute("""
            INSERT INTO finance_records (contract_id, type, amount, category, description,
                                        date, invoice_no, status,
                                        funding_source, business_note, related_record_id, related_note,
                                        settlement_status, outsource_name, has_invoice,
                                        invoice_direction, invoice_type, tax_rate, tax_amount,
                                        related_project_id, invoice_id, accounting_period,
                                        export_batch_id, reconciliation_status,
                                        created_at, updated_at, is_deleted)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (*f, now, now))

    # ━━ 发票 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    cur.execute("""
        INSERT INTO invoices (invoice_no, contract_id, invoice_type, invoice_date,
                             amount_excluding_tax, tax_rate, tax_amount, total_amount,
                             status, issued_at, received_at, received_by, verified_at,
                             notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ("INV-2026-001", contract_id, "output", "2026-02-10",
          226415.09, 0.06, 13584.91, 240000.0,
          "received", days_ago(60), days_ago(58), "张伟", days_ago(55),
          "第一期进度款发票", now, now))

    # ━━ 任务 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    tasks_data = [
        ("需求调研与业务流程梳理", "完成政务服务中心业务流程调研，梳理高频问答场景", "high", "completed", "董天文", "2026-02-15"),
        ("数据集方案设计", "设计政务问答数据集标注方案，定义标签体系", "high", "completed", "董天文", "2026-03-01"),
        ("数据标注执行", "执行5000条政务问答对数据标注", "medium", "in_progress", "李明", "2026-04-30"),
        ("Llama3-8B模型精调", "基于标注数据精调Llama3-8B政务问答模型", "high", "in_progress", "董天文", "2026-05-31"),
        ("系统API开发", "开发模型推理API和对话管理接口", "medium", "pending", "王磊", "2026-06-15"),
        ("前端集成与联调", "完成政务服务大厅终端的前端集成", "medium", "pending", "王磊", "2026-07-10"),
        ("性能测试与优化", "压力测试、并发优化、响应时间调优", "high", "pending", "董天文", "2026-07-20"),
        ("用户培训与交付", "编写操作手册，现场培训政务工作人员", "low", "pending", "董天文", "2026-07-30"),
    ]
    task_ids = []
    for t in tasks_data:
        cur.execute("""
            INSERT INTO tasks (project_id, title, description, priority, status, assignee, due_date,
                             created_at, updated_at, is_deleted)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (project_id, *t, now, now))
        task_ids.append(cur.lastrowid)

    # ━━ 里程碑 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    milestones_data = [
        ("M1: 需求确认与方案设计", "完成需求调研、方案评审并签署确认", "2026-02-28",
         "2026-03-01", True, 240000.0, "2026-03-05", "received",
         days_ago(55)),
        ("M2: 数据集构建与模型训练", "5000条标注数据交付，模型精调完成", "2026-05-31",
         None, False, 320000.0, "2026-06-05", "pending", None),
        ("M3: 系统集成与终验交付", "系统上线运行，终验通过", "2026-07-30",
         None, False, 240000.0, "2026-08-05", "unpaid", None),
    ]
    milestone_ids = []
    for m in milestones_data:
        cur.execute("""
            INSERT INTO milestones (project_id, title, description, due_date, completed_date,
                                   is_completed, payment_amount, payment_due_date, payment_status,
                                   payment_received_at, created_at, updated_at, is_deleted)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (project_id, m[0], m[1], m[2], m[3], m[4], m[5], m[6], m[7], m[8], now, now))
        milestone_ids.append(cur.lastrowid)

    # ━━ 需求版本 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    cur.execute("""
        INSERT INTO requirements (project_id, version_no, summary, confirm_status,
                                 confirmed_at, confirm_method, is_current, notes,
                                 requirement_type, annotation_task_id,
                                 created_at, updated_at, is_deleted)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    """, (project_id, "REQ-V1.0",
          "智能政务多模态交互系统需求规格说明书V1.0，包含：\n"
          "1. 政务问答场景定义（32个高频场景）\n"
          "2. 数据标注规范（问答对格式、标签体系）\n"
          "3. 模型性能指标（准确率≥92%，响应≤2s）\n"
          "4. 系统集成要求（API接口、前端组件）\n"
          "5. 验收标准（测试用例覆盖率达90%）",
          "confirmed", days_ago(85), "email", False,
          "初始版本，经客户评审通过", "functional", None, now, now))
    req_v1_id = cur.lastrowid

    cur.execute("""
        INSERT INTO requirements (project_id, version_no, summary, confirm_status,
                                 confirmed_at, confirm_method, is_current, notes,
                                 requirement_type, annotation_task_id,
                                 created_at, updated_at, is_deleted)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    """, (project_id, "REQ-V2.0",
          "智能政务多模态交互系统需求规格说明书V2.0（当前版本），更新内容：\n"
          "1. 新增多轮对话场景（5个新增场景）\n"
          "2. 数据标注规范V2更新（增加否定样本标注）\n"
          "3. 模型性能指标上调（准确率≥95%，响应≤1.5s）\n"
          "4. 新增移动端适配需求\n"
          "5. 新增数据安全与脱敏要求",
          "confirmed", days_ago(40), "meeting", True,
          "V2.0版本，增加移动端和安全需求", "functional", None, now, now))
    req_v2_id = cur.lastrowid

    # ━━ 需求变更 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    changes = [
        (req_v1_id, "新增多轮对话场景需求", "客户要求增加5个多轮对话场景，需重新评估数据标注工作量",
         "addition", True, None, "client", now),
        (req_v1_id, "模型性能指标上调", "客户将准确率要求从92%上调至95%，响应时间从2s缩短至1.5s",
         "modification", False, None, "client", now),
        (req_v2_id, "新增移动端适配需求", "需支持iOS/Android政务APP内嵌H5访问",
         "addition", True, None, "client", now),
    ]
    for c in changes:
        cur.execute("""
            INSERT INTO requirement_changes (requirement_id, title, description, change_type,
                                           is_billable, change_order_id, initiated_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, c)

    # ━━ 变更单 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    cur.execute("""
        INSERT INTO change_orders (order_no, contract_id, requirement_change_id, title, description,
                                  amount, status, confirmed_at, confirm_method, notes,
                                  extra_days, extra_amount, client_confirmed_at, client_rejected_at,
                                  rejection_reason, created_at, updated_at, is_deleted)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    """, ("CO-2026-001", contract_id, None,
          "新增多轮对话场景及移动端适配", "因客户业务扩展，需增加5个多轮对话场景和移动端H5适配，预计增加15个工作日",
          80000.0, "confirmed", days_ago(35), "email",
          "客户已书面确认变更内容",
          15, 80000.0, days_ago(35), None, None, now, now))
    change_order_id = cur.lastrowid

    # ━━ 验收 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    cur.execute("""
        INSERT INTO acceptances (project_id, milestone_id, acceptance_name, acceptance_date,
                                acceptor_name, acceptor_title, result, notes,
                                trigger_payment_reminder, reminder_id, confirm_method,
                                delivery_package_id, acceptance_type,
                                created_at, is_deleted)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    """, (project_id, milestone_ids[0],
          "M1 需求确认阶段验收", "2026-03-01",
          "张伟", "项目经理", "pass",
          "需求文档完整，方案评审通过，客户已确认",
          True, None, "email", None, "milestone", now))

    cur.execute("""
        INSERT INTO acceptances (project_id, milestone_id, acceptance_name, acceptance_date,
                                acceptor_name, acceptor_title, result, notes,
                                trigger_payment_reminder, reminder_id, confirm_method,
                                delivery_package_id, acceptance_type,
                                created_at, is_deleted)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    """, (project_id, None,
          "数据标注质量抽检", "2026-04-08",
          "李明", "数据工程师", "pass",
          "抽检500条标注数据，合格率98.2%，超过95%阈值",
          False, None, "onsite", None, "interim", now))

    # ━━ 交付物 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    deliverables_data = [
        ("智能政务问答系统技术方案", "document", "2026-02-28", "张伟", "email",
         "系统架构设计方案，含技术选型与部署方案", "/docs/技术方案V2.0.pdf", "V2.0"),
        ("政务问答数据集V1.0", "dataset", "2026-04-05", "李明", "online",
         "5000条政务问答对标注数据集", "/data/gov_qa_v1.jsonl", "V1.0"),
        ("Llama3-8B政务精调模型", "model", "2026-04-10", "董天文", "online",
         "Llama3-8B政务问答精调模型权重", "/models/llama3-gov-v1/", "V1.0"),
    ]
    deliverable_ids = []
    for d in deliverables_data:
        cur.execute("""
            INSERT INTO deliverables (project_id, acceptance_id, name, deliverable_type,
                                     delivery_date, recipient_name, delivery_method,
                                     description, storage_location, version_no,
                                     delivery_package_id, created_at, is_deleted)
            VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, 0)
        """, (project_id, *d, now))
        deliverable_ids.append(cur.lastrowid)

    # ━━ 版本发布 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    cur.execute("""
        INSERT INTO releases (project_id, deliverable_id, version_no, release_date,
                             release_type, is_current_online, changelog, deploy_env,
                             notes, created_at, is_deleted)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    """, (project_id, deliverable_ids[2], "v0.9-beta", "2026-04-10",
          "beta", True,
          "## v0.9-beta\n- 初始内测版本\n- 支持基础问答功能\n- 政务场景覆盖率72%\n- 平均响应时间1.8s",
          "staging",
          "内测版本，用于功能验证", now))

    cur.execute("""
        INSERT INTO releases (project_id, deliverable_id, version_no, release_date,
                             release_type, is_current_online, changelog, deploy_env,
                             notes, created_at, is_deleted)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    """, (project_id, deliverable_ids[0], "v1.0-rc1", "2026-05-01",
          "rc", False,
          "## v1.0-rc1\n- 新增多轮对话支持\n- 准确率提升至94%\n- 政务场景覆盖率95%\n- 响应时间优化至1.2s",
          "production",
          "Release Candidate 1，准备正式发布", now))

    # ━━ 售后/维护期 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    cur.execute("""
        INSERT INTO maintenance_periods (project_id, contract_id, service_type, service_description,
                                        start_date, end_date, annual_fee, status,
                                        renewed_by_id, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (project_id, contract_id, "standard",
          "系统运维保障服务，含7×12小时技术支持、季度巡检、Bug修复",
          "2026-08-01", "2027-07-31", 120000.0,
          "active", None, "年度运维合同，自动续约", now))

    # ━━ 工时记录 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    work_hours = [
        ("2026-01-15", 8.0, "需求调研会议，梳理政务服务中心业务流程", None),
        ("2026-01-20", 6.0, "编写需求规格说明书V1.0初稿", None),
        ("2026-02-01", 8.0, "数据标注方案设计，定义标签体系", None),
        ("2026-02-15", 7.0, "标注团队培训，标注规范评审", None),
        ("2026-03-01", 8.0, "模型选型评估，确定Llama3-8B方案", None),
        ("2026-03-15", 8.0, "Llama3-8B政务语料精调第一轮", None),
        ("2026-04-01", 6.0, "精调模型评测与参数调优", None),
        ("2026-04-10", 8.0, "Llama3-8B政务语料精调第二轮", "偏差原因：GPU集群故障导致重训"),
    ]
    for wh in work_hours:
        cur.execute("""
            INSERT INTO work_hour_logs (project_id, log_date, hours_spent, task_description,
                                       deviation_note, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (project_id, *wh, now))

    # ━━ 固定成本 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    cur.execute("""
        INSERT INTO fixed_costs (name, category, amount, period, effective_date, end_date,
                                project_id, notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ("GPU服务器租赁", "server", 15000.0, "monthly",
          "2026-03-01", "2026-07-31", project_id,
          "阿里云GPU集群（2×A100），模型训练专用", now, now))

    cur.execute("""
        INSERT INTO fixed_costs (name, category, amount, period, effective_date, end_date,
                                project_id, notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ("数据标注工具授权", "software", 5000.0, "monthly",
          "2026-02-01", "2026-06-30", project_id,
          "Label Studio企业版月度授权", now, now))

    # ━━ 进项发票 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    cur.execute("""
        INSERT INTO input_invoices (invoice_no, vendor_name, invoice_date,
                                   amount_excluding_tax, tax_rate, tax_amount, total_amount,
                                   category, project_id, notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ("IN-2026-001", "阿里云计算有限公司", "2026-03-05",
          14150.94, 0.06, 849.06, 15000.0,
          "server", project_id, "GPU服务器3月租赁费", now, now))

    cur.execute("""
        INSERT INTO input_invoices (invoice_no, vendor_name, invoice_date,
                                   amount_excluding_tax, tax_rate, tax_amount, total_amount,
                                   category, project_id, notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, ("IN-2026-002", "数据供应商A", "2026-02-20",
          4716.98, 0.06, 283.02, 5000.0,
          "data", project_id, "政务公开数据语料采购", now, now))

    # ━━ 数据集 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    cur.execute("""
        INSERT INTO datasets (project_id, name, dataset_type, description, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (project_id, "政务问答训练数据集", "text",
          "包含政务服务中心32个高频问答场景的训练数据，用于Llama3-8B精调", now, now))
    dataset_id = cur.lastrowid

    # 数据集版本
    cur.execute("""
        INSERT INTO dataset_versions (dataset_id, version_no, status, sample_count, file_path,
                                     data_source, label_schema_version, change_summary, notes,
                                     created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (dataset_id, "V1.0", "ready", 5000,
          "/data/gov_qa_v1.jsonl",
          "人工标注+政务公开数据", "schema-v1",
          "初始版本，5000条政务问答对", "经过质量抽检，合格率98.2%", now, now))
    ds_version_v1 = cur.lastrowid

    cur.execute("""
        INSERT INTO dataset_versions (dataset_id, version_no, status, sample_count, file_path,
                                     data_source, label_schema_version, change_summary, notes,
                                     created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (dataset_id, "V1.1", "ready", 5500,
          "/data/gov_qa_v1.1.jsonl",
          "V1.0基础上补充多轮对话", "schema-v2",
          "新增500条多轮对话样本", "含否定样本标注", now, now))
    ds_version_v1_1 = cur.lastrowid

    # ━━ 标注任务 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    cur.execute("""
        INSERT INTO annotation_tasks (project_id, dataset_version_id, name, status, batch_no,
                                     sample_count, annotator_count, quality_check_result,
                                     rework_reason, completed_at, notes,
                                     created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (project_id, ds_version_v1,
          "政务问答对首轮标注", "completed", "BATCH-001",
          5000, 3, "抽检合格率98.2%，超过95%阈值",
          None, days_ago(10), "5000条政务问答对标注已完成", now, now))
    annotation_task_id = cur.lastrowid

    # ━━ 训练实验 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    cur.execute("""
        INSERT INTO training_experiments (project_id, name, description, framework,
                                         hyperparameters, metrics, started_at, finished_at,
                                         notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (project_id,
          "Llama3-8B政务精调实验-Run1", "基于标注数据的Llama3-8B LoRA精调实验",
          "PyTorch + HuggingFace Transformers",
          '{"learning_rate": 2e-4, "lora_r": 16, "lora_alpha": 32, "epochs": 3, "batch_size": 8, "max_length": 2048}',
          '{"accuracy": 0.951, "f1_score": 0.947, "bleu": 0.82, "response_time_avg": 1.2}',
          days_ago(30), days_ago(5),
          "第二轮精调，准确率提升至95.1%", now, now))
    experiment_id = cur.lastrowid

    # 关联数据集版本
    cur.execute("""
        INSERT INTO experiment_dataset_versions (experiment_id, dataset_version_id, created_at)
        VALUES (?, ?, ?)
    """, (experiment_id, ds_version_v1_1, now))

    # ━━ 模型版本 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    cur.execute("""
        INSERT INTO model_versions (project_id, experiment_id, name, version_no, status,
                                   metrics, file_path, notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (project_id, experiment_id,
          "Llama3-8B-Gov-QA-v1", "v1.0", "ready",
          '{"accuracy": 0.951, "f1_score": 0.947, "bleu": 0.82}',
          "/models/llama3-gov-v1/",
          "正式发布版本，准确率95.1%", now, now))
    model_version_id = cur.lastrowid

    # ━━ 交付包 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    cur.execute("""
        INSERT INTO delivery_packages (project_id, name, status, description,
                                       delivered_at, notes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (project_id,
          "智能政务问答系统 Alpha 交付包", "delivered",
          "包含精调模型、推理API和部署文档的Alpha交付包",
          days_ago(5), "Alpha版本交付，供客户内部测试", now, now))
    package_id = cur.lastrowid

    # 关联模型版本到交付包
    cur.execute("""
        INSERT INTO package_model_versions (package_id, model_version_id, created_at)
        VALUES (?, ?, ?)
    """, (package_id, model_version_id, now))

    # 关联数据集版本到交付包
    cur.execute("""
        INSERT INTO package_dataset_versions (package_id, dataset_version_id, created_at)
        VALUES (?, ?, ?)
    """, (package_id, ds_version_v1_1, now))

    # ━━ 提醒 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    cur.execute("""
        INSERT INTO reminders (title, reminder_type, is_critical, reminder_date, status,
                              entity_type, entity_id, note, completed_at, source,
                              created_at, updated_at, is_deleted)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    """, ("M2里程碑到期提醒", "milestone_due", True, "2026-05-25", "pending",
          "project", project_id, "数据集构建与模型训练里程碑将于5月31日到期",
          None, "system", now, now))

    cur.execute("""
        INSERT INTO reminders (title, reminder_type, is_critical, reminder_date, status,
                              entity_type, entity_id, note, completed_at, source,
                              created_at, updated_at, is_deleted)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    """, ("第二期进度款催收", "payment_due", True, "2026-04-20", "pending",
          "contract", contract_id, "第二期进度款¥320,000待到账",
          None, "system", now, now))

    # ━━ 客户资产 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    cur.execute("""
        INSERT INTO customer_assets (customer_id, asset_type, name, expiry_date, supplier,
                                    annual_fee, account_info, notes,
                                    created_at, updated_at, is_deleted)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
    """, (customer_id, "domain", "shubiao-gov.cn", "2027-01-15",
          "阿里云", 2000.0, "备案号：京ICP备20260001号",
          "政务项目专用域名", now, now))

    return project_id, customer_id, contract_id


# ── 执行 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = OFF")
    cur = conn.cursor()

    print("阶段1: 清理所有数据...")
    clean_all(cur)
    conn.commit()
    print("  清理完成")

    print("\n阶段2: 创建Golden Path测试数据...")
    project_id, customer_id, contract_id = seed(cur)
    conn.commit()

    # 验证
    print(f"\n创建完成:")
    print(f"  客户ID: {customer_id}")
    print(f"  项目ID: {project_id}")
    print(f"  合同ID: {contract_id}")

    for table in ["projects", "customers", "contracts", "tasks", "milestones",
                  "requirements", "requirement_changes", "change_orders",
                  "acceptances", "deliverables", "releases",
                  "maintenance_periods", "finance_records", "invoices",
                  "quotations", "quotation_items", "work_hour_logs",
                  "fixed_costs", "input_invoices",
                  "datasets", "dataset_versions", "annotation_tasks",
                  "training_experiments", "model_versions", "delivery_packages",
                  "package_model_versions", "package_dataset_versions",
                  "experiment_dataset_versions", "reminders", "customer_assets"]:
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        cnt = cur.fetchone()[0]
        print(f"  {table}: {cnt} 条")

    conn.close()
    print("\n完成！")


if __name__ == "__main__":
    main()
