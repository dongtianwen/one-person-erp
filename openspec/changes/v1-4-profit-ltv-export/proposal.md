## Why

v1.3 已完成外包协作、发票台账、现金流预测等功能，但项目维度的盈利能力分析缺失（无法按项目核算收入/成本/利润），客户价值无法量化（缺少生命周期价值指标），且所有业务数据仅限在线查看，无法导出为 Excel/PDF 用于离线汇报或归档。v1.4 补齐这三大能力，使系统从"记录工具"升级为"决策辅助工具"。

## What Changes

- **新增 `related_project_id` 字段**：`finance_records` 表新增可空外键，关联支出记录到具体项目，为项目成本核算提供数据基础
- **项目利润核算**（FR-401）：实现项目维度的收入/成本/利润/利润率计算，支持项目详情页和列表页展示
- **客户生命周期价值**（FR-402）：汇总客户历史合同总额、实收金额、合作项目数、平均项目金额、首次/最近合作日期
- **数据导出**（FR-403）：支持五种数据类型（月度财务报表、客户列表、项目列表、合同列表、增值税台账）的 Excel 和 PDF 导出
- **前端联调**：项目利润面板、客户价值面板、财务录入关联项目字段、数据导出页面
- **全局重构**：常量集中、函数长度/复杂度检查、重复逻辑合并、日志覆盖、PDF 中文字体验证

## Capabilities

### New Capabilities
- `project-profit`: 项目利润核算——包含收入/成本/利润/利润率的计算逻辑、API 接口、前端展示
- `customer-ltv`: 客户生命周期价值——包含 LTV 指标计算、API 接口、前端展示
- `data-export`: 数据导出——包含五种业务数据的 Excel/PDF 导出、前端导出页面
- `finance-project-link`: 财务记录关联项目——finance_records 新增 related_project_id 字段及迁移

### Modified Capabilities
- `project-management`: 项目列表和详情接口追加利润相关字段（profit、profit_margin）
- `customer-management`: 客户详情接口追加 lifetime_value 对象
- `finance-management`: 财务收支创建/更新接口支持 related_project_id 字段
- `db-migrations`: 新增 v1_4_migrate.py 迁移脚本

## Impact

- **数据库**：`finance_records` 表新增 `related_project_id` 列（INTEGER NULL）及索引
- **后端新增文件**：`backend/core/profit_utils.py`、`backend/core/customer_utils.py`、`backend/core/export_utils.py`、`backend/migrations/v1_4_migrate.py`
- **后端新增依赖**：`openpyxl`（Excel 导出）、`reportlab` 或 `weasyprint`（PDF 导出，需支持中文字体）
- **后端 API 新增接口**：
  - `GET /api/v1/projects/{id}/profit`
  - `GET /api/v1/customers/{id}/lifetime-value`
  - `POST /api/v1/export/{export_type}`
- **后端 API 修改接口**：`GET /api/v1/projects`（追加利润字段）、`GET /api/v1/customers/{id}`（追加 lifetime_value）
- **前端新增页面**：数据导出页面
- **前端修改页面**：项目详情/列表页、客户详情页、财务收支录入页
- **新增测试文件**：`test_migration_v14.py`、`test_project_profit.py`、`test_customer_ltv.py`、`test_export.py`
