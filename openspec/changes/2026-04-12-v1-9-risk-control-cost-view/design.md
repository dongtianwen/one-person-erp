## Context

v1.0~v1.8 已建立完整的报价→合同→项目→财务→发票链路。v1.9 在此链路上加装"仪表盘和预警灯"，不扩展系统边界。技术栈：FastAPI + SQLite + Vue 3。所有新功能均为后端工具函数 + API 路由 + 前端 Tab 的模式，与现有架构一致。

关键约束：
- 一致性校验为**纯只读**，不修改任何字段
- 客户 risk_level **不参与业务拦截**
- 工时成本换算必须使用 `hours_spent / HOURS_PER_DAY * daily_rate`，禁止直接乘
- 固定成本月汇总返回原始金额，不做摊销
- 进项发票与销项发票完全独立

## Goals / Non-Goals

**Goals:**
- 为已有链路数据加装一致性校验，发现合同/收款/发票差异
- 实现里程碑逾期预警和客户风险等级计算
- 补全成本侧数据入口（固定成本、进项发票）
- 提供项目粗利润视图（实收 - 工时 - 固定成本 - 进项发票）
- 所有计算公式严格按 PRD 零章定义，有测试锁定

**Non-Goals:**
- 税务计算、增值税/所得税申报
- 会计损益表
- 成本月度自动摊销
- 预算管理体系
- 客户信用硬拦截（risk_level 不阻断任何操作）
- 银行流水对接

## Decisions

### 1. 新建独立工具模块，不修改已有业务逻辑

**决策**：新增 `consistency_utils.py` / `overdue_utils.py` / `fixed_cost_utils.py` / `profit_utils.py` / `input_invoice_utils.py`，各模块独立，不交叉引用。

**理由**：v1.9 是"加装仪表盘"，不是重构核心链路。独立模块降低风险，测试隔离。

**备选**：在现有 finance_utils.py 中追加 → 拒绝，文件已超过 400 行，职责过重。

### 2. 粗利润缓存写入 projects 表

**决策**：profit refresh 时将计算结果写入 projects 表的 cached_* 字段，overview 接口优先读缓存。

**理由**：看板需快速展示多个项目的粗利润，实时计算会遍历 4 张表（finance_records / work_hour_logs / fixed_costs / input_invoices），缓存避免重复计算。

**备选**：独立缓存表 → 拒绝，SQLite 单文件场景下 JOIN projects 表更高效。

### 3. 进项发票独立建表 input_invoices

**决策**：进项发票（成本票）使用独立 input_invoices 表，不与销项发票 invoices 表共用。

**理由**：字段结构完全不同（vendor_name / amount_excluding_tax / tax_rate），无状态流转，合并会增加复杂度。

### 4. 一致性校验不持久化

**决策**：一致性校验结果不写入数据库，每次调用实时计算或 refresh 时返回最新结果。

**理由**：校验结果时效性强，持久化会引入缓存失效问题。只读设计确保零副作用。

### 5. 工时换算常量集中管理

**决策**：`HOURS_PER_DAY = 8` 只在 constants.py 定义，profit_utils.py 引用，业务代码禁止硬编码。

**理由**：防止工时/日费率单位混淆导致的 8 倍放大错误。

### 6. 客户风险字段批量刷新为原子事务

**决策**：refresh_customer_risk_fields 使用数据库事务，一次性更新所有客户的风险字段。

**理由**：防止部分更新导致不一致状态。

## Risks / Trade-offs

- **[工时换算单位混淆]** → 用常量 + 专用测试（test_labor_cost_not_direct_multiply）锁定正确公式
- **[固定成本月汇总被误解为摊销]** → 汇总返回结构含说明文字，前端展示提示"原始金额，非摊销"
- **[粗利润缓存过期]** → 提供 refresh 接口手动刷新，overview 接口缓存为 NULL 时实时计算兜底
- **[SQLite ALTER TABLE 限制]** → 迁移脚本用 PRAGMA table_info 逐字段检查，已存在则跳过
- **[客户风险等级可能被误用为拦截]** → 测试锁定"风险等级不阻断合同/报价创建"
