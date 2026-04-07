## ADDED Requirements

### Requirement: Customer lifetime value calculation
系统 SHALL 通过独立函数 `calculate_customer_lifetime_value(customer_id, db)` 计算客户生命周期价值，返回 total_contract_amount、total_received_amount、project_count、avg_project_amount、first_cooperation_date、last_cooperation_date。所有金额 round(x, 2)。

#### Scenario: Total contract amount includes all statuses
- **WHEN** 客户有多个不同状态的合同
- **THEN** total_contract_amount 为所有合同 amount 字段之和（不限合同状态）

#### Scenario: Total received amount confirmed income only
- **WHEN** 客户有关联合同的收入记录
- **THEN** total_received_amount 仅为 record_type=INCOME、status=CONFIRMED 且合同属于该客户的记录金额之和

#### Scenario: Total received amount only from customer contracts
- **WHEN** 存在其他客户的收入记录
- **THEN** 其他客户的收入不计入该客户的实收金额

#### Scenario: Project count includes all statuses
- **WHEN** 客户有多个不同状态的项目
- **THEN** project_count 为该客户关联的项目总数（不限项目状态）

#### Scenario: Avg project amount correct
- **WHEN** 客户有 5 个项目，合同总额 200000
- **THEN** avg_project_amount = round(200000 / 5, 2) = 40000.00

#### Scenario: Avg project amount null when no projects
- **WHEN** 客户合作项目数为 0
- **THEN** avg_project_amount 返回 None

#### Scenario: First cooperation date earliest sign date
- **WHEN** 客户有多个合同
- **THEN** first_cooperation_date 为最早 sign_date

#### Scenario: Last cooperation date latest sign date
- **WHEN** 客户有多个合同
- **THEN** last_cooperation_date 为最新 sign_date

#### Scenario: Cooperation dates exclude null sign date
- **WHEN** 客户有合同 sign_date 为 NULL
- **THEN** sign_date 为 NULL 的合同不纳入首次/最近合作日期计算

#### Scenario: All zero when no contracts
- **WHEN** 客户没有任何合同
- **THEN** total_contract_amount=0.00, total_received_amount=0.00, project_count=0
- **AND** avg_project_amount=None, first_cooperation_date=None, last_cooperation_date=None

### Requirement: Customer lifetime value API endpoint
系统 SHALL 提供 `GET /api/v1/customers/{customer_id}/lifetime-value` 接口，返回 customer_id、customer_name、total_contract_amount、total_received_amount、project_count、avg_project_amount、first_cooperation_date、last_cooperation_date、currency。

#### Scenario: LTV API structure exact match
- **WHEN** 请求有效客户 ID 的生命周期价值
- **THEN** 返回包含所有规定字段的 JSON

#### Scenario: Customer not found returns 404
- **WHEN** 请求不存在的 customer_id
- **THEN** 返回 HTTP 404

### Requirement: Customer detail includes lifetime value
客户详情接口 `GET /api/v1/customers/{customer_id}` SHALL 在响应中追加 `lifetime_value` 对象，复用 `calculate_customer_lifetime_value` 函数。

#### Scenario: Customer detail includes lifetime value
- **WHEN** 请求客户详情
- **THEN** 响应包含 lifetime_value 对象
- **AND** lifetime_value 结构与独立接口一致

### Requirement: Customer value panel in frontend
客户详情页 SHALL 新增"客户价值"面板，展示历史合同总额、历史实收金额、合作项目数、平均项目金额、首次合作日期、最近合作日期。平均项目金额为 null 时显示"—"。无合同数据时金额显示 0.00、日期显示"—"。接口失败时面板显示"数据加载失败，请刷新"。

#### Scenario: Display LTV panel with full data
- **WHEN** 客户有完整数据
- **THEN** 六个指标全部正确展示

#### Scenario: Avg amount shows dash when no projects
- **WHEN** 合作项目数为 0
- **THEN** 平均项目金额显示"—"

#### Scenario: No contract data shows defaults
- **WHEN** 客户无合同数据
- **THEN** 金额显示 0.00，日期显示"—"

#### Scenario: LTV panel shows error on API failure
- **WHEN** LTV 接口请求失败
- **THEN** 面板显示"数据加载失败，请刷新"，不影响客户详情其他内容
