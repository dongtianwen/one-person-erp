## Context

数标云管系统（ShuBiao Cloud ERP）是一个面向小型 IT 服务公司的单用户 ERP 系统，基于 Python/FastAPI + SQLite + Streamlit 构建。v1.0~v1.4 已实现客户管理、项目管理、合同管理、财务核算、利润分析、数据导出等核心功能。v1.5 填补项目交付生命周期中的需求管理、验收、交付物、版本发布、变更单、售后维护六个环节。

当前技术栈：
- 后端：FastAPI + SQLite（WAL 模式）+ SQLAlchemy
- 前端：Streamlit
- 测试：pytest + 内存 SQLite
- 日志：RotatingFileHandler（10MB/文件，保留 30 个）

关键约束：单用户场景，无并发竞争，但事务完整性仍需保证（单次操作内多表写入的原子性）。

## Goals / Non-Goals

**Goals:**
- 新增 8 张数据库表，覆盖需求/验收/交付物/版本/变更单/维护期
- 实现同项目唯一性约束（`is_current`、`is_current_online`）的事务级保证
- 实现变更单状态流转白名单的严格校验
- 实现账号交接条目的字段名密码检测（不扫描值）
- 扩展事件驱动逾期检查覆盖维护期场景
- 前端项目详情页新增 6 个 Tab，合同详情页新增变更单 Tab

**Non-Goals:**
- 不引入新的外部依赖（纯 Python 标准库 + 已有依赖即可）
- 不修改已有接口的返回结构（仅追加字段）
- 不实现多用户权限或角色系统
- 不实现文件上传/存储（交付物仅记录元数据）
- 不实现 WebSocket 或实时推送

## Decisions

### D1：唯一性约束在应用层实现

SQLite 不支持部分唯一索引（`WHERE is_current = TRUE`），且单用户场景无并发竞争。选择在应用层通过事务内 `UPDATE ... SET is_current = FALSE WHERE project_id = ?` + `INSERT/UPDATE is_current = TRUE` 实现唯一性。

**替代方案**：使用触发器 → 拒绝，触发器逻辑隐藏在数据库层，调试困难，且与"业务逻辑在应用层"的设计原则冲突。

### D2：变更单编号在事务内生成

`order_no` 格式 `BG-YYYYMMDD-001`，序号基于当日已有数量 +1。在创建事务内 `SELECT COUNT` + 拼接 + `INSERT`，单用户场景不存在并发重复风险。

**替代方案**：独立序号表 → 拒绝，增加复杂度但无实际收益（单用户）。

### D3：密码检测采用字段名子串匹配

`FORBIDDEN_FIELD_PATTERNS = ["password", "pwd", "secret", "passwd", "token"]`，将 JSON 请求体中所有 key 转小写后检查是否包含上述子串。仅检测 key，不扫描 value。

**替代方案**：正则匹配 value 中的密码模式 → 拒绝，PRD 明确禁止扫描字段值。

### D4：禁止删除通过 HTTP 405 实现

`acceptances`、`deliverables`、`releases` 三个实体的 DELETE 端点注册但直接返回 405，而非不注册路由。这样 API 文档中会显示该端点存在但不可用，更符合 REST 语义。

### D5：事件驱动检查采用追加模式

在 v1.2 已有的 `event_driven_check()` 函数末尾追加维护期检查逻辑，不重写原有函数。保证 v1.1/v1.2 的提醒升级和报价单过期逻辑不受影响。

### D6：核心函数提取为独立工具模块

每个功能模块提取核心计算函数到独立的 `*_utils.py` 文件中，不依赖 FastAPI 应用实例，可直接在测试中 import 调用。这符合 v1.4 已建立的模式（`profit_utils.py`、`customer_utils.py`、`export_utils.py`）。

### D7：维护期提醒采用幂等保护

通过 `related_object_type = 'maintenance_period'` + `related_object_id = period_id` 判断 reminders 表中是否已存在对应提醒，避免重复生成。

### D8：前端 Tab 追加模式

在 Streamlit 的 `st.tabs()` 中追加新 Tab，不修改已有 Tab 的顺序和内容。变更单管理按职责分离原则：合同页完整 CRUD，项目页只读摘要。

## Risks / Trade-offs

- **[事务回滚覆盖面]** 8 张新表中有多处需要在同一事务中完成多步操作（需求版本切换、续期事务等）。→ 缓解：每个事务操作都有对应的原子性回滚测试（test_*_transaction_rollback）
- **[变更单状态流转复杂度]** 5 种状态 × 多条合法路径，容易遗漏非法路径校验。→ 缓解：使用全局常量 `CHANGE_ORDER_VALID_TRANSITIONS` 字典驱动校验，所有路径均有测试覆盖
- **[维护期提醒幂等性]** 事件驱动检查每次调用都会查询 reminders 表。→ 缓解：单用户场景下调用频率低，查询开销可忽略；幂等保护防止重复创建
- **[SQLite 外键限制]** SQLite 的 `ALTER TABLE` 不支持 `ADD FOREIGN KEY`。→ 缓解：`change_orders.requirement_change_id` 的外键约束通过应用层保证，建表时不声明该外键
- **[Streamlit Tab 数量]** 项目详情页 Tab 从原有数量增加到 6+ 个。→ 缓解：Streamlit `st.tabs()` 原生支持多 Tab，无性能问题
