已配置markdown# 数标云管 v1.5 — Claude Code 执行指令（修订版）

## 前置检查（任意一项失败则停止，将失败原因写入 PROGRESS.md 后退出）
```bash
# 1. 确认 v1.0 ~ v1.4 全量测试通过
pytest tests/ -v --tb=short
# 要求：0 FAILED，若有 FAILED 则停止，将失败用例列表写入 PROGRESS.md 后退出

# 2. 通过 PRAGMA table_info 确认以下表和字段实际存在于数据库（不得依赖 ORM 模型文件）：
#   表：projects / contracts / customers / finance_records / milestones / tasks / reminders
#   字段：finance_records.related_project_id（v1.4 新增）

# 3. 确认 logs/ 目录存在且 RotatingFileHandler 配置正确（10MB/文件，保留 30 个）
# 4. 确认 .env 文件存在且 SECRET_KEY 已配置
```

前置检查全部通过后，将以下内容写入项目根目录 `PROGRESS.md`，然后开始执行：
```markdown
# v1.5 执行进度

## 状态：执行中
## 开始时间：[自动填写当前时间]

| 簇 | 名称 | 状态 | 完成时间 | 通过测试数 |
|----|------|------|----------|------------|
| A | 数据库迁移 | ⏳ | - | - |
| B | FR-501 需求与变更管理——后端 | ⏳ | - | - |
| C | FR-502 验收管理——后端 | ⏳ | - | - |
| D | FR-503 交付物管理——后端 | ⏳ | - | - |
| E | FR-504 版本/发布记录——后端 | ⏳ | - | - |
| F | FR-505 变更单/增补单——后端 | ⏳ | - | - |
| G | FR-506 售后/维护期管理——后端 | ⏳ | - | - |
| H | 前端联调 | ⏳ | - | - |
| I | 全局重构 | ⏳ | - | - |

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

## 全局工程约束（所有簇强制遵守，不得自行解释）

排序稳定性：所有列表接口必须有明确的排序字段（不得依赖数据库默认顺序）。
空值显式返回：所有详情接口的可空字段必须显式返回 null（JSON），
不得省略字段，不得返回字符串 "null"。
禁止删除的统一规范：
DELETE 接口一律返回 HTTP 405。
不得通过其他路径（如软删除、状态变更）间接实现删除效果。
本条适用于：acceptances / deliverables / releases 三个实体。
创建与更新一致性：所有字段校验规则必须同时在 POST 创建接口
和 PUT/PATCH 更新接口中生效，不得只在创建接口实现。
空值存储：非必填字段为空时存 NULL，禁止存空字符串 ""。
前端 payload 清理：动态字段隐藏时其旧值必须从提交 payload 中移除，
不得依赖后端过滤兜底。
唯一性硬约束：所有"同项目唯一"的布尔标记字段
（requirements.is_current / releases.is_current_online）：

接口层在同一事务中切换，保证任意时刻同 project_id 下只有一条为 True
测试层必须验证切换后不存在两条同时为 True 的记录
日志层记录每次切换操作（操作类型 / project_id / 旧值 ID / 新值 ID）


职责分离：
变更单完整 CRUD 在合同详情页实现。
项目详情页仅展示该项目关联合同的变更单摘要（只读，无操作按钮）。
不得在项目详情页实现任何变更单写操作。


---

## 全局精度与边界约定
```python
# 必须追加到 backend/core/constants.py，禁止修改已有常量

REQUIREMENT_VERSION_PREFIX = "v"
REQUIREMENT_SUMMARY_MAX_LENGTH = 10000
CHANGE_ORDER_PREFIX = "BG"
MAINTENANCE_REMINDER_DAYS_BEFORE = 30
NOTES_SEPARATOR = "\n"   # notes 追加时的分隔符

# ── 变更单状态流转白名单（精确定义，不得自行扩展）────────────────
# 允许的流转路径（源状态 → 目标状态）：
# draft → sent
# draft → confirmed      （允许跳过 sent，客户口头确认场景）
# sent → confirmed
# confirmed → in_progress
# in_progress → completed
# 任何状态 → completed   （提前终止场景）
# completed → 任何状态   （禁止，返回 HTTP 422）
# 以上未列出的路径一律视为非法，返回 HTTP 422

CHANGE_ORDER_VALID_TRANSITIONS = {
    "draft": ["sent", "confirmed", "completed"],
    "sent": ["confirmed", "completed"],
    "confirmed": ["in_progress", "completed"],
    "in_progress": ["completed"],
    "completed": [],  # 空列表 = 不允许任何流转
}

# ── "当前有效版本"定义 ────────────────────────────────────────────
# 同一 project_id 下，is_current = True 的需求版本记录有且仅有一条。
# 设置新版本为当前有效时，必须在同一事务中将同项目其他版本 is_current 设为 False。
# 事务失败时全部回滚，不得出现中间状态。

# ── "当前线上版本"定义 ────────────────────────────────────────────
# 同一 project_id 下，is_current_online = True 的发布记录有且仅有一条。
# 切换当前线上版本时，必须在同一事务中将同项目其他记录 is_current_online 设为 False。
# 事务失败时全部回滚，不得出现中间状态。

# ── "实际应收合计"定义（合同维度）────────────────────────────────
# confirmed_total = 该合同下 status IN (confirmed, in_progress, completed)
#                   的变更单 amount 之和，round(sum, 2)，无符合记录时为 0.00
# actual_receivable = round(合同 amount + confirmed_total, 2)
# draft / sent 状态的变更单不纳入计算

# ── "变更单编号"生成规则 ──────────────────────────────────────────
# 格式：BG-YYYYMMDD-序号（当日从 001 起，3 位补零）
# 示例：BG-20260405-001 / BG-20260405-002
# 必须在创建事务中生成，防止并发重复

# ── notes 追加规则 ────────────────────────────────────────────────
# 追加格式：原内容 + NOTES_SEPARATOR + 新备注
# 原内容为空时：直接存入新备注，不加分隔符

# ── 密码字段检测规则（仅检测字段名，不扫描字段值）────────────────
FORBIDDEN_FIELD_PATTERNS = ["password", "pwd", "secret", "passwd", "token"]
# 检测方式：将 JSON 请求体中的所有字段名转为小写后，
# 判断是否包含上述任意字符串（子串匹配）
# 示例：{"account_password": "xxx"} → 拦截（含 "password"）
#       {"account_name": "admin@xxx.com"} → 放行
# 注意：只检测字段名，不检测字段值内容，不得做值扫描

# ── 维护期续期边界约束 ────────────────────────────────────────────
# 新记录 start_date = 原记录 end_date + 1 天（自动计算，不接受调用方传入）
# 新记录 end_date 必须由调用方明确传入，不得为空，不得早于新 start_date
# 其他字段（service_type / service_description / annual_fee）可由调用方修改
```

---

## 执行清单（按顺序执行，前一簇全量回归通过才能进入下一簇）

---

### 簇 A：数据库迁移

**目标**：创建 v1.5 全部新表，建立索引和外键约束。

**步骤 1**：迁移前记录快照

通过 `PRAGMA table_info` 确认现有表结构，记录：
- `projects` / `contracts` / `finance_records` 各自总行数
- 随机抽取各表 3 条记录，保存 `id` 及所有已有字段值

**步骤 2**：创建并执行迁移脚本 `backend/migrations/v1_5_migrate.py`
```sql
-- 需求版本表
CREATE TABLE IF NOT EXISTS requirements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    version_no VARCHAR(50) NOT NULL,
    summary TEXT NOT NULL,
    confirm_status VARCHAR(20) NOT NULL DEFAULT 'pending',
    confirmed_at TIMESTAMP NULL,
    confirm_method VARCHAR(20) NULL,
    is_current BOOLEAN NOT NULL DEFAULT FALSE,
    notes TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 变更单表（需先建，requirement_changes 有外键引用）
CREATE TABLE IF NOT EXISTS change_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_no VARCHAR(30) NOT NULL UNIQUE,
    contract_id INTEGER NOT NULL REFERENCES contracts(id) ON DELETE RESTRICT,
    requirement_change_id INTEGER NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    confirmed_at TIMESTAMP NULL,
    confirm_method VARCHAR(20) NULL,
    notes TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 需求变更记录表
CREATE TABLE IF NOT EXISTS requirement_changes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    requirement_id INTEGER NOT NULL REFERENCES requirements(id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    change_type VARCHAR(20) NOT NULL,
    is_billable BOOLEAN NOT NULL DEFAULT FALSE,
    change_order_id INTEGER NULL REFERENCES change_orders(id) ON DELETE SET NULL,
    initiated_by VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 补全 change_orders 的外键（SQLite 不支持 ALTER ADD FOREIGN KEY，建表时已预留字段）
-- requirement_change_id 的外键约束通过应用层保证

-- 验收记录表
CREATE TABLE IF NOT EXISTS acceptances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    milestone_id INTEGER NULL REFERENCES milestones(id) ON DELETE SET NULL,
    acceptance_name VARCHAR(200) NOT NULL,
    acceptance_date DATE NOT NULL,
    acceptor_name VARCHAR(100) NOT NULL,
    acceptor_title VARCHAR(100) NULL,
    result VARCHAR(20) NOT NULL,
    notes TEXT NULL,
    trigger_payment_reminder BOOLEAN NOT NULL DEFAULT FALSE,
    reminder_id INTEGER NULL REFERENCES reminders(id) ON DELETE SET NULL,
    confirm_method VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 交付物记录表
CREATE TABLE IF NOT EXISTS deliverables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    acceptance_id INTEGER NULL REFERENCES acceptances(id) ON DELETE SET NULL,
    name VARCHAR(200) NOT NULL,
    deliverable_type VARCHAR(30) NOT NULL,
    delivery_date DATE NOT NULL,
    recipient_name VARCHAR(100) NOT NULL,
    delivery_method VARCHAR(20) NOT NULL,
    description TEXT NULL,
    storage_location VARCHAR(500) NULL,
    version_no VARCHAR(50) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 账号交接条目表
CREATE TABLE IF NOT EXISTS account_handovers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deliverable_id INTEGER NOT NULL REFERENCES deliverables(id) ON DELETE CASCADE,
    platform_name VARCHAR(200) NOT NULL,
    account_name VARCHAR(200) NOT NULL,
    notes VARCHAR(500) NULL
);

-- 版本发布记录表
CREATE TABLE IF NOT EXISTS releases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    deliverable_id INTEGER NULL REFERENCES deliverables(id) ON DELETE SET NULL,
    version_no VARCHAR(50) NOT NULL,
    release_date DATE NOT NULL,
    release_type VARCHAR(20) NOT NULL,
    is_current_online BOOLEAN NOT NULL DEFAULT FALSE,
    changelog TEXT NOT NULL,
    deploy_env VARCHAR(20) NULL,
    notes TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 售后/维护期记录表
CREATE TABLE IF NOT EXISTS maintenance_periods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE RESTRICT,
    contract_id INTEGER NULL REFERENCES contracts(id) ON DELETE SET NULL,
    service_type VARCHAR(20) NOT NULL,
    service_description VARCHAR(500) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    annual_fee DECIMAL(10,2) NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    renewed_by_id INTEGER NULL REFERENCES maintenance_periods(id) ON DELETE SET NULL,
    notes TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ── 核心索引 ──────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_requirements_project_id
    ON requirements(project_id);
CREATE INDEX IF NOT EXISTS idx_requirements_is_current
    ON requirements(is_current);
CREATE INDEX IF NOT EXISTS idx_requirement_changes_requirement_id
    ON requirement_changes(requirement_id);
CREATE INDEX IF NOT EXISTS idx_requirement_changes_change_order_id
    ON requirement_changes(change_order_id);
CREATE INDEX IF NOT EXISTS idx_acceptances_project_id
    ON acceptances(project_id);
CREATE INDEX IF NOT EXISTS idx_acceptances_acceptance_date
    ON acceptances(acceptance_date);
CREATE INDEX IF NOT EXISTS idx_acceptances_reminder_id
    ON acceptances(reminder_id);
CREATE INDEX IF NOT EXISTS idx_deliverables_project_id
    ON deliverables(project_id);
CREATE INDEX IF NOT EXISTS idx_deliverables_delivery_date
    ON deliverables(delivery_date);
CREATE INDEX IF NOT EXISTS idx_deliverables_acceptance_id
    ON deliverables(acceptance_id);
CREATE INDEX IF NOT EXISTS idx_releases_project_id
    ON releases(project_id);
CREATE INDEX IF NOT EXISTS idx_releases_is_current_online
    ON releases(is_current_online);
CREATE INDEX IF NOT EXISTS idx_releases_deliverable_id
    ON releases(deliverable_id);
CREATE INDEX IF NOT EXISTS idx_change_orders_contract_id
    ON change_orders(contract_id);
CREATE INDEX IF NOT EXISTS idx_change_orders_status
    ON change_orders(status);
CREATE INDEX IF NOT EXISTS idx_maintenance_periods_project_id
    ON maintenance_periods(project_id);
CREATE INDEX IF NOT EXISTS idx_maintenance_periods_end_date
    ON maintenance_periods(end_date);
CREATE INDEX IF NOT EXISTS idx_maintenance_periods_status
    ON maintenance_periods(status);
CREATE INDEX IF NOT EXISTS idx_maintenance_periods_renewed_by_id
    ON maintenance_periods(renewed_by_id);
```

**步骤 3**：迁移后执行以下验证，任意一项失败则停止并写入 PROGRESS.md

- ✅ 8 张新表全部存在（通过 `sqlite_master` 查询验证）
- ✅ 所有索引存在（通过 `PRAGMA index_list` 逐表验证）
- ✅ `projects` / `contracts` / `finance_records` 原有表总行数与迁移前一致
- ✅ 抽样记录所有原有字段值与快照完全一致
- ✅ `change_orders.order_no` UNIQUE 约束存在（通过 `PRAGMA index_info` 验证）

**步骤 4**：创建测试文件 `tests/test_migration_v15.py`
```python
# 测试用例清单（对应需求 NFR-501）：
# test_all_8_new_tables_exist → NFR-501
# test_all_indexes_exist → NFR-501
# test_projects_count_unchanged → NFR-501
# test_contracts_count_unchanged → NFR-501
# test_finance_records_count_unchanged → NFR-501
# test_existing_records_fields_unchanged → NFR-501
# test_change_order_no_unique_constraint → NFR-501
# test_foreign_key_requirements_cascade_delete_on_project → NFR-501
# test_foreign_key_acceptances_restrict_delete_on_project → NFR-501
# test_foreign_key_account_handovers_cascade_on_deliverable → NFR-501
# test_requirement_changes_change_order_id_index_exists → NFR-501
# test_acceptances_reminder_id_index_exists → NFR-501
# test_deliverables_acceptance_id_index_exists → NFR-501
# test_maintenance_periods_renewed_by_id_index_exists → NFR-501
```

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 B。

---

### 簇 B：FR-501 需求与变更管理——后端

**目标**：实现需求版本 CRUD 和需求变更记录接口。

**枚举定义**（追加到 `backend/models/enums.py`，不修改已有枚举）：
```python
class RequirementStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DISPUTED = "disputed"

class ChangeType(str, Enum):
    ADD = "add"
    REMOVE = "remove"
    MODIFY = "modify"
    DESIGN = "design"

class ConfirmMethod(str, Enum):
    OFFLINE = "offline"
    WECHAT = "wechat"
    EMAIL = "email"
    SYSTEM = "system"
```

**字段修改约束（必须同时在 POST / PUT / PATCH 中生效）**：
confirm_status 为 confirmed 时，以下字段不可修改：

summary
version_no
尝试修改时返回 HTTP 422："已确认的需求版本不可修改内容"

以下字段在任何状态下均可修改：

confirm_method
notes


**接口规范**：
POST /api/v1/projects/{project_id}/requirements
创建需求版本。
新版本 is_current 默认为 True。
必须在同一事务中将同项目其他版本 is_current 设为 False。
事务失败时全部回滚。
GET /api/v1/projects/{project_id}/requirements
返回该项目所有需求版本列表，按 created_at 倒序。
每条记录包含：id / version_no / confirm_status / is_current / created_at。
GET /api/v1/projects/{project_id}/requirements/{requirement_id}
返回需求版本详情，包含完整 summary 和 changes 数组。
PUT /api/v1/projects/{project_id}/requirements/{requirement_id}
全量更新。confirm_status = confirmed 时，summary / version_no 不可修改。
PATCH /api/v1/projects/{project_id}/requirements/{requirement_id}
部分更新。confirm_status = confirmed 时，summary / version_no 不可修改。
（PATCH 不豁免此约束）
POST /api/v1/projects/{project_id}/requirements/{requirement_id}/set-current
将指定版本设为当前有效版本。
同一事务中将同项目其他版本 is_current 设为 False。
POST /api/v1/projects/{project_id}/requirements/{requirement_id}/changes
创建变更记录。
is_billable = True 且 change_order_id 为 NULL 时：
返回 HTTP 422："收费变更必须先关联或创建变更单"

**核心函数**（提取到 `backend/core/requirement_utils.py`）：
```python
def set_requirement_as_current(requirement_id: int, project_id: int, db) -> None:
    """
    在同一事务中将指定需求版本设为当前有效，同项目其他版本 is_current 设为 False。
    操作失败时回滚。记录日志：操作类型 / project_id / 旧版本 ID / 新版本 ID。
    """

def can_modify_field(requirement_status: str, field_name: str) -> bool:
    """
    confirmed 状态下，summary 和 version_no 返回 False（不可修改）。
    其他字段或其他状态返回 True。
    此函数被 POST / PUT / PATCH 三个接口共同调用。
    """
```

**创建测试文件** `tests/test_requirements.py`：
```python
# 测试用例清单（对应需求 FR-501）：
# test_create_requirement_sets_as_current → FR-501
# test_create_requirement_clears_previous_current → FR-501
# test_create_requirement_no_two_current_after_create → FR-501（唯一性）
# test_create_requirement_transaction_rollback_on_failure → FR-501
# test_get_requirements_list_ordered_by_created_desc → FR-501
# test_get_requirement_detail_includes_changes → FR-501
# test_put_pending_requirement_summary_success → FR-501
# test_put_confirmed_requirement_summary_rejected → FR-501
# test_put_confirmed_requirement_version_no_rejected → FR-501
# test_put_confirmed_requirement_notes_allowed → FR-501
# test_patch_confirmed_requirement_summary_rejected → FR-501（PATCH 同样约束）
# test_patch_confirmed_requirement_notes_allowed → FR-501
# test_set_current_clears_other_versions → FR-501
# test_set_current_no_two_current_same_project → FR-501（唯一性）
# test_create_change_billable_without_order_rejected → FR-501
# test_create_change_not_billable_success → FR-501
# test_create_change_billable_with_order_success → FR-501
# test_project_not_found_returns_404 → FR-501
```

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 C。

---

### 簇 C：FR-502 验收管理——后端

**目标**：实现验收记录接口，验收通过时联动提醒管理中心。

**枚举定义**（追加，不修改已有枚举）：
```python
class AcceptanceResult(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    CONDITIONAL = "conditional"
```

**接口规范**：
POST /api/v1/projects/{project_id}/acceptances
创建验收记录。
当 result = passed 或 conditional 且 trigger_payment_reminder = True 时：
在同一事务中于 reminders 表创建提醒：
title = "收款提醒：{acceptance_name}"
type = custom，is_critical = False，status = pending
关联对象 = 该验收记录
将生成的 reminder_id 写回 acceptances.reminder_id
事务失败时全部回滚。
GET /api/v1/projects/{project_id}/acceptances
返回该项目所有验收记录，按 acceptance_date 倒序。
GET /api/v1/projects/{project_id}/acceptances/{acceptance_id}
返回验收记录详情。
DELETE /api/v1/projects/{project_id}/acceptances/{acceptance_id}
返回 HTTP 405，不执行任何操作。
PUT/PATCH result 字段：
尝试修改 result 时返回 HTTP 422："验收结果不可修改"
result 字段在 POST / PUT / PATCH 中均检查：一旦记录已创建，result 不可变更。
PATCH /api/v1/projects/{project_id}/acceptances/{acceptance_id}/append-notes
追加 notes。格式：原内容 + "\n" + 新备注。
原内容为空时直接存入新备注，不加换行符。

**核心函数**（提取到 `backend/core/acceptance_utils.py`）：
```python
def create_payment_reminder_for_acceptance(acceptance_name: str, acceptance_id: int, db) -> int:
    """
    创建收款提醒，返回 reminder_id。
    必须在调用方事务中执行，不得单独提交。
    title = "收款提醒：{acceptance_name}"
    """

def append_notes(existing_notes: str | None, new_note: str) -> str:
    """
    追加 notes，使用 NOTES_SEPARATOR 分隔。
    existing_notes 为 None 或空字符串时直接返回 new_note。
    """
```

**创建测试文件** `tests/test_acceptances.py`：
```python
# 测试用例清单（对应需求 FR-502）：
# test_create_acceptance_passed_triggers_reminder → FR-502
# test_create_acceptance_conditional_triggers_reminder → FR-502
# test_create_acceptance_failed_no_reminder → FR-502
# test_create_acceptance_flag_false_no_reminder → FR-502
# test_reminder_created_in_same_transaction → FR-502
# test_reminder_id_written_back_to_acceptance → FR-502
# test_get_acceptances_ordered_by_date_desc → FR-502
# test_delete_acceptance_returns_405 → FR-502
# test_put_result_field_rejected → FR-502
# test_patch_result_field_rejected → FR-502（PATCH 同样约束）
# test_append_notes_adds_newline_separator → FR-502
# test_append_notes_empty_original_no_separator → FR-502
# test_project_not_found_returns_404 → FR-502
# test_acceptance_detail_response_structure → FR-502
```

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 D。

---

### 簇 D：FR-503 交付物管理——后端

**目标**：实现交付物记录接口，账号交接清单通过字段名检测禁止存储密码。

**枚举定义**（追加，不修改已有枚举）：
```python
class DeliverableType(str, Enum):
    SOURCE_CODE = "source_code"
    INSTALLER = "installer"
    DEPLOYMENT_DOC = "deployment_doc"
    API_DOC = "api_doc"
    USER_MANUAL = "user_manual"
    ACCOUNT_HANDOVER = "account_handover"
    DESIGN_FILE = "design_file"
    TEST_REPORT = "test_report"
    OTHER = "other"

class DeliveryMethod(str, Enum):
    OFFLINE = "offline"
    REMOTE = "remote"
    CLOUD = "cloud"
    REPOSITORY = "repository"
```

**密码字段检测函数**（提取到 `backend/core/deliverable_utils.py`）：
```python
FORBIDDEN_FIELD_PATTERNS = ["password", "pwd", "secret", "passwd", "token"]

def contains_password_field(handover_item: dict) -> bool:
    """
    检测账号交接条目的 JSON 字段名（不是字段值）是否含有禁止字符串。
    检测方式：将字段名转为小写，判断是否包含 FORBIDDEN_FIELD_PATTERNS 中任意子串。
    示例：{"account_password": "x"} → True（含 "password"）
          {"account_name": "admin"} → False
          {"notes": "密码已通过微信发送"} → False（notes 是允许字段名）
    不得扫描字段值内容。
    """
```

**接口规范**：
POST /api/v1/projects/{project_id}/deliverables
创建交付物记录。
当 deliverable_type = account_handover 时，请求体可包含 account_handovers 数组。
对每条 account_handover 条目调用 contains_password_field() 检测：
检测到禁止字段名时返回 HTTP 422："账号交接清单禁止存储密码，请仅记录账号名"
account_handovers 数组和主记录必须在同一事务中写入。
GET /api/v1/projects/{project_id}/deliverables
返回该项目所有交付物，按 delivery_date 倒序。
支持 deliverable_type 参数筛选。
GET /api/v1/projects/{project_id}/deliverables/{deliverable_id}
返回交付物详情。account_handover 类型时包含 account_handovers 数组。
DELETE /api/v1/projects/{project_id}/deliverables/{deliverable_id}
返回 HTTP 405，不执行任何操作。

**创建测试文件** `tests/test_deliverables.py`：
```python
# 测试用例清单（对应需求 FR-503）：
# test_create_source_code_deliverable → FR-503
# test_create_account_handover_with_valid_accounts → FR-503
# test_create_account_handover_password_field_rejected → FR-503
# test_create_account_handover_pwd_field_rejected → FR-503
# test_create_account_handover_token_field_rejected → FR-503
# test_create_account_handover_notes_field_allowed → FR-503（notes 是合法字段名）
# test_password_detection_checks_field_name_not_value → FR-503
# test_account_handovers_saved_in_same_transaction → FR-503
# test_get_deliverables_ordered_by_date_desc → FR-503
# test_get_deliverables_filter_by_type → FR-503
# test_get_deliverable_detail_includes_handovers → FR-503
# test_delete_deliverable_returns_405 → FR-503
# test_contains_password_field_function → FR-503（独立函数测试）
# test_project_not_found_returns_404 → FR-503
```

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 E。

---

### 簇 E：FR-504 版本/发布记录——后端

**目标**：实现版本发布记录接口，维护当前线上版本唯一性。

**枚举定义**（追加，不修改已有枚举）：
```python
class ReleaseType(str, Enum):
    RELEASE = "release"
    HOTFIX = "hotfix"
    BETA = "beta"
    ROLLBACK = "rollback"

class DeployEnv(str, Enum):
    PRODUCTION = "production"
    TESTING = "testing"
    INTRANET = "intranet"
```

**字段修改约束**：
version_no 和 release_date 创建后不可修改（POST / PUT / PATCH 均检查）。
尝试修改时返回 HTTP 422："版本号和发布日期不可修改"
changelog 和 notes 字段始终可修改。

**接口规范**：
POST /api/v1/projects/{project_id}/releases
创建发布记录。
is_current_online = True 时：
必须在同一事务中将同项目其他记录的 is_current_online 设为 False。
GET /api/v1/projects/{project_id}/releases
返回该项目所有发布记录，按 release_date 倒序。
is_current_online = True 的记录在响应中标注 is_pinned: true，前端据此置顶展示。
GET /api/v1/projects/{project_id}/releases/{release_id}
返回发布记录详情。
POST /api/v1/projects/{project_id}/releases/{release_id}/set-online
将指定版本设为当前线上版本。
在同一事务中将同项目其他记录 is_current_online 设为 False。
记录日志：project_id / 旧版本 ID / 新版本 ID。
DELETE /api/v1/projects/{project_id}/releases/{release_id}
返回 HTTP 405，不执行任何操作。
在 GET /api/v1/projects/{project_id} 响应中追加：
"current_version": "v1.2.0"（无线上版本时返回 null）

**核心函数**（提取到 `backend/core/release_utils.py`）：
```python
def set_release_as_online(release_id: int, project_id: int, db) -> None:
    """
    在同一事务中将指定发布记录设为当前线上，同项目其他记录 is_current_online 设为 False。
    操作失败时回滚。记录日志：project_id / 旧版本 ID / 新版本 ID。
    """
```

**创建测试文件** `tests/test_releases.py`：
```python
# 测试用例清单（对应需求 FR-504）：
# test_create_release_as_current_online → FR-504
# test_create_release_clears_previous_online → FR-504
# test_create_release_no_two_current_online → FR-504（唯一性）
# test_create_release_transaction_rollback → FR-504
# test_set_online_clears_other_versions → FR-504
# test_set_online_no_two_current_online → FR-504（唯一性）
# test_get_releases_ordered_by_date_desc → FR-504
# test_get_releases_current_online_has_is_pinned_true → FR-504
# test_delete_release_returns_405 → FR-504
# test_put_version_no_rejected → FR-504
# test_put_release_date_rejected → FR-504
# test_patch_version_no_rejected → FR-504（PATCH 同样约束）
# test_patch_changelog_success → FR-504
# test_project_detail_includes_current_version → FR-504
# test_project_detail_current_version_null_when_none → FR-504
```

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 F。

---

### 簇 F：FR-505 变更单/增补单——后端

**目标**：实现变更单 CRUD，维护合同实际应收合计。

**枚举定义**（追加，不修改已有枚举）：
```python
class ChangeOrderStatus(str, Enum):
    DRAFT = "draft"
    SENT = "sent"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
```

**状态流转白名单（严格执行，使用全局常量 CHANGE_ORDER_VALID_TRANSITIONS）**：
```python
# 合法路径（来自全局常量）：
# draft → sent / confirmed / completed
# sent → confirmed / completed
# confirmed → in_progress / completed
# in_progress → completed
# completed → （空，任何流转均非法）
# 非法流转返回 HTTP 422，错误信息格式：
# "状态从 {current_status} 变更为 {target_status} 不被允许"
```

**字段修改约束**：
status 为 confirmed / in_progress / completed 时，以下字段不可修改：

amount
description
尝试修改时返回 HTTP 422："已确认的变更单不可修改金额和描述"
此约束同时在 PUT 和 PATCH 中生效。


**核心函数**（提取到 `backend/core/change_order_utils.py`）：
```python
def generate_change_order_no(db) -> str:
    """
    格式：BG-YYYYMMDD-序号（3 位补零）。
    当日序号 = 当日已有变更单数量 + 1。
    必须在调用方事务中执行，防止并发重复。
    """

def validate_status_transition(current: str, target: str) -> bool:
    """
    使用 CHANGE_ORDER_VALID_TRANSITIONS 校验状态流转是否合法。
    返回 True 表示合法，False 表示非法。
    """

def calculate_actual_receivable(contract_id: int, db) -> dict:
    """
    confirmed_total：
      change_orders 中 status IN (confirmed, in_progress, completed) 的 amount 之和
      round(sum, 2)，无符合记录时为 0.00
    actual_receivable：
      round(contracts.amount + confirmed_total, 2)
    返回：{"confirmed_total": Decimal, "actual_receivable": Decimal}
    """
```

**接口规范**：
POST /api/v1/contracts/{contract_id}/change-orders
创建变更单，在事务中调用 generate_change_order_no() 生成编号。
status 默认为 draft。
GET /api/v1/contracts/{contract_id}/change-orders
返回该合同所有变更单，按 created_at 倒序。
响应追加合计字段：
confirmed_total: Decimal
actual_receivable: Decimal
GET /api/v1/contracts/{contract_id}/change-orders/{order_id}
返回变更单详情。
PUT/PATCH /api/v1/contracts/{contract_id}/change-orders/{order_id}
更新变更单。
校验字段修改约束（confirmed 及以后不可改 amount / description）。
若包含 status 字段，调用 validate_status_transition() 校验合法性。
GET /api/v1/projects/{project_id}/change-orders/summary
项目维度摘要（只读，职责分离要求）。
返回该项目所有关联合同的变更单列表（仅展示字段）：
order_no / title / amount / status / contract_id / contract_no
不提供任何写操作入口。

**创建测试文件** `tests/test_change_orders.py`：
```python
# 测试用例清单（对应需求 FR-505）：
# test_create_change_order_generates_no → FR-505
# test_change_order_no_format_bg_yyyymmdd_001 → FR-505
# test_change_order_no_increments_same_day → FR-505
# test_get_change_orders_includes_confirmed_total → FR-505
# test_get_change_orders_includes_actual_receivable → FR-505
# test_actual_receivable_includes_confirmed → FR-505
# test_actual_receivable_includes_in_progress → FR-505
# test_actual_receivable_includes_completed → FR-505
# test_actual_receivable_excludes_draft → FR-505
# test_actual_receivable_excludes_sent → FR-505
# test_status_draft_to_sent_allowed → FR-505
# test_status_draft_to_confirmed_allowed → FR-505（跳过 sent 合法）
# test_status_draft_to_completed_allowed → FR-505（提前终止合法）
# test_status_completed_to_any_rejected → FR-505
# test_status_illegal_transition_returns_422_with_message → FR-505
# test_update_draft_amount_success → FR-505
# test_update_confirmed_amount_rejected → FR-505
# test_update_confirmed_description_rejected → FR-505
# test_patch_confirmed_amount_rejected → FR-505（PATCH 同样约束）
# test_project_summary_endpoint_readonly → FR-505（无写操作入口）
# test_validate_status_transition_function → FR-505（独立函数测试）
# test_generate_change_order_no_unique → FR-505（独立函数测试）
```

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 G。

---

### 簇 G：FR-506 售后/维护期管理——后端

**目标**：实现售后/维护期记录接口，联动提醒管理中心和事件驱动逾期检查。

**枚举定义**（追加，不修改已有枚举）：
```python
class MaintenanceType(str, Enum):
    WARRANTY = "warranty"
    MAINTENANCE = "maintenance"
    ANNUAL_FEE = "annual_fee"
    HOSTING = "hosting"
    SUPPORT = "support"

class MaintenanceStatus(str, Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    RENEWED = "renewed"
    TERMINATED = "terminated"
```

**接口规范**：
POST /api/v1/projects/{project_id}/maintenance-periods
创建服务期记录。
end_date < start_date 时返回 HTTP 422："结束日期不得早于开始日期"
创建成功后，若 end_date 在今日起 MAINTENANCE_REMINDER_DAYS_BEFORE 天内，
立即创建提醒（调用事件驱动检查函数中的提醒生成逻辑，保证幂等）。
GET /api/v1/projects/{project_id}/maintenance-periods
返回该项目所有服务期记录，按 end_date 升序。
支持 status 参数筛选。
GET /api/v1/projects/{project_id}/maintenance-periods/{period_id}
返回服务期详情。
POST /api/v1/projects/{project_id}/maintenance-periods/{period_id}/renew
续期操作，以下三步必须在同一事务中完成：
1. 创建新服务期记录：
start_date = 原记录 end_date + 1 天（自动计算，不接受调用方传入）
end_date 必须由调用方明确传入，不得为空，不得早于新 start_date
service_type / service_description / annual_fee 由调用方传入（可与原记录不同）
2. 原记录 status 变更为 renewed
3. 原记录 renewed_by_id 指向新记录 ID
若新服务期 annual_fee > 0，提醒的 notes 自动追加："年费金额：¥{annual_fee}，请确认是否续签"
PATCH /api/v1/projects/{project_id}/maintenance-periods/{period_id}
仅允许修改：service_description / annual_fee / notes。
status 为 expired / renewed / terminated 时返回 HTTP 422："已结束的服务期不可修改"
尝试修改其他字段时返回 HTTP 422："仅允许修改服务说明、年费和备注"

**事件驱动逾期检查扩展**（在 v1.2 FR-103 的事件驱动函数中追加，不重写原有逻辑）：
```python
# 追加到现有事件驱动检查函数（90 天窗口限制同样适用）：

# 1. 检查 maintenance_periods 中 status = active 且 end_date < 今日的记录
#    批量更新 status 为 expired

# 2. 检查 maintenance_periods 中 status = active 且
#    end_date 在今日起 MAINTENANCE_REMINDER_DAYS_BEFORE 天内的记录
#    若 reminders 表中尚不存在该 maintenance_period 对应的提醒，则自动创建
#    （幂等保护：通过 related_object_type + related_object_id 判断是否已存在）
```

**看板接口扩展**（在已有看板接口响应中追加字段，不新建接口）：
```json
"active_maintenance_count": 3
```

**创建测试文件** `tests/test_maintenance.py`：
```python
# 测试用例清单（对应需求 FR-506）：
# test_create_maintenance_success → FR-506
# test_create_maintenance_end_before_start_rejected → FR-506
# test_create_maintenance_near_expiry_generates_reminder → FR-506
# test_create_maintenance_far_expiry_no_immediate_reminder → FR-506
# test_create_reminder_idempotent → FR-506（重复触发不生成重复提醒）
# test_get_maintenance_ordered_by_end_date_asc → FR-506
# test_get_maintenance_filter_by_status → FR-506
# test_renew_new_start_date_is_original_end_plus_one → FR-506
# test_renew_requires_explicit_end_date → FR-506（end_date 必填）
# test_renew_end_date_before_start_rejected → FR-506
# test_renew_original_status_becomes_renewed → FR-506
# test_renew_original_renewed_by_id_set → FR-506
# test_renew_annual_fee_appends_to_reminder_notes → FR-506
# test_renew_transaction_atomic → FR-506
# test_patch_active_allowed_fields → FR-506
# test_patch_expired_rejected → FR-506
# test_patch_disallowed_fields_rejected → FR-506
# test_event_driven_expires_overdue_maintenance → FR-506
# test_event_driven_creates_reminder_near_expiry → FR-506
# test_event_driven_reminder_idempotent → FR-506
# test_dashboard_includes_active_maintenance_count → FR-506
```

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 H。

---

### 簇 H：前端联调

**目标**：实现 v1.5 六个模块的前端展示与交互。

**约束**：
- 所有展示组件在数据为空时显示"—"或空列表，不得显示 null 字符串或报错
- 动态字段隐藏时其值必须从提交 payload 中完全移除
- 所有列表组件必须有明确的排序依据，不依赖数据库默认顺序

---

**项目详情页 Tab 结构**
新增 Tab（追加到已有 Tab 后）：
[需求] [验收] [交付物] [版本] [售后] [变更单摘要]
项目详情页顶部信息栏新增：
当前线上版本：v1.2.0（无数据时显示"未发布"）

**需求管理 Tab（FR-501）**
可观察验收行为：
A. 展示当前有效需求版本摘要（is_current=True 的版本），标注"当前版本"徽标
B. "历史版本"折叠区展示所有非当前版本列表，默认折叠
C. 新建版本表单：填写 version_no 和 summary
D. 创建成功后，原当前版本降级，新版本显示为当前版本
E. confirm_status = confirmed 的版本：summary 和 version_no 只读，不出现编辑按钮
F. confirm_status = confirmed 的版本：notes 和 confirm_method 仍可编辑
G. 变更记录列表展示在当前版本下方，含 change_type 标签和 is_billable 标识
H. Network 面板：is_billable=True 且无 change_order_id 时，
前端弹出"请先关联或创建变更单"，不发送请求

**验收管理 Tab（FR-502）**
可观察验收行为：
A. 展示该项目所有验收记录，按 acceptance_date 倒序
B. 新建验收记录表单：含 acceptance_name / acceptance_date / acceptor_name /
result / confirm_method
C. result 选择 passed 或 conditional 时，"触发收款提醒"开关出现，默认开启
D. result 选择 failed 时，"触发收款提醒"开关消失，值清空，payload 中不含此字段
E. 验收记录无删除按钮（不渲染删除入口）
F. result 字段在详情展示中只读，无编辑入口
G. "追加备注"按钮：弹出文本框，提交后新内容追加到 notes 末尾（换行分隔）

**交付物管理 Tab（FR-503）**
可观察验收行为：
A. 展示该项目所有交付物，含 deliverable_type 标签和 delivery_date
B. 新建交付物表单：含 name / deliverable_type / delivery_date / recipient_name / delivery_method
C. deliverable_type 选择 account_handover 时，出现"账号条目"多行录入区
D. 账号条目表单只有"平台名称"和"账号"两个字段，无密码字段，无 token 字段
E. 切换 deliverable_type 为其他时，账号条目区消失，已填内容清空
F. 交付物记录无删除按钮
G. 支持按 deliverable_type 筛选
H. Network 面板确认：账号条目提交的字段名中不含 password / pwd / token 等

**版本记录 Tab（FR-504）**
可观察验收行为：
A. is_current_online=True 的版本置顶，标注"当前线上"徽标
B. 其他版本按 release_date 倒序排列
C. 新建版本表单：含 version_no / release_date / release_type / changelog / deploy_env
D. "设为当前线上"按钮：点击后该版本置顶，原置顶版本移除徽标
E. 版本记录无删除按钮
F. version_no 和 release_date 在详情中只读，无编辑入口
G. changelog 和 notes 可编辑

**变更单摘要 Tab（FR-505，项目页只读）**
可观察验收行为：
A. 展示该项目关联合同的所有变更单摘要：
order_no / title / amount / status / 所属合同编号
B. 无任何创建/编辑/删除操作入口（只读展示）
C. 点击变更单条目可跳转到对应合同详情页的变更单 Tab
D. Network 面板确认：此 Tab 只有 GET 请求，无任何写操作

**合同详情页——变更单 Tab（FR-505，完整管理）**
可观察验收行为：
A. 合同详情页新增"变更单"Tab
B. Tab 顶部展示：原合同金额 / 变更单确认合计(confirmed_total) /
实际应收合计(actual_receivable)，三者来源清晰标注
C. 新建变更单表单：含 title / description / amount
D. 变更单列表含状态徽标（草稿灰 / 已发送蓝 / 已确认绿 / 完成深蓝）
E. confirmed / in_progress / completed 状态的 amount 和 description 字段只读
F. 状态流转按钮根据 CHANGE_ORDER_VALID_TRANSITIONS 动态展示：
draft 状态：显示"发送"和"直接确认"两个按钮
sent 状态：显示"确认"按钮
confirmed 状态：显示"开始执行"和"完成"按钮
in_progress 状态：显示"完成"按钮
completed 状态：不显示任何状态变更按钮
G. Network 面板：状态变更通过 PATCH status 字段实现，非法流转时后端返回 422

**售后/维护期 Tab（FR-506）**
可观察验收行为：
A. 服务期列表按 end_date 升序排列
B. 即将到期（30天内）的记录行背景标黄
C. 已到期（status=expired）的记录行背景标红
D. 新建服务期表单：含 service_type / service_description / start_date / end_date / annual_fee（选填）
E. end_date 早于 start_date 时，前端立即提示"结束日期不得早于开始日期"，不发送请求
F. "续期"按钮仅在 status=active 的记录上显示
G. 续期表单：start_date 自动填入原 end_date+1 天（只读展示）；
end_date 必填，由用户输入；annual_fee 可修改
H. expired / renewed / terminated 状态的记录：所有编辑入口隐藏
I. PATCH 表单只展示 service_description / annual_fee / notes 三个字段

运行全量测试，要求 0 FAILED。更新 `PROGRESS.md`，继续执行簇 I。

---

### 簇 I：全局重构

**目标**：在全量测试通过的前提下优化代码结构。

**核心约束（违反则撤回该重构项，重跑全量测试恢复通过后再继续）**：
重构不得改变：

任何接口的返回字段名（包括大小写和下划线）
任何错误信息文案
任何 HTTP 状态码
任何校验触发时机（POST / PUT / PATCH 的约束均不得弱化）
任何业务规则语义（流转规则、事务原子性、唯一性约束、禁删约束）


**必须完成的重构项（逐项执行，每项后运行全量测试）**：

**1. 常量集中管理**

确认 `backend/core/constants.py` 包含 v1.5 新增常量，业务代码中无以下魔术数字：
- `30`（使用 `MAINTENANCE_REMINDER_DAYS_BEFORE`）
- `"BG"`（使用 `CHANGE_ORDER_PREFIX`）
- `"\n"`（使用 `NOTES_SEPARATOR`）

**2. 函数长度与复杂度检查**

所有函数 ≤ 50 行，圈复杂度 < 10，超出者必须拆分后重跑全量测试。

**3. 独立函数可调用性验证**

以下函数必须可在测试中直接 import 调用（不依赖启动 FastAPI 应用）：
- `backend.core.requirement_utils.set_requirement_as_current`
- `backend.core.requirement_utils.can_modify_field`
- `backend.core.acceptance_utils.create_payment_reminder_for_acceptance`
- `backend.core.acceptance_utils.append_notes`
- `backend.core.deliverable_utils.contains_password_field`
- `backend.core.release_utils.set_release_as_online`
- `backend.core.change_order_utils.generate_change_order_no`
- `backend.core.change_order_utils.validate_status_transition`
- `backend.core.change_order_utils.calculate_actual_receivable`

**4. 事务一致性验证**

确认以下操作均在单一数据库事务中完成（通过测试中的事务回滚测试验证）：
- 创建需求版本并清除同项目其他版本的 is_current
- 设置当前线上版本并清除同项目其他版本的 is_current_online
- 创建验收记录并生成收款提醒（reminder_id 写回）
- 续期操作（新建记录 + 原记录 status=renewed + renewed_by_id 写入）

**5. 事件驱动逾期检查完整性验证**

确认事件驱动函数完整覆盖以下场景（通过测试验证，不仅是人工确认）：
- v1.1：提醒状态逾期升级 ✅
- v1.2：报价单过期、客户资产到期提醒 ✅
- v1.5（新增）：维护期到期状态变更为 expired、维护期到期提醒生成（幂等）

**6. 日志覆盖验证**

确认以下操作均写入 RotatingFileHandler，每条日志包含：操作类型 / 涉及表名 / 业务主键 / 失败原因 / 时间戳：
- 需求版本 is_current 切换（含 project_id / 旧版本 ID / 新版本 ID）
- 版本记录 is_current_online 切换（含 project_id / 旧版本 ID / 新版本 ID）
- 验收记录创建事务失败
- 变更单非法状态流转尝试（含 current_status / target_status）
- 维护期续期事务失败
- 账号交接禁止密码字段拦截（含被拦截的字段名）

**7. 最终全量回归**
```bash
pytest tests/ -v --tb=short
# 要求：0 FAILED
# 将完整输出写入 PROGRESS.md
```

---

## 完成标准

以下全部满足时，在 `PROGRESS.md` 写入"v1.5 执行完成"并记录时间：

- [ ] 簇 A ~ I 全部状态为 ✅
- [ ] `pytest tests/ -v` 结果：0 FAILED，输出已记录在 `PROGRESS.md`
- [ ] `backend/core/constants.py` 已追加 v1.5 常量，无魔术数字
- [ ] 9 个核心工具函数均存在且可独立调用
- [ ] 4 处事务操作均有对应的原子性回滚测试
- [ ] 事件驱动逾期检查已通过测试验证覆盖维护期场景
- [ ] 项目页变更单 Tab 为只读摘要，合同页变更单 Tab 为完整管理（通过测试验证无写操作入口）
- [ ] 所有"禁止删除"的实体均有对应的 HTTP 405 测试
- [ ] 账号交接密码检测为字段名检测（不扫描值），有专项测试验证
- [ ] `logs/` 目录本次执行产生了日志文件
- [ ] 所有接口字段名、错误文案、HTTP 状态码与本文档约定完全一致