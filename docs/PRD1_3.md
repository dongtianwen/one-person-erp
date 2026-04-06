# 数标云管 v1.3 — Claude Code 执行指令

## 前置检查（开始执行前必须完成，任意一项失败则停止，将失败原因写入 PROGRESS.md 后退出）
```bash
# 1. 确认 v1.0 ~ v1.2 全量测试通过
pytest tests/ -v --tb=short
# 要求：0 FAILED，若有 FAILED 则停止，将失败用例列表写入 PROGRESS.md 后退出

# 2. 确认数据库结构与 v1.2 一致
# 必须通过 PRAGMA table_info 或等价 schema introspection 完成
# 不得仅依赖 ORM 模型文件（模型文件可能与实际数据库不一致）
# 必须确认以下字段实际存在于数据库中：
#
# finance_records 表：
#   id, record_type, amount, category, date, status, invoice_no,
#   funding_source, business_note, related_record_id, related_note, settlement_status
#
# contracts 表：
#   id, contract_no, title, customer_id, amount, status,
#   sign_date, effective_date, expiry_date

# 3. 确认 logs/ 目录存在且 RotatingFileHandler 配置正确（10MB/文件，保留 30 个）
# 4. 确认 .env 文件存在且 SECRET_KEY 已配置
```

前置检查全部通过后，将以下内容写入项目根目录 `PROGRESS.md`，然后开始执行：
```markdown
# v1.3 执行进度

## 状态：执行中
## 开始时间：[自动填写当前时间]

| 簇 | 名称 | 状态 | 完成时间 | 通过测试数 |
|----|------|------|----------|------------|
| A | 数据库迁移 | ⏳ | - | - |
| B | FR-302 外包协作 | ⏳ | - | - |
| C | FR-303 发票校验+税额计算 | ⏳ | - | - |
| D | FR-303 季度统计接口 | ⏳ | - | - |
| E | FR-301 现金流预测接口 | ⏳ | - | - |
| F | 前端联调 | ⏳ | - | - |
| G | 全局重构 | ⏳ | - | - |

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

## 全局精度与边界约定（所有代码必须严格遵守，不得自行解释）
```python
# 必须定义在 backend/core/constants.py，业务代码中禁止出现以下魔术数字
CASHFLOW_FORECAST_DAYS = 90          # 预测天数
CASHFLOW_WEEKS_PER_MONTH = 4.33      # 月均周数
CASHFLOW_HISTORY_MONTHS = 3          # 支出历史统计月数
DECIMAL_PLACES = 2                   # 金额精度
WEEK_START_DAY = 0                   # 0 = 周一（Python weekday()）

# ── 时间范围精确定义 ──────────────────────────────────────────────

# "未来 90 天"：
#   从 start_date 当天起，连续 90 个自然日，包含起始日（第 1 天）和第 90 日
#   示例：start_date = 2026-04-06，则范围为 2026-04-06 ~ 2026-07-04

# "最近 3 个完整自然月"：
#   不含当月，向前推 3 个完整自然月
#   示例：今天 2026-04-06，则统计范围为 2026-01-01 ~ 2026-03-31

# "周"：
#   自然周，周一为起始日（weekday() == 0），周日为结束日（weekday() == 6）

# ── 精度规则 ─────────────────────────────────────────────────────

# 所有金额字段：round(x, 2)，四舍五入到 2 位小数
# tax_amount = round(amount * tax_rate, 2)
# 周均支出 = round(月均支出 / CASHFLOW_WEEKS_PER_MONTH, 2)

# ── 空值与表单行为 ────────────────────────────────────────────────

# 非必填字段为空时存 NULL，禁止存空字符串 ""
# 前端切换财务分类时：动态字段旧值必须从表单状态和提交 payload 中完全移除
# 前端字段隐藏时：其旧值不得出现在提交的请求体中（不得依赖后端过滤兜底）

# ── 创建与更新接口的一致性要求 ───────────────────────────────────

# 所有字段校验规则（外包字段清空、发票字段清空）
# 必须同时在创建接口（POST）和更新接口（PUT/PATCH）中生效
# 不得只在创建接口实现，更新接口遗漏，导致编辑时旧值残留
```

---

## 执行清单（按顺序执行，前一簇全量回归通过才能进入下一簇）

---

### 簇 A：数据库迁移

**目标**：新增字段、建立索引、验证迁移正确性。

**步骤 1**：迁移前记录快照

通过 `PRAGMA table_info` 获取当前 `finance_records` 和 `contracts` 表实际字段列表，确认与 v1.2 预期一致。记录：
- `finance_records` 当前总行数
- `contracts` 当前总行数
- 随机抽取 5 条 `finance_records` 记录，保存 `id` 及所有已有字段值
- 随机抽取 5 条 `contracts` 记录，保存 `id` 及所有已有字段值

**步骤 2**：创建并执行迁移脚本 `backend/migrations/v1_3_migrate.py`
```sql
-- contracts 表新增字段
ALTER TABLE contracts ADD COLUMN expected_payment_date DATE NULL;
ALTER TABLE contracts ADD COLUMN payment_stage_note VARCHAR(200) NULL;

-- finance_records 表新增字段
ALTER TABLE finance_records ADD COLUMN outsource_name VARCHAR(200) NULL;
ALTER TABLE finance_records ADD COLUMN has_invoice BOOLEAN NULL;
ALTER TABLE finance_records ADD COLUMN tax_treatment VARCHAR(20) NULL;
ALTER TABLE finance_records ADD COLUMN invoice_direction VARCHAR(10) NULL;
ALTER TABLE finance_records ADD COLUMN invoice_type VARCHAR(20) NULL;
ALTER TABLE finance_records ADD COLUMN tax_rate DECIMAL(5,4) NULL;
ALTER TABLE finance_records ADD COLUMN tax_amount DECIMAL(12,2) NULL;

-- 建立索引
CREATE INDEX IF NOT EXISTS idx_contracts_expected_payment_date
    ON contracts(expected_payment_date);
CREATE INDEX IF NOT EXISTS idx_finance_records_invoice_direction
    ON finance_records(invoice_direction);
CREATE INDEX IF NOT EXISTS idx_finance_records_invoice_no
    ON finance_records(invoice_no);
```

**步骤 3**：迁移后执行以下六项验证，任意一项失败则停止并写入 PROGRESS.md

- ✅ `finance_records` 总行数与迁移前一致
- ✅ `contracts` 总行数与迁移前一致
- ✅ 抽样 5 条 `finance_records` 记录，所有原有字段值与快照完全一致
- ✅ 抽样 5 条 `contracts` 记录，所有原有字段值与快照完全一致
- ✅ 所有新增字段的默认值均为 NULL（通过查询验证，不得仅依赖 DDL 推断）：
  - `contracts`：`expected_payment_date`、`payment_stage_note`
  - `finance_records`：`outsource_name`、`has_invoice`、`tax_treatment`、`invoice_direction`、`invoice_type`、`tax_rate`、`tax_amount`
- ✅ 三个索引均存在（通过 `PRAGMA index_list('table_name')` 验证）

**步骤 4**：创建测试文件 `tests/test_migration_v13.py`
```python
# 测试用例清单：
# test_index_contracts_expected_payment_date_exists → NFR-301
# test_index_finance_records_invoice_direction_exists → NFR-301
# test_index_finance_records_invoice_no_exists → NFR-301
# test_finance_records_new_fields_all_null_by_default → NFR-302
# test_contracts_new_fields_all_null_by_default → NFR-302
# test_finance_records_total_count_unchanged → NFR-302
# test_contracts_total_count_unchanged → NFR-302
# test_finance_records_existing_fields_unchanged → NFR-302

# 约束：每个测试必须可独立运行，不依赖其他测试文件的执行顺序
```

**步骤 5**：运行全量测试
```bash
pytest tests/ -v --tb=short
# 要求：0 FAILED
```

更新 `PROGRESS.md`：簇 A 状态改为 ✅，填写完成时间和通过测试数，继续执行簇 B。

---

### 簇 B：FR-302 外包协作记录

**目标**：实现外包费用分类的字段校验逻辑，覆盖创建和更新接口。

**新增枚举值**（在现有枚举文件中追加，不修改任何已有枚举值）：
```python
# backend/models/enums.py 追加

class FinanceCategory(str, Enum):
    # ... 保留原有所有枚举值，不得修改 ...
    OUTSOURCING = "outsourcing"  # 外包费用（v1.3新增）

class TaxTreatment(str, Enum):
    INVOICED = "invoiced"        # 已取得发票
    WITHHOLDING = "withholding"  # 代扣个税
    NONE = "none"                # 无需处理
```

**后端校验规则**（必须同时在 POST 创建接口和 PUT/PATCH 更新接口中实现）：
```python
# 当 category == OUTSOURCING 时：
#   outsource_name 为 NULL → HTTP 422，{"detail": "外包费用必须填写外包方姓名"}
#   has_invoice 为 NULL → HTTP 422，{"detail": "外包费用必须填写是否取得发票"}
#   tax_treatment 为 NULL → HTTP 422，{"detail": "外包费用必须填写税务处理方式"}

# 当 category != OUTSOURCING 时：
#   三个字段（outsource_name / has_invoice / tax_treatment）：
#   无论前端传入任何值，均强制存为 NULL
#   不得保留旧值，不得透传前端传入值
#   此规则同时作用于创建接口和更新接口
```

**创建测试文件** `tests/test_outsource.py`：
```python
# 测试用例清单（对应需求 FR-302）：
# test_outsource_create_all_fields_success → FR-302
# test_outsource_create_missing_name_returns_422 → FR-302
# test_outsource_create_missing_has_invoice_returns_422 → FR-302
# test_outsource_create_missing_tax_treatment_returns_422 → FR-302
# test_outsource_error_message_contains_field_name → FR-302
# test_non_outsource_create_ignores_outsource_fields → FR-302
# test_non_outsource_create_stores_null → FR-302
# test_outsource_update_also_validates_fields → FR-302（更新接口同样校验）
# test_non_outsource_update_clears_outsource_fields → FR-302（更新接口切换分类时旧值清空）
```

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 C。

---

### 簇 C：FR-303 发票台账——字段校验 + 税额计算

**目标**：实现发票字段校验、tax_amount 自动计算，覆盖创建和更新接口。

**新增枚举值**（追加，不修改已有值）：
```python
class InvoiceDirection(str, Enum):
    OUTPUT = "output"    # 开具（销项）
    INPUT = "input"      # 取得（进项）

class InvoiceType(str, Enum):
    GENERAL = "general"          # 普通发票
    SPECIAL = "special"          # 专用发票
    ELECTRONIC = "electronic"    # 电子发票
```

**税额计算函数**（必须提取为独立函数，放在 `backend/core/finance_utils.py`）：
```python
def calculate_tax_amount(amount: Decimal, tax_rate: Decimal) -> Decimal:
    """
    计算税额，四舍五入到 2 位小数。
    tax_amount = round(amount * tax_rate, 2)
    参数和返回值均为 Decimal 类型，禁止使用 float 计算。
    """
```

**后端校验规则**（必须同时在 POST 创建接口和 PUT/PATCH 更新接口中实现）：
```python
# 当 invoice_no 不为空（非 NULL 且非空字符串）时：
#   invoice_direction 为 NULL → HTTP 422，{"detail": "填写发票号码时必须填写发票方向"}
#   invoice_type 为 NULL → HTTP 422，{"detail": "填写发票号码时必须填写发票类型"}
#   tax_rate 为 NULL → HTTP 422，{"detail": "填写发票号码时必须填写税率"}
#   tax_amount：
#     后端调用 calculate_tax_amount(amount, tax_rate) 计算后写入数据库
#     请求体中的 tax_amount 字段不得作为可写字段（Pydantic Schema 中排除此字段的写入）
#     不得采用"前端传什么先存什么，后端再覆盖"的实现方式

# 当 invoice_no 为空或 NULL 时：
#   invoice_direction / invoice_type / tax_rate / tax_amount 均强制存为 NULL
#   无论前端传入任何值，均忽略
#   此规则同时作用于创建接口和更新接口（更新时清空发票号码，四个字段同步清空）
```

**创建测试文件** `tests/test_tax_ledger.py`（本簇写前 8 个测试，季度统计测试在簇 D 追加）：
```python
# 本簇测试用例清单（对应需求 FR-303）：
# test_tax_amount_calculated_by_backend → FR-303
# test_tax_amount_frontend_value_not_accepted_in_schema → FR-303
# test_tax_amount_precision_two_decimal_places → FR-303
# test_invoice_direction_required_when_invoice_no_present → FR-303
# test_invoice_type_required_when_invoice_no_present → FR-303
# test_tax_rate_required_when_invoice_no_present → FR-303
# test_invoice_no_empty_clears_all_invoice_fields → FR-303
# test_update_clearing_invoice_no_also_clears_invoice_fields → FR-303（更新时清空联动）
```

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 D。

---

### 簇 D：FR-303 发票台账——季度统计接口

**目标**：实现 `GET /api/v1/finance/tax-summary` 接口。

**接口规格**：
GET /api/v1/finance/tax-summary?year={year}&quarter={quarter}
参数：
year: int，如 2026
quarter: int，1 ~ 4，超出范围返回 HTTP 422
季度日期范围（精确定义）：
Q1: 该年 01-01 ~ 03-31
Q2: 该年 04-01 ~ 06-30
Q3: 该年 07-01 ~ 09-30
Q4: 该年 10-01 ~ 12-31
**核心函数**（必须提取为独立函数，放在 `backend/core/finance_utils.py`，可被测试直接调用）：
```python
def get_quarter_date_range(year: int, quarter: int) -> tuple[date, date]:
    """
    返回季度起始日和结束日（均为 date 对象）。
    示例：get_quarter_date_range(2026, 1) → (date(2026,1,1), date(2026,3,31))
    """

def calculate_quarterly_tax(year: int, quarter: int, db) -> dict:
    """
    output_tax_total：
      本季度内 invoice_direction = OUTPUT 的所有记录的 tax_amount 之和
      round(sum, 2)，无数据时返回 0.00

    input_tax_total：
      本季度内 invoice_direction = INPUT 且 invoice_type = SPECIAL 的记录的 tax_amount 之和
      GENERAL 和 ELECTRONIC 类型不纳入，round(sum, 2)，无数据时返回 0.00

    tax_payable：
      round(output_tax_total - input_tax_total, 2)
    """
```

**返回结构（字段名、类型、精度严格遵守，禁止自行添加或修改字段）**：
```json
{
  "year": 2026,
  "quarter": 1,
  "output_tax_total": 3000.00,
  "input_tax_total": 500.00,
  "tax_payable": 2500.00,
  "record_count": {
    "output": 5,
    "input": 3
  }
}
```

**在 `tests/test_tax_ledger.py` 追加以下测试**：
```python
# 季度统计测试用例清单（对应需求 FR-303）：
# test_quarterly_output_tax_includes_all_output_records → FR-303
# test_quarterly_input_tax_includes_only_special_invoices → FR-303
# test_quarterly_input_tax_excludes_general_invoices → FR-303
# test_quarterly_input_tax_excludes_electronic_invoices → FR-303
# test_quarterly_tax_payable_equals_output_minus_input → FR-303
# test_quarterly_tax_payable_precision_two_decimal → FR-303
# test_quarterly_empty_quarter_returns_zero_http200 → FR-303
# test_quarterly_response_structure_exact_match → FR-303
# test_quarterly_invalid_quarter_returns_422 → FR-303
# test_get_quarter_date_range_q1 → FR-303（独立验证 Q1 边界）
# test_get_quarter_date_range_q4 → FR-303（独立验证 Q4 边界）
```

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 E。

---

### 簇 E：FR-301 现金流预测接口

**目标**：实现 `GET /api/v1/cashflow/forecast` 接口。

**合同状态白名单（严格执行，不得自行扩展）**：
```python
# 纳入现金流预测的合同状态，只有以下两个，其他状态一律不算：
CASHFLOW_CONTRACT_STATUSES = ["active", "executing"]
# 明确排除：draft, signed, completed, terminated, cancelled 等所有其他状态
```

**已确认收入的精确定义**：
```python
# 某合同的已确认收入 = finance_records 中满足以下全部条件的记录金额之和：
#   record_type = INCOME（收入类型）
#   status = CONFIRMED（已确认状态，排除 pending / cancelled 等）
#   related_contract_id = 该合同 ID（必须关联到此合同，不得统计未关联合同的收入）
# 应收账款 = 合同金额 - 已确认收入
# 若应收账款 <= 0，该合同不纳入预测（不报错，跳过）
```

**核心函数**（必须提取为独立函数，放在 `backend/core/cashflow_utils.py`，可被测试直接调用）：
```python
def get_forecast_weeks(start_date: date) -> list[dict]:
    """
    生成未来 90 天的自然周列表。
    - 从 start_date（含）起连续 90 个自然日，包含第 1 天和第 90 天
    - 按自然周（周一起始）分组
    - 最后一周不足 7 天时，week_end 取第 90 天
    - 返回：[{"week_index": 1, "week_start": date, "week_end": date}, ...]
    """

def calculate_weekly_income(weeks: list, db) -> dict:
    """
    按 expected_payment_date 将应收账款分配到对应周。
    - 只处理 contracts.status IN CASHFLOW_CONTRACT_STATUSES 的合同
    - expected_payment_date 为 NULL 的合同跳过，不报错，不影响其他合同
    - 应收账款 <= 0 的合同跳过
    - 返回：{week_index: predicted_income, ...}，未分配周的 week_index 不出现在结果中
    """

def calculate_weekly_expense(weeks: list, db) -> dict:
    """
    基于历史支出计算周均支出并平均分配到每周。
    - 统计范围：finance_records 中 record_type=EXPENSE, status=CONFIRMED
      发生日期在最近 3 个完整自然月内（不含当月）
    - 月均支出 = 3个月支出总和 ÷ 3
    - 周均支出 = round(月均支出 / CASHFLOW_WEEKS_PER_MONTH, 2)
    - 每周分配相同的周均支出
    - 无历史数据时周均支出为 0.00，不报错
    - 返回：{week_index: predicted_expense, ...}
    """
```

**返回结构（字段名、类型、精度严格遵守）**：
```json
{
  "forecast": [
    {
      "week_index": 1,
      "week_start": "2026-04-06",
      "week_end": "2026-04-12",
      "predicted_income": 10000.00,
      "predicted_expense": 2000.00,
      "predicted_net": 8000.00
    }
  ],
  "summary": {
    "total_predicted_income": 50000.00,
    "total_predicted_expense": 18000.00,
    "total_predicted_net": 32000.00
  }
}
```

**创建测试文件** `tests/test_cashflow.py`：
```python
# 测试用例清单（对应需求 FR-301）：
# test_forecast_returns_correct_week_count → FR-301（90天覆盖的周数正确）
# test_forecast_first_week_starts_on_monday → FR-301
# test_forecast_last_day_is_exactly_day_90 → FR-301
# test_forecast_includes_active_contract → FR-301
# test_forecast_includes_executing_contract → FR-301
# test_forecast_excludes_completed_contract → FR-301（completed 不纳入）
# test_forecast_excludes_draft_contract → FR-301（draft 不纳入）
# test_forecast_excludes_null_payment_date_no_error → FR-301
# test_forecast_receivable_equals_amount_minus_confirmed_income → FR-301
# test_forecast_only_counts_confirmed_income_of_same_contract → FR-301
# test_forecast_expense_from_last_3_complete_months_only → FR-301
# test_forecast_expense_zero_when_no_history_no_error → FR-301
# test_forecast_no_data_returns_90day_zeros_http200 → FR-301
# test_forecast_response_structure_exact_match → FR-301
# test_forecast_all_amounts_two_decimal_precision → FR-301
# test_forecast_summary_totals_match_weekly_sum → FR-301
# test_get_forecast_weeks_boundary → FR-301（独立验证 90 天边界）
# test_calculate_weekly_expense_formula → FR-301（独立验证周均支出公式）
```

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 F。

---

### 簇 F：前端联调

**目标**：实现三个模块的前端动态字段交互、图表和 Tab 视图。

**约束**：前端字段隐藏时，其旧值必须从 Vue 组件状态和提交 payload 中完全移除，不得依赖后端过滤兜底。

---

**财务录入页——外包字段（FR-302）**
实现要求：

分类选择"外包费用"时，展示：outsource_name / has_invoice / tax_treatment（均标注必填）
切换为其他分类时：三个字段 DOM 移除，Vue 响应式数据清空，提交 payload 中不含这三个字段
三个字段隐藏时：不参与前端表单校验

可观察验收行为：
A. 选外包费用 → 三字段出现，有必填星号
B. 不填直接提交 → 前端拦截，不发送 HTTP 请求，显示错误提示
C. 填好数据后切换其他分类 → 三字段消失
D. 再切回外包费用 → 三字段出现，值为空（不保留旧值）
E. Network 面板确认：切换分类后提交，payload 中不含 outsource_name / has_invoice / tax_treatment
**财务录入页——发票字段（FR-303）**

实现要求：

发票号码不为空时，展示：invoice_direction / invoice_type / tax_rate（均标注必填）
tax_amount：只读展示框，值从接口响应中取，提交 payload 中不包含此字段
发票号码清空时：三个字段 DOM 移除，值清空，提交 payload 中不含四个发票字段

可观察验收行为：
A. 填写发票号码 → 三字段出现，有必填星号
B. tax_amount 展示框只读，无法编辑，值与接口响应 tax_amount 一致
C. 三字段为空提交（invoice_no 有值）→ 前端拦截，不发送请求
D. 清空发票号码 → 三字段消失，值清空
E. Network 面板确认：正常提交的 payload 中不含 tax_amount 字段
F. Network 面板确认：清空发票号码后提交，payload 中不含四个发票字段

**合同编辑页（FR-301）**

可观察验收行为：
A. expected_payment_date 日期选择器：可选择日期、保存后回显、可清空
B. payment_stage_note 文本输入：可输入、保存后回显、可清空
C. 两个字段均为选填，为空时可正常保存

**看板页——现金流折线图（FR-301）**
可观察验收行为：
A. 折线图展示三条线：预测收入（蓝）/ 预测支出（红）/ 净值（绿）
B. X 轴为周序号（第1周、第2周...），Y 轴为金额（元）
C. 无合同和支出数据时：图表渲染全零曲线，不报错，不白屏，不显示 loading 无限转圈
D. 接口请求失败时：图表区域显示"数据加载失败，请刷新"，不影响看板其他组件

**财务列表页——发票台账 Tab（FR-303）**
可观察验收行为：
A. 财务列表页新增"发票台账"Tab
B. Tab 内只展示 invoice_no 不为空的记录
C. 支持按年份和季度筛选
D. 显示列：发票号码 / 发票方向 / 发票类型 / 金额 / 税率 / 税额 / 日期

**看板——季度增值税汇总卡片（FR-303）**
可观察验收行为：
A. 展示当前季度：销项税合计 / 进项税合计 / 应纳税额
B. 当前季度无数据时显示 0.00，不白屏
C. 卡片下方标注"仅供参考，不替代正式申报口径"

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 G。

---

### 簇 G：全局重构

**目标**：在全量测试通过的前提下优化代码结构。

**核心约束（必须遵守）**：
重构不得改变任何接口的：

返回字段名（包括大小写）
错误信息文案
HTTP 状态码
校验触发时机（如从创建时校验改为提交时校验）
业务计算语义（如税额计算公式、周均支出公式）

重构前后全量测试必须 0 FAILED，如重构导致测试失败，必须撤回该重构项。
**必须完成的重构项（逐项执行，每项后运行全量测试）**：

**1. 常量集中管理**

确认 `backend/core/constants.py` 包含以下全部常量，业务代码中无以下魔术数字：
- `90`（预测天数）
- `4.33`（月均周数）
- `3`（历史月数）
- `2`（精度位数）
- `["active", "executing"]`（合同状态白名单）

**2. 函数长度与复杂度检查**

所有函数 ≤ 50 行，圈复杂度 < 10。超出者必须拆分，拆分后重跑全量测试。

**3. 独立函数可调用性验证**

以下函数必须可在测试中直接 import 调用（不依赖启动 FastAPI 应用）：
- `backend.core.finance_utils.calculate_tax_amount`
- `backend.core.finance_utils.get_quarter_date_range`
- `backend.core.finance_utils.calculate_quarterly_tax`
- `backend.core.cashflow_utils.get_forecast_weeks`
- `backend.core.cashflow_utils.calculate_weekly_income`
- `backend.core.cashflow_utils.calculate_weekly_expense`

**4. 日志覆盖验证**

检查以下位置均已写入 RotatingFileHandler，每条日志必须包含：操作类型 / 涉及表名 / 业务主键（如有）/ 失败原因 / 时间戳：
- 迁移脚本执行（开始 / 完成 / 失败）
- `finance_records` 写入异常
- `contracts` 写入异常
- `GET /api/v1/cashflow/forecast` 接口异常
- `GET /api/v1/finance/tax-summary` 接口异常

**5. 最终全量回归**
```bash
pytest tests/ -v --tb=short
# 要求：0 FAILED
# 将完整输出（含所有测试用例名称和结果）写入 PROGRESS.md
```

---

## 完成标准

以下全部满足时，在 `PROGRESS.md` 写入"v1.3 执行完成"并记录时间：

- [ ] 簇 A ~ G 全部状态为 ✅
- [ ] `pytest tests/ -v` 结果：0 FAILED，输出已记录在 `PROGRESS.md`
- [ ] `backend/core/constants.py` 包含全部约定常量，业务代码无魔术数字
- [ ] `backend/core/cashflow_utils.py` 和 `backend/core/finance_utils.py` 存在，所有核心函数可独立调用
- [ ] `logs/` 目录存在且本次执行产生了日志文件
- [ ] `requirements.txt` 已更新（若有新增依赖，注释说明引入原因）
- [ ] 所有接口字段名、错误文案、HTTP 状态码与本文档约定完全一致
