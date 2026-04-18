# 🎯 项目执行指令（给 Claude Code）

## 🧠 前置分析（编码前必须输出）
在编写任何代码前，先输出简要的技术风险分析与实现策略，包含以下三点：
1. 本项目最复杂的 3 个技术难点识别。
2. 针对 snapshot 写入失败、summary 刷新失败两条高风险链的防御策略。
3. SQLite 单文件场景下 dashboard_summary 查询性能的应对方案。

不展开内部推理细节，直接给出结论性判断。

---

# 给 Claude Code 的项目提示词

## 🎯 项目概述
- **项目名称**：数标云管 v2.2
- **核心目标**：在 v1.x 已有经营数据基础上，建立统一留痕底座与仪表盘聚合层，使至少一类高频日常动作能在系统内闭环完成，至少一类关键经营信息能稳定留痕不再丢失，至少一个周常重复操作压缩为一键执行。
- **目标用户**：单人使用，本地单机部署，无多端协作需求。

---

## 🧪 开发工作流：测试驱动开发（TDD）
本项目采用**测试驱动开发（TDD）**，严格遵循 "Red → Green → Refactor" 循环。

### TDD 循环：
写测试（Red：测试失败） → 写实现（Green：测试通过） → 重构（Refactor：优化代码） → 重复

---

## 📐 Cluster 划分与执行顺序

### 执行规则
- **Cluster A 必须先行完成并全量回归通过**，B / C / D 方可并行推进。
- Cluster A 内部执行顺序强制为：**先完成 A1（snapshot 底座）全套测试与实现并回归通过，再进入 A2（summary 底座）**，禁止两者并行开工。
- 每个 Cluster 内部严格执行 TDD 三循环，不得跨 Cluster 预实现逻辑。
- **全量回归时机**：Phase 1 / Phase 2 内部可局部测试；**Phase 3（Refactor）结束时必须执行一次全量回归**（含 v1.0 至当前版本），0 FAILED 方可标记 Cluster 完成。禁止在 Phase 1 / Phase 2 每步都跑全量回归。
- 使用 `PROGRESS.md` 记录每个 Cluster 的执行状态，提供中断恢复入点。

### Cluster 总览

| Cluster | 内容 | 依赖 |
|---------|------|------|
| A1 | snapshot 底座（entity_snapshots 表） | 无，先行 |
| A2 | summary 底座（dashboard_summary 表 + 刷新机制） | 依赖 A1 完成 |
| B | 首页仪表盘 | 依赖 A 全部完成 |
| C | 模板 / 纪要 / 报告留痕 | 依赖 A 全部完成 |
| D | 工具入口台账 + 客户线索台账 | 依赖 A 全部完成 |

---

## 🚨 关键架构决策（全局生效，所有 Cluster 必须遵守）

### 异常返回约定（snapshot / summary 失败路径）
- snapshot 写入失败或 summary 刷新失败时：
  - **主业务不回滚**
  - **API 必须返回**：`{ "success": true, "warning_code": "SNAPSHOT_WRITE_FAILED" | "SUMMARY_REFRESH_FAILED", "warning_message": "..." }`
  - **前端按 warning_code 显示 toast 提示**（不阻断用户操作）
  - **日志必须完整记录**（含 entity_type、entity_id、失败原因）
  - 测试必须能通过断言 API 返回的 warning_code 来验证此路径
- 禁止只打日志不给接口信号；禁止只给前端信号而测试无法断言

### dashboard_summary 数据模型约定
- 采用**统一键值模型**：`metric_key`（唯一字符串） + `metric_value`（JSON 或数值）
- 后端 API 返回完整 metric 集合，不做后端分组
- **前端负责分组展示**：六组分组（客户/项目/合同/财务/交付/提醒）的映射关系，由前端 `constants/dashboard.js` 静态常量定义，后端不感知分组逻辑
- 空值处理：metric_value 为 null 时，前端显示"暂无数据"，不报错
- 所有 metric_key 字符串定义为 `constants.py` 命名常量，禁止魔术字符串

### summary 刷新触发原则
- **仅以下关键经营状态变更触发 summary 刷新**，其余普通写入不触发：
  - 合同状态确认
  - 收款录入
  - 发票录入（销项/进项）
  - 交付完成
  - 里程碑状态变更
- 禁止将 summary 刷新挂载到非上述事件的 API 写操作上

---

## 🤖 Agent 技能定义

---

### Cluster A1：snapshot 底座

**Agent 角色**：测试工程师 → 开发工程师 → 代码审查员

**核心目标**：建立 `entity_snapshots` 统一快照表，作为 A2 / C 的底层依赖。

---

#### A1-Phase 1：编写测试用例（Red）

**约束条件**：
- ⚠️ 此阶段禁止编写任何业务代码。
- ⚠️ 每个测试用例必须对应一个明确的需求条目。

**测试用例清单（必须全部覆盖）**：

```
[FR-A1-001] test_snapshot_create_report        - 报告实体快照写入成功，is_latest=True
[FR-A1-002] test_snapshot_create_sets_previous_not_latest - 新快照写入后，同实体前一版 is_latest 自动置 False
[FR-A1-003] test_snapshot_version_increments   - 同一实体多次快照，version_no 单调递增
[FR-A1-004] test_snapshot_json_validated_by_pydantic - snapshot_json 入库前经过 pydantic 校验，非法结构拒绝写入
[FR-A1-005] test_snapshot_write_failure_returns_warning - 快照写入失败时，API 返回 success=true + warning_code=SNAPSHOT_WRITE_FAILED，主业务未回滚，日志记录
[FR-A1-006] test_snapshot_supports_multiple_entity_types - entity_type 支持 report / minutes / template，查询互不干扰
[FR-A1-007] test_snapshot_parent_chain         - parent_snapshot_id 正确关联上一版本，形成可回溯链
```

**交付物**：`tests/test_cluster_a1_snapshot.py`，运行结果全部 FAILED（符合预期）。

**检查点**：
- ✅ 7 个测试用例全部存在？
- ✅ 运行后全部显示 FAILED？
- ✅ FR-A1-005 的断言是否针对 API 返回的 warning_code？

---

#### A1-Phase 2：实现功能代码（Green）

**约束条件（强制执行）**：
- ⚠️ **最小实现原则**：每次只实现能让**当前一个**失败测试变为 Pass 的最少代码。
- ⚠️ 每实现一个测试通过后，必须立即停止，输出以下格式报告，再等待下一步指令：

```
✅ [test_函数名] 已通过
剩余失败测试：[数量] 个
等待指令继续执行下一个测试的实现。
```

- ⚠️ 严禁一次性实现多个测试的逻辑。
- ⚠️ 严禁在测试未覆盖的地方添加任何冗余逻辑。

**数据库迁移规范**：
- 新增 `entity_snapshots` 表：`id, entity_type, entity_id, version_no, snapshot_json, created_at, parent_snapshot_id, is_latest`
- 所有新增通过新表实现，**禁止修改 v1.x 已有字段**。
- 迁移脚本：`migrations/v2.2_cluster_a1.sql`

**核心函数签名（必须提取为独立可测试单元）**：

```python
def create_snapshot(entity_type: str, entity_id: int, snapshot_json: dict) -> tuple[bool, str | None]:
    """
    创建快照。
    返回 (True, None) 表示成功；
    返回 (False, warning_code) 表示失败，失败时不抛出异常，日志记录。
    调用方负责将 warning_code 注入 API 返回。
    """

def get_latest_snapshot(entity_type: str, entity_id: int) -> dict | None:
    """获取指定实体的最新快照。"""

def get_snapshot_history(entity_type: str, entity_id: int) -> list[dict]:
    """获取指定实体的完整快照链，按 version_no 升序。"""
```

**检查点**：
- ✅ snapshot 写入失败路径：API 返回 warning_code，日志已记录，主业务未回滚？
- ✅ snapshot_json 入库前经过 pydantic 校验？
- ✅ is_latest 自动维护逻辑正确？

---

#### A1-Phase 3：重构优化（Refactor）

**任务**：
- entity_type 枚举值定义为 `constants.py` 命名常量。
- warning_code 字符串定义为 `constants.py` 命名常量。
- 确认函数长度 ≤ 50 行，圈复杂度 < 10。
- **新增错误码必须同步写入 `help_content.py`**。

**约束条件**：
- ⚠️ Phase 3 结束时执行一次全量回归（v1.0 至当前），0 FAILED 方可标记 A1 完成。
- ⚠️ 禁止在重构阶段新增功能。

---

### Cluster A2：summary 底座

**前置条件**：A1 全量回归 0 FAILED。

**Agent 角色**：测试工程师 → 开发工程师 → 代码审查员

**核心目标**：建立 `dashboard_summary` 统一键值表，实现关键经营事件触发刷新机制。

---

#### A2-Phase 1：编写测试用例（Red）

**测试用例清单（必须全部覆盖）**：

```
[FR-A2-001] test_summary_refreshed_on_contract_confirm   - 合同状态确认后，相关 metric_key 刷新
[FR-A2-002] test_summary_refreshed_on_payment_record     - 收款录入后，相关 metric_key 刷新
[FR-A2-003] test_summary_refreshed_on_invoice_record     - 发票录入后，相关 metric_key 刷新
[FR-A2-004] test_summary_refreshed_on_delivery_complete  - 交付完成后，相关 metric_key 刷新
[FR-A2-005] test_summary_refreshed_on_milestone_change   - 里程碑状态变更后，相关 metric_key 刷新
[FR-A2-006] test_summary_refresh_failure_returns_warning - summary 刷新失败时，API 返回 success=true + warning_code=SUMMARY_REFRESH_FAILED，主业务未回滚，日志记录
[FR-A2-007] test_summary_full_rebuild                    - 全量重建接口可被手动触发，结果与逐条刷新一致
[FR-A2-008] test_summary_read_only_from_summary_table    - 首页 API 不执行任何跨表 join，仅查 dashboard_summary
[FR-A2-009] test_summary_non_trigger_write_no_refresh    - 非触发事件的普通写操作不触发 summary 刷新
```

**交付物**：`tests/test_cluster_a2_summary.py`，运行全部 FAILED。

---

#### A2-Phase 2：实现功能代码（Green）

**约束条件**：同 A1-Phase 2，逐一实现，每步停止报告。

**数据库迁移规范**：
- 新增 `dashboard_summary` 表：`id, metric_key, metric_value, refreshed_at`
- `metric_key` 唯一索引。
- 迁移脚本：`migrations/v2.2_cluster_a2.sql`

**核心函数签名**：

```python
def refresh_summary(trigger_event: str, related_ids: dict) -> tuple[bool, str | None]:
    """
    触发 summary 局部刷新。
    trigger_event 必须是 SUMMARY_TRIGGER_* 常量之一，否则不执行刷新。
    返回 (True, None) 表示成功；
    返回 (False, warning_code) 表示失败，不回滚主业务，日志记录。
    """

def rebuild_summary_full() -> bool:
    """全量重建 dashboard_summary，可手动触发。"""
```

**检查点**：
- ✅ 非触发事件写操作不触发刷新（FR-A2-009 通过）？
- ✅ summary 刷新失败路径：API 返回 warning_code，日志已记录，主业务未回滚？
- ✅ 所有 metric_key 使用 constants.py 命名常量？

---

#### A2-Phase 3：重构优化（Refactor）

- 触发事件类型定义为 `SUMMARY_TRIGGER_*` 命名常量，集中在 `constants.py`。
- warning_code 统一复用 A1 已定义常量，不重复定义。
- **新增错误码同步写入 `help_content.py`**。
- Phase 3 结束时执行全量回归（v1.0 至当前），0 FAILED 方可标记 A2 完成，B/C/D 方可并行启动。

---

### Cluster B：首页仪表盘

**前置条件**：A1 + A2 全量回归 0 FAILED。

**Agent 角色**：测试工程师 → 开发工程师 → 代码审查员

**核心目标**：首页统一工作台，数据源仅读 `dashboard_summary`，不直接跨表 join，展示六组经营状态。

---

#### B-Phase 1：编写测试用例（Red）

**测试用例清单**：

```
[FR-B-001] test_dashboard_reads_only_summary_table     - 首页 API 不执行任何跨表 join，仅查 dashboard_summary
[FR-B-002] test_dashboard_returns_all_metric_keys      - 返回所有已定义的 metric_key，前端按常量映射分组展示
[FR-B-003] test_dashboard_reflects_summary_after_refresh - summary 刷新后，下次首页请求返回新值
[FR-B-004] test_dashboard_graceful_when_summary_empty  - summary 表为空时，首页正常返回，metric_value 为 null，不报 500
[FR-B-005] test_dashboard_overdue_metrics_present      - 逾期相关 metric_key 存在且可返回数值
```

**交付物**：`tests/test_cluster_b_dashboard.py`，运行全部 FAILED。

---

#### B-Phase 2：实现功能代码（Green）

**约束条件**：同 A1-Phase 2，逐一实现，每步停止报告。

**后端规范**：
- 新增 `GET /api/v1/dashboard/summary` 接口，仅读 `dashboard_summary` 表，返回完整 metric 集合。
- 返回格式：`{ "metrics": { "metric_key_1": value, "metric_key_2": value, ... } }`
- 所有 metric_key 字符串使用 `constants.py` 命名常量。

**前端规范（Vue 3 + Element Plus）**：
- 六组分组映射定义在 `frontend/src/constants/dashboard.js`，后端不感知分组。
- 首页组件按分组渲染六个 widget，每个 widget 独立处理自己的 metric_key 列表。
- 单个 widget 内 metric_value 为 null 时，降级显示"暂无数据"，不影响其他 widget。
- 提供"手动刷新"按钮，触发后端 `rebuild_summary_full()`。

**检查点**：
- ✅ 首页 API 无跨表 join？
- ✅ 分组逻辑在前端常量控制，后端无分组逻辑？
- ✅ null 值处理正确，不报错？

---

#### B-Phase 3：重构优化（Refactor）

- 提取六个 widget 为独立 Vue 组件文件。
- 确认所有 metric_key 使用 constants.py 命名常量，无魔术字符串。
- **新增错误码同步写入 `help_content.py`**。
- Phase 3 结束时执行全量回归，0 FAILED 方可标记 B 完成。

---

### Cluster C：模板 / 纪要 / 报告留痕

**前置条件**：A1 + A2 全量回归 0 FAILED。

**Agent 角色**：测试工程师 → 开发工程师 → 代码审查员

**核心目标**：在 v1.12 Jinja2 模板基础上扩展交付/复盘/纪要模板，报告/纪要/模板的创建与更新自动触发 snapshot 写入。

---

#### C-Phase 1：编写测试用例（Red）

**测试用例清单**：

```
[FR-C-001] test_report_save_triggers_snapshot          - 报告保存后，entity_snapshots 自动新增一条记录
[FR-C-002] test_minutes_save_triggers_snapshot         - 纪要保存后，entity_snapshots 自动新增一条记录
[FR-C-003] test_template_save_triggers_snapshot        - 模板保存后，entity_snapshots 自动新增一条记录
[FR-C-004] test_snapshot_version_no_increments         - 同一实体多次保存，version_no 单调递增
[FR-C-005] test_can_retrieve_any_historical_version    - 可通过 version_no 检索任意历史快照内容
[FR-C-006] test_minutes_linked_to_project_or_client   - 纪要必须关联项目或客户（至少一个非空），孤立纪要拒绝写入
[FR-C-007] test_minutes_fields_complete                - 纪要包含：标题、参与人、结论、待办、风险点五字段
[FR-C-008] test_template_types_covered                 - 模板库覆盖：方案、合同、交付、复盘、报价五类
[FR-C-009] test_snapshot_failure_returns_warning       - snapshot 写入失败时，API 返回 warning_code，主业务保存成功，日志记录
[FR-C-010] test_report_version_compare_api             - 提供接口返回同一实体两个版本的 snapshot_json，供前端对比
[FR-C-011] test_template_snapshot_contains_full_structure - 模板 snapshot_json 包含模板类型、标题、正文、变量定义、占位符配置完整结构，不仅存正文
```

**交付物**：`tests/test_cluster_c_snapshot_content.py`，运行全部 FAILED。

---

#### C-Phase 2：实现功能代码（Green）

**约束条件**：同 A1-Phase 2，逐一实现，每步停止报告。

**数据库迁移规范**：
- 新增 `meeting_minutes` 表：`id, title, participants, conclusions, action_items, risk_points, project_id, client_id, created_at, updated_at`
- `project_id` 与 `client_id` 至少一个非空，由业务层校验（不用数据库约束，保持迁移简洁）。
- 模板类型扩展：在现有 templates 表 `template_type` 字段补充枚举值（方案/合同/交付/复盘/报价），禁止修改已有字段。
- 迁移脚本：`migrations/v2.2_cluster_c.sql`

**模板 snapshot 内容约定（硬约束）**：
- 模板的 snapshot_json 必须包含完整结构：`{ "template_type": ..., "title": ..., "body": ..., "variables": [...], "placeholders": {...} }`
- 禁止只存正文，变量定义和占位符配置必须一并快照。

**核心函数签名**：

```python
def save_with_snapshot(entity_type: str, entity_id: int, data: dict, db_save_fn: Callable) -> tuple[bool, str | None]:
    """
    执行主业务保存，成功后触发 snapshot 写入。
    snapshot 失败时返回 warning_code，不阻断主流程。
    此函数为通用工具，C / D 均可复用。
    """

def get_version_diff(entity_type: str, entity_id: int, v1: int, v2: int) -> dict:
    """返回两个版本的 snapshot_json，供前端展示对比。"""
```

**检查点**：
- ✅ 三类实体保存均触发 snapshot？
- ✅ snapshot 失败返回 warning_code，不阻断主业务？
- ✅ 纪要关联校验（project_id / client_id 至少一个非空）在业务层实现？
- ✅ 模板 snapshot 包含完整结构（FR-C-011 通过）？

---

#### C-Phase 3：重构优化（Refactor）

- `save_with_snapshot` 提取为 `src/services/snapshot_service.py` 中的通用函数，C / D 均 import 使用。
- 确认 `meeting_minutes` 表相关错误码已写入 `help_content.py`。
- 模板类型新增枚举值写入 `constants.py` 白名单 `TEMPLATE_TYPE_WHITELIST`。
- Phase 3 结束时执行全量回归，0 FAILED 方可标记 C 完成。

---

### Cluster D：工具入口台账 + 客户线索台账

**前置条件**：A1 + A2 全量回归 0 FAILED。

**Agent 角色**：测试工程师 → 开发工程师 → 代码审查员

**核心目标**：工具入口台账记录"当前动作用哪个工具、状态如何、是否回填"；客户线索台账做最轻量跟进记录，不做营销 CRM。

---

#### D-Phase 1：编写测试用例（Red）

**测试用例清单**：

```
[FR-D-001] test_tool_entry_create                      - 工具入口记录可创建，包含动作名/工具名/状态/是否回填四字段
[FR-D-002] test_tool_entry_status_update               - 工具入口状态可更新（待处理/进行中/已完成/已回填）
[FR-D-003] test_tool_entry_backfill_flag               - is_backfilled 标记可独立更新，不影响其他字段
[FR-D-004] test_tool_entry_list_filter_by_status       - 可按状态过滤工具入口列表
[FR-D-005] test_lead_create_minimal                    - 线索记录可创建，仅需来源/状态/下次动作三字段（其余可空）
[FR-D-006] test_lead_link_to_client_or_project         - 线索可通过整数外键关联 client_id / project_id，均可空，不做额外漏斗实体表
[FR-D-007] test_lead_status_transitions                - 线索状态流转：初步接触→意向确认→转化为客户→无效
[FR-D-008] test_lead_list_filter_by_status             - 可按状态过滤线索列表
[FR-D-009] test_lead_does_not_duplicate_crm            - leads 表字段不重复 v1.x clients 表已有字段
```

**交付物**：`tests/test_cluster_d_tools_leads.py`，运行全部 FAILED。

---

#### D-Phase 2：实现功能代码（Green）

**约束条件**：同 A1-Phase 2，逐一实现，每步停止报告。

**数据库迁移规范**：
- 新增 `tool_entries` 表：`id, action_name, tool_name, status, is_backfilled, notes, created_at, updated_at`
- 新增 `leads` 表：`id, source, status, next_action, client_id, project_id, notes, created_at, updated_at`
- `leads.client_id` 和 `leads.project_id` 均为整数外键，可空。
- 迁移脚本：`migrations/v2.2_cluster_d.sql`

**字段范围硬约束（Claude Code 禁止自行扩展）**：
- `tool_entries`：严格限定 action_name / tool_name / status / is_backfilled / notes 五字段。
- `leads`：严格限定 source / status / next_action / client_id / project_id / notes 六字段。
- 禁止向营销 CRM 方向扩张（如漏斗阶段、意向分、触达记录等）。

**状态枚举**：
- `tool_entries.status`：`TOOL_STATUS_PENDING / IN_PROGRESS / DONE / BACKFILLED`（定义于 constants.py）
- `leads.status`：`LEAD_STATUS_INITIAL / INTENT_CONFIRMED / CONVERTED / INVALID`（定义于 constants.py）

**检查点**：
- ✅ leads 字段未重复 clients 表已有字段（FR-D-009 通过）？
- ✅ 所有状态枚举值在 constants.py 定义？
- ✅ 字段数量未超出硬约束？
- ✅ leads 关联使用整数外键而非文本引用？

---

#### D-Phase 3：重构优化（Refactor）

- 确认两张新表的所有错误码已同步写入 `help_content.py`。
- 确认所有状态值使用 constants.py 命名常量，无魔术字符串。
- Phase 3 结束时执行全量回归，0 FAILED 方可标记 D 完成。

---

## 🚨 关键约束（贯穿所有 Cluster）

1. **数据库变更原则**：所有变更通过新表或新列实现，禁止修改 v1.x 已有字段。
2. **命名常量**：所有业务规则常量集中在 `constants.py`，禁止魔术数字和魔术字符串。
3. **原子事务**：多步写操作使用原子事务，snapshot / summary 失败路径除外（按异常返回约定处理）。
4. **无静默失败**：所有 DB 写入和文件 IO 异常必须记录日志，禁止吞掉异常。
5. **异常返回约定**：见本文档"关键架构决策"一节，所有 Cluster 统一执行。
6. **help_content 同步**：每个 Cluster 引入的新错误码，必须在 Phase 3 同步写入 `help_content.py`，缺失视为 Phase 3 未完成。
7. **核心计算函数**：提取为独立可测试单元，不内嵌于 API handler 中。
8. **版本冻结规则**：沿用 v1.x 版本冻结机制，在 API 层强制执行。
9. **全量回归时机**：每个 Cluster 的 Phase 3 结束时执行一次，Phase 1/2 内部局部测试即可。
10. **TEMPLATE_TYPE_WHITELIST**：只在 constants.py 定义一次，Cluster C 新增枚举值在此处追加，不重复定义。

---

## 📦 最终交付清单

**迁移脚本**：
- [ ] `migrations/v2.2_cluster_a1.sql` — entity_snapshots 建表
- [ ] `migrations/v2.2_cluster_a2.sql` — dashboard_summary 建表
- [ ] `migrations/v2.2_cluster_c.sql` — meeting_minutes 建表 + 模板类型扩展
- [ ] `migrations/v2.2_cluster_d.sql` — tool_entries + leads 建表

**测试文件**：
- [ ] `tests/test_cluster_a1_snapshot.py`
- [ ] `tests/test_cluster_a2_summary.py`
- [ ] `tests/test_cluster_b_dashboard.py`
- [ ] `tests/test_cluster_c_snapshot_content.py`
- [ ] `tests/test_cluster_d_tools_leads.py`

**后端服务**：
- [ ] `src/services/snapshot_service.py`（含 create_snapshot / get_latest_snapshot / get_snapshot_history / save_with_snapshot / get_version_diff）
- [ ] `src/services/summary_service.py`（含 refresh_summary / rebuild_summary_full）
- [ ] `src/api/dashboard.py`
- [ ] `src/api/minutes.py`
- [ ] `src/api/tool_entries.py`
- [ ] `src/api/leads.py`

**配置与常量**：
- [ ] `constants.py` — 新增 entity_type 枚举、warning_code 常量、metric_key 常量、SUMMARY_TRIGGER_* 常量、状态枚举、TEMPLATE_TYPE_WHITELIST 追加项
- [ ] `backend/core/help_content.py` — 新增所有 v2.2 错误码条目（每个 Cluster Phase 3 必须同步）
- [ ] `frontend/src/constants/dashboard.js` — 六组分组映射常量

**进度与文档**：
- [ ] `PROGRESS.md` — Cluster 执行状态记录（含恢复入点）
- [ ] 全量回归 0 FAILED 运行记录（每个 Cluster Phase 3 各一份）

---

## 📋 PROGRESS.md 模板

```markdown
# 数标云管 v2.2 执行进度

## Cluster A1：snapshot 底座
- [ ] Phase 1 Red — 测试编写完成，全部 FAILED
- [ ] Phase 2 Green — 全部测试 PASSED
- [ ] Phase 3 Refactor — 重构完成，全量回归 0 FAILED，help_content.py 已同步
- **恢复入点**：从最后一个未通过的测试用例继续 Green 阶段。

## Cluster A2：summary 底座（依赖 A1 完成）
- [ ] Phase 1 Red
- [ ] Phase 2 Green
- [ ] Phase 3 Refactor — 全量回归 0 FAILED，help_content.py 已同步

## Cluster B：首页仪表盘（依赖 A1+A2 完成）
- [ ] Phase 1 Red
- [ ] Phase 2 Green
- [ ] Phase 3 Refactor — 全量回归 0 FAILED，help_content.py 已同步

## Cluster C：模板 / 纪要 / 报告留痕（依赖 A1+A2 完成）
- [ ] Phase 1 Red
- [ ] Phase 2 Green
- [ ] Phase 3 Refactor — 全量回归 0 FAILED，help_content.py 已同步

## Cluster D：工具入口台账 + 客户线索台账（依赖 A1+A2 完成）
- [ ] Phase 1 Red
- [ ] Phase 2 Green
- [ ] Phase 3 Refactor — 全量回归 0 FAILED，help_content.py 已同步

## 最终交付
- [ ] 全量回归（v1.0 - v2.2）0 FAILED
- [ ] help_content.py 全部新增错误码已验证
```

---

## 🎯 开始执行

请现在开始 **Cluster A1 — Phase 1：编写测试用例**。

先创建 `PROGRESS.md`，再输出 `tests/test_cluster_a1_snapshot.py`，确认全部 7 个测试用例存在且运行后全部显示 FAILED。
