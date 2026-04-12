## Why

数标云管系统 v1.0~v1.4 已覆盖客户管理、项目管理、合同管理、财务核算、利润分析等核心业务。但在项目交付全生命周期中，需求版本管理、验收流程、交付物跟踪、版本发布记录、变更单/增补单管理、售后维护期管理仍然缺失。这些环节是项目交付闭环的关键——没有需求基线就无法控制变更，没有验收记录就无法触发收款，没有维护期管理就无法跟踪售后服务。v1.5 填补这些空白。

## What Changes

- 新增 8 张数据库表：`requirements`、`requirement_changes`、`change_orders`、`acceptances`、`deliverables`、`account_handovers`、`releases`、`maintenance_periods`
- 新增 6 个后端功能模块（FR-501~FR-506），含完整 CRUD 接口、状态流转、事务约束
- 新增"唯一性硬约束"：需求版本 `is_current` 和发布记录 `is_current_online` 在同项目下仅允许一条为 True，事务级别保证
- 新增"禁止删除"规范：`acceptances`、`deliverables`、`releases` 三个实体的 DELETE 接口一律返回 HTTP 405
- 新增"账号交接密码检测"：通过字段名子串匹配拦截密码类字段，不扫描字段值
- 扩展事件驱动逾期检查：在 v1.2 已有逻辑基础上追加维护期到期自动过期和提醒生成
- 新增前端项目详情页 6 个 Tab 和合同详情页变更单 Tab
- 扩展看板接口：追加 `active_maintenance_count` 字段

## Capabilities

### New Capabilities
- `requirement-management`: 需求版本 CRUD、需求变更记录、当前有效版本唯一性维护（FR-501）
- `acceptance-management`: 验收记录 CRUD、验收通过联动收款提醒、结果不可修改约束（FR-502）
- `deliverable-management`: 交付物 CRUD、账号交接条目、密码字段名检测（FR-503）
- `release-management`: 版本发布 CRUD、当前线上版本唯一性维护、项目详情追加 current_version（FR-504）
- `change-order-management`: 变更单完整 CRUD、状态流转白名单、合同实际应收合计、编号自动生成（FR-505）
- `maintenance-management`: 售后/维护期 CRUD、续期事务、到期自动过期、到期提醒生成（幂等）（FR-506）

### Modified Capabilities
- `event-driven-checks`: 追加维护期到期状态过期和到期提醒生成（幂等保护）
- `dashboard`: 响应追加 `active_maintenance_count` 字段
- `project-management`: 项目详情响应追加 `current_version` 字段；项目详情页新增 6 个 Tab

## Impact

- **数据库**: 8 张新表、20+ 索引、多个外键约束
- **后端新增文件**: `backend/core/requirement_utils.py`、`acceptance_utils.py`、`deliverable_utils.py`、`release_utils.py`、`change_order_utils.py`、`maintenance_utils.py`（6 个工具模块）
- **后端新增文件**: `backend/migrations/v1_5_migrate.py`（迁移脚本）
- **后端新增文件**: `backend/models/enums.py` 追加 8 个新枚举类
- **测试新增文件**: `tests/test_migration_v15.py`、`test_requirements.py`、`test_acceptances.py`、`test_deliverables.py`、`test_releases.py`、`test_change_orders.py`、`test_maintenance.py`（7 个测试文件）
- **前端**: 项目详情页新增 6 个 Tab，合同详情页新增变更单 Tab
- **依赖**: 无新增外部依赖（SQLite + FastAPI 已足够）
