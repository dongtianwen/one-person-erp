## Why

v1.0~v1.8 已完成报价→合同→项目→财务→发票的完整链路，但缺少"链路健康监控"和"成本侧数据"能力。财务数据可能出现合同/收款/发票不一致而不自知；里程碑收款逾期无法预警；项目实际成本（工时、固定成本、进项发票）缺少汇总视图，无法判断项目是否盈利。v1.9 在现有链路上加装"仪表盘和预警灯"，确保数据跑得稳、不亏钱、不被拖死。

## What Changes

- **三表数据一致性校验**：只读校验合同/收款/发票三表差异（payment_gap / invoice_gap / unlinked_payment / invoice_payment_mismatch），提供单合同和全局报告接口
- **收款逾期预警**：基于里程碑 payment_due_date 检测逾期，计算客户风险等级（normal/warning/high），批量刷新写入客户表风险字段
- **固定成本登记 CRUD**：新增 fixed_costs 表，支持按月汇总（业务视角原始金额，不摊销），可选关联项目
- **项目粗利润视图**：汇总实收/工时成本/固定成本/进项发票成本，计算 gross_profit 和 gross_margin，支持缓存刷新
- **进项发票记录 CRUD**：新增 input_invoices 表（与销项 invoices 表独立），支持关联项目、按类别汇总
- **前端联调**：财务管理页新增 4 个 Tab（数据核查/固定成本/进项发票/利润分析），首页看板新增逾期预警和项目粗利润区块，客户列表显示风险标签

## Capabilities

### New Capabilities
- `consistency-check`: 三表（合同/收款/发票）数据一致性只读校验，四维度检测差异
- `overdue-warning`: 里程碑收款逾期预警与客户风险等级计算（纯展示，不拦截）
- `fixed-cost`: 固定成本 CRUD，按月汇总（原始金额不摊销），可选关联项目
- `project-profit`: 项目粗利润视图（实收-工时成本-固定成本-进项发票），缓存机制
- `input-invoice`: 进项发票 CRUD（独立于销项发票），关联项目，按类别汇总
- `risk-control-constants`: v1.9 风险控制与成本视图全局常量定义

### Modified Capabilities
- `db-migrations`: 新增 fixed_costs 和 input_invoices 表，扩展 customers（风险字段）和 projects（利润缓存字段）
- `customer-management`: 新增客户风险等级展示字段（overdue_milestone_count / overdue_amount / risk_level），仅展示不拦截
- `project-management`: 新增项目利润缓存字段（cached_revenue / cached_gross_profit 等）
- `dashboard`: 首页新增逾期预警区块和项目粗利润 Top 5 列表
- `finance-management`: 财务管理页新增数据核查、固定成本、进项发票、利润分析 Tab

## Impact

- **数据库**：2 张新表（fixed_costs / input_invoices），customers 表新增 3 字段，projects 表新增 7 字段，7 个新索引
- **后端新增文件**：consistency_utils.py / overdue_utils.py / fixed_cost_utils.py / profit_utils.py / input_invoice_utils.py / v1_9_migrate.py
- **后端修改文件**：constants.py（追加常量）、enums.py（追加枚举）、路由注册
- **后端新增路由**：/api/v1/finance/consistency-check、/api/v1/finance/overdue-warnings、/api/v1/fixed-costs、/api/v1/input-invoices、/api/v1/projects/{id}/profit、/api/v1/finance/profit-overview
- **前端修改**：Finances.vue（新增 Tab）、Dashboard.vue（新增区块）、Customers.vue（风险标签）、ProjectDetail（利润分析 Tab）
- **测试新增**：test_migration_v19.py / test_consistency.py / test_overdue.py / test_fixed_costs.py / test_profit.py / test_input_invoices.py
