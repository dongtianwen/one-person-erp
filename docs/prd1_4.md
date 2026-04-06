执行时不得跳步；每完成一个簇，必须先更新 PROGRESS.md，再进行下一簇；若任一验证失败，立即停止并写入失败记录。
```markdown
# 数标云管 v1.4 — Claude Code 执行指令

## 前置检查（任意一项失败则停止，将失败原因写入 PROGRESS.md 后退出）

```bash
# 1. 确认 v1.0 ~ v1.3 全量测试通过
pytest tests/ -v --tb=short
# 要求：0 FAILED，若有 FAILED 则停止，将失败用例列表写入 PROGRESS.md 后退出

# 2. 通过 PRAGMA table_info 确认以下字段实际存在于数据库（不得依赖 ORM 模型文件）：
#
# finance_records 表（v1.3 新增字段应已存在）：
#   outsource_name, has_invoice, tax_treatment,
#   invoice_direction, invoice_type, tax_rate, tax_amount
#
# contracts 表（v1.3 新增字段应已存在）：
#   expected_payment_date, payment_stage_note
#
# 3. 确认 logs/ 目录存在且 RotatingFileHandler 配置正确（10MB/文件，保留 30 个）
# 4. 确认 .env 文件存在且 SECRET_KEY 已配置
```

前置检查全部通过后，将以下内容写入项目根目录 `PROGRESS.md`，然后开始执行：

```markdown
# v1.4 执行进度

## 状态：执行中
## 开始时间：[自动填写当前时间]

| 簇 | 名称 | 状态 | 完成时间 | 通过测试数 |
|----|------|------|----------|------------|
| A | 数据库迁移 | ⏳ | - | - |
| B | FR-401 项目利润核算——后端 | ⏳ | - | - |
| C | FR-402 客户生命周期价值——后端 | ⏳ | - | - |
| D | FR-403 数据导出——后端 | ⏳ | - | - |
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

## 全局精度与边界约定（所有代码必须严格遵守）

```python
# 必须定义在 backend/core/constants.py，追加到已有常量后，禁止修改已有常量
PROFIT_DECIMAL_PLACES = 2          # 利润率精度，保留 2 位小数
EXPORT_MAX_ROWS_PER_SHEET = 10000  # 单 Sheet 最大导出行数
EXPORT_DATE_FORMAT = "%Y-%m-%d"    # 导出文件中的日期格式

# ── 项目利润核算精确定义 ──────────────────────────────────────────

# 项目收入：
#   finance_records 中满足以下全部条件的记录金额之和：
#     record_type = INCOME
#     status = CONFIRMED
#     related_contract_id 对应的合同关联到该项目
#   不得统计未关联到该项目合同的收入记录

# 项目成本：
#   finance_records 中满足以下全部条件的记录金额之和：
#     record_type = EXPENSE
#     status = CONFIRMED
#     related_project_id = 该项目 ID（v1.4 新增字段）

# 项目利润：round(项目收入 - 项目成本, 2)
# 利润率：
#   项目收入 > 0 时：round(项目利润 / 项目收入 * 100, 2)，单位 %
#   项目收入 = 0 时：返回 null，不得除以零

# ── 客户生命周期价值精确定义 ──────────────────────────────────────

# 历史合同总额：该客户所有合同（不限状态）的 amount 字段之和
# 历史实收金额：
#   finance_records 中满足以下全部条件的记录金额之和：
#     record_type = INCOME
#     status = CONFIRMED
#     related_contract_id 对应的合同的 customer_id = 该客户 ID
# 合作项目数：该客户关联的项目总数（不限项目状态）
# 平均项目金额：
#   合作项目数 > 0 时：round(历史合同总额 / 合作项目数, 2)
#   合作项目数 = 0 时：返回 null
# 首次合作日期：该客户所有合同中最早的 sign_date（sign_date 为 NULL 的合同不纳入）
# 最近合作日期：该客户所有合同中最新的 sign_date（sign_date 为 NULL 的合同不纳入）

# ── 导出文件命名规则 ──────────────────────────────────────────────

# 文件名格式：{模块名}_{年份}_{月份或季度}.{扩展名}
# 示例：
#   月度财务报表：finance_report_2026_04.xlsx / finance_report_2026_04.pdf
#   客户列表：customers_2026_04.xlsx
#   增值税台账：tax_ledger_2026_Q1.xlsx
# 时间戳取生成时刻，不使用用户传入值

# ── 空值策略 ─────────────────────────────────────────────────────

# 利润率为 null 时，接口返回 null，前端展示"—"，不显示 0% 或报错
# 首次/最近合作日期无数据时，接口返回 null，前端展示"—"
# 导出内容为空时，生成包含表头的空文件，HTTP 200，不报错
```

---

## 执行清单（按顺序执行，前一簇全量回归通过才能进入下一簇）

---

### 簇 A：数据库迁移

**目标**：新增 `related_project_id` 字段到 `finance_records` 表，建立索引。

**步骤 1**：迁移前记录快照

通过 `PRAGMA table_info('finance_records')` 确认当前字段列表，记录：
- `finance_records` 当前总行数
- 随机抽取 5 条记录，保存 `id` 及所有已有字段值

**步骤 2**：创建并执行迁移脚本 `backend/migrations/v1_4_migrate.py`

```sql
-- finance_records 表新增字段
ALTER TABLE finance_records ADD COLUMN related_project_id INTEGER NULL
    REFERENCES projects(id) ON DELETE SET NULL;

-- 建立索引
CREATE INDEX IF NOT EXISTS idx_finance_records_related_project_id
    ON finance_records(related_project_id);
```

**步骤 3**：迁移后执行以下五项验证，任意一项失败则停止并写入 PROGRESS.md

- ✅ `finance_records` 总行数与迁移前一致
- ✅ 抽样 5 条记录，所有原有字段值与快照完全一致
- ✅ `related_project_id` 新字段默认值均为 NULL（通过查询验证）
- ✅ 索引 `idx_finance_records_related_project_id` 存在（通过 `PRAGMA index_list` 验证）
- ✅ 外键约束正确（通过 `PRAGMA foreign_key_list('finance_records')` 验证）

**步骤 4**：创建测试文件 `tests/test_migration_v14.py`

```python
# 测试用例清单（对应需求 NFR-401）：
# test_index_finance_records_related_project_id_exists → NFR-401
# test_finance_records_related_project_id_default_null → NFR-401
# test_finance_records_total_count_unchanged → NFR-401
# test_finance_records_existing_fields_unchanged → NFR-401
# test_related_project_id_foreign_key_constraint → NFR-401（关联不存在的项目返回错误）
# test_related_project_id_set_null_on_project_delete → NFR-401（项目删除后字段置 NULL）
```

**步骤 5**：运行全量测试

```bash
pytest tests/ -v --tb=short
# 要求：0 FAILED
```

更新 `PROGRESS.md`：簇 A 状态改为 ✅，填写完成时间和通过测试数，继续执行簇 B。

---

### 簇 B：FR-401 项目利润核算——后端

**目标**：在 finance_records 支持关联项目，实现项目利润核算接口。

**步骤 1**：更新 finance_records 创建/更新接口

在 POST 创建接口和 PUT/PATCH 更新接口中支持 `related_project_id` 字段：
- `related_project_id` 为选填字段，传入时验证对应项目 ID 存在，不存在返回 HTTP 422
- `related_project_id` 可传 null 以清空关联

**步骤 2**：实现项目利润核算核心函数

提取为独立函数，放在 `backend/core/profit_utils.py`，可被测试直接调用：

```python
def calculate_project_income(project_id: int, db) -> Decimal:
    """
    项目收入 = finance_records 中满足以下全部条件的金额之和：
      record_type = INCOME
      status = CONFIRMED
      related_contract_id 对应合同的 project_id = 该项目 ID
    无符合记录时返回 Decimal("0.00")
    """

def calculate_project_cost(project_id: int, db) -> Decimal:
    """
    项目成本 = finance_records 中满足以下全部条件的金额之和：
      record_type = EXPENSE
      status = CONFIRMED
      related_project_id = 该项目 ID
    无符合记录时返回 Decimal("0.00")
    """

def calculate_project_profit(project_id: int, db) -> dict:
    """
    返回：
      income: Decimal（项目收入）
      cost: Decimal（项目成本）
      profit: Decimal（利润 = 收入 - 成本）
      profit_margin: Decimal | None（利润率 %，收入为 0 时返回 None）
    所有金额 round(x, 2)
    """
```

**步骤 3**：实现项目利润接口

```
GET /api/v1/projects/{project_id}/profit

返回结构（字段名严格遵守）：
{
  "project_id": 1,
  "project_name": "xxx",
  "income": 50000.00,
  "cost": 8000.00,
  "profit": 42000.00,
  "profit_margin": 84.00,
  "currency": "CNY"
}

特殊情况：
- income = 0 时：profit_margin 返回 null，不返回 0 或报错
- project_id 不存在时：HTTP 404
```

**步骤 4**：实现项目列表利润汇总接口（扩展已有项目列表接口）

在 `GET /api/v1/projects` 响应的每条项目记录中追加以下字段：
```json
{
  "profit": 42000.00,
  "profit_margin": 84.00
}
```
- 利润字段为实时计算，不存储到数据库
- 列表接口性能要求：100 个项目的利润汇总计算响应时间 < 1 秒

**创建测试文件** `tests/test_project_profit.py`：

```python
# 测试用例清单（对应需求 FR-401）：
# test_project_income_from_confirmed_contract_income → FR-401
# test_project_income_excludes_pending_records → FR-401
# test_project_income_excludes_unrelated_contracts → FR-401
# test_project_cost_from_related_project_id → FR-401
# test_project_cost_excludes_unrelated_expenses → FR-401
# test_project_profit_calculation → FR-401
# test_project_profit_margin_correct → FR-401
# test_project_profit_margin_null_when_income_zero → FR-401（收入为 0 返回 null）
# test_project_profit_all_zero_when_no_records → FR-401
# test_project_profit_api_structure_exact_match → FR-401
# test_project_not_found_returns_404 → FR-401
# test_related_project_id_valid_project_accepted → FR-401
# test_related_project_id_invalid_project_returns_422 → FR-401
# test_related_project_id_null_clears_association → FR-401
# test_project_list_includes_profit_fields → FR-401
```

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 C。

---

### 簇 C：FR-402 客户生命周期价值——后端

**目标**：实现客户生命周期价值汇总接口。

**核心函数**（提取为独立函数，放在 `backend/core/customer_utils.py`）：

```python
def calculate_customer_lifetime_value(customer_id: int, db) -> dict:
    """
    返回：
      total_contract_amount: Decimal（历史合同总额，不限合同状态）
      total_received_amount: Decimal（历史实收金额，已确认收入）
      project_count: int（合作项目数，不限项目状态）
      avg_project_amount: Decimal | None（平均项目金额，项目数为 0 时返回 None）
      first_cooperation_date: date | None（最早合同 sign_date，无数据返回 None）
      last_cooperation_date: date | None（最新合同 sign_date，无数据返回 None）
    所有金额 round(x, 2)
    """
```

**实现客户生命周期价值接口**：

```
GET /api/v1/customers/{customer_id}/lifetime-value

返回结构（字段名严格遵守）：
{
  "customer_id": 1,
  "customer_name": "xxx",
  "total_contract_amount": 200000.00,
  "total_received_amount": 180000.00,
  "project_count": 5,
  "avg_project_amount": 40000.00,
  "first_cooperation_date": "2024-01-15",
  "last_cooperation_date": "2026-03-20",
  "currency": "CNY"
}

特殊情况：
- project_count = 0 时：avg_project_amount 返回 null
- 无合同数据时：total_contract_amount = 0.00，first/last_cooperation_date = null
- customer_id 不存在时：HTTP 404
```

**在客户详情接口中追加字段**：

在 `GET /api/v1/customers/{customer_id}` 响应中追加 `lifetime_value` 对象，结构与上方接口一致（复用 `calculate_customer_lifetime_value` 函数，不重复实现逻辑）。

**创建测试文件** `tests/test_customer_ltv.py`：

```python
# 测试用例清单（对应需求 FR-402）：
# test_total_contract_amount_includes_all_statuses → FR-402
# test_total_received_amount_confirmed_income_only → FR-402
# test_total_received_amount_only_from_customer_contracts → FR-402
# test_project_count_includes_all_statuses → FR-402
# test_avg_project_amount_correct → FR-402
# test_avg_project_amount_null_when_no_projects → FR-402
# test_first_cooperation_date_earliest_sign_date → FR-402
# test_last_cooperation_date_latest_sign_date → FR-402
# test_cooperation_dates_exclude_null_sign_date → FR-402
# test_all_zero_when_no_contracts → FR-402
# test_ltv_api_structure_exact_match → FR-402
# test_customer_not_found_returns_404 → FR-402
# test_customer_detail_includes_lifetime_value → FR-402（详情接口包含 ltv 字段）
```

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 D。

---

### 簇 D：FR-403 数据导出——后端

**目标**：实现五类数据的 Excel 和 PDF 导出接口。

**依赖库**（若引入新依赖，必须在 requirements.txt 注释说明用途）：
- Excel 导出：`openpyxl`（轻量，无需 LibreOffice）
- PDF 导出：`reportlab` 或 `weasyprint`（选择时优先考虑中文字体支持，注释说明选型理由）

**导出接口规范**：

```
POST /api/v1/export/{export_type}

export_type 枚举（严格限制，不得自行扩展）：
  finance_report    → 月度财务报表
  customers         → 客户列表
  projects          → 项目列表（含利润数据）
  contracts         → 合同列表
  tax_ledger        → 增值税发票台账（按季度）

请求体：
{
  "format": "xlsx" | "pdf",
  "year": 2026,
  "month": 4,       // finance_report / customers / projects / contracts 使用
  "quarter": 1      // tax_ledger 使用，与 month 互斥
}

响应：
  成功：HTTP 200，Content-Type 对应文件类型，Content-Disposition 含文件名
  参数错误：HTTP 422，说明缺少哪个参数
  数据为空：HTTP 200，返回含表头的空文件，不报错
  导出失败：HTTP 500，错误写入日志，响应体含友好错误提示
```

**各导出类型的列定义（严格遵守，不得自行增减列）**：

**finance_report（月度财务报表）**：

Sheet 1 - 收支明细：
```
日期 | 类型(收入/支出) | 分类 | 金额 | 资金来源 | 关联合同 | 发票号码 | 状态 | 备注
```

Sheet 2 - 分类汇总：
```
分类 | 收入合计 | 支出合计 | 净额
```

Sheet 3 - 资金来源汇总：
```
资金来源 | 支出合计 | 未结清笔数 | 未结清金额
```

**customers（客户列表）**：
```
客户名称 | 联系人 | 电话 | 公司名称 | 状态 | 来源渠道 | 合作项目数 |
历史合同总额 | 历史实收金额 | 首次合作日期 | 最近合作日期 | 创建日期
```

**projects（项目列表）**：
```
项目名称 | 关联客户 | 项目状态 | 预算金额 | 项目收入 | 项目成本 |
项目利润 | 利润率(%) | 开始日期 | 结束日期 | 进度(%)
```

**contracts（合同列表）**：
```
合同编号 | 合同标题 | 关联客户 | 关联项目 | 合同金额 | 已收金额 |
应收账款 | 合同状态 | 签署日期 | 生效日期 | 到期日期
```

**tax_ledger（增值税发票台账）**：
```
日期 | 发票号码 | 发票方向(销项/进项) | 发票类型 | 金额 | 税率 | 税额 | 关联合同 | 备注
```
底部汇总行：销项税合计 | 进项税合计（仅专用发票）| 应纳税额

**核心导出函数**（提取为独立函数，放在 `backend/core/export_utils.py`）：

```python
def generate_excel(export_type: str, data: dict, year: int, month: int = None, quarter: int = None) -> bytes:
    """生成 Excel 文件，返回 bytes。数据为空时生成含表头的空文件。"""

def generate_pdf(export_type: str, data: dict, year: int, month: int = None, quarter: int = None) -> bytes:
    """生成 PDF 文件，返回 bytes。必须正确渲染中文字体。数据为空时生成含标题的空文件。"""

def get_export_filename(export_type: str, format: str, year: int, month: int = None, quarter: int = None) -> str:
    """
    生成文件名，格式：{模块名}_{年份}_{月份或季度}.{扩展名}
    示例：finance_report_2026_04.xlsx / tax_ledger_2026_Q1.pdf
    """
```

**创建测试文件** `tests/test_export.py`：

```python
# 测试用例清单（对应需求 FR-403）：
# test_export_finance_report_xlsx_success → FR-403
# test_export_finance_report_pdf_success → FR-403
# test_export_finance_report_empty_data_returns_file_with_headers → FR-403
# test_export_customers_xlsx_columns_match_spec → FR-403
# test_export_projects_xlsx_includes_profit_columns → FR-403
# test_export_contracts_xlsx_includes_receivable → FR-403
# test_export_tax_ledger_xlsx_includes_summary_row → FR-403
# test_export_tax_ledger_requires_quarter_not_month → FR-403
# test_export_invalid_format_returns_422 → FR-403
# test_export_invalid_export_type_returns_422 → FR-403
# test_export_missing_year_returns_422 → FR-403
# test_export_filename_format_correct → FR-403
# test_export_excel_chinese_content_readable → FR-403（验证中文内容可读，不是乱码）
# test_export_pdf_chinese_content_no_tofu → FR-403（验证 PDF 中文不显示方块）
# test_export_failure_writes_to_log → FR-403
# test_generate_excel_empty_data_returns_bytes_with_headers → FR-403（独立函数测试）
# test_get_export_filename_monthly → FR-403（独立函数测试）
# test_get_export_filename_quarterly → FR-403（独立函数测试）
```

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 E。

---

### 簇 E：前端联调

**目标**：实现项目利润、客户价值、数据导出三个模块的前端展示。

**约束**：所有展示组件在接口返回 null 时必须展示"—"，不得显示 0、null 字符串或报错。

---

**项目详情页——利润面板（FR-401）**

```
实现要求：
- 项目详情页新增"利润分析"卡片，展示：
  项目收入 / 项目成本 / 项目利润 / 利润率
- 利润率为 null 时显示"—"（无收入数据）
- 利润为负数时，数值标红显示

可观察验收行为：
A. 有收入和成本数据 → 四个指标正确展示，利润率有百分号
B. 收入为 0 → 利润率显示"—"，不显示 0% 或报错
C. 利润为负 → 数值标红
D. 接口失败 → 卡片显示"数据加载失败，请刷新"，不影响项目详情其他内容
```

**项目列表页——利润列（FR-401）**

```
可观察验收行为：
A. 项目列表新增"利润"和"利润率"两列
B. 利润率为 null 时显示"—"
C. 利润为负时标红
D. 列表可按利润率排序（升序/降序）
```

**财务收支录入页——关联项目字段（FR-401）**

```
实现要求：
- 支出类型记录新增"关联项目"字段（下拉选择，选填）
- 收入类型记录不展示此字段

可观察验收行为：
A. 支出类型 → "关联项目"下拉出现，显示项目列表
B. 切换为收入类型 → "关联项目"字段消失，值清空，payload 中不含此字段
C. 选填，不选时可正常提交
D. 选择不存在的项目 ID → 前端下拉不允许，后端 422 兜底
```

**客户详情页——生命周期价值面板（FR-402）**

```
实现要求：
- 客户详情页新增"客户价值"面板，展示：
  历史合同总额 / 历史实收金额 / 合作项目数 /
  平均项目金额 / 首次合作日期 / 最近合作日期

可观察验收行为：
A. 有完整数据 → 六个指标全部正确展示
B. 合作项目数为 0 → 平均项目金额显示"—"
C. 无合同数据 → 金额显示 0.00，日期显示"—"
D. 接口失败 → 面板显示"数据加载失败，请刷新"，不影响客户详情其他内容
```

**数据导出入口（FR-403）**

```
实现要求：
- 在系统顶部导航栏或设置页新增"数据导出"入口
- 导出页面包含以下配置项：
  导出类型（下拉：月度财务报表 / 客户列表 / 项目列表 / 合同列表 / 增值税台账）
  导出格式（单选：Excel / PDF）
  时间范围（月度类型显示年份+月份选择；增值税台账显示年份+季度选择）
  导出按钮
- 点击导出按钮后：显示 loading 状态，文件生成后浏览器自动下载，loading 消失
- 导出失败时：显示错误提示，不下载空文件

可观察验收行为：
A. 选增值税台账 → 时间范围切换为年份+季度选择，月份选择消失
B. 选其他类型 → 时间范围显示年份+月份选择，季度选择消失
C. 点击导出 → 出现 loading 状态
D. 导出成功 → 浏览器触发文件下载，文件名符合命名规范
E. 导出失败 → 显示"导出失败，请重试"，不下载文件
F. Network 面板确认：请求为 POST，Content-Type 为 application/json
```

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 F。

---

### 簇 F：全局重构

**目标**：在全量测试通过的前提下优化代码结构。

**核心约束（必须遵守，违反则撤回该重构项）**：

```
重构不得改变任何接口的：
- 返回字段名（包括大小写和下划线）
- 错误信息文案
- HTTP 状态码
- 校验触发时机
- 业务计算语义（利润率公式、LTV 计算逻辑、导出列定义）

重构前后全量测试必须 0 FAILED。
```

**必须完成的重构项（逐项执行，每项后运行全量测试）**：

**1. 常量集中管理**

确认 `backend/core/constants.py` 包含 v1.4 新增常量，业务代码中无以下魔术数字：
- `10000`（单 Sheet 最大行数）
- `"%Y-%m-%d"`（日期格式字符串）
- `2`（精度位数，复用已有 `DECIMAL_PLACES`）

**2. 函数长度与复杂度检查**

所有函数 ≤ 50 行，圈复杂度 < 10。超出者必须拆分，拆分后重跑全量测试。

**3. 独立函数可调用性验证**

以下函数必须可在测试中直接 import 调用（不依赖启动 FastAPI 应用）：
- `backend.core.profit_utils.calculate_project_income`
- `backend.core.profit_utils.calculate_project_cost`
- `backend.core.profit_utils.calculate_project_profit`
- `backend.core.customer_utils.calculate_customer_lifetime_value`
- `backend.core.export_utils.generate_excel`
- `backend.core.export_utils.generate_pdf`
- `backend.core.export_utils.get_export_filename`

**4. 重复逻辑合并检查**

检查以下两处是否复用同一函数，不得各自实现：
- `GET /api/v1/projects/{id}/profit` 与项目列表利润字段，必须复用 `calculate_project_profit`
- `GET /api/v1/customers/{id}/lifetime-value` 与客户详情 `lifetime_value` 字段，必须复用 `calculate_customer_lifetime_value`

**5. 日志覆盖验证**

检查以下位置均已写入 RotatingFileHandler，每条日志必须包含：操作类型 / 涉及表名 / 业务主键（如有）/ 失败原因 / 时间戳：
- `POST /api/v1/export/{export_type}` 导出失败
- `generate_excel` 异常
- `generate_pdf` 异常
- `finance_records` 写入 `related_project_id` 异常

**6. PDF 中文字体验证**

人工确认 PDF 导出中包含中文的字段（如客户名称、项目名称）可正常渲染，不显示方块（tofu）或乱码。若存在问题，在此步骤修复，修复后重跑全量测试。

**7. 最终全量回归**

```bash
pytest tests/ -v --tb=short
# 要求：0 FAILED
# 将完整输出（含所有测试用例名称和结果）写入 PROGRESS.md
```

---

## 完成标准

以下全部满足时，在 `PROGRESS.md` 写入"v1.4 执行完成"并记录时间：

- [ ] 簇 A ~ F 全部状态为 ✅
- [ ] `pytest tests/ -v` 结果：0 FAILED，输出已记录在 `PROGRESS.md`
- [ ] `backend/core/constants.py` 已追加 v1.4 常量，无魔术数字
- [ ] `backend/core/profit_utils.py`、`backend/core/customer_utils.py`、`backend/core/export_utils.py` 存在，所有核心函数可独立调用
- [ ] PDF 导出中文渲染正常（无方块、无乱码）
- [ ] `logs/` 目录本次执行产生了日志文件
- [ ] `requirements.txt` 已更新，新增依赖注释说明用途
- [ ] 所有接口字段名、错误文案、HTTP 状态码与本文档约定完全一致
```