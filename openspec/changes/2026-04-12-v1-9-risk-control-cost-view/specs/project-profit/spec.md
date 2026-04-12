## ADDED Requirements

### Requirement: Project labor cost calculation
系统 SHALL 使用公式 `labor_cost = round((hours_total / HOURS_PER_DAY) * daily_rate, 2)` 计算工时成本，其中 hours_total 来自 work_hour_logs.hours_spent 之和，daily_rate 来自关联报价单。HOURS_PER_DAY 常量（值=8）必须在 constants.py 中定义，禁止硬编码。无工时记录或无 daily_rate 时 labor_cost = None。

#### Scenario: Labor cost uses hours divided by hours per day
- **WHEN** hours_total=160，daily_rate=800
- **THEN** labor_cost = round((160/8) * 800, 2) = 16000.00

#### Scenario: Labor cost not direct multiply
- **WHEN** hours_total=160，daily_rate=800
- **THEN** labor_cost = 16000.00（不是 160 * 800 = 128000）

#### Scenario: Labor cost null when no work logs
- **WHEN** 项目无 work_hour_logs 记录
- **THEN** labor_cost = None

#### Scenario: Labor cost null when no daily rate
- **WHEN** 项目关联报价单无 daily_rate
- **THEN** labor_cost = None

#### Scenario: Hours per day constant used
- **WHEN** 计算工时成本
- **THEN** 使用 constants.HOURS_PER_DAY，不使用硬编码 8

### Requirement: Project profit calculation
系统 SHALL 计算项目粗利润：revenue = SUM(finance_records.amount)，total_cost = (labor_cost or 0) + (fixed_cost or 0) + (input_cost or 0)，gross_profit = revenue - total_cost，gross_margin = gross_profit / revenue（revenue > 0 时）。数据不完整时仍计算并返回 warnings 列表。

#### Scenario: Revenue uses received not contract amount
- **WHEN** 合同金额 100000，实收 finance_records 总额 80000
- **THEN** revenue = 80000

#### Scenario: Has complete data true when all present
- **WHEN** work_hour_logs 有记录且关联报价单有 daily_rate
- **THEN** has_complete_data = true

#### Scenario: Has complete data false when no logs
- **WHEN** 项目无 work_hour_logs 记录
- **THEN** has_complete_data = false

#### Scenario: Fixed cost uses original amount not prorated
- **WHEN** 项目关联固定成本 amount=12000（yearly）
- **THEN** 固定成本计入 total_cost = 12000（不摊销）

#### Scenario: Input invoice cost included
- **WHEN** 项目关联进项发票 total_amount=3000
- **THEN** input_cost = 3000

#### Scenario: Gross profit calculated correctly
- **WHEN** revenue=80000, total_cost=20000
- **THEN** gross_profit=60000, gross_margin=0.7500

#### Scenario: Gross margin null when no revenue
- **WHEN** revenue=0
- **THEN** gross_margin=null

#### Scenario: Warnings returned when incomplete data
- **WHEN** 项目无工时记录或无 daily_rate
- **THEN** warnings 列表包含缺失项说明

#### Scenario: Project not found returns 404
- **WHEN** GET /api/v1/projects/{nonexistent_id}/profit
- **THEN** 返回 HTTP 404

### Requirement: Project profit cache
系统 SHALL 支持将利润计算结果写入 projects 表缓存字段（cached_revenue / cached_labor_cost / cached_fixed_cost / cached_input_cost / cached_gross_profit / cached_gross_margin / profit_cache_updated_at），原子事务。

#### Scenario: Refresh cache writes to projects
- **WHEN** POST /api/v1/projects/{project_id}/profit/refresh
- **THEN** projects 表缓存字段更新为最新计算值

#### Scenario: Refresh cache atomic
- **WHEN** 缓存写入过程中出错
- **THEN** 事务回滚，缓存字段保持原值

### Requirement: Profit overview
系统 SHALL 提供所有项目粗利润列表接口，优先读 projects 缓存字段，缓存为 NULL 时实时计算。

#### Scenario: Profit overview uses cache
- **WHEN** 项目 cached_gross_profit 不为 NULL
- **THEN** 返回缓存值，不实时计算

### Requirement: Project profit API endpoints
系统 SHALL 提供 GET /api/v1/projects/{project_id}/profit、POST /api/v1/projects/{project_id}/profit/refresh、GET /api/v1/finance/profit-overview 接口。
