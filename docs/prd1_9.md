# 数标云管 v1.9 — Claude Code 执行指令（风险控制与成本视图模块，修正版 R2）

## 项目目标

在已完成的 v1.0 ~ v1.8 代码库基础上，新增**业务风险控制与项目成本视图**能力：
**三表数据一致性校验 / 收款逾期预警 / 固定成本登记 / 项目粗利润视图 / 进项发票记录 / 客户逾期展示**

本版本不做：税务计算、增值税/所得税申报、会计损益表、成本月度自动摊销、
预算管理体系、客户信用硬拦截、银行流水对接。

---

## 零、关键语义边界定义（实施前必读，禁止跳过）

### 0.1 本版本的定位

v1.9 的目标是：**让已建好的报价→合同→项目→财务→发票链路"跑得稳、不亏钱、不被拖死"**。

不是扩展系统边界，而是在现有链路上加装"仪表盘和预警灯"。

### 0.2 工时成本的单位换算规则（必须严格遵守）

```python
# work_hour_logs.hours_spent 单位：小时（hour）
# quotations.daily_rate 单位：元/天（元/day）
# 换算基准：1天 = 8小时（固定，不可配置）
#
# 工时成本计算公式（唯一合法公式）：
# labor_cost = round((hours_spent_total / 8) * daily_rate, 2)
#
# 禁止直接使用：hours_spent * daily_rate（单位不匹配，会放大8倍）
#
# daily_rate 来源：该项目关联报价单的 daily_rate 字段
# 若报价单无 daily_rate 或项目无关联报价单：labor_cost = None，has_complete_data = False
```

### 0.3 固定成本月汇总的口径（业务视角，不摊销）

```python
# 月汇总口径：业务视角统计，不做自动摊销
#
# 规则（所有 period 类型统一适用）：
# 条目纳入某月汇总的条件：
#   effective_date <= 该月最后一天
#   AND（end_date IS NULL OR end_date >= 该月第一天）
#
# 纳入时计入金额：条目的原始 amount 字段（不除以月数，不摊销）
#
# 举例：
#   一条 yearly 条目，amount=12000，effective_date=2024-01-01，end_date=2024-12-31
#   → 在 2024-01 ~ 2024-12 每个月的汇总中，均计入 12000（原始金额）
#   → 不会自动变成 1000/月
#
# 这是业务视角的"当月有哪些在生效的成本"，不是会计摊销
# 若用户需要看摊销后金额，由用户自行换算，系统不做
```

### 0.4 三表一致性校验的精确定义

```python
# "三表"：contracts / finance_records / invoices
# 所有校验为只读操作，不修改任何字段
#
# 校验维度与字段来源：
#
# 1. payment_gap（未收款差异）
#    合同未收款 = contracts.amount - SUM(finance_records.amount WHERE contract_id=X)
#    触发条件：差值 > CONSISTENCY_CHECK_TOLERANCE
#
# 2. invoice_gap（未开票差异）
#    合同未开票 = contracts.amount - SUM(invoices.total_amount WHERE contract_id=X AND status != 'cancelled')
#    触发条件：差值 > CONSISTENCY_CHECK_TOLERANCE
#
# 3. unlinked_payment（收款未关联发票）
#    finance_records WHERE invoice_id IS NULL AND contract_id IS NOT NULL
#    触发条件：存在此类记录即报告
#
# 4. invoice_payment_mismatch（核销发票与实收差异）
#    "已核销发票"定义：invoices.status = 'verified'（来自 v1.8，终态）
#    已核销发票总额 = SUM(invoices.total_amount WHERE contract_id=X AND status='verified')
#    实收总额 = SUM(finance_records.amount WHERE contract_id=X)
#    差值 = ABS(已核销总额 - 实收总额)
#    触发条件：差值 > CONSISTENCY_CHECK_TOLERANCE
#
# 金额容忍度：CONSISTENCY_CHECK_TOLERANCE = 0.01（分位误差，低于此值不报告）
```

### 0.5 项目粗利润的计算口径

```python
# 粗利润（业务视角，不是会计准则）：
#
# revenue = SUM(finance_records.amount WHERE project_id=X)   # 实收，不用合同金额
#
# cost 构成（三项均为可选，有数据才计入）：
#   labor_cost = round((SUM(work_hour_logs.hours_spent) / 8) * daily_rate, 2)
#              ← daily_rate 来自关联报价单；无数据则 labor_cost = None
#   fixed_cost = SUM(fixed_costs.amount WHERE project_id=X)   # 手动关联的固定成本原始金额
#   input_cost = SUM(input_invoices.total_amount WHERE project_id=X)  # 进项发票含税金额
#
# total_cost = (labor_cost or 0) + (fixed_cost or 0) + (input_cost or 0)
# gross_profit = revenue - total_cost
# gross_margin = gross_profit / revenue（revenue > 0 时计算，否则为 null）
#
# has_complete_data = True 的条件：
#   work_hour_logs 有记录 AND 关联报价单有 daily_rate
#
# 数据不完整时：
#   仍然计算（用已有数据），labor_cost = None
#   warnings 字段说明缺失项，不因数据不完整返回错误
```

### 0.6 客户风险展示的性质声明

```python
# 客户风险展示为纯信息展示，不做任何业务拦截
# 任何接口均不得因客户 risk_level 而拒绝请求
# risk_level 只影响看板展示颜色和预警列表
```

### 0.7 进项发票的范围边界

```python
# 进项发票 = 供应商开给你的成本票
# 与 v1.8 的销项发票（invoices 表）完全独立，分开建表
# 不做：增值税抵扣、税务申报、认证流程
# 只做：记录、查询、可选关联项目
```

---

## 一、前置检查（任意一项失败则停止，将失败原因写入 PROGRESS.md 后退出）

```bash
# 1. 确认 v1.0 ~ v1.8 全量测试通过
pytest tests/ -v --tb=short
# 要求：0 FAILED

# 2. 通过 PRAGMA table_info 确认以下表实际存在（不得依赖 ORM 模型）
#   customers / projects / contracts / finance_records / milestones / tasks
#   requirements / requirement_changes / acceptances / deliverables
#   releases / change_orders / maintenance_periods
#   quotations / quotation_items / quotation_changes
#   work_hour_logs / invoices / export_batches

# 3. 确认 logs/ 目录存在且 RotatingFileHandler 配置正确（10MB/文件，保留 30 个）
# 4. 确认 .env 文件存在且 SECRET_KEY 已配置
```

前置检查全部通过后，将以下内容写入项目根目录 `PROGRESS.md`，然后开始执行：

```markdown
# v1.9 执行进度

## 状态：执行中
## 开始时间：[自动填写当前时间]

| 簇 | 名称 | 状态 | 完成时间 | 通过测试数 |
|----|------|------|----------|------------|
| A | 数据库迁移 | ⏳ | - | - |
| B | 三表数据一致性校验——后端 | ⏳ | - | - |
| C | 收款逾期预警——后端 | ⏳ | - | - |
| D | 固定成本登记——后端 | ⏳ | - | - |
| E | 项目粗利润视图——后端 | ⏳ | - | - |
| F | 进项发票记录——后端 | ⏳ | - | - |
| G | 前端联调 | ⏳ | - | - |
| H | 全局重构 | ⏳ | - | - |

---

## 失败记录模板（执行中止时填写）
## 状态：失败
## 失败步骤：簇 X / 第 N 步
## 失败原因：[具体错误信息]
## 影响范围：[哪些功能受影响]
## 当前已完成项：[已完成的簇列表]
## 下次恢复入口：[从哪一步重新开始]
```

---

## 二、全局精度与边界约定

```python
# 必须追加到 backend/core/constants.py，禁止修改已有常量

# 工时换算（唯一来源，禁止在业务代码中硬编码 8）
HOURS_PER_DAY = 8                       # 1天=8小时，工时成本换算基准

# 风险控制
OVERDUE_PAYMENT_WARN_DAYS = 0           # payment_due_date < 今日即为逾期
CUSTOMER_OVERDUE_WARN_THRESHOLD = 1     # 逾期笔数 >= 1 → warning
CUSTOMER_OVERDUE_HIGH_THRESHOLD = 3     # 逾期笔数 >= 3 → high
CUSTOMER_OVERDUE_HIGH_RATIO = 0.30      # 逾期金额 / 合同总额 >= 30% → high

# 一致性校验
CONSISTENCY_CHECK_TOLERANCE = 0.01      # 金额差异容忍度，低于此值不报告

# 固定成本
FIXED_COST_PERIOD_WHITELIST = ["monthly", "quarterly", "yearly", "onetime"]
FIXED_COST_CATEGORY_WHITELIST = ["office", "cloud", "software", "equipment", "other"]

# 粗利润
GROSS_PROFIT_DECIMAL_PLACES = 2
GROSS_MARGIN_DECIMAL_PLACES = 4

# 精确定义：
# 1. 工时成本 = (hours_spent / HOURS_PER_DAY) * daily_rate，禁止直接乘
# 2. 固定成本月汇总：只统计当月有效条目的原始金额，不摊销
# 3. "已核销发票"定义：invoices.status = 'verified'
# 4. 三表一致性校验为只读，不修改任何字段
# 5. customer.risk_level 不参与任何接口校验
```

---

## 三、执行清单

---

### 簇 A：数据库迁移

**目标**：新增固定成本表、进项发票表，扩展 projects 和 customers 表字段，建立索引。

#### 步骤 1：迁移前记录快照

通过 `PRAGMA table_info` 和查询记录行数，记录：
- `projects` 总行数及现有字段列表
- `customers` 总行数及现有字段列表
- `milestones` 总行数
- 随机抽样各表 3 条记录，保存 `id` 及所有已有字段值

#### 步骤 2：创建并执行迁移脚本 `backend/migrations/v1_9_migrate.py`

```python
# SQLite 不支持 ADD COLUMN IF NOT EXISTS
# 迁移脚本必须用 PRAGMA table_info 检查每个字段是否存在
# 不存在才执行 ALTER TABLE，已存在则跳过并记录日志
# 禁止因字段已存在而报错中止
```

```sql
-- 新增固定成本表
CREATE TABLE IF NOT EXISTS fixed_costs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    category VARCHAR(30) NOT NULL DEFAULT 'other',
    amount DECIMAL(12,2) NOT NULL,
    period VARCHAR(20) NOT NULL DEFAULT 'monthly',
    effective_date DATE NOT NULL,
    end_date DATE NULL,
    project_id INTEGER NULL REFERENCES projects(id) ON DELETE SET NULL,
    notes TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 新增进项发票表（与销项发票 invoices 表独立）
CREATE TABLE IF NOT EXISTS input_invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_no VARCHAR(100) NOT NULL,
    vendor_name VARCHAR(200) NOT NULL,
    invoice_date DATE NOT NULL,
    amount_excluding_tax DECIMAL(12,2) NOT NULL,
    tax_rate DECIMAL(5,4) NOT NULL DEFAULT 0.13,
    tax_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
    total_amount DECIMAL(12,2) NOT NULL,
    category VARCHAR(50) NOT NULL DEFAULT 'other',
    project_id INTEGER NULL REFERENCES projects(id) ON DELETE SET NULL,
    notes TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 扩展 customers 表（风险展示字段，不参与业务拦截）
ALTER TABLE customers ADD COLUMN overdue_milestone_count INTEGER NOT NULL DEFAULT 0;
ALTER TABLE customers ADD COLUMN overdue_amount DECIMAL(12,2) NOT NULL DEFAULT 0;
ALTER TABLE customers ADD COLUMN risk_level VARCHAR(20) NOT NULL DEFAULT 'normal';
-- risk_level 白名单：normal / warning / high

-- 扩展 projects 表（粗利润缓存，供看板快速读取）
ALTER TABLE projects ADD COLUMN cached_revenue DECIMAL(12,2) NULL;
ALTER TABLE projects ADD COLUMN cached_labor_cost DECIMAL(12,2) NULL;
ALTER TABLE projects ADD COLUMN cached_fixed_cost DECIMAL(12,2) NULL;
ALTER TABLE projects ADD COLUMN cached_input_cost DECIMAL(12,2) NULL;
ALTER TABLE projects ADD COLUMN cached_gross_profit DECIMAL(12,2) NULL;
ALTER TABLE projects ADD COLUMN cached_gross_margin DECIMAL(8,4) NULL;
ALTER TABLE projects ADD COLUMN profit_cache_updated_at TIMESTAMP NULL;

-- 索引
CREATE INDEX IF NOT EXISTS idx_fixed_costs_project_id ON fixed_costs(project_id);
CREATE INDEX IF NOT EXISTS idx_fixed_costs_effective_date ON fixed_costs(effective_date);
CREATE INDEX IF NOT EXISTS idx_fixed_costs_category ON fixed_costs(category);
CREATE INDEX IF NOT EXISTS idx_input_invoices_project_id ON input_invoices(project_id);
CREATE INDEX IF NOT EXISTS idx_input_invoices_invoice_date ON input_invoices(invoice_date);
CREATE INDEX IF NOT EXISTS idx_input_invoices_vendor_name ON input_invoices(vendor_name);
CREATE INDEX IF NOT EXISTS idx_customers_risk_level ON customers(risk_level);
```

#### 步骤 3：迁移后验证

任意一项失败则停止并写入 `PROGRESS.md`：
- `fixed_costs / input_invoices` 两张新表存在
- `customers` 新增字段存在
- `projects` 粗利润缓存字段存在
- 所有索引存在
- 原有表行数与快照一致，抽样字段值一致

#### 步骤 4：创建测试文件 `tests/test_migration_v19.py`

```python
# test_fixed_costs_table_exists → NFR-901
# test_input_invoices_table_exists → NFR-901
# test_customers_new_columns_exist → NFR-901
# test_projects_profit_cache_columns_exist → NFR-901
# test_all_new_indexes_exist → NFR-901
# test_existing_row_counts_unchanged → NFR-901
# test_existing_records_fields_unchanged → NFR-901
# test_customers_risk_level_default_normal → NFR-901
# test_customers_overdue_count_default_zero → NFR-901
# test_fixed_cost_project_id_nullable → NFR-901
# test_input_invoice_project_id_nullable → NFR-901
```

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 B。

---

### 簇 B：三表数据一致性校验——后端

**目标**：实现合同/收款/发票三表的只读一致性校验，发现并报告数据差异。

#### 接口规范

```http
GET    /api/v1/finance/consistency-check
GET    /api/v1/finance/consistency-check/{contract_id}
POST   /api/v1/finance/consistency-check/refresh
```

#### 一致性报告结构

```json
{
  "checked_at": "2024-01-15T10:00:00",
  "summary": {
    "total_contracts_checked": 10,
    "contracts_with_issues": 2,
    "total_issue_count": 4
  },
  "issues": [
    {
      "contract_id": 1,
      "contract_no": "HT-20240101-001",
      "customer_name": "XX科技",
      "issue_type": "payment_gap",
      "description": "合同金额 100000.00，实收 80000.00，差额 20000.00",
      "contract_amount": 100000.00,
      "received_amount": 80000.00,
      "invoiced_amount": 90000.00,
      "verified_invoice_amount": 70000.00,
      "gap_amount": 20000.00
    }
  ]
}
```

#### 核心规则（严格按零章 0.4 执行）

- **只读**，不修改任何字段，任何实现路径均不得产生写操作
- 四个校验维度（见零章 0.4）：
  - `payment_gap`：合同金额 > 实收总额，差值 > 容忍度
  - `invoice_gap`：合同金额 > 已开票总额（排除 cancelled），差值 > 容忍度
  - `unlinked_payment`：finance_records 中有合同但无发票关联的收款记录
  - `invoice_payment_mismatch`：`invoices.status='verified'` 的发票总额 vs 实收总额差值 > 容忍度
- `POST /refresh`：重新计算并返回最新结果（不持久化校验结果到数据库）

#### 核心函数签名（`backend/core/consistency_utils.py`）

```python
def check_contract_consistency(db, contract_id: int) -> list:
    """对单个合同做四维度只读校验，返回该合同的 issues 列表（空列表=无问题）"""

def check_all_contracts_consistency(db) -> dict:
    """对所有合同做只读校验，返回汇总报告"""

def get_contract_received_amount(db, contract_id: int) -> Decimal:
    """只读：获取合同实收总额"""

def get_contract_invoiced_amount_active(db, contract_id: int) -> Decimal:
    """只读：获取合同已开票总额（排除 cancelled）"""

def get_contract_verified_invoice_amount(db, contract_id: int) -> Decimal:
    """只读：获取合同 status='verified' 的发票总额"""

def detect_payment_gap(contract_amount: Decimal, received_amount: Decimal) -> dict | None:
    """差值 <= CONSISTENCY_CHECK_TOLERANCE 返回 None"""

def detect_invoice_payment_mismatch(verified_amount: Decimal, received_amount: Decimal) -> dict | None:
    """差值 <= CONSISTENCY_CHECK_TOLERANCE 返回 None"""
```

#### 创建测试文件 `tests/test_consistency.py`

```python
# test_no_issues_when_fully_paid_and_invoiced → FR-901
# test_payment_gap_detected_correctly → FR-901
# test_invoice_gap_detected_correctly → FR-901
# test_unlinked_payment_detected → FR-901
# test_invoice_payment_mismatch_uses_verified_status → FR-901  ← 锁定 verified 来源
# test_cancelled_invoice_excluded_from_invoice_gap → FR-901
# test_gap_below_tolerance_not_reported → FR-901
# test_consistency_check_produces_no_writes → FR-901           ← 验证只读
# test_all_contracts_summary_counts_correct → FR-901
# test_single_contract_check_returns_correct_issues → FR-901
# test_consistency_check_empty_db → FR-901
# test_verified_invoice_amount_source_is_invoices_table → FR-901
```

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 C。

---

### 簇 C：收款逾期预警——后端

**目标**：实现里程碑逾期未收款预警和客户风险等级展示（只展示，不拦截）。

#### 接口规范

```http
GET    /api/v1/finance/overdue-warnings
GET    /api/v1/customers/{customer_id}/risk-summary
POST   /api/v1/finance/overdue-warnings/refresh
```

#### 逾期预警报告结构

```json
{
  "checked_at": "2024-01-15T10:00:00",
  "overdue_milestones": [
    {
      "milestone_id": 1,
      "milestone_name": "第一阶段交付",
      "project_id": 1,
      "project_name": "XX项目",
      "customer_id": 1,
      "customer_name": "XX科技",
      "payment_amount": 50000.00,
      "payment_due_date": "2024-01-01",
      "overdue_days": 14,
      "payment_status": "invoiced"
    }
  ],
  "customer_risk_summary": [
    {
      "customer_id": 1,
      "customer_name": "XX科技",
      "overdue_count": 2,
      "overdue_amount": 80000.00,
      "risk_level": "warning"
    }
  ]
}
```

#### 核心规则

- 逾期条件：`milestones.payment_due_date < 今日` 且 `payment_status != received`
- 逾期天数：今日 - payment_due_date（整数天）
- 客户风险等级计算（严格按常量）：
  ```python
  # normal：overdue_count = 0
  # warning：overdue_count >= CUSTOMER_OVERDUE_WARN_THRESHOLD(1)
  # high：overdue_count >= CUSTOMER_OVERDUE_HIGH_THRESHOLD(3)
  #        OR overdue_amount / total_contract_amount >= CUSTOMER_OVERDUE_HIGH_RATIO(0.30)
  # high 优先级高于 warning
  ```
- `POST /refresh`：批量重新计算所有客户的风险字段并写入 customers 表，原子事务
- **risk_level 不参与任何业务接口校验**（见零章 0.6）

#### 核心函数签名（`backend/core/overdue_utils.py`）

```python
def get_overdue_milestones(db) -> list:
    """只读：返回所有逾期未收款里程碑"""

def calculate_customer_risk_level(
    overdue_count: int,
    overdue_amount: Decimal,
    total_contract_amount: Decimal
) -> str:
    """返回 normal / warning / high，严格按常量阈值"""

def refresh_customer_risk_fields(db) -> int:
    """批量更新 customers 表风险字段，原子事务，返回更新记录数"""

def get_customer_risk_summary(db, customer_id: int) -> dict:
    """获取单个客户逾期与风险摘要"""
```

#### 创建测试文件 `tests/test_overdue.py`

```python
# test_milestone_overdue_when_due_date_passed → FR-902
# test_milestone_not_overdue_when_received → FR-902
# test_overdue_days_calculated_correctly → FR-902
# test_customer_risk_normal_when_no_overdue → FR-902
# test_customer_risk_warning_when_one_overdue → FR-902
# test_customer_risk_high_when_count_threshold_reached → FR-902
# test_customer_risk_high_when_ratio_threshold_reached → FR-902
# test_customer_risk_high_takes_priority_over_warning → FR-902
# test_refresh_updates_customer_risk_fields → FR-902
# test_refresh_is_atomic → FR-902
# test_risk_level_does_not_block_contract_creation → FR-902
# test_risk_level_does_not_block_quote_creation → FR-902
# test_overdue_warnings_empty_when_all_paid → FR-902
```

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 D。

---

### 簇 D：固定成本登记——后端

**目标**：实现固定成本 CRUD，支持按月汇总查询（业务视角，不摊销），可选关联项目。

#### 新增枚举

追加到 `backend/models/enums.py`，不修改已有枚举：

```python
class FixedCostPeriod(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    ONETIME = "onetime"

class FixedCostCategory(str, Enum):
    OFFICE = "office"
    CLOUD = "cloud"
    SOFTWARE = "software"
    EQUIPMENT = "equipment"
    OTHER = "other"
```

#### 接口规范

```http
POST   /api/v1/fixed-costs
GET    /api/v1/fixed-costs
GET    /api/v1/fixed-costs/{cost_id}
PUT    /api/v1/fixed-costs/{cost_id}
DELETE /api/v1/fixed-costs/{cost_id}
GET    /api/v1/fixed-costs/summary?period=YYYY-MM
GET    /api/v1/projects/{project_id}/fixed-costs
```

#### 核心规则

- `amount` 必须 > 0
- `period` 必须在白名单内
- `effective_date` 必填；`end_date` 可为 NULL（表示持续有效）
- `end_date` 若填写必须 >= `effective_date`
- `project_id` 为可选，关联后参与该项目粗利润计算

**月汇总逻辑（严格按零章 0.3）**：
```python
# 纳入条件：
#   effective_date <= period_end_date
#   AND (end_date IS NULL OR end_date >= period_start_date)
# 纳入金额：条目原始 amount（不除以月数，不摊销）
```

- `GET /summary` 返回结构：
  ```json
  {
    "accounting_period": "2024-01",
    "period_start": "2024-01-01",
    "period_end": "2024-01-31",
    "total_amount": 5000.00,
    "by_category": {
      "office": 3000.00,
      "cloud": 1500.00,
      "software": 500.00
    },
    "items": []
  }
  ```

#### 核心函数签名（`backend/core/fixed_cost_utils.py`）

```python
def get_monthly_fixed_costs(db, accounting_period: str) -> dict:
    """按零章 0.3 规则返回指定月份有效固定成本汇总（原始金额，不摊销）"""

def get_project_fixed_costs_total(db, project_id: int) -> Decimal:
    """返回关联到指定项目的固定成本原始金额之和"""

def validate_fixed_cost_dates(effective_date: date, end_date: date | None) -> bool:
    """校验 end_date >= effective_date"""

def is_cost_active_in_period(effective_date: date, end_date: date | None, period_start: date, period_end: date) -> bool:
    """判断成本条目是否在指定月份有效"""
```

#### 创建测试文件 `tests/test_fixed_costs.py`

```python
# test_create_fixed_cost_success → FR-903
# test_fixed_cost_amount_must_be_positive → FR-903
# test_fixed_cost_period_must_be_in_whitelist → FR-903
# test_fixed_cost_end_date_must_after_effective_date → FR-903
# test_project_association_optional → FR-903
# test_monthly_summary_includes_active_monthly_cost → FR-903
# test_monthly_summary_includes_active_yearly_cost_at_original_amount → FR-903  ← 锁定不摊销
# test_monthly_summary_excludes_ended_cost → FR-903
# test_monthly_summary_excludes_not_yet_started_cost → FR-903
# test_onetime_cost_appears_only_in_effective_month → FR-903
# test_monthly_summary_by_category_correct → FR-903
# test_project_fixed_costs_total_correct → FR-903
# test_update_fixed_cost_success → FR-903
# test_delete_fixed_cost_success → FR-903
# test_fixed_cost_not_found_returns_404 → FR-903
```

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 E。

---

### 簇 E：项目粗利润视图——后端

**目标**：实现项目粗利润计算，更新利润缓存，提供项目和看板粗利润接口。

#### 接口规范

```http
GET    /api/v1/projects/{project_id}/profit
POST   /api/v1/projects/{project_id}/profit/refresh
GET    /api/v1/finance/profit-overview
```

#### 粗利润报告结构

```json
{
  "project_id": 1,
  "project_name": "XX项目",
  "calculated_at": "2024-01-15T10:00:00",
  "revenue": {
    "contract_amount": 100000.00,
    "received_amount": 80000.00,
    "outstanding_amount": 20000.00
  },
  "cost": {
    "labor_cost": 15000.00,
    "labor_hours_actual": 150.0,
    "daily_rate_used": 800.00,
    "hours_per_day": 8,
    "fixed_cost_allocated": 2000.00,
    "input_invoice_cost": 3000.00,
    "total_cost": 20000.00,
    "has_complete_data": true
  },
  "profit": {
    "gross_profit": 60000.00,
    "gross_margin": 0.7500,
    "based_on": "received_amount"
  },
  "warnings": []
}
```

#### 核心规则（严格按零章 0.2 和 0.5）

- 收入基准：`finance_records` 实收金额之和（不用合同金额）
- 工时成本（唯一合法公式）：
  ```python
  hours_total = SUM(work_hour_logs.hours_spent WHERE project_id=X)
  daily_rate = 关联报价单的 daily_rate（若无则 None）
  labor_cost = round((hours_total / HOURS_PER_DAY) * daily_rate, 2)  # HOURS_PER_DAY=8
  # 禁止直接 hours_total * daily_rate
  ```
- 固定成本：`SUM(fixed_costs.amount WHERE project_id=X)`（原始金额，不摊销）
- 进项成本：`SUM(input_invoices.total_amount WHERE project_id=X)`
- `has_complete_data`：`work_hour_logs` 有记录 AND 报价单有 `daily_rate`
- `POST /profit/refresh`：计算并写入 projects 缓存字段，原子事务
- `GET /profit-overview`：优先读缓存，缓存为 NULL 则实时计算

#### 核心函数签名（`backend/core/profit_utils.py`）

```python
def get_project_labor_cost(db, project_id: int) -> dict:
    """
    返回：
    {
      "labor_cost": Decimal | None,
      "hours_total": Decimal,
      "daily_rate": Decimal | None,
      "has_complete_data": bool
    }
    使用 HOURS_PER_DAY 常量换算，禁止硬编码 8
    """

def calculate_project_profit(db, project_id: int) -> dict:
    """计算项目粗利润完整报告，数据不完整时返回 warnings 而非报错"""

def refresh_project_profit_cache(db, project_id: int) -> dict:
    """写入 projects 缓存字段，原子事务"""

def get_profit_overview(db) -> list:
    """所有项目粗利润列表，优先读缓存"""
```

#### 创建测试文件 `tests/test_profit.py`

```python
# test_profit_revenue_uses_received_not_contract_amount → FR-904
# test_labor_cost_uses_hours_divided_by_hours_per_day → FR-904    ← 锁定换算公式
# test_labor_cost_not_direct_multiply → FR-904                    ← 防止单位错误
# test_labor_cost_null_when_no_work_logs → FR-904
# test_labor_cost_null_when_no_daily_rate → FR-904
# test_has_complete_data_true_when_all_present → FR-904
# test_has_complete_data_false_when_no_logs → FR-904
# test_fixed_cost_uses_original_amount_not_prorated → FR-904      ← 锁定不摊销
# test_input_invoice_cost_included → FR-904
# test_gross_profit_calculated_correctly → FR-904
# test_gross_margin_null_when_no_revenue → FR-904
# test_warnings_returned_when_incomplete_data → FR-904
# test_refresh_cache_writes_to_projects → FR-904
# test_refresh_cache_atomic → FR-904
# test_profit_overview_uses_cache → FR-904
# test_hours_per_day_constant_used → FR-904
# test_project_not_found_returns_404 → FR-904
```

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 F。

---

### 簇 F：进项发票记录——后端

**目标**：实现进项发票（成本票）CRUD，支持关联项目，无状态机，无抵扣逻辑。

#### 接口规范

```http
POST   /api/v1/input-invoices
GET    /api/v1/input-invoices
GET    /api/v1/input-invoices/{invoice_id}
PUT    /api/v1/input-invoices/{invoice_id}
DELETE /api/v1/input-invoices/{invoice_id}
GET    /api/v1/projects/{project_id}/input-invoices
GET    /api/v1/input-invoices/summary
```

#### 核心规则

- 与销项发票（`invoices` 表）完全独立，不共用接口（见零章 0.7）
- `vendor_name`、`invoice_no` 必填
- 金额计算：
  ```python
  tax_amount = round(amount_excluding_tax * tax_rate, 2)
  total_amount = round(amount_excluding_tax + tax_amount, 2)
  # 金额不得为负数
  ```
- `project_id` 可选，关联后参与项目粗利润直接成本计算
- 无状态流转，只有增删改查
- `GET /summary` 返回指定日期范围的进项发票汇总（按类别）

#### 核心函数签名（`backend/core/input_invoice_utils.py`）

```python
def calculate_input_invoice_amount(amount_excluding_tax: Decimal, tax_rate: Decimal) -> dict:
    """返回 {tax_amount, total_amount}，四舍五入到 2 位小数"""

def get_project_input_invoice_total(db, project_id: int) -> Decimal:
    """返回项目关联进项发票含税金额之和"""

def get_input_invoice_summary(db, start_date: str = None, end_date: str = None) -> dict:
    """按类别汇总进项发票"""
```

#### 创建测试文件 `tests/test_input_invoices.py`

```python
# test_create_input_invoice_success → FR-905
# test_vendor_name_required → FR-905
# test_invoice_no_required → FR-905
# test_amount_calculation_correct → FR-905
# test_amount_must_be_positive → FR-905
# test_project_association_optional → FR-905
# test_project_input_invoice_total_correct → FR-905
# test_input_invoice_summary_by_category → FR-905
# test_update_input_invoice_success → FR-905
# test_delete_input_invoice_success → FR-905
# test_input_invoice_not_found_returns_404 → FR-905
# test_input_invoices_use_separate_table_from_output_invoices → FR-905
# test_no_status_field_on_input_invoice → FR-905
```

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 G。

---

### 簇 G：前端联调

**目标**：实现 v1.9 所有新增功能的前端页面。

#### 前端页面要求

**1. 数据一致性校验面板**
- 财务管理页新增"数据核查"Tab
- 展示有差异的合同列表（差异类型标签 / 合同号 / 客户 / 差异金额）
- 差异类型颜色：payment_gap=橙 / invoice_gap=黄 / unlinked_payment=蓝 / mismatch=红
- 支持"立即核查"按钮（调用 POST /refresh）
- 无差异时显示"✅ 数据一致，无问题"，不白屏

**2. 收款逾期预警面板**
- 首页看板新增"逾期预警"区块
- 逾期里程碑列表（项目名 / 客户 / 金额 / 逾期天数）
- 逾期天数 > 30 天标红，7-30 天标橙，< 7 天标黄
- 客户列表页客户名称旁显示风险标签（warning=⚠️黄色 / high=🔴红色 / normal=不显示）
- **风险标签不禁用任何操作按钮，不拦截任何提交**

**3. 固定成本管理**
- 财务管理页新增"固定成本"Tab
- 支持新增/编辑/删除固定成本条目
- 月度汇总：YYYY-MM 选择器 + 当月有效条目列表 + 分类汇总金额
- 汇总说明文字："以下为当月有效成本条目原始金额，非摊销后金额"
- 可选关联项目

**4. 项目粗利润视图**
- 项目详情页新增"利润分析"Tab
- 展示收入 / 成本明细 / 粗利润 / 毛利率
- `has_complete_data = false` 时展示黄色 warnings 提示条
- 支持"刷新计算"按钮（调用 POST /profit/refresh）
- 首页看板新增"项目粗利润"列表（Top 5，读缓存）

**5. 进项发票管理**
- 财务管理页新增"进项发票"Tab
- Tab 标签注明"进项（收到的票）"，与"发票台账（开出的票）"区分
- 支持新增/编辑/删除进项发票
- 可选关联项目
- 按日期范围汇总展示

#### 前端验收标准

- 一致性校验无差异时展示"✅"，不白屏
- 客户风险标签不禁用任何按钮，不拦截提交
- 固定成本月汇总有说明文字（非摊销）
- 粗利润无工时数据时正确展示 warnings，不报错
- 进项/销项发票 Tab 标签区分清晰
- 所有金额无数据时展示 0.00

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 H。

---

### 簇 H：全局重构

**目标**：在全量测试通过的前提下优化代码结构。

#### 核心约束

重构不得改变任何接口的返回字段名、错误信息文案、HTTP 状态码、校验触发时机、业务规则语义。
重构前后全量测试必须 0 FAILED。

#### 必须完成的重构项

**1. 常量集中管理**
- `HOURS_PER_DAY = 8` 只在 `constants.py` 定义，`profit_utils.py` 引用，业务代码中禁止硬编码 8
- `CONSISTENCY_CHECK_TOLERANCE` 只在 `consistency_utils.py` 中引用
- `CUSTOMER_OVERDUE_*` 常量只在 `overdue_utils.py` 中引用

**2. 函数长度与复杂度检查**
- 所有函数 ≤ 50 行，圈复杂度 < 10，超出者必须拆分

**3. 独立函数可调用性验证**
- `backend.core.consistency_utils.check_contract_consistency`
- `backend.core.consistency_utils.get_contract_verified_invoice_amount`
- `backend.core.overdue_utils.calculate_customer_risk_level`
- `backend.core.overdue_utils.refresh_customer_risk_fields`
- `backend.core.fixed_cost_utils.get_monthly_fixed_costs`
- `backend.core.fixed_cost_utils.is_cost_active_in_period`
- `backend.core.profit_utils.get_project_labor_cost`
- `backend.core.profit_utils.calculate_project_profit`
- `backend.core.input_invoice_utils.get_project_input_invoice_total`

**4. 事务一致性验证**
- 客户风险字段批量刷新（原子事务）
- 项目利润缓存写入（原子事务）

**5. 只读操作验证（新增要求）**
以下函数必须通过测试确认不产生任何写操作：
- `check_contract_consistency`
- `check_all_contracts_consistency`
- `get_overdue_milestones`

**6. 日志覆盖验证**
- 一致性校验执行异常
- 客户风险字段刷新失败
- 项目利润缓存写入失败
- 固定成本月汇总计算异常

**7. 最终全量回归**

```bash
pytest tests/ -v --tb=short
# 要求：0 FAILED
# 将完整输出写入 PROGRESS.md
```

---

## 四、完成标准

以下全部满足时，在 `PROGRESS.md` 写入"v1.9 执行完成"并记录时间：

- [ ] 簇 A ~ H 全部状态为 ✅
- [ ] `pytest tests/ -v` 结果：0 FAILED，输出已记录在 `PROGRESS.md`
- [ ] `backend/core/constants.py` 已追加 v1.9 常量
- [ ] `HOURS_PER_DAY` 只在 constants.py 定义一处，profit_utils.py 引用，无硬编码 8
- [ ] 一致性校验为只读（有测试覆盖）
- [ ] 固定成本月汇总返回原始金额（不摊销，有测试覆盖）
- [ ] `invoices.status='verified'` 为"已核销"的唯一来源（有测试覆盖）
- [ ] 客户风险标签不参与任何接口校验（有测试覆盖）
- [ ] 进项发票与销项发票独立建表，不共用接口
- [ ] `logs/` 目录本次执行产生了日志文件
- [ ] 所有接口字段名、错误文案、HTTP 状态码与本文档约定一致

---

## 附录 A：v1.6 ~ v1.9 功能闭环全景

```
报价（v1.6）
  ↓ accepted → 触发需求冻结
合同（v1.0）
  ↓
项目执行控制（v1.7）
  变更冻结 / 里程碑收款绑定 / 工时记录 / 项目强制关闭
  ↓
财务台账（v1.8）
  销项发票 / 收款导出 / 对账报表
  ↓
风险控制与成本视图（v1.9）
  三表一致性校验 ← 确保链路数据无缝隙
  收款逾期预警   ← 发现回款风险
  固定成本登记   ← 补全成本侧数据入口
  项目粗利润视图 ← 项目是否真的赚钱
  进项发票记录   ← 成本票归档
```

## 附录 B：工时成本换算说明

```python
# 为什么不直接用 hours * daily_rate：
#   hours_spent 单位是小时，daily_rate 单位是元/天
#   直接相乘会把成本放大 8 倍（按8小时工作日计算）
#
# 正确公式：
#   labor_cost = round((hours_total / HOURS_PER_DAY) * daily_rate, 2)
#
# 例：实际工时 160小时，日费率 800元/天
#   错误：160 × 800 = 128,000（错误，放大8倍）
#   正确：(160 / 8) × 800 = 20 天 × 800 = 16,000（正确）
```

## 附录 C：固定成本月汇总示例

```
条目：年度云服务费 amount=12000，period=yearly
effective_date=2024-01-01，end_date=2024-12-31

2024-01 月汇总：纳入，金额=12000（原始金额）
2024-06 月汇总：纳入，金额=12000（原始金额）
2024-12 月汇总：纳入，金额=12000（原始金额）
2025-01 月汇总：不纳入（end_date < period_start）

说明：不做 12000/12=1000 的月度摊销
用户若需要看月均成本，自行除以12，系统不做这个计算
```
