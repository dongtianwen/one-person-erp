## Why

数标云管 v1.0~v1.5 已完成客户管理、项目管理、合同管理、财务管理等基础能力，但缺少报价单（Quotation）全流程支持。一人软件公司需要在与客户签订合同前，通过标准化的报价单明确需求、工期、费用明细，并能一键将已接受的报价转为合同草稿。当前系统无法生成报价、无法追踪报价状态流转、无法将报价与合同关联，导致业务流程断链。

## What Changes

- 新增报价单 CRUD：创建/查询/更新/删除报价单，自动生成编号（BJ-YYYYMMDD-序号）
- 新增报价金额计算引擎：人工成本、直接成本、风险缓冲、折扣、税额 → 小计/总价，精度 2 位小数
- 新增报价预览接口：POST /api/v1/quotes/preview，纯计算不写库，与正式保存共用计算逻辑
- 新增报价状态流转：draft → sent → accepted/rejected，expired 由事件驱动自动设置
- 新增报价转合同：accepted 报价单一键转合同草稿，同事务原子操作，一张报价只能转一次
- 新增报价明细项：支持按报价添加 labor/design/testing/deployment/outsource/other 类型明细
- 新增报价变更日志：字段修改/状态变更/转合同均记录 before/after 快照
- 新增数据库迁移：quotations / quotation_items / quotation_changes 三张新表 + contracts.quotation_id 字段
- 新增前端报价管理页面：客户详情报价 Tab、报价编辑/详情/列表页、看板报价指标
- 扩展事件驱动逾期检查：sent 状态报价单过期自动标记 expired

## Capabilities

### New Capabilities

- `quotation-calculation`: 报价金额计算引擎——labor/base/buffer/subtotal/tax/total 全链路计算，精度控制，预览与保存共用逻辑
- `quotation-items`: 报价明细项管理——按报价单添加/排序/删除多类型明细行
- `quotation-changelog`: 报价变更日志——字段修改、状态变更、转合同的 before/after 快照记录
- `quotation-convert`: 报价转合同——accepted 报价单原子转合同草稿，字段映射，单次转换约束
- `quotation-frontend`: 报价前端页面——编辑页（含实时预览）、详情页（含转合同入口）、列表页（含过期标红）、客户报价 Tab、看板指标

### Modified Capabilities

- `quotation`: 扩展报价单创建/查询/更新/删除/状态流转规则——增加 estimate_days/daily_rate 等字段、accepted 后核心字段只读、accepted/rejected/expired/cancelled 不可删除、draft 可直接跳 accepted
- `event-driven-checks`: 扩展逾期检查——增加 sent 状态报价单过期自动标记 expired 逻辑，写入 quotation_changes 日志
- `db-migrations`: 新增 v1.6 迁移——quotations / quotation_items / quotation_changes 三表 + contracts.quotation_id 反查字段

## Impact

- **数据库**: 新增 3 张表（quotations / quotation_items / quotation_changes），contracts 表新增 quotation_id 列，7 个新索引
- **后端 API**: 新增 12 个报价相关端点（CRUD + 状态操作 + 明细 + 预览 + 转合同）
- **后端模块**: 新增 `backend/core/quote_utils.py`、`backend/models/quotation.py`、报价路由、枚举扩展
- **前端**: 新增报价列表/编辑/详情页面，客户详情页新增报价 Tab，看板新增报价指标卡片
- **依赖**: 无新外部依赖，纯 SQLite 操作
- **测试**: 新增 6 个测试文件（迁移、CRUD、计算、预览、转合同、变更日志）
