````markdown
# 数标云管 v1.6 — Claude Code 执行指令（报价模块，修正版）

## 项目目标
在已完成的 v1.0 ~ v1.5 代码库基础上，新增“报价单 / 报价预览 / 报价转合同 / 报价过期”能力，服务于一人软件公司的软件开发业务。

本版本只做“报价模块”，不扩展客户线索、审批流、电子签名、外部市场价格抓取、AI 自动定价等功能。

---

## 一、前置检查（任意一项失败则停止，将失败原因写入 PROGRESS.md 后退出）

```bash
# 1. 确认 v1.0 ~ v1.5 全量测试通过
pytest tests/ -v --tb=short
# 要求：0 FAILED，若有 FAILED 则停止，将失败用例列表写入 PROGRESS.md 后退出

# 2. 通过 PRAGMA table_info / sqlite_master 确认以下表实际存在于数据库（不得依赖 ORM 模型文件）
#   customers / projects / contracts / finance_records / milestones / tasks
#   以及 v1.5 新增表 requirements / requirement_changes / acceptances / deliverables / releases / change_orders / maintenance_periods

# 3. 确认 logs/ 目录存在且 RotatingFileHandler 配置正确（10MB/文件，保留 30 个）
# 4. 确认 .env 文件存在且 SECRET_KEY 已配置
````

前置检查全部通过后，将以下内容写入项目根目录 `PROGRESS.md`，然后开始执行：

```markdown
# v1.6 执行进度

## 状态：执行中
## 开始时间：[自动填写当前时间]

| 簇 | 名称 | 状态 | 完成时间 | 通过测试数 |
|----|------|------|----------|------------|
| A | 数据库迁移 | ⏳ | - | - |
| B | 报价单模块——后端 | ⏳ | - | - |
| C | 报价评估器——后端 | ⏳ | - | - |
| D | 报价转合同 + 过期处理——后端 | ⏳ | - | - |
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

## 二、全局精度与边界约定（所有代码必须严格遵守）

```python
# 必须追加到 backend/core/constants.py，禁止修改已有常量

QUOTE_NO_PREFIX = "BJ"              # 报价单编号前缀
QUOTE_VALID_DAYS_DEFAULT = 30       # 默认报价有效期天数
QUOTE_DECIMAL_PLACES = 2            # 金额精度
QUOTE_ESTIMATE_MAX_DAYS = 365       # 单个报价允许的最大预计工期

# 事件驱动逾期检查扩展窗口
QUOTE_EXPIRE_WINDOW_DAYS = 0        # 报价过期按 valid_until < 今日 判定，不额外窗口

# 精确定义：
# 1. 报价单编号格式：BJ-YYYYMMDD-序号（当日从 001 起）
# 2. 报价有效期：默认创建日 + 30 天，可手动修改
# 3. 报价金额相关数值统一四舍五入到 2 位小数
# 4. 报价状态白名单：
#    draft / sent / accepted / rejected / expired / cancelled
# 5. expired 状态仅由事件驱动逾期检查设置，不接受接口直接传入
# 6. accepted / rejected / expired / cancelled 状态的报价单，不允许删除
# 7. accepted 后报价单核心内容不可改，只允许修改 notes
# 8. 前端切换字段隐藏时，其旧值必须从 payload 中移除
# 9. 创建与更新接口：所有校验规则必须同时在 POST 和 PUT/PATCH 中生效
# 10. 不引入外部市场价格接口，不做联网自动定价
```

---

## 三、报价金额计算规则（必须写死，不得留歧义）

```python
labor_amount = round(estimate_days * daily_rate, 2) if daily_rate is not None else 0.00
base_amount = round(labor_amount + direct_cost, 2)  # direct_cost 为空按 0 处理
buffer_amount = round(base_amount * risk_buffer_rate, 2)
subtotal_amount = round(base_amount + buffer_amount, 2)
tax_amount = round(subtotal_amount * tax_rate, 2)
total_amount = round(subtotal_amount - discount_amount + tax_amount, 2)

# 所有金额不得为负数
```

---

## 四、执行清单（按顺序执行，前一簇全量回归通过才能进入下一簇）

---

### 簇 A：数据库迁移

**目标**：创建报价单相关新表、补齐合同反查字段、建立索引和外键约束。

#### 步骤 1：迁移前记录快照

通过 `PRAGMA table_info` 和查询记录行数，记录：

* `customers` 总行数
* `projects` 总行数
* `contracts` 总行数
* 随机抽样各表 3 条记录，保存 `id` 及所有已有字段值

#### 步骤 2：创建并执行迁移脚本 `backend/migrations/v1_6_migrate.py`

```sql
CREATE TABLE IF NOT EXISTS quotations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quote_no VARCHAR(30) NOT NULL UNIQUE,
    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    project_id INTEGER NULL REFERENCES projects(id) ON DELETE SET NULL,
    title VARCHAR(200) NOT NULL,
    requirement_summary TEXT NOT NULL,
    estimate_days INTEGER NOT NULL,
    estimate_hours INTEGER NULL,
    daily_rate DECIMAL(12,2) NULL,
    direct_cost DECIMAL(12,2) NULL,
    risk_buffer_rate DECIMAL(5,2) NOT NULL DEFAULT 0,
    discount_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
    tax_rate DECIMAL(5,4) NOT NULL DEFAULT 0,
    subtotal_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
    tax_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
    total_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
    valid_until DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    notes TEXT NULL,
    sent_at TIMESTAMP NULL,
    accepted_at TIMESTAMP NULL,
    rejected_at TIMESTAMP NULL,
    expired_at TIMESTAMP NULL,
    converted_contract_id INTEGER NULL REFERENCES contracts(id) ON DELETE SET NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS quotation_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quotation_id INTEGER NOT NULL REFERENCES quotations(id) ON DELETE CASCADE,
    item_name VARCHAR(200) NOT NULL,
    item_type VARCHAR(20) NOT NULL,
    quantity DECIMAL(12,2) NOT NULL DEFAULT 1,
    unit_price DECIMAL(12,2) NOT NULL DEFAULT 0,
    amount DECIMAL(12,2) NOT NULL DEFAULT 0,
    notes TEXT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS quotation_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    quotation_id INTEGER NOT NULL REFERENCES quotations(id) ON DELETE CASCADE,
    change_type VARCHAR(20) NOT NULL,
    before_snapshot TEXT NOT NULL,
    after_snapshot TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 若 contracts 表无 quotation_id，则迁移补充
ALTER TABLE contracts ADD COLUMN quotation_id INTEGER NULL REFERENCES quotations(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_quotations_customer_id ON quotations(customer_id);
CREATE INDEX IF NOT EXISTS idx_quotations_project_id ON quotations(project_id);
CREATE INDEX IF NOT EXISTS idx_quotations_status ON quotations(status);
CREATE INDEX IF NOT EXISTS idx_quotations_valid_until ON quotations(valid_until);
CREATE INDEX IF NOT EXISTS idx_quotation_items_quotation_id ON quotation_items(quotation_id);
CREATE INDEX IF NOT EXISTS idx_quotation_items_sort_order ON quotation_items(sort_order);
CREATE INDEX IF NOT EXISTS idx_quotation_changes_quotation_id ON quotation_changes(quotation_id);
CREATE INDEX IF NOT EXISTS idx_contracts_quotation_id ON contracts(quotation_id);
```

#### 步骤 3：迁移后验证

任意一项失败则停止并写入 `PROGRESS.md`：

* `quotations / quotation_items / quotation_changes` 三张新表全部存在
* 所有索引存在
* `customers / projects / contracts` 原有表总行数与迁移前一致
* 抽样记录原有字段值与快照完全一致
* `contracts.quotation_id` 字段存在

#### 步骤 4：创建测试文件 `tests/test_migration_v16.py`

```python
# 测试用例清单（对应需求 NFR-601）：
# test_all_new_tables_exist → NFR-601
# test_all_new_indexes_exist → NFR-601
# test_customers_count_unchanged → NFR-601
# test_projects_count_unchanged → NFR-601
# test_contracts_count_unchanged → NFR-601
# test_existing_records_fields_unchanged → NFR-601
# test_foreign_key_quotation_customer_exists → NFR-601
# test_foreign_key_quotation_project_exists → NFR-601
# test_foreign_key_quotation_item_cascade_delete → NFR-601
# test_quote_no_unique_constraint → NFR-601
# test_contracts_quotation_id_exists → NFR-601
```

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 B。

---

### 簇 B：报价单模块——后端

**目标**：实现报价单 CRUD、编号生成、状态流转和基础字段校验。

#### 新增枚举

追加到 `backend/models/enums.py`，不修改已有枚举：

```python
class QuoteStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class QuoteItemType(str, Enum):
    LABOR = "labor"
    DESIGN = "design"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    OUTSOURCE = "outsource"
    OTHER = "other"

class QuoteChangeType(str, Enum):
    FIELD_UPDATE = "field_update"
    STATUS_CHANGE = "status_change"
    CONVERTED = "converted"
```

#### 状态流转白名单

```python
QUOTE_VALID_TRANSITIONS = {
    "draft": ["sent", "accepted", "cancelled"],
    "sent": ["accepted", "rejected", "cancelled"],
    "accepted": [],
    "rejected": [],
    "expired": [],
    "cancelled": [],
}
# expired 仅由事件驱动逾期检查设置，不接受接口直接传入
```

#### 接口规范

```http
POST /api/v1/quotes
GET /api/v1/quotes
GET /api/v1/quotes/{quote_id}
PUT /api/v1/quotes/{quote_id}
PATCH /api/v1/quotes/{quote_id}
DELETE /api/v1/quotes/{quote_id}
POST /api/v1/quotes/{quote_id}/send
POST /api/v1/quotes/{quote_id}/accept
POST /api/v1/quotes/{quote_id}/reject
POST /api/v1/quotes/{quote_id}/cancel
GET /api/v1/quotes/{quote_id}/items
POST /api/v1/quotes/{quote_id}/items
POST /api/v1/quotes/preview
```

#### 核心规则

* 报价单编号由后端自动生成，格式为 `BJ-YYYYMMDD-序号`
* `quote_no` 必须唯一
* 报价单可关联客户，项目为可选
* 创建默认状态为 `draft`
* `draft` 可直接跳到 `accepted`
* `sent` 可流转到 `accepted / rejected / cancelled`
* `accepted / rejected / expired / cancelled` 状态的报价单，不允许删除
* `accepted` 后报价单核心内容不可改，只允许修改 `notes`
* `cancelled` 后不允许再流转
* `send` 操作会写入 `sent_at`
* `accept` 操作会写入 `accepted_at`
* `reject` 操作会写入 `rejected_at`
* `expired` 仅由事件驱动写入 `expired_at`

#### 事件驱动逾期检查扩展

在现有事件驱动逾期检查函数中追加：

```python
# quotations 中 status = sent 且 valid_until < 今日 的记录
# 批量更新 status 为 expired，写入 expired_at
# 同时在 quotation_changes 中记录状态变更日志
```

#### 创建测试文件 `tests/test_quotes.py`

```python
# 测试用例清单（对应需求 FR-601）：
# test_create_quote_auto_generates_no → FR-601
# test_quote_no_format_correct → FR-601
# test_quote_no_increments_same_day → FR-601
# test_create_quote_default_status_draft → FR-601
# test_get_quotes_ordered_by_created_desc → FR-601
# test_get_quote_detail_success → FR-601
# test_update_draft_quote_success → FR-601
# test_update_accepted_quote_core_fields_rejected → FR-601
# test_update_accepted_quote_notes_allowed → FR-601
# test_delete_draft_quote_success → FR-601
# test_delete_sent_quote_rejected → FR-601
# test_delete_accepted_quote_rejected → FR-601
# test_project_not_found_returns_404 → FR-601
# test_customer_not_found_returns_404 → FR-601
# test_status_transition_illegal_returns_422 → FR-601
# test_expired_quote_cannot_be_sent → FR-601
# test_cancelled_quote_cannot_be_accepted → FR-601
# test_event_driven_expires_sent_quote → FR-601
# test_event_driven_writes_expired_at → FR-601
```

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 C。

---

### 簇 C：报价评估器——后端

**目标**：实现报价金额计算逻辑、报价预览接口和报价评估能力。

#### 核心函数

提取到 `backend/core/quote_utils.py`：

```python
def generate_quote_no(db) -> str:
    """
    格式：BJ-YYYYMMDD-序号（当日从 001 起）
    必须在创建事务中执行，防止并发重复。
    """

def calculate_quote_amount(
    estimate_days: int,
    daily_rate: Decimal | None,
    direct_cost: Decimal | None,
    risk_buffer_rate: Decimal,
    discount_amount: Decimal,
    tax_rate: Decimal,
) -> dict:
    """
    返回：
    {
      "labor_amount": ...,
      "base_amount": ...,
      "buffer_amount": ...,
      "subtotal_amount": ...,
      "tax_amount": ...,
      "total_amount": ...
    }

    规则：
    - labor_amount = estimate_days × daily_rate（daily_rate 为空时为 0）
    - base_amount = labor_amount + direct_cost
    - buffer_amount = round(base_amount × risk_buffer_rate, 2)
    - subtotal_amount = round(base_amount + buffer_amount, 2)
    - tax_amount = round(subtotal_amount × tax_rate, 2)
    - total_amount = round(subtotal_amount - discount_amount + tax_amount, 2)
    - 所有金额四舍五入到 2 位小数
    - 不允许出现负数结果
    """

def build_quote_preview(db, payload) -> dict:
    """
    根据输入的需求摘要、预计工期、日费率、风险系数等，返回报价预览。
    不保存数据库，仅用于报价草稿预览。
    """

def can_edit_quote(quote) -> bool:
    """
    accepted 之后，仅允许修改 notes。
    其他状态返回 True。
    """

def can_delete_quote(quote) -> bool:
    """
    accepted / rejected / expired / cancelled 不可删除。
    """
```

#### 业务校验规则

* `estimate_days` 必填，且必须大于 0
* `estimate_days` 不得超过 `QUOTE_ESTIMATE_MAX_DAYS`
* `daily_rate / direct_cost / discount_amount / tax_rate / risk_buffer_rate` 必须非负
* `accepted` 报价单的核心字段不可再改
* 空值字段在数据库中存 NULL，禁止空字符串
* 报价预览与正式保存必须使用同一套计算逻辑

#### 创建测试文件 `tests/test_quote_utils.py`

```python
# 测试用例清单（对应需求 FR-602）：
# test_calculate_quote_amount_basic → FR-602
# test_calculate_quote_amount_without_daily_rate → FR-602
# test_calculate_quote_amount_without_direct_cost → FR-602
# test_calculate_quote_amount_precision_two_decimal → FR-602
# test_calculate_quote_amount_no_negative_total → FR-602
# test_build_quote_preview_success → FR-602
# test_build_quote_preview_matches_save_logic → FR-602
# test_estimate_days_must_be_positive → FR-602
# test_estimate_days_exceeds_limit_rejected → FR-602
# test_negative_amount_rejected → FR-602
```

#### 创建测试文件 `tests/test_quote_preview.py`

```python
# 测试用例清单（对应需求 FR-602）：
# test_preview_endpoint_returns_calculation_result → FR-602
# test_preview_endpoint_no_db_write → FR-602
# test_preview_endpoint_structure_matches_spec → FR-602
# test_preview_endpoint_precision_two_decimal → FR-602
# test_preview_endpoint_negative_values_rejected → FR-602
```

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 D。

---

### 簇 D：报价转合同 + 过期处理——后端

**目标**：实现报价单一键转合同，以及与合同映射、过期联动。

#### 接口规范

```http
POST /api/v1/quotes/{quote_id}/convert-to-contract
```

#### 转合同字段映射（必须写死）

```text
quotations.title              → contracts.title
quotations.customer_id         → contracts.customer_id
quotations.total_amount        → contracts.amount
quotations.requirement_summary  → contracts.notes
quotations.id                  → contracts.quotation_id
contracts.status              → 固定为 "draft"
contracts.sign_date           → NULL
```

#### 规则

* 仅 `accepted` 状态的报价单可转换
* 转换成功后创建合同草稿
* 一张报价单只能转换一次
* 转换操作必须在同一事务中完成
* 转换成功后生成一条报价转换日志到 `quotation_changes`
* 合同表必须支持 `quotation_id` 反查

#### 创建测试文件 `tests/test_quote_convert.py`

```python
# 测试用例清单（对应需求 FR-603）：
# test_convert_accepted_quote_to_contract_success → FR-603
# test_convert_only_accepted_allowed → FR-603
# test_convert_quote_only_once → FR-603
# test_convert_sets_converted_contract_id → FR-603
# test_convert_transaction_atomic → FR-603
# test_convert_logs_change_snapshot → FR-603
# test_contract_created_from_quote_fields_copied → FR-603
# test_quote_not_found_returns_404 → FR-603
# test_contract_quotation_id_set → FR-603
```

#### 创建测试文件 `tests/test_quote_changes.py`

```python
# 测试用例清单（对应需求 FR-603）：
# test_quote_changes_has_quotation_id_index → FR-603
# test_quote_changes_change_type_enum_defined → FR-603
# test_quote_changes_record_field_update_log → FR-603
# test_quote_changes_record_status_change_log → FR-603
# test_quote_changes_record_converted_log → FR-603
```

#### 事件驱动逾期检查补充

在现有事件驱动逾期检查函数中追加报价单过期逻辑：

```python
# quotations 中 status = sent 且 valid_until < 今日 的记录
# 批量更新 status 为 expired，写入 expired_at
# 同时在 quotation_changes 中记录状态变更日志
```

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 E。

---

### 簇 E：前端联调

**目标**：实现报价单页面、报价预览、报价转合同入口、过期状态展示。

#### 前端页面与交互要求

1. **客户详情页新增“报价”Tab**

   * 展示该客户所有报价单
   * 支持按状态筛选
   * 支持新建报价单

2. **报价单编辑页**

   * 表单包含：

     * 标题
     * 需求摘要
     * 预计工期（天）
     * 日费率
     * 直接成本
     * 风险缓冲率
     * 折扣金额
     * 税率
     * 有效期
     * 备注
   * 输入变化后可查看报价预览
   * 预览显示：

     * 人工成本
     * 基础金额
     * 缓冲金额
     * 小计
     * 税额
     * 总价
   * accepted 之后核心字段只读，只允许改备注

3. **报价列表页**

   * 显示报价编号、客户、标题、总价、状态、有效期
   * 过期自动标红
   * accepted / rejected / expired / cancelled 状态不可删除

4. **报价详情页**

   * 显示完整报价内容
   * 若状态为 accepted，显示“一键转合同”按钮
   * 转换后显示已关联合同编号
   * 若状态为 expired，显示“已过期”提示，不展示发送/确认按钮

5. **报价预览接口联调**

   * `POST /api/v1/quotes/preview` 用于纯计算预览
   * 不写数据库
   * 与正式保存使用同一套计算逻辑

6. **看板新增报价指标**

   * 本月发出报价数
   * 报价转化率（accepted ÷ sent × 100%）

#### 前端验收

* 动态字段隐藏时，旧值必须从 payload 中移除
* 预览为空时显示 `—`
* 无数据时不报错，不白屏
* 一键转合同按钮只在 accepted 状态显示
* expired 状态报价不可继续发起流转
* 看板报价指标在无数据时显示 0.00 或 0

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 F。

---

### 簇 F：全局重构

**目标**：在全量测试通过的前提下优化代码结构。

#### 核心约束

重构不得改变任何接口的：

* 返回字段名
* 错误信息文案
* HTTP 状态码
* 校验触发时机
* 业务规则语义

重构前后全量测试必须 0 FAILED。

#### 必须完成的重构项

1. **常量集中管理**

   * `backend/core/constants.py` 包含本版本新增常量
   * 业务代码中无魔术数字、无硬编码前缀

2. **函数长度与复杂度检查**

   * 所有函数 ≤ 50 行
   * 圈复杂度 < 10
   * 超出者必须拆分

3. **独立函数可调用性验证**
   以下函数必须可在测试中直接 import 调用：

   * `backend.core.quote_utils.generate_quote_no`
   * `backend.core.quote_utils.calculate_quote_amount`
   * `backend.core.quote_utils.build_quote_preview`
   * `backend.core.quote_utils.can_edit_quote`
   * `backend.core.quote_utils.can_delete_quote`
   * `backend.core.quote_utils.convert_quote_to_contract`

4. **事务一致性验证**

   * 创建报价单并生成编号
   * 报价接受
   * 一键转合同
     以上操作均需单一事务完成，失败全部回滚

5. **日志覆盖验证**
   检查以下位置均已写入 RotatingFileHandler：

   * 报价单创建 / 更新失败
   * 报价编号生成失败
   * 报价转换合同失败
   * 报价金额计算失败
   * 报价过期状态批处理失败

6. **最终全量回归**

```bash
pytest tests/ -v --tb=short
# 要求：0 FAILED
# 将完整输出写入 PROGRESS.md
```

---

## 五、完成标准

以下全部满足时，在 `PROGRESS.md` 写入“v1.6 执行完成”并记录时间：

* [ ] 簇 A ~ F 全部状态为 ✅
* [ ] `pytest tests/ -v` 结果：0 FAILED，输出已记录在 `PROGRESS.md`
* [ ] `backend/core/constants.py` 已追加 v1.6 常量
* [ ] 报价模块核心函数可独立调用
* [ ] 报价单编号唯一且格式正确
* [ ] 报价单可一键转合同且只允许一次
* [ ] 报价单过期状态由事件驱动自动设置
* [ ] `logs/` 目录本次执行产生了日志文件
* [ ] 所有接口字段名、错误文案、HTTP 状态码与本文档约定一致
* [ ] 账号交接清单无任何密码字段可录入（本版本不新增相关录入能力）

```

如果你要，我也可以下一步把这份再压成一版 **“更短、更像 Claude Code 直接执行的精简版”**。
```
