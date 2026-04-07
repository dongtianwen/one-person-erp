## MODIFIED Requirements

### Requirement: Customer retrieval
系统 SHALL 支持查询客户信息，包含关联资产列表和生命周期价值数据。

#### Scenario: Get customer by ID
- GIVEN 客户存在
- WHEN 用户请求客户详情
- THEN 系统返回完整客户信息
- AND 包含关联项目和合同列表
- AND 包含关联资产列表（按到期时间升序）
- AND 包含 lifetime_value 对象（复用 calculate_customer_lifetime_value 函数）

## ADDED Requirements

### Requirement: Customer lifetime value endpoint
系统 SHALL 提供 `GET /api/v1/customers/{customer_id}/lifetime-value` 独立接口。

#### Scenario: LTV endpoint returns full value data
- **WHEN** 请求有效客户的 LTV 接口
- **THEN** 返回 customer_id、customer_name、total_contract_amount、total_received_amount、project_count、avg_project_amount、first_cooperation_date、last_cooperation_date、currency

#### Scenario: LTV endpoint returns 404 for missing customer
- **WHEN** 请求不存在客户的 LTV 接口
- **THEN** 返回 HTTP 404
