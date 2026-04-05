## Why

v1.1 定义了四个核心模块：提醒管理、文件索引、财务留痕扩展、默认数据模板。经代码审查，提醒管理已完整实现，但其余三个模块存在缺口：文件索引缺少 `file_group_id` 版本分组机制；财务记录缺少 `settlement_status` 结算状态字段及前端 UI；系统默认模板和初始化锁机制（`settings` 表 + `system_initialized`）完全未实现。这些缺口导致 v1.1 无法闭环，文件版本管理、垫付/借款结算追踪、系统首次初始化均无法正常工作。

## What Changes

- 为 `file_indexes` 表新增 `file_group_id` 字段（UUID），实现同文件多版本分组管理
- 新增版本时自动将同组原有效版本的 `is_current` 设为 false
- 为 `finance_records` 表新增 `settlement_status` 字段（枚举：open/partial/closed）
- 前端财务表单新增结算状态下拉框（仅当资金来源为个人垫付/借款时显示且必填）
- 新建 `settings` 表，含 `system_initialized` 布尔字段
- 系统启动时检查 `system_initialized`，为 false 则写入默认提醒配置和默认文件索引清单，完成后设为 true
- 引入 alembic 管理增量数据库迁移，替代 `create_all()` 自动建表

## Capabilities

### New Capabilities
- `file-versioning`: 文件索引版本管理，基于 file_group_id 的分组、版本切换、历史版本查看
- `finance-settlement`: 财务结算状态追踪，垫付/借款的 open/partial/closed 状态管理及前端 UI
- `system-defaults`: 系统默认数据模板与初始化锁，首次启动自动写入默认提醒配置和文件索引清单
- `db-migrations`: Alembic 数据库迁移框架，支持增量 schema 变更和历史数据零损坏

### Modified Capabilities
- `finance-management`: 新增 settlement_status 字段和资金来源/结算状态校验规则（FIN-006 至 FIN-010）

## Impact

- **Backend models**: `file_index.py` 新增 `file_group_id` 字段；`finance.py` 新增 `settlement_status` 字段；新建 `settings.py` 模型
- **Backend schemas**: 对应新增/修改 Pydantic schema
- **Backend CRUD**: `file_index.py` 新增版本管理逻辑；`finance.py` 新增结算状态校验；新建 `settings.py` CRUD
- **Backend API**: 文件索引新增版本端点；财务端点新增 settlement_status 校验；新建 settings 初始化端点
- **Backend services**: `seed.py` 改造为基于 system_initialized 的条件初始化；新建 alembic 迁移脚本
- **Frontend**: `Finances.vue` 新增结算状态 UI；`FileIndexes.vue` 新增版本管理 UI
- **Database**: SQLite 新增 3 个字段 + 1 张表，历史数据通过 alembic 迁移脚本填充默认值
