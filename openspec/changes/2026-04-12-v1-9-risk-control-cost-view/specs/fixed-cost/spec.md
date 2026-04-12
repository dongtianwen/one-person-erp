## ADDED Requirements

### Requirement: Fixed cost CRUD
系统 SHALL 支持固定成本条目的创建、查询、更新、删除。每个条目包含 name、category（白名单：office/cloud/software/equipment/other）、amount（必须 > 0）、period（白名单：monthly/quarterly/yearly/onetime）、effective_date（必填）、end_date（可选，若填写必须 >= effective_date）、project_id（可选关联项目）、notes。

#### Scenario: Create fixed cost success
- **WHEN** POST /api/v1/fixed-costs 提供完整有效数据
- **THEN** 创建成功，返回 HTTP 200

#### Scenario: Amount must be positive
- **WHEN** POST /api/v1/fixed-costs 提交 amount <= 0
- **THEN** 返回 HTTP 422

#### Scenario: Period must be in whitelist
- **WHEN** POST /api/v1/fixed-costs 提交 period 不在白名单内
- **THEN** 返回 HTTP 422

#### Scenario: End date must after effective date
- **WHEN** POST /api/v1/fixed-costs 提交 end_date < effective_date
- **THEN** 返回 HTTP 422

#### Scenario: Project association optional
- **WHEN** POST /api/v1/fixed-costs 不提供 project_id
- **THEN** 创建成功，project_id = NULL

#### Scenario: Update fixed cost success
- **WHEN** PUT /api/v1/fixed-costs/{cost_id} 提供有效更新数据
- **THEN** 更新成功

#### Scenario: Delete fixed cost success
- **WHEN** DELETE /api/v1/fixed-costs/{cost_id}
- **THEN** 删除成功

#### Scenario: Fixed cost not found returns 404
- **WHEN** GET /api/v1/fixed-costs/{nonexistent_id}
- **THEN** 返回 HTTP 404

### Requirement: Monthly fixed cost summary
系统 SHALL 提供按月汇总固定成本功能，使用业务视角口径：纳入 effective_date <= period_end_date 且（end_date IS NULL 或 end_date >= period_start_date）的条目，计入原始 amount（不除以月数，不摊销）。返回结构含 accounting_period、total_amount、by_category、items 列表。

#### Scenario: Monthly summary includes active monthly cost
- **WHEN** 查询 2024-01 月汇总，有一条 monthly 条目 effective_date=2024-01-01
- **THEN** 纳入该条目，金额为原始 amount

#### Scenario: Yearly cost included at original amount not prorated
- **WHEN** 查询 2024-06 月汇总，有一条 yearly 条目 amount=12000，effective_date=2024-01-01，end_date=2024-12-31
- **THEN** 纳入该条目，金额=12000（不摊销为 1000）

#### Scenario: Summary excludes ended cost
- **WHEN** 查询 2024-06 月汇总，有一条条目 end_date=2024-05-31
- **THEN** 不纳入该条目

#### Scenario: Summary excludes not yet started cost
- **WHEN** 查询 2024-06 月汇总，有一条条目 effective_date=2024-07-01
- **THEN** 不纳入该条目

#### Scenario: Onetime cost appears only in effective month
- **WHEN** onetime 条目 effective_date=2024-03-15
- **THEN** 仅在 2024-03 月汇总中纳入，其他月份不纳入

#### Scenario: Summary by category correct
- **WHEN** 有两条条目 category=office（3000）和 category=cloud（1500）
- **THEN** by_category = {office: 3000, cloud: 1500}

### Requirement: Project fixed costs total
系统 SHALL 提供获取项目关联固定成本总额的接口。

#### Scenario: Project fixed costs total correct
- **WHEN** 项目关联了 3 条固定成本条目，amount 分别为 3000、2000、1000
- **THEN** 返回 total=6000

### Requirement: Fixed cost API endpoints
系统 SHALL 提供 POST/GET/PUT/DELETE /api/v1/fixed-costs、GET /api/v1/fixed-costs/summary?period=YYYY-MM、GET /api/v1/projects/{project_id}/fixed-costs 接口。
