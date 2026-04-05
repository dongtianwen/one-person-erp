## Context

v1.1 定义了四个模块：提醒管理、文件索引、财务留痕扩展、默认数据模板。当前状态：
- 提醒管理：完整实现（model/schema/CRUD/API/frontend）
- 文件索引：已实现基础 CRUD 和版本管理，但使用 `file_name + file_type` 隐式分组，缺少 `file_group_id` 显式 UUID 分组
- 财务扩展：已实现 `funding_source`/`business_note`/`related_record_id`/`related_note`，但缺少 `settlement_status` 字段
- 默认模板：`seed.py` 已存在并写入默认数据，但缺少 `system_initialized` 初始化锁机制，无 `settings` 表
- 数据库迁移：无 alembic，依赖 `Base.metadata.create_all()` 自动建表

技术栈：FastAPI + SQLAlchemy 2.0 (async) + SQLite + Vue 3 + Element Plus

## Goals / Non-Goals

**Goals:**
- 为 file_indexes 引入 `file_group_id`（UUID）显式分组，替代当前的 name+type 隐式分组
- 为 finance_records 新增 `settlement_status` 字段，完成垫付/借款结算闭环
- 引入 `settings` 表 + `system_initialized` 锁，改造 seed.py 为条件初始化
- 引入 alembic 管理增量迁移，历史数据零损坏

**Non-Goals:**
- 不修改已完成的提醒管理模块
- 不引入 v1.2 功能（报价单、客户资产、事件驱动逾期检查）
- 不迁移到其他数据库（保持 SQLite）
- 不实现文件实际上传/存储（仅管理元数据）

## Decisions

### 1. file_group_id 使用 UUID4 字符串存储

**Decision**: 在 `file_indexes` 表新增 `file_group_id` 列（String(36)），存储 UUID4 字符串。

**Rationale**: 
- SQLite 无原生 UUID 类型，String(36) 兼容性最佳
- 新建文件时自动生成 UUID4 作为 group_id
- 新增版本时复用原记录的 group_id
- 相比 name+type 隐式分组，UUID 支持文件重命名而不破坏分组关系

**Migration**: 对已有数据，按 `(file_name, file_type)` 分组，每组生成一个 UUID 回填到 `file_group_id`。

### 2. settlement_status 仅在特定 funding_source 下生效

**Decision**: `settlement_status` 字段在 model 层始终存在，但业务校验仅当 `funding_source` 为 `personal_advance` 或 `loan` 时强制。

**Rationale**: 符合 PRD 规则 FIN-007，其他资金来源的记录该字段为 NULL，前端条件显示。

### 3. settings 表使用通用 key-value 设计

**Decision**: `settings` 表采用 `key` (String, unique) + `value` (Text/JSON) 设计，而非每配置一个字段。

**Rationale**: 扩展性强，后续新增配置无需改表结构。`system_initialized` 作为 `key="system_initialized"` 的布尔值存储。

### 4. seed.py 改造为条件初始化

**Decision**: 启动时检查 `settings` 表中 `system_initialized` 键，为 false 则执行默认数据写入，完成后写入 `system_initialized=true`。

**Rationale**: 满足 PRD 初始化锁机制要求，防止用户删除默认数据后误触发重建。

### 5. Alembic 异步支持

**Decision**: Alembic 配置使用 `asyncio` 模式，`run_migrations_online` 中使用 `create_async_engine`。

**Rationale**: 项目使用 SQLAlchemy async session，迁移脚本必须兼容异步引擎。SQLite 的 alembic 异步支持有限，但基础 DDL 操作（ADD COLUMN, CREATE TABLE）在 SQLite 中通过同步连接执行更稳定。

**Alternative considered**: 使用同步引擎执行迁移。SQLite 对异步 DDL 支持不完善，最终选择同步引擎执行迁移（alembic 默认行为），与运行时异步引擎分离。

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| 已有数据的 file_group_id 回填可能因 name+type 组合不唯一导致分组错误 | 迁移脚本按 `(file_name, file_type, created_at)` 排序后分组，同一组合共享一个 UUID |
| Alembic 与 SQLite 的 ALTER TABLE 限制（SQLite 不支持 DROP/ALTER COLUMN） | 仅使用 ADD COLUMN 和 CREATE TABLE，符合 PRD 数据完整性约束 |
| seed.py 条件初始化在并发启动时可能重复执行 | 使用数据库事务 + 唯一键约束保证幂等，重复插入被忽略 |
| settlement_status 为 NULL 的历史记录影响统计查询 | 统计查询使用 `COALESCE(settlement_status, 'closed')` 或 `IS NOT NULL` 过滤 |
| 迁移过程中数据库不一致 | 每次迁移在事务中执行，失败自动回滚 |
