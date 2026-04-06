## Why

v1.2 已完成基础财务记账、合同管理、报价单和客户资产等功能，但缺少三大关键能力：外包协作费用的合规记录与税务处理、发票台账的精细化管理（进销项税额计算与季度统计）、以及基于合同的 90 天现金流预测。这些是单人 ERP 从"记账工具"升级为"经营决策辅助"的必要功能，也是 v1.3 产品路线图的核心里程碑。

## What Changes

- **数据库迁移（簇 A）**：`contracts` 新增 `expected_payment_date`、`payment_stage_note` 字段；`finance_records` 新增 `outsource_name`、`has_invoice`、`tax_treatment`、`invoice_direction`、`invoice_type`、`tax_rate`、`tax_amount` 字段，并建立三个索引
- **外包协作（FR-302）**：新增 `outsourcing` 财务分类，当分类为外包时强制校验外包方姓名、是否取得发票、税务处理方式；非外包时三个字段强制置 NULL（创建和更新接口均生效）
- **发票台账（FR-303）**：当发票号码非空时校验发票方向/类型/税率，`tax_amount` 由后端计算（禁止前端写入）；发票号码为空时四个发票字段强制置 NULL；新增 `GET /api/v1/finance/tax-summary` 季度增值税统计接口
- **现金流预测（FR-301）**：新增 `GET /api/v1/cashflow/forecast` 接口，基于 active/executing 状态合同的应收账款和最近 3 个月历史支出，生成 90 天按周维度的预测
- **前端联调（簇 F）**：财务录入页动态字段（外包/发票）、合同编辑页新字段、看板现金流折线图、财务列表发票台账 Tab、看板季度增值税卡片
- **全局重构（簇 G）**：常量集中管理、函数拆分、日志覆盖验证

## Capabilities

### New Capabilities
- `outsource-collaboration`: 外包费用分类的字段校验逻辑（创建/更新接口一致校验，非外包强制置 NULL）
- `invoice-ledger`: 发票字段校验、税额自动计算（Decimal 精度）、季度增值税统计接口
- `cashflow-forecast`: 90 天现金流预测——自然周分组、应收账款分配、历史支出周均化

### Modified Capabilities
- `db-migrations`: v1.3 迁移脚本（contracts 和 finance_records 新增字段 + 索引）
- `finance-management`: 新增外包分类枚举、发票字段校验逻辑、创建/更新接口变更
- `dashboard`: 新增现金流折线图组件、季度增值税汇总卡片

## Impact

- **数据库**：两张表新增 9 个字段、3 个索引，需迁移脚本和回滚验证
- **API**：新增 2 个 GET 接口（`/cashflow/forecast`、`/finance/tax-summary`）；修改 2 个写入接口（finance_records 的 POST 和 PUT）的校验逻辑
- **前端**：财务录入页动态字段交互、合同编辑页新字段、看板新增 2 个组件、财务列表新增 Tab
- **新增文件**：`backend/core/finance_utils.py`、`backend/core/cashflow_utils.py`、`backend/migrations/v1_3_migrate.py`、4 个测试文件
- **依赖**：无新增第三方依赖
