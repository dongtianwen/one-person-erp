# 数标云管 v1.8 — Claude Code 执行指令（财务对接模块，修正版 R2）

## 项目目标

在已完成的 v1.0 ~ v1.7 代码库基础上，新增**财务数据导出与发票管理**能力：
**发票台账 / 收款导出 / 会计期间对账 / 财务软件对接导出**

本版本不做：完整记账凭证系统、会计科目体系、税务申报接口、银行流水自动对账、
固定资产管理、进项发票认证、发票抵扣、总账/明细账/凭证链。

---

## 零、关键语义边界定义（实施前必读，禁止跳过）

### 0.1 本系统财务模块与专业财务软件的职责边界

| 职责 | 本系统 | 专业财务软件（金蝶/用友/畅捷通） |
|------|--------|----------------------------------|
| 核心视角 | 项目/客户/合同的业务财务追踪 | 会计科目/凭证的合规核算 |
| 发票管理 | 销项发票台账（记录、查询、导出） | 发票认证、抵扣、税务申报 |
| 收款记录 | 关联项目/合同的收款追踪 | 银行对账、会计分录 |
| 报表输出 | 项目利润表、客户LTV、收款汇总 | 资产负债表、利润表（会计准则）|
| 数据流向 | 业务数据 → 导出给代理记账 | 导入数据 → 生成凭证 → 报税 |

**规则**：
- 本系统只做**销项发票台账**（开给客户的发票），进项票、认证、抵扣、红冲不在范围
- 发票预开、作废、作废重开不在本版本范围
- 本系统不生成会计凭证，不维护会计科目体系，不直接对接税务局接口
- 导出格式以通用 Excel/CSV 为必达目标；金蝶/用友/畅捷通专属格式为可选扩展，见附录 B

### 0.2 核心数据关联链路（禁止偏离）

```
合同 → 收款记录 → 发票 → 导出批次 → 对账结果
```

- 发票必须关联已存在的合同（不允许孤立发票）
- 收款记录可关联发票（invoice_id 可为 NULL，即未开票收款）
- 一张合同可对应多张发票（分批开票），累计金额不得超合同金额
- cancelled 发票不计入累计金额校验
- 导出批次记录哪些数据在哪个时间点被导出，支持追溯

### 0.3 发票状态与收款对账状态的语义边界

**两套状态独立，不互相驱动：**

| 字段 | 所在表 | 含义 | 触发方式 |
|------|--------|------|----------|
| `invoices.status` | invoices | 发票本身的流转状态 | 人工操作接口触发 |
| `finance_records.reconciliation_status` | finance_records | 收款记录的对账确认状态 | `POST /finance/reconciliation/sync` 批量触发 |

```python
# invoices.status 白名单：draft / issued / received / verified / cancelled
# verified = 财务人工确认发票已核销，终态，不驱动 reconciliation_status

# finance_records.reconciliation_status 白名单：pending / matched / verified
# verified = 对账同步批次确认，终态，不驱动 invoices.status

# 两个 verified 是不同的业务事件，禁止用一方状态驱动另一方
```

### 0.4 发票关联与金额校验规则

```python
# 1. 发票必须关联已存在的合同（contract_id 必填）
# 2. 同一合同下 status != cancelled 的发票 total_amount 累计不得超合同金额
# 3. cancelled 发票不计入累计金额，也不计入本期开票统计
# 4. 本版本只做销项发票（开给客户的），进项发票不建模
```

### 0.5 会计期间界定与历史数据处理

```python
# 1. 会计期间按自然月界定：YYYY-MM
# 2. 以合同签订日（sign_date）判定合同所属期间
# 3. 以实际收款日（transaction_date）判定收款所属期间
# 4. 以开票日期（invoice_date）判定发票所属期间
# 5. 对账数据基于系统内已录入数据，不导入历史余额
# 6. 第一个有数据的自然月期初余额固定为 0
#    （历史遗留数据由代理记账方在专业软件中处理，本系统不承担）
```

### 0.6 财务软件导出格式的范围边界

```
本版本必达：通用 Excel/CSV 格式（generic）
可选扩展（附录 B）：金蝶 / 用友 / 畅捷通专属格式

原因：金蝶/用友/畅捷通的导入字段（科目代码、凭证字、借贷方）
需要客户提供账套配置，本系统无会计科目体系，无法硬编码。
map_to_finance_format 对非 generic 格式抛出 NotImplementedError，不作为本版本测试门槛。
```

---

## 一、前置检查（任意一项失败则停止，将失败原因写入 PROGRESS.md 后退出）

```bash
# 1. 确认 v1.0 ~ v1.7 全量测试通过
pytest tests/ -v --tb=short
# 要求：0 FAILED

# 2. 通过 PRAGMA table_info 确认以下表实际存在（不得依赖 ORM 模型）
#   customers / projects / contracts / finance_records / milestones / tasks
#   requirements / requirement_changes / acceptances / deliverables
#   releases / change_orders / maintenance_periods
#   quotations / quotation_items / quotation_changes
#   work_hour_logs

# 3. 确认 logs/ 目录存在且 RotatingFileHandler 配置正确（10MB/文件，保留 30 个）
# 4. 确认 .env 文件存在且 SECRET_KEY 已配置
```

前置检查全部通过后，将以下内容写入项目根目录 `PROGRESS.md`，然后开始执行：

```markdown
# v1.8 执行进度

## 状态：执行中
## 开始时间：[自动填写当前时间]

| 簇 | 名称 | 状态 | 完成时间 | 通过测试数 |
|----|------|------|----------|------------|
| A | 数据库迁移 | ⏳ | - | - |
| B | 发票台账管理——后端 | ⏳ | - | - |
| C | 财务数据导出——后端 | ⏳ | - | - |
| D | 会计期间对账——后端 | ⏳ | - | - |
| E | 前端联调 | ⏳ | - | - |
| F | 全局重构 | ⏳ | - | - |

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

# 发票管理
INVOICE_NO_PREFIX = "INV"
INVOICE_TAX_RATE_STANDARD = 0.13       # 标准增值税率
INVOICE_TAX_RATE_SMALL = 0.03          # 小规模纳税人税率

# 财务导出
EXPORT_DATE_FORMAT = "%Y-%m-%d"
EXPORT_DECIMAL_PLACES = 2
ACCOUNTING_PERIOD_FORMAT = "%Y-%m"

# 导出格式（generic 为必达，其余预留常量但本版本不实现）
EXPORT_FORMAT_GENERIC = "generic"
EXPORT_FORMAT_KINGDEE = "kingdee"      # 预留，未实现
EXPORT_FORMAT_YOYO = "yoyo"            # 预留，未实现
EXPORT_FORMAT_CHANJET = "chanjet"      # 预留，未实现
EXPORT_FORMAT_SUPPORTED = [EXPORT_FORMAT_GENERIC]   # 本版本只支持 generic

# 精确定义：
# 1. 发票编号格式：INV-YYYYMMDD-序号（当日从 001 起）
# 2. tax_amount = round(amount_excluding_tax * tax_rate, 2)
# 3. total_amount = round(amount_excluding_tax + tax_amount, 2)
# 4. 累计校验：同合同下 status != cancelled 的发票 total_amount 之和不超合同金额
# 5. 导出文件名格式：{export_type}_{target_format}_{batch_id}.xlsx
# 6. 会计期间以交易日期所属自然月自动计算
```

---

## 三、执行清单

---

### 簇 A：数据库迁移

**目标**：创建发票台账表和导出批次记录表，扩展财务记录表字段，建立索引。

#### 步骤 1：迁移前记录快照

通过 `PRAGMA table_info` 和查询记录行数，记录：
- `finance_records` 总行数及现有字段列表
- `contracts` 总行数
- 随机抽样各表 3 条记录，保存 `id` 及所有已有字段值

#### 步骤 2：创建并执行迁移脚本 `backend/migrations/v1_8_migrate.py`

```python
# SQLite 不支持 ADD COLUMN IF NOT EXISTS
# 迁移脚本必须用 PRAGMA table_info 检查每个字段是否存在
# 不存在才执行 ALTER TABLE，已存在则跳过并记录日志
# 禁止因字段已存在而报错中止
```

```sql
-- 新增发票台账表（仅销项发票）
CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_no VARCHAR(30) NOT NULL UNIQUE,
    contract_id INTEGER NOT NULL REFERENCES contracts(id) ON DELETE RESTRICT,
    invoice_type VARCHAR(20) NOT NULL DEFAULT 'standard',
    invoice_date DATE NOT NULL,
    amount_excluding_tax DECIMAL(12,2) NOT NULL,
    tax_rate DECIMAL(5,4) NOT NULL DEFAULT 0.13,
    tax_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
    total_amount DECIMAL(12,2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    issued_at TIMESTAMP NULL,
    received_at TIMESTAMP NULL,
    received_by VARCHAR(100) NULL,
    verified_at TIMESTAMP NULL,
    notes TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 扩展 finance_records 表
ALTER TABLE finance_records ADD COLUMN invoice_id INTEGER NULL REFERENCES invoices(id) ON DELETE SET NULL;
ALTER TABLE finance_records ADD COLUMN accounting_period VARCHAR(7) NULL;
ALTER TABLE finance_records ADD COLUMN export_batch_id VARCHAR(50) NULL;
ALTER TABLE finance_records ADD COLUMN reconciliation_status VARCHAR(20) NOT NULL DEFAULT 'pending';

-- 新增导出批次记录表
CREATE TABLE IF NOT EXISTS export_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id VARCHAR(50) NOT NULL UNIQUE,
    export_type VARCHAR(30) NOT NULL,
    target_format VARCHAR(20) NOT NULL DEFAULT 'generic',
    accounting_period VARCHAR(7) NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    record_count INTEGER NOT NULL DEFAULT 0,
    file_path TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_invoices_contract_id ON invoices(contract_id);
CREATE INDEX IF NOT EXISTS idx_invoices_invoice_date ON invoices(invoice_date);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_finance_records_invoice_id ON finance_records(invoice_id);
CREATE INDEX IF NOT EXISTS idx_finance_records_accounting_period ON finance_records(accounting_period);
CREATE INDEX IF NOT EXISTS idx_finance_records_export_batch_id ON finance_records(export_batch_id);
CREATE INDEX IF NOT EXISTS idx_finance_records_reconciliation_status ON finance_records(reconciliation_status);
CREATE INDEX IF NOT EXISTS idx_export_batches_accounting_period ON export_batches(accounting_period);
CREATE INDEX IF NOT EXISTS idx_export_batches_created_at ON export_batches(created_at);
```

#### 步骤 3：迁移后验证

任意一项失败则停止并写入 `PROGRESS.md`：
- `invoices / export_batches` 两张新表存在
- `finance_records` 新增字段存在
- 所有索引存在
- 原有表行数与快照一致，抽样字段值一致

#### 步骤 4：创建测试文件 `tests/test_migration_v18.py`

```python
# test_invoices_table_exists → NFR-801
# test_export_batches_table_exists → NFR-801
# test_finance_records_new_columns_exist → NFR-801
# test_all_new_indexes_exist → NFR-801
# test_existing_row_counts_unchanged → NFR-801
# test_existing_records_fields_unchanged → NFR-801
# test_foreign_key_invoice_contract_restrict → NFR-801
# test_invoice_no_unique_constraint → NFR-801
# test_export_batch_id_unique_constraint → NFR-801
# test_finance_records_reconciliation_status_default_pending → NFR-801
```

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 B。

---

### 簇 B：发票台账管理——后端

**目标**：实现销项发票 CRUD、编号生成、金额累计校验、状态流转。

#### 新增枚举

追加到 `backend/models/enums.py`，不修改已有枚举：

```python
class InvoiceType(str, Enum):
    STANDARD = "standard"        # 增值税专用发票
    ORDINARY = "ordinary"        # 增值税普通发票
    ELECTRONIC = "electronic"    # 电子发票
    SMALL_SCALE = "small_scale"  # 小规模纳税人

class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    RECEIVED = "received"
    VERIFIED = "verified"      # 终态：财务人工确认核销
    CANCELLED = "cancelled"    # 终态：作废

class ReconciliationStatus(str, Enum):
    PENDING = "pending"
    MATCHED = "matched"
    VERIFIED = "verified"      # 终态：对账同步确认（与 InvoiceStatus.VERIFIED 独立）
```

#### 接口规范

```http
POST   /api/v1/invoices
GET    /api/v1/invoices
GET    /api/v1/invoices/{invoice_id}
PUT    /api/v1/invoices/{invoice_id}
PATCH  /api/v1/invoices/{invoice_id}
DELETE /api/v1/invoices/{invoice_id}
POST   /api/v1/invoices/{invoice_id}/issue
POST   /api/v1/invoices/{invoice_id}/receive
POST   /api/v1/invoices/{invoice_id}/verify
POST   /api/v1/invoices/{invoice_id}/cancel
GET    /api/v1/contracts/{contract_id}/invoices
GET    /api/v1/invoices/summary
```

#### 核心规则

- 发票编号后端自动生成，格式 `INV-YYYYMMDD-序号`（当日从 001 起），原子事务
- 发票必须关联已存在的合同，孤立发票不允许创建（HTTP 422）
- 金额计算：
  ```python
  tax_amount = round(amount_excluding_tax * tax_rate, 2)
  total_amount = round(amount_excluding_tax + tax_amount, 2)
  # 所有金额不得为负数
  ```
- 累计金额校验：同合同下 `status != cancelled` 的发票 `total_amount` 之和不超合同金额
- 状态流转白名单：
  - `draft` → `issued / cancelled`
  - `issued` → `received / cancelled`
  - `received` → `verified`
  - `verified / cancelled` 为终态，不可再流转
- 时间戳规则：`issued` → `issued_at`；`received` → `received_at + received_by`；`verified` → `verified_at`
- `verified / cancelled` 不允许删除（HTTP 409）
- `issued` 后核心字段（amount、tax_rate、contract_id）不可修改，只允许改 `notes`

#### 核心函数签名（`backend/core/invoice_utils.py`）

```python
def generate_invoice_no(db) -> str:
    """格式：INV-YYYYMMDD-序号，原子事务"""

def calculate_invoice_amount(amount_excluding_tax: Decimal, tax_rate: Decimal) -> dict:
    """返回 {tax_amount, total_amount}，四舍五入到 2 位小数"""

def validate_invoice_amount(db, contract_id: int, new_amount: Decimal, exclude_invoice_id: int = None) -> bool:
    """校验累计金额是否超合同金额；exclude_invoice_id 用于更新场景"""

def get_contract_invoiced_amount(db, contract_id: int, exclude_invoice_id: int = None) -> Decimal:
    """获取合同已开票总额（排除 cancelled，可排除指定 invoice_id）"""

def validate_invoice_transition(current: str, target: str) -> bool:
    """校验状态流转是否合法"""

def get_invoice_summary(db, start_date: str = None, end_date: str = None) -> dict:
    """按状态统计发票数量和金额"""
```

#### 创建测试文件 `tests/test_invoices.py`

```python
# test_create_invoice_auto_generates_no → FR-801
# test_invoice_no_format_correct → FR-801
# test_invoice_no_increments_same_day → FR-801
# test_create_invoice_default_status_draft → FR-801
# test_invoice_must_associate_existing_contract → FR-801
# test_invoice_amount_calculation_correct → FR-801
# test_tax_amount_rounded_to_two_decimal → FR-801
# test_invoice_amount_exceeds_contract_rejected → FR-801
# test_invoice_amount_equals_contract_accepted → FR-801
# test_cancelled_invoice_excluded_from_cumulative → FR-801
# test_get_invoices_ordered_by_invoice_date_desc → FR-801
# test_get_invoice_detail_success → FR-801
# test_update_draft_invoice_success → FR-801
# test_update_issued_invoice_core_fields_rejected → FR-801
# test_update_issued_invoice_notes_allowed → FR-801
# test_delete_draft_invoice_success → FR-801
# test_delete_verified_invoice_rejected → FR-801
# test_delete_cancelled_invoice_rejected → FR-801
# test_issue_invoice_success → FR-801
# test_issue_writes_issued_at → FR-801
# test_receive_invoice_success → FR-801
# test_receive_writes_received_at_and_by → FR-801
# test_verify_invoice_success → FR-801
# test_verify_invoice_is_terminal → FR-801
# test_cancel_draft_invoice_success → FR-801
# test_cancel_issued_invoice_success → FR-801
# test_cancel_verified_invoice_rejected → FR-801
# test_invalid_transition_returns_409 → FR-801
# test_invoice_not_found_returns_404 → FR-801
# test_contract_not_found_returns_404 → FR-801
# test_invoice_summary_calculates_correctly → FR-801
# test_contract_invoices_list_returns_all → FR-801
```

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 C。

---

### 簇 C：财务数据导出——后端

**目标**：实现财务数据通用格式导出，建立导出批次追溯记录。

> **本簇必达**：`generic` 格式。
> 金蝶/用友/畅捷通专属格式预留参数但不实现，调用时抛出 `NotImplementedError`，不作为本版本测试门槛。

#### 接口规范

```http
POST   /api/v1/finance/export
GET    /api/v1/finance/export/batches
GET    /api/v1/finance/export/batches/{batch_id}
GET    /api/v1/finance/export/download/{batch_id}
```

#### 导出类型与字段（通用格式）

**1. 合同导出**

| 输出列名 | 数据来源 |
|----------|----------|
| 合同编号 | contracts.contract_no |
| 合同名称 | contracts.title |
| 客户名称 | customers.name |
| 合同金额 | contracts.amount |
| 签订日期 | contracts.sign_date |
| 会计期间 | 由 sign_date 自动计算 |
| 关联报价单 | quotations.quote_no（可为空） |

**2. 收款导出**

| 输出列名 | 数据来源 |
|----------|----------|
| 收款日期 | finance_records.transaction_date |
| 收款金额 | finance_records.amount |
| 收款方式 | finance_records.payment_method |
| 客户名称 | customers.name |
| 关联合同 | contracts.contract_no |
| 关联发票 | invoices.invoice_no（可为空） |
| 会计期间 | finance_records.accounting_period |
| 对账状态 | finance_records.reconciliation_status |
| 备注 | finance_records.notes |

**3. 发票导出**

| 输出列名 | 数据来源 |
|----------|----------|
| 发票编号 | invoices.invoice_no |
| 发票类型 | invoices.invoice_type |
| 开票日期 | invoices.invoice_date |
| 客户名称 | customers.name |
| 不含税金额 | invoices.amount_excluding_tax |
| 税率 | invoices.tax_rate |
| 税额 | invoices.tax_amount |
| 价税合计 | invoices.total_amount |
| 关联合同 | contracts.contract_no |
| 发票状态 | invoices.status |

#### 核心规则

- 导出请求参数：
  ```python
  {
    "export_type": "contracts" | "payments" | "invoices",
    "target_format": "generic",        # 本版本只支持 generic
    "accounting_period": "YYYY-MM",    # 与日期范围二选一
    "start_date": "YYYY-MM-DD",
    "end_date": "YYYY-MM-DD"
  }
  ```
- `target_format` 不在 `EXPORT_FORMAT_SUPPORTED` 中时返回 HTTP 400
- 导出生成唯一 `batch_id`，格式：`EXP-YYYYMMDD-HHMMSS-随机6位`
- 导出文件保存到 `exports/` 目录
- 导出记录写入 `export_batches` 表（含 record_count、file_path）
- 导出的 `finance_records` 更新 `export_batch_id` 和 `accounting_period`
- 导出失败时：`export_batches` 记录写入但 `file_path` 为 NULL，日志记录失败原因
- 下载接口：`file_path` 为 NULL 时返回 HTTP 404

#### 核心函数签名（`backend/core/export_utils.py`）

```python
def generate_export_batch_id() -> str:
    """格式：EXP-YYYYMMDD-HHMMSS-随机6位"""

def calculate_accounting_period(d: date) -> str:
    """返回 YYYY-MM 格式会计期间"""

def export_to_excel(db, export_type: str, filters: dict, target_format: str) -> dict:
    """统一导出入口，返回 {batch_id, file_path, record_count}，原子事务"""

def map_to_finance_format(data: list, target_format: str, export_type: str) -> list:
    """
    generic 分支：按导出字段规范输出。
    其他格式：抛出 NotImplementedError，不作为本版本测试门槛。
    """

def save_export_file(batch_id: str, export_type: str, target_format: str, data: list) -> str:
    """保存 xlsx 文件到 exports/，返回文件路径"""

def mark_records_as_exported(db, record_ids: list, batch_id: str, accounting_period: str) -> None:
    """更新已导出 finance_records，原子事务"""
```

#### 创建测试文件 `tests/test_finance_export.py`

```python
# test_export_contracts_generic_success → FR-802
# test_export_payments_generic_success → FR-802
# test_export_invoices_generic_success → FR-802
# test_export_generates_unique_batch_id → FR-802
# test_export_batch_id_format_correct → FR-802
# test_export_saves_to_exports_directory → FR-802
# test_export_file_name_format_correct → FR-802
# test_export_creates_export_batch_record → FR-802
# test_export_batch_record_count_correct → FR-802
# test_export_updates_records_batch_id → FR-802
# test_export_updates_records_accounting_period → FR-802
# test_export_by_accounting_period_filters_correctly → FR-802
# test_export_by_date_range_filters_correctly → FR-802
# test_export_generic_columns_match_spec → FR-802
# test_export_download_returns_file → FR-802
# test_export_download_missing_file_returns_404 → FR-802
# test_export_batch_list_ordered_by_created_desc → FR-802
# test_unsupported_format_returns_400 → FR-802
# test_export_failure_records_null_file_path → FR-802
# test_map_to_finance_format_generic_correct → FR-802
# test_map_to_finance_format_unimplemented_raises → FR-802
```

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 D。

---

### 簇 D：会计期间对账——后端

**目标**：实现按自然月的业务财务汇总，支持客户维度分解和未对账记录识别。

> 本簇不做：总账、明细账、凭证链、锁账、跨期调账。
> 所有计算基于系统内录入数据，第一期期初余额固定为 0（见零章 0.5）。

#### 接口规范

```http
GET    /api/v1/finance/reconciliation
GET    /api/v1/finance/reconciliation/{accounting_period}
POST   /api/v1/finance/reconciliation/sync
```

#### 对账报表结构

```json
{
  "accounting_period": "2024-01",
  "period_start": "2024-01-01",
  "period_end": "2024-01-31",
  "opening_balance": {
    "accounts_receivable": 100000.00,
    "unbilled_amount": 20000.00,
    "total": 120000.00
  },
  "current_period": {
    "contracts_signed": 1,
    "contracts_amount": 50000.00,
    "invoices_issued": 1,
    "invoices_amount": 30000.00,
    "payments_received": 2,
    "payments_amount": 40000.00,
    "invoices_verified": 1,
    "verified_amount": 30000.00
  },
  "closing_balance": {
    "accounts_receivable": 110000.00,
    "unbilled_amount": 40000.00,
    "total": 150000.00
  },
  "breakdown": [
    {
      "customer_id": 1,
      "customer_name": "XX科技有限公司",
      "contracts_amount_this_period": 50000.00,
      "invoices_amount_this_period": 30000.00,
      "payments_amount_this_period": 40000.00,
      "outstanding_balance": 60000.00
    }
  ],
  "unreconciled_records": [
    {
      "record_id": 1,
      "record_type": "payment",
      "amount": 5000.00,
      "transaction_date": "2024-01-15",
      "reason": "无匹配合同"
    }
  ]
}
```

#### 核心规则

- 期初余额 = 上期期末余额；若为系统内第一期则期初全零
- 本期合同 = `sign_date` 在本期内的合同金额之和
- 本期开票 = `invoice_date` 在本期内且 `status != cancelled` 的发票金额之和
- 本期收款 = `transaction_date` 在本期内的收款金额之和
- 期末应收账款 = 期初 + 本期合同 - 本期收款
- 未开票金额 = 本期合同 - 本期开票
- 未对账记录 = `finance_records` 中 `contract_id IS NULL` 的收款记录
- `reconciliation_status` 流转：`pending` → `matched` → `verified`（见零章 0.3）
- `POST /sync`：根据合同/发票关联批量更新状态，原子事务，返回更新记录数
- `GET /reconciliation`：返回所有有数据的期间列表

#### 核心函数签名（`backend/core/reconciliation_utils.py`）

```python
def get_period_date_range(accounting_period: str) -> tuple:
    """返回 (period_start: date, period_end: date)"""

def get_opening_balance(db, accounting_period: str) -> dict:
    """期初余额；第一期返回全零"""

def get_current_period_activity(db, accounting_period: str) -> dict:
    """统计本期合同、开票（排除cancelled）、收款数据"""

def get_closing_balance(db, accounting_period: str) -> dict:
    """期末余额 = 期初 + 本期合同 - 本期收款"""

def get_customer_breakdown(db, accounting_period: str) -> list:
    """按客户分解本期活动"""

def get_unreconciled_records(db, accounting_period: str) -> list:
    """返回 contract_id IS NULL 的收款记录"""

def generate_reconciliation_report(db, accounting_period: str) -> dict:
    """生成完整对账报表"""

def sync_reconciliation_status(db, accounting_period: str) -> int:
    """批量更新 reconciliation_status，原子事务，返回更新记录数"""
```

#### 创建测试文件 `tests/test_reconciliation.py`

```python
# test_get_period_date_range_correct → FR-803
# test_first_period_opening_balance_is_zero → FR-803
# test_opening_balance_equals_previous_closing → FR-803
# test_current_period_contracts_calculates_correctly → FR-803
# test_current_period_invoices_excludes_cancelled → FR-803
# test_current_period_payments_calculates_correctly → FR-803
# test_closing_balance_formula_correct → FR-803
# test_customer_breakdown_aggregates_correctly → FR-803
# test_unreconciled_records_filters_no_contract → FR-803
# test_reconciliation_report_structure_matches_spec → FR-803
# test_reconciliation_sync_updates_matched_status → FR-803
# test_reconciliation_sync_returns_updated_count → FR-803
# test_reconciliation_sync_atomic_on_failure → FR-803
# test_reconciliation_period_invalid_format_returns_400 → FR-803
# test_reconciliation_list_returns_all_active_periods → FR-803
```

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 E。

---

### 簇 E：前端联调

**目标**：实现发票管理、财务导出、对账报表的前端页面。

#### 前端页面要求

**1. 发票台账**
- 合同详情页新增"发票"Tab
- 展示该合同所有发票列表，状态颜色区分：
  - `draft`=灰 / `issued`=蓝 / `received`=绿 / `verified`=深灰 / `cancelled`=红
- 支持新建发票，实时展示已开票进度条（已开 / 合同总额）
- 超限时红色警告"开票金额已超限"，不允许提交
- `verified / cancelled` 状态不展示编辑/删除按钮

**2. 财务导出**
- 财务管理页新增"数据导出"区块
- 导出选项：导出类型（合同/收款/发票）、时间范围（会计期间 或 日期范围）
- 目标格式选择器：默认且只可选 `generic`；其他格式显示"即将支持"并禁用
- 导出历史列表（batch_id / 类型 / 期间 / 记录数 / 下载按钮）
- `file_path` 为 NULL 时不展示下载按钮

**3. 对账报表**
- 财务管理页新增"对账报表"Tab
- 会计期间下拉选择器（只展示系统内有数据的期间）
- 展示：期初余额卡片 / 本期活动卡片 / 期末余额卡片 / 客户分解表格 / 未对账记录列表
- 未对账记录支持点击跳转到关联收款记录页面
- 支持"同步对账状态"按钮，点击后刷新当前期间报表
- 无数据时展示 0.00，不白屏

**4. 财务看板（首页新增指标）**
- 本月开票金额 / 本月收款金额 / 应收账款余额 / 未开票金额
- 无数据时展示 0.00

#### 前端验收标准

- 发票金额超限不允许提交（前端校验 + 接口双重拦截）
- 非 generic 导出格式禁用且有"即将支持"提示
- `file_path` 为 NULL 时不展示下载按钮
- 对账期间选择器只含有数据的期间
- `verified / cancelled` 发票不展示编辑/删除入口
- 所有金额无数据时展示 0.00，不展示 NaN 或空白

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 F。

---

### 簇 F：全局重构

**目标**：在全量测试通过的前提下优化代码结构。

#### 核心约束

重构不得改变任何接口的返回字段名、错误信息文案、HTTP 状态码、校验触发时机、业务规则语义。
重构前后全量测试必须 0 FAILED。

#### 必须完成的重构项

**1. 常量集中管理**
- `EXPORT_FORMAT_SUPPORTED` 只含 `generic`，其他格式常量单独定义但不出现在校验逻辑中
- 税率常量只在 `invoice_utils.py` 中引用
- 业务代码无魔术数字

**2. 函数长度与复杂度检查**
- 所有函数 ≤ 50 行，圈复杂度 < 10，超出者必须拆分

**3. 独立函数可调用性验证**
- `backend.core.invoice_utils.generate_invoice_no`
- `backend.core.invoice_utils.calculate_invoice_amount`
- `backend.core.invoice_utils.validate_invoice_amount`
- `backend.core.invoice_utils.validate_invoice_transition`
- `backend.core.export_utils.generate_export_batch_id`
- `backend.core.export_utils.calculate_accounting_period`
- `backend.core.export_utils.map_to_finance_format`
- `backend.core.reconciliation_utils.generate_reconciliation_report`
- `backend.core.reconciliation_utils.sync_reconciliation_status`

**4. 事务一致性验证**
以下操作必须单一事务，失败全部回滚：
- 发票创建（编号生成 + 金额校验 + 记录写入）
- 发票状态流转（状态更新 + 时间戳写入）
- 导出批次创建（export_batches 写入 + finance_records 标记 + 文件保存）
- 对账同步（批量更新 reconciliation_status）

**5. 日志覆盖验证**
以下位置均已写入 RotatingFileHandler：
- 发票金额超限校验失败
- 发票非法状态流转
- 导出文件创建失败
- 导出记录标记失败
- 对账报表生成失败
- 对账同步事务失败

**6. 最终全量回归**

```bash
pytest tests/ -v --tb=short
# 要求：0 FAILED
# 将完整输出写入 PROGRESS.md
```

---

## 四、完成标准

以下全部满足时，在 `PROGRESS.md` 写入"v1.8 执行完成"并记录时间：

- [ ] 簇 A ~ F 全部状态为 ✅
- [ ] `pytest tests/ -v` 结果：0 FAILED，输出已记录在 `PROGRESS.md`
- [ ] `backend/core/constants.py` 已追加 v1.8 常量
- [ ] `EXPORT_FORMAT_SUPPORTED` 只含 `generic`
- [ ] 发票编号唯一且格式正确
- [ ] 发票累计金额不超合同金额（cancelled 不计入）
- [ ] `verified / cancelled` 发票不可删除
- [ ] 导出批次可追溯（batch_id 唯一，file_path 可为 NULL）
- [ ] 对账第一期期初余额为 0，后续期间 = 上期期末
- [ ] cancelled 发票不计入本期开票统计
- [ ] `invoices.status` 与 `reconciliation_status` 独立流转，不互相驱动
- [ ] `exports/` 目录存在且有导出文件
- [ ] `logs/` 目录本次执行产生了日志文件
- [ ] 所有接口字段名、错误文案、HTTP 状态码与本文档约定一致

---

## 附录 A：与代理记账协作流程

```
1. 月末在本系统导出数据（通用 Excel 格式）
2. 将导出文件发送给代理记账会计
3. 会计在专业财务软件中按账套格式手动调整并导入，生成凭证
4. 会计完成报税后反馈确认
5. 本系统执行 POST /finance/reconciliation/sync 标记对应期间已对账
```

---

## 附录 B：财务软件专属格式（可选扩展，本版本不实现）

> 以下格式仅供参考。实际适配须先确认代理记账公司的软件版本和账套配置（科目编码因账套而异）。
> 本版本 `map_to_finance_format` 对非 generic 格式抛出 `NotImplementedError`。
> 后续版本可按需扩展，每种格式单独实现并补充对应测试。

**金蝶参考字段**（需客户提供科目代码）：
```
凭证字 | 凭证号 | 日期 | 摘要 | 科目代码 | 借方金额 | 贷方金额 | 核算项目
```

**用友参考字段**（需客户提供科目编码）：
```
制单日期 | 凭证类别 | 凭证号 | 摘要 | 科目编码 | 借方金额 | 贷方金额 | 辅助核算
```

**畅捷通参考字段**：
```
日期 | 凭证号 | 摘要 | 科目名称 | 借方 | 贷方 | 往来单位
```

---

## 附录 C：导出文件命名规范

```
格式：{export_type}_{target_format}_{batch_id}.xlsx
示例：
  contracts_generic_EXP_20240115_143052_ABC123.xlsx
  payments_generic_EXP_20240115_150231_DEF456.xlsx
  invoices_generic_EXP_20240115_160345_GHI789.xlsx
```

---

## 附录 D：会计期间自动计算规则

```python
# 会计期间 = 交易/签订/开票日期所属自然月
# 2024-01-15 → 2024-01
# 2024-02-28 → 2024-02
# 2024-12-31 → 2024-12

# 导出时选择会计期间：筛选该月的数据
# 导出时选择日期范围：自动计算并标记各条记录的会计期间
```
