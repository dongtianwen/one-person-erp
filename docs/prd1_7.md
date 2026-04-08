# 数标云管 v1.7 — Claude Code 执行指令（项目执行控制模块，修正版 R2）

## 项目目标

在已完成的 v1.0 ~ v1.6 代码库基础上，新增项目执行控制能力：
**变更冻结机制 / 里程碑收款绑定 / 项目关闭强制条件 / WIP 看板 / 工时偏差记录**

本版本不做：自动报价推荐、组件沉淀库、WIP 硬性拦截、AI 自动定价。

---

## 零、关键语义边界定义（实施前必读，禁止跳过）

### 0.1 requirement_changes 与 change_orders 的职责边界

这两张表在本系统中同时存在，职责必须严格区分，禁止混用：

| 表 | 职责 | 触发时机 | 是否对外 |
|----|------|----------|----------|
| `requirement_changes` | 需求字段的内部历史快照（字段级变更记录） | 每次修改需求记录时自动写入 | 否，内部审计用 |
| `change_orders` | 正式变更申请，包含额外工时与费用，需客户确认 | 项目需求冻结后，新增/修改需求的唯一入口 | 是，对客计费依据 |

**规则**：
- 需求冻结前，需求修改只写 `requirement_changes`（历史快照），不创建 `change_orders`
- 需求冻结后，任何需求变动必须先创建 `change_orders`（status=pending），客户 confirmed 后才允许落库，同时仍写 `requirement_changes` 快照
- 禁止在 `change_orders` 之外对冻结后的需求做直接字段更新

### 0.2 final_acceptance_passed 的判定来源

项目关闭条件中的"最终验收通过"定义如下，不得自行解释：

```python
# 判定规则（唯一来源：acceptances 表）
# 1. 查询 acceptances 表中 project_id = 当前项目 且 acceptance_type = 'final' 的记录
# 2. 取 created_at 最新的一条
# 3. 该记录的 status = 'passed' 则判定通过
# 4. 若不存在任何 final 类型的验收记录，则判定为未通过
# 5. 禁止用里程碑状态或交付物状态代替此判定
```

### 0.3 WIP 限制的性质声明

**WIP 只是运营提示，不参与任何状态流转校验。**
任何业务接口（创建项目、启动里程碑、转合同等）均不得因 WIP 超限而拒绝请求。
`WIP_DISPLAY_LIMIT` 常量仅供前端看板展示使用，禁止在后端校验逻辑中引用。

### 0.4 工时偏差阈值的前后端同源规则

前端判断是否需要填写偏差备注，必须以接口返回的 `deviation_exceeds_threshold` 字段为准，
禁止前端自行用 20% 硬编码计算。后端是唯一的阈值判断来源。

---

## 一、前置检查（任意一项失败则停止，将失败原因写入 PROGRESS.md 后退出）

```bash
# 1. 确认 v1.0 ~ v1.6 全量测试通过
pytest tests/ -v --tb=short
# 要求：0 FAILED

# 2. 通过 PRAGMA table_info 确认以下表实际存在（不得依赖 ORM 模型）
#   customers / projects / contracts / finance_records / milestones / tasks
#   requirements / requirement_changes / acceptances / deliverables
#   releases / change_orders / maintenance_periods
#   quotations / quotation_items / quotation_changes

# 3. 确认 logs/ 目录存在且 RotatingFileHandler 配置正确（10MB/文件，保留 30 个）
# 4. 确认 .env 文件存在且 SECRET_KEY 已配置
```

> Chrome DevTools MCP 环境检查已移至【附录 A】，不作为主流程前置门槛。

前置检查全部通过后，将以下内容写入项目根目录 `PROGRESS.md`，然后开始执行：

```markdown
# v1.7 执行进度

## 状态：执行中
## 开始时间：[自动填写当前时间]

| 簇 | 名称 | 状态 | 完成时间 | 通过测试数 |
|----|------|------|----------|------------|
| A | 数据库迁移 | ⏳ | - | - |
| B | 变更冻结机制——后端 | ⏳ | - | - |
| C | 里程碑收款绑定——后端 | ⏳ | - | - |
| D | 项目关闭强制条件——后端 | ⏳ | - | - |
| E | 前端联调 | ⏳ | - | - |
| F | 工时偏差记录 | ⏳ | - | - |
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

## 二、全局精度与边界约定

```python
# 必须追加到 backend/core/constants.py，禁止修改已有常量

# 项目执行控制
WIP_DISPLAY_LIMIT = 2                       # 看板警戒线（展示用，禁止在后端校验中引用）
WORK_HOUR_DEVIATION_THRESHOLD = 0.20        # 工时偏差阈值，后端唯一判断来源

# 变更控制
CHANGE_ORDER_STATUS_WHITELIST = ["pending", "confirmed", "rejected", "cancelled"]

# 精确定义：
# 1. 报价确认（quotation.status = accepted）后，该项目需求自动冻结
# 2. 冻结后需求变动唯一入口：change_orders（status=pending），confirmed 后落库
# 3. requirement_changes 始终记录字段级快照（冻结前后均写）
# 4. confirmed 的变更单才允许关联里程碑或进入开发
# 5. pending/confirmed/rejected/cancelled 均为终态（confirmed 除外的三个不可再流转）
# 6. 里程碑 payment_status 白名单：unpaid / invoiced / received
# 7. 项目关闭条件全部满足才允许执行关闭，见零章 0.2
# 8. WIP_DISPLAY_LIMIT 仅供前端看板使用，不参与任何接口校验
# 9. 工时偏差判断由后端计算并通过 deviation_exceeds_threshold 字段返回前端
```

---

## 三、执行清单

---

### 簇 A：数据库迁移

**目标**：扩展 change_orders、milestones、projects 表字段，新增 work_hour_logs 表，建立索引。

#### 步骤 1：迁移前记录快照

通过 `PRAGMA table_info` 和查询记录行数，记录：
- `change_orders` 总行数及现有字段列表
- `milestones` 总行数及现有字段列表
- `projects` 总行数
- 随机抽样各表 3 条记录，保存 `id` 及所有已有字段值

#### 步骤 2：创建并执行迁移脚本 `backend/migrations/v1_7_migrate.py`

```python
# SQLite 不支持 ADD COLUMN IF NOT EXISTS
# 迁移脚本必须用 PRAGMA table_info 检查每个字段是否存在
# 不存在才执行 ALTER TABLE，已存在则跳过并记录日志
# 禁止因字段已存在而报错中止
```

```sql
-- 扩展 change_orders 表
ALTER TABLE change_orders ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'pending';
ALTER TABLE change_orders ADD COLUMN extra_days INTEGER NULL;
ALTER TABLE change_orders ADD COLUMN extra_amount DECIMAL(12,2) NULL;
ALTER TABLE change_orders ADD COLUMN client_confirmed_at TIMESTAMP NULL;
ALTER TABLE change_orders ADD COLUMN client_rejected_at TIMESTAMP NULL;
ALTER TABLE change_orders ADD COLUMN rejection_reason TEXT NULL;

-- 扩展 milestones 表
ALTER TABLE milestones ADD COLUMN payment_amount DECIMAL(12,2) NULL;
ALTER TABLE milestones ADD COLUMN payment_due_date DATE NULL;
ALTER TABLE milestones ADD COLUMN payment_received_at TIMESTAMP NULL;
ALTER TABLE milestones ADD COLUMN payment_status VARCHAR(20) NOT NULL DEFAULT 'unpaid';

-- 扩展 projects 表
ALTER TABLE projects ADD COLUMN close_checklist TEXT NULL;
-- JSON 格式：{"all_milestones_completed": false, "final_acceptance_passed": false,
--             "payment_cleared": false, "deliverables_archived": false}
ALTER TABLE projects ADD COLUMN closed_at TIMESTAMP NULL;
ALTER TABLE projects ADD COLUMN estimated_hours INTEGER NULL;
ALTER TABLE projects ADD COLUMN actual_hours INTEGER NULL;

-- 新增工时偏差日志表
CREATE TABLE IF NOT EXISTS work_hour_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    log_date DATE NOT NULL,
    hours_spent DECIMAL(6,2) NOT NULL,
    task_description TEXT NOT NULL,
    deviation_note TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_change_orders_status ON change_orders(status);
CREATE INDEX IF NOT EXISTS idx_milestones_payment_status ON milestones(payment_status);
CREATE INDEX IF NOT EXISTS idx_work_hour_logs_project_id ON work_hour_logs(project_id);
CREATE INDEX IF NOT EXISTS idx_work_hour_logs_log_date ON work_hour_logs(log_date);
```

#### 步骤 3：迁移后验证

任意一项失败则停止并写入 `PROGRESS.md`：
- `work_hour_logs` 表存在
- `change_orders` 新增字段存在
- `milestones` 新增字段存在
- `projects` 新增字段存在
- 所有新增索引存在
- 原有表行数与快照一致，抽样字段值一致

#### 步骤 4：创建测试文件 `tests/test_migration_v17.py`

```python
# test_work_hour_logs_table_exists → NFR-701
# test_change_orders_new_columns_exist → NFR-701
# test_milestones_new_columns_exist → NFR-701
# test_projects_new_columns_exist → NFR-701
# test_all_new_indexes_exist → NFR-701
# test_existing_row_counts_unchanged → NFR-701
# test_existing_records_fields_unchanged → NFR-701
# test_change_order_status_default_pending → NFR-701
# test_milestone_payment_status_default_unpaid → NFR-701
```

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 B。

---

### 簇 B：变更冻结机制——后端

**目标**：报价确认后需求冻结，所有变更必须经 change_orders 流转且客户 confirmed 后才允许落库。

#### 新增枚举

追加到 `backend/models/enums.py`，不修改已有枚举：

```python
class ChangeOrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
```

#### 接口规范

```http
POST   /api/v1/projects/{project_id}/change-orders
GET    /api/v1/projects/{project_id}/change-orders
GET    /api/v1/change-orders/{co_id}
PATCH  /api/v1/change-orders/{co_id}/confirm
PATCH  /api/v1/change-orders/{co_id}/reject
PATCH  /api/v1/change-orders/{co_id}/cancel
```

#### 核心规则

- 项目关联的 quotation.status = accepted 后，该项目进入需求冻结状态
- 冻结状态下，直接修改需求的接口返回 HTTP 409："需求已冻结，请通过变更单提交"
- 新建变更单默认 `pending`
- `confirmed` 的变更单才允许关联里程碑或标记为已纳入开发
- 变更单同时触发 `requirement_changes` 写入快照（见零章 0.1）
- `extra_amount` 允许为 0，但必须显式传入，不得省略
- 状态流转：`pending` → `confirmed / rejected / cancelled`；其余三个为终态

#### 核心函数签名（`backend/core/change_order_utils.py`）

```python
def is_project_requirements_frozen(db, project_id: int) -> bool:
    """项目关联报价单 status = accepted 时返回 True"""

def validate_change_order_transition(current: str, target: str) -> bool:
    """校验状态流转是否合法"""

def confirm_change_order(db, co_id: int) -> dict:
    """客户确认变更，写入 client_confirmed_at，同时写 requirement_changes 快照，原子事务"""

def reject_change_order(db, co_id: int, reason: str) -> dict:
    """客户拒绝，写入 client_rejected_at + rejection_reason，原子事务"""
```

#### 创建测试文件 `tests/test_change_freeze.py`

```python
# test_requirements_not_frozen_before_quote_accepted → FR-701
# test_requirements_frozen_after_quote_accepted → FR-701
# test_direct_requirement_edit_blocked_when_frozen → FR-701
# test_create_change_order_success → FR-701
# test_change_order_default_status_pending → FR-701
# test_confirm_change_order_success → FR-701
# test_confirm_writes_requirement_changes_snapshot → FR-701
# test_reject_change_order_success → FR-701
# test_cancel_change_order_success → FR-701
# test_confirmed_change_order_cannot_transition → FR-701
# test_rejected_change_order_cannot_transition → FR-701
# test_extra_amount_zero_allowed → FR-701
# test_extra_amount_negative_rejected → FR-701
# test_change_order_not_found_returns_404 → FR-701
```

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 C。

---

### 簇 C：里程碑收款绑定——后端

**目标**：里程碑与收款节点强绑定，completed 里程碑才能触发收款流转。

#### 接口规范

```http
PATCH  /api/v1/milestones/{milestone_id}/payment-invoiced
PATCH  /api/v1/milestones/{milestone_id}/payment-received
GET    /api/v1/projects/{project_id}/payment-summary
```

#### 核心规则

- `payment_status` 流转：`unpaid` → `invoiced`（需里程碑 status=completed）→ `received`（终态）
- 非 completed 里程碑触发 `invoiced` 返回 HTTP 409
- `payment_received_at` 在 `received` 时写入
- `GET /payment-summary` 响应结构：
  ```json
  {
    "total_contract_amount": 0.00,
    "total_milestone_amount": 0.00,
    "received_amount": 0.00,
    "invoiced_amount": 0.00,
    "unpaid_amount": 0.00,
    "overdue_milestones": []
  }
  ```
- `overdue_milestones`：payment_due_date < 今日 且 payment_status != received

#### 核心函数签名（`backend/core/milestone_payment_utils.py`）

```python
def validate_payment_transition(milestone, target_status: str) -> bool:
    """校验里程碑是否满足收款状态流转条件"""

def get_project_payment_summary(db, project_id: int) -> dict:
    """计算项目收款汇总，金额精确到 2 位小数"""

def get_overdue_payment_milestones(db, project_id: int) -> list:
    """返回逾期未收款里程碑列表"""
```

#### 创建测试文件 `tests/test_milestone_payment.py`

```python
# test_milestone_payment_amount_set_on_create → FR-702
# test_payment_invoiced_requires_milestone_completed → FR-702
# test_payment_invoiced_blocked_if_milestone_not_done → FR-702
# test_payment_received_after_invoiced → FR-702
# test_payment_received_is_terminal → FR-702
# test_payment_summary_amounts_correct → FR-702
# test_payment_summary_overdue_milestones_returned → FR-702
# test_payment_amount_zero_allowed → FR-702
# test_payment_amount_negative_rejected → FR-702
# test_milestone_not_found_returns_404 → FR-702
```

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 D。

---

### 簇 D：项目关闭强制条件——后端

**目标**：项目 status 变更为 completed 必须满足关闭条件白名单。

#### 关闭条件白名单（全部满足才允许关闭）

```python
PROJECT_CLOSE_CHECKLIST = {
    "all_milestones_completed": "所有里程碑 status = completed",
    "final_acceptance_passed": "acceptances 表中该项目 acceptance_type=final 的最新记录 status=passed（见零章 0.2）",
    "payment_cleared": "所有里程碑 payment_status=received 或 payment_amount=0",
    "deliverables_archived": "至少存在一条 deliverable 记录",
}
# 任何一项未满足，均返回 HTTP 409，响应体列出未满足项
```

#### 接口规范

```http
POST  /api/v1/projects/{project_id}/close
GET   /api/v1/projects/{project_id}/close-check
```

#### 核心规则

- `close-check` 只读，返回每项条件满足状态
- `close` 接口执行前必须重新校验所有条件，不信任前端状态
- 关闭成功后：status → `completed`，写入 `closed_at` 和 `close_checklist` JSON 快照
- 已关闭项目不允许再次关闭（HTTP 409）
- 已关闭项目核心字段不允许修改

#### 核心函数签名（`backend/core/project_close_utils.py`）

```python
def check_project_close_conditions(db, project_id: int) -> dict:
    """
    返回：
    {
      "all_milestones_completed": bool,
      "final_acceptance_passed": bool,   # 严格按零章 0.2 判定
      "payment_cleared": bool,
      "deliverables_archived": bool,
      "can_close": bool,
      "blocking_items": ["..."]
    }
    """

def close_project(db, project_id: int) -> dict:
    """原子事务：校验条件 → 更新状态 → 写入快照，失败全部回滚"""
```

#### 创建测试文件 `tests/test_project_close.py`

```python
# test_close_check_returns_all_conditions → FR-703
# test_close_blocked_if_milestone_not_completed → FR-703
# test_close_blocked_if_no_final_acceptance → FR-703
# test_close_blocked_if_final_acceptance_not_passed → FR-703
# test_close_uses_latest_final_acceptance_record → FR-703   ← 锁定"最新一条"语义
# test_close_blocked_if_payment_not_cleared → FR-703
# test_close_blocked_if_no_deliverables → FR-703
# test_close_success_when_all_conditions_met → FR-703
# test_close_writes_closed_at → FR-703
# test_close_writes_checklist_snapshot → FR-703
# test_already_closed_project_returns_409 → FR-703
# test_closed_project_core_fields_immutable → FR-703
# test_close_transaction_atomic → FR-703
# test_project_not_found_returns_404 → FR-703
```

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 E。

---

### 簇 E：前端联调

**目标**：实现 v1.7 前端页面，Chrome DevTools MCP 调试为可选增强项（见附录 A）。

#### 前端页面要求

**1. 变更单管理**
- 项目详情页新增"变更单"Tab
- 展示变更单列表（状态 / 描述 / 额外费用 / 操作按钮）
- 需求冻结状态下，需求编辑入口显示"已冻结"标识，禁用直接编辑
- 变更单操作按钮根据当前状态动态显示（pending 才显示确认/拒绝/撤回）

**2. 里程碑收款看板**
- 里程碑列表新增收款状态列（未付款 / 已开票 / 已到账）
- 一键标记开票 / 到账（需里程碑已完成才可操作，否则显示禁用并提示）
- 收款汇总区块：合同金额 / 已到账 / 待收款 / 逾期未收款
- 逾期未收款里程碑红色高亮

**3. 项目关闭入口**
- 项目详情页新增"关闭项目"按钮（仅 active 状态显示）
- 点击展示关闭条件检查结果（绿色=满足 / 红色=未满足）
- 所有条件满足时才激活"确认关闭"按钮
- 关闭后项目卡片显示"已完成"标识，不展示操作按钮

**4. WIP 看板（展示，不拦截）**
- 首页看板新增"当前进行中项目"区块，展示所有 status=active 项目卡片
- 超过 `WIP_DISPLAY_LIMIT` 时显示黄色警告："当前有 N 个项目并行，注意精力分配"
- **前端不得因 WIP 超限禁用任何提交按钮或拦截任何操作**

**5. 工时记录入口**
- 项目详情页新增"工时记录"Tab
- 支持按日期记录工时（日期 / 小时数 / 任务描述 / 偏差备注）
- 展示预计总工时 vs 实际已记录工时
- **偏差备注是否必填，以接口返回的 `deviation_exceeds_threshold` 字段为准，前端不得自行计算阈值**

#### 前端验收标准

- 需求冻结时直接编辑入口不可用
- 非 completed 里程碑的开票按钮禁用并有提示
- 项目关闭条件不满足时"确认关闭"按钮 disabled
- WIP 超限只显示警告，不阻断任何操作
- deviation_exceeds_threshold=true 时偏差备注字段前端拦截（必填校验）
- 无数据时不白屏，数值类展示 0 或 0.00
- 动态字段隐藏时旧值必须从 payload 中移除

> Chrome DevTools MCP 自动化调试为可选增强，见附录 A。

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 F。

---

### 簇 F：工时偏差记录

**目标**：记录每日工时，后端统一计算偏差，超阈值时强制填写原因。

#### 接口规范

```http
POST  /api/v1/projects/{project_id}/work-hours
GET   /api/v1/projects/{project_id}/work-hours
GET   /api/v1/projects/{project_id}/work-hours/summary
PATCH /api/v1/projects/{project_id}/estimated-hours
```

#### 核心规则

- `hours_spent` 必须 > 0 且 ≤ 24
- `GET /work-hours/summary` 响应：
  ```json
  {
    "estimated_hours": 0,
    "actual_hours_total": 0.0,
    "deviation_rate": 0.0,
    "deviation_exceeds_threshold": false,
    "logs": []
  }
  ```
- `deviation_rate = (actual - estimated) / estimated`，仅在 estimated_hours > 0 时计算，否则为 null
- `deviation_exceeds_threshold`：后端用 `WORK_HOUR_DEVIATION_THRESHOLD` 计算，结果通过此字段返回
- 后端：deviation_exceeds_threshold=true 且 deviation_note 为空时，返回 HTTP 422
- **前端不得自行用 20% 计算，必须消费 deviation_exceeds_threshold**

#### 创建测试文件 `tests/test_work_hours.py`

```python
# test_create_work_hour_log_success → FR-704
# test_hours_spent_must_be_positive → FR-704
# test_hours_spent_exceeds_24_rejected → FR-704
# test_work_hour_summary_correct → FR-704
# test_deviation_rate_calculated_correctly → FR-704
# test_deviation_exceeds_threshold_true_when_over_limit → FR-704
# test_deviation_exceeds_threshold_false_when_under_limit → FR-704
# test_deviation_note_required_when_exceeds_threshold → FR-704
# test_deviation_rate_null_when_no_estimated_hours → FR-704
# test_work_hours_list_ordered_by_date_desc → FR-704
# test_update_estimated_hours_success → FR-704
```

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 G。

---

### 簇 G：全局重构

**目标**：在全量测试通过的前提下优化代码结构。

#### 核心约束

重构不得改变任何接口的返回字段名、错误信息文案、HTTP 状态码、校验触发时机、业务规则语义。
重构前后全量测试必须 0 FAILED。

#### 必须完成的重构项

**1. 常量集中管理**
- `backend/core/constants.py` 包含本版本新增常量
- `WIP_DISPLAY_LIMIT` 只在前端看板相关代码中引用，禁止出现在后端校验逻辑
- `WORK_HOUR_DEVIATION_THRESHOLD` 只在 `work_hour_utils.py` 中引用一处

**2. 函数长度与复杂度检查**
- 所有函数 ≤ 50 行，圈复杂度 < 10，超出者必须拆分

**3. 独立函数可调用性验证**
- `backend.core.change_order_utils.is_project_requirements_frozen`
- `backend.core.change_order_utils.validate_change_order_transition`
- `backend.core.change_order_utils.confirm_change_order`
- `backend.core.milestone_payment_utils.validate_payment_transition`
- `backend.core.milestone_payment_utils.get_project_payment_summary`
- `backend.core.project_close_utils.check_project_close_conditions`
- `backend.core.project_close_utils.close_project`

**4. 事务一致性验证**
以下操作必须单一事务，失败全部回滚：
- 变更单状态确认（含 requirement_changes 快照写入）
- 里程碑收款状态流转
- 项目关闭（条件校验 + 状态更新 + 快照写入）

**5. 日志覆盖验证**
以下位置均已写入 RotatingFileHandler：
- 变更单状态流转失败
- 里程碑收款流转失败
- 项目关闭条件不满足
- 项目关闭事务失败
- 工时记录校验失败

**6. 最终全量回归**

```bash
pytest tests/ -v --tb=short
# 要求：0 FAILED
# 将完整输出写入 PROGRESS.md
```

---

## 四、完成标准

以下全部满足时，在 `PROGRESS.md` 写入"v1.7 执行完成"并记录时间：

- [ ] 簇 A ~ G 全部状态为 ✅
- [ ] `pytest tests/ -v` 结果：0 FAILED，输出已记录在 `PROGRESS.md`
- [ ] `backend/core/constants.py` 已追加 v1.7 常量
- [ ] `WIP_DISPLAY_LIMIT` 未出现在任何后端校验逻辑中
- [ ] `WORK_HOUR_DEVIATION_THRESHOLD` 只在 work_hour_utils.py 中引用一处
- [ ] 变更冻结在报价 accepted 后自动生效
- [ ] 冻结后变更同时写 change_orders 和 requirement_changes
- [ ] 里程碑收款状态流转符合约束
- [ ] final_acceptance_passed 判定严格来自 acceptances 表最新 final 记录
- [ ] WIP 看板超限显示警告，不拦截任何操作
- [ ] 工时偏差阈值由后端统一计算并通过接口字段返回
- [ ] `logs/` 目录本次执行产生了日志文件
- [ ] 所有接口字段名、错误文案、HTTP 状态码与本文档约定一致

---

## 附录 A：Chrome DevTools MCP 调试（可选增强）

> **性质**：可选，不作为任何簇的通过门槛。若环境不支持，标注 `[MCP-SKIP]` 后继续执行，不影响主流程。

### 环境准备

```bash
# 以调试模式启动 Chrome
google-chrome --remote-debugging-port=9222 --no-first-run --no-default-browser-check &
# 或 Chromium：
chromium-browser --remote-debugging-port=9222 &

# 验证端口
curl http://localhost:9222/json/version
```

### MCP 连接配置（Claude Code 侧）

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["@modelcontextprotocol/server-puppeteer"],
      "env": {
        "PUPPETEER_WS_ENDPOINT": "ws://localhost:9222"
      }
    }
  }
}
```

> 若使用 Playwright 版本，将 WS 地址替换为对应 CDP endpoint。

### 调试流程（簇 E 完成后执行）

```
1. 导航到目标页面
2. 检查 console Error 级别日志
3. 检查 Network 面板 API 请求状态码
4. 对关键交互执行操作并捕获响应
5. 将调试结果（截图 + console 日志摘要）写入 PROGRESS.md
```

### 建议验证点

| 功能 | 检查点 |
|------|--------|
| 变更单 Tab | 无 console Error；冻结时编辑按钮不可点击 |
| 里程碑收款 | 非 completed 里程碑点击开票显示正确错误 |
| 项目关闭 | 条件不满足时确认关闭按钮 disabled |
| WIP 看板 | 超限时黄色警告可见，无操作被拦截 |
| 工时记录 | deviation_exceeds_threshold=true 时偏差备注变必填 |
