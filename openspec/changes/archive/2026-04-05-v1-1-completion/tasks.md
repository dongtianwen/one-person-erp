## 1. Alembic 数据库迁移框架

- [x] 1.1 在 backend 目录初始化 alembic（`alembic init alembic`）
- [x] 1.2 配置 `alembic.ini` 连接 SQLite 数据库
- [x] 1.3 配置 `env.py` 支持 SQLAlchemy 模型元数据
- [x] 1.4 生成初始迁移脚本（从现有数据库自动检测表结构）
- [x] 1.5 验证 `alembic upgrade head` 可在新库上重建所有表
- [x] 1.6 在 FastAPI lifespan 事件中集成自动迁移逻辑

## 2. file_group_id 字段与版本管理

- [x] 2.1 生成 alembic 迁移：为 `file_indexes` 表新增 `file_group_id` 列（String(36)）
- [x] 2.2 迁移脚本回填已有数据的 `file_group_id`（按 file_name + file_type 分组生成 UUID）
- [x] 2.3 更新 `FileIndex` model 新增 `file_group_id` 字段定义
- [x] 2.4 更新 `FileIndexCreate` / `FileIndexUpdate` schema 支持 `file_group_id`
- [x] 2.5 修改 `CRUDFileIndex.create` 自动生成 UUID 作为 `file_group_id`
- [x] 2.6 修改 `CRUDFileIndex.create_version` 按 `file_group_id` 降级旧版本（替代 name+type 匹配）
- [x] 2.7 修改 `CRUDFileIndex.get_versions` 按 `file_group_id` 查询
- [x] 2.8 前端 `FileIndexes.vue` 新增版本表单传入 `file_group_id`
- [x] 2.9 前端列表按 `file_group_id` 分组展示，支持展开/收起

## 3. settlement_status 财务结算状态

- [x] 3.1 生成 alembic 迁移：为 `finance_records` 表新增 `settlement_status` 列（String(20), nullable）
- [x] 3.2 更新 `FinanceRecord` model 新增 `settlement_status` 字段和 `SettlementStatus` 枚举
- [x] 3.3 更新 `FinanceRecordCreate` / `FinanceRecordUpdate` schema 新增 `settlement_status` 字段
- [x] 3.4 在 CRUD 层新增校验：funding_source 为 personal_advance/loan 时 settlement_status 必填
- [x] 3.5 前端 `Finances.vue` 表单新增结算状态下拉框（条件显示）
- [x] 3.6 前端列表新增结算状态列（仅垫付/借款记录显示）
- [x] 3.7 月度报表接口新增资金来源维度汇总和未结清统计
- [x] 3.8 仪表盘接口新增未结清垫付/借款预警指标

## 4. settings 表与系统默认模板

- [x] 4.1 新建 `settings` model（key String unique, value Text, TimestampMixin）
- [x] 4.2 生成 alembic 迁移创建 `settings` 表
- [x] 4.3 新建 `settings.py` CRUD（get_by_key, set_key, delete_key）
- [x] 4.4 改造 `seed.py`：检查 `system_initialized` 键，为 false 则执行初始化
- [x] 4.5 初始化完成后写入 `system_initialized = true` 到 settings 表
- [x] 4.6 更新默认文件索引种子数据，使用正确 FileType 枚举值和 file_group_id
- [x] 4.7 更新默认提醒配置种子数据，使用正确 ReminderType 枚举值
- [x] 4.8 在 FastAPI lifespan 事件中调用 seed 逻辑（替代原有 create_all 后的直接调用）

## 5. 验证与测试

- [x] 5.1 运行 `pytest` 确保所有现有测试通过
- [x] 5.2 新增 file_group_id 版本管理单元测试
- [x] 5.3 新增 settlement_status 校验单元测试
- [x] 5.4 新增 system_initialized 初始化锁测试
- [x] 5.5 手动验证 alembic 迁移在空库和已有库上均正常工作
- [x] 5.6 手动验证前端文件索引版本管理和财务结算状态 UI
