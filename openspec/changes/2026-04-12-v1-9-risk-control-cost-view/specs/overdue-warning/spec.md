## ADDED Requirements

### Requirement: Overdue milestone detection
系统 SHALL 检测 payment_due_date < 今日 且 payment_status != received 的里程碑，返回逾期里程碑列表含项目名、客户名、金额、逾期天数。

#### Scenario: Milestone overdue when due date passed
- **WHEN** 里程碑 payment_due_date 为 2024-01-01，今日为 2024-01-15，payment_status != received
- **THEN** 该里程碑出现在逾期列表，overdue_days=14

#### Scenario: Milestone not overdue when received
- **WHEN** 里程碑 payment_status = received 且 payment_due_date 已过期
- **THEN** 该里程碑不出现在逾期列表

#### Scenario: All paid returns empty list
- **WHEN** 所有里程碑 payment_status = received
- **THEN** 逾期列表为空

### Requirement: Customer risk level calculation
系统 SHALL 根据客户逾期里程碑数量和金额计算风险等级：normal（overdue_count=0）、warning（overdue_count >= 1）、high（overdue_count >= 3 或 overdue_amount/total_contract_amount >= 30%）。high 优先级高于 warning。

#### Scenario: Risk normal when no overdue
- **WHEN** 客户无逾期里程碑
- **THEN** risk_level = normal

#### Scenario: Risk warning when one overdue
- **WHEN** 客户有 1 个逾期里程碑
- **THEN** risk_level = warning

#### Scenario: Risk high when count threshold reached
- **WHEN** 客户有 3 个逾期里程碑
- **THEN** risk_level = high

#### Scenario: Risk high when ratio threshold reached
- **WHEN** 客户逾期金额 / 合同总额 >= 0.30
- **THEN** risk_level = high

#### Scenario: High takes priority over warning
- **WHEN** 客户同时满足 warning 和 high 条件
- **THEN** risk_level = high

### Requirement: Customer risk field refresh
系统 SHALL 提供批量刷新所有客户风险字段的接口，原子事务写入 customers 表的 overdue_milestone_count、overdue_amount、risk_level。

#### Scenario: Refresh updates customer risk fields
- **WHEN** POST /api/v1/finance/overdue-warnings/refresh
- **THEN** 所有客户风险字段更新为最新计算值

#### Scenario: Refresh is atomic
- **WHEN** 刷新过程中任一客户更新失败
- **THEN** 事务回滚，所有客户字段保持原值

### Requirement: Risk level does not block operations
客户 risk_level SHALL 不参与任何业务接口校验，不影响合同创建、报价创建等操作。

#### Scenario: Risk level does not block contract creation
- **WHEN** 客户 risk_level = high
- **THEN** 仍可正常创建合同

#### Scenario: Risk level does not block quote creation
- **WHEN** 客户 risk_level = high
- **THEN** 仍可正常创建报价

### Requirement: Overdue warning API endpoints
系统 SHALL 提供 GET /api/v1/finance/overdue-warnings、GET /api/v1/customers/{customer_id}/risk-summary、POST /api/v1/finance/overdue-warnings/refresh 接口。

#### Scenario: Get overdue warnings
- **WHEN** GET /api/v1/finance/overdue-warnings
- **THEN** 返回逾期里程碑列表和客户风险摘要
