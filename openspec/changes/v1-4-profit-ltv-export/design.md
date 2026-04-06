## Context

当前系统（v1.3）已完成核心 CRUD、财务记账、发票台账、现金流预测、外包协作等功能。系统基于 FastAPI + SQLite + Vue.js 构建，使用 Alembic 管理数据库迁移。finance_records 表通过 `related_contract_id` 关联合同，但支出记录无法直接关联到项目，导致项目成本无法精确核算。导出功能完全缺失，用户需手动截图或复制数据用于汇报。

## Goals / Non-Goals

**Goals:**
- 为 finance_records 支出记录增加项目关联能力，实现项目维度的收入/成本/利润核算
- 实现客户生命周期价值（LTV）汇总，辅助客户关系决策
- 提供五种业务数据的 Excel/PDF 导出，支持中文字体正确渲染
- 保持全部现有接口的向后兼容性（仅追加字段，不修改/删除）
- 核心计算函数可独立于 FastAPI 应用直接调用和测试

**Non-Goals:**
- 不实现多币种支持（固定 CNY）
- 不实现导出数据的定时任务/自动邮件
- 不实现导出模板自定义
- 不修改现有的利润计算逻辑（v1.3 已有的财务统计不受影响）
- 不实现 PDF 中的图表/图形渲染（仅表格数据）

## Decisions

### D1: related_project_id 仅限支出记录

**决定**：`related_project_id` 字段加在 `finance_records` 表上，允许所有记录类型设置，但前端仅在支出类型时展示。

**理由**：收入通过关联合同间接关联项目（合同已有 project_id），无需重复关联。字段允许所有记录类型设置是为了数据模型灵活性，但前端和业务逻辑仅在支出类型时使用此关联。

**替代方案**：创建独立的 project_expense 关联表 → 过度设计，v1.4 阶段直接外键更简洁。

### D2: 利润计算为实时计算，不持久化

**决定**：项目利润（收入、成本、利润、利润率）全部实时从 finance_records 聚合计算，不存储到 projects 表。

**理由**：
- 数据量小（单人 ERP），100 个项目的利润汇总 < 1 秒完全可行
- 避免缓存一致性问题和刷新逻辑
- PRD 明确要求"实时计算，不存储到数据库"

**替代方案**：定时物化视图/缓存表 → 引入一致性风险，单人 ERP 无需此复杂度。

### D3: 导出依赖库选型

**Excel**: `openpyxl`
- 轻量纯 Python，无需 LibreOffice
- 社区活跃，中文字体支持良好
- PRD 明确指定

**PDF**: `reportlab`
- 选择 reportlab 而非 weasyprint
- reportlab 更轻量，无系统级依赖（weasyprint 依赖 GTK/Pango）
- reportlab 可通过注册 TTF 字体完美支持中文
- 将使用系统自带的中文字体（如 SimHei、Microsoft YaHei）

### D4: 导出接口为单一 POST 端点

**决定**：`POST /api/v1/export/{export_type}` 统一端点，通过路径参数区分导出类型。

**理由**：
- 导出类型有限且固定（5 种），无需动态路由
- POST 方法支持请求体传递筛选参数（年/月/季度）
- 返回二进制文件流，Content-Disposition 触发浏览器下载

### D5: 核心函数提取为独立模块

**决定**：
- `backend/core/profit_utils.py` — 利润计算
- `backend/core/customer_utils.py` — 客户 LTV
- `backend/core/export_utils.py` — 导出生成

**理由**：PRD 要求这些函数可在测试中直接 import 调用，不依赖 FastAPI 应用启动。独立模块实现关注点分离，便于单元测试。

### D6: 迁移脚本独立于 Alembic

**决定**：使用 `backend/migrations/v1_4_migrate.py` 独立脚本，不通过 Alembic 自动生成。

**理由**：与 v1.3 保持一致的迁移方式，直接执行 SQL 语句，便于前后数据对比验证。

## Risks / Trade-offs

- **[PDF 中文字体]** → 在 Windows 开发环境使用 SimHei/Microsoft YaHei，部署时需确认字体可用，或内嵌字体文件。缓解：export_utils 初始化时检测字体可用性，不可用时回退到基础字体并记录警告。
- **[导出大数据量]** → EXPORT_MAX_ROWS_PER_SHEET = 10000 限制单 Sheet 行数，避免内存溢出。超出时分多个 Sheet 或提示用户缩小时间范围。
- **[项目列表性能]** → 100 个项目利润汇总 < 1 秒的目标需在测试中验证。缓解：利用 finance_records 的 related_project_id 索引和 related_contract_id 索引进行高效查询。
- **[迁移安全性]** → 迁移前快照 + 迁移后验证五项检查，确保零数据丢失。缓解：测试用例覆盖迁移前后数据一致性。
