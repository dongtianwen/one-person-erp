## MODIFIED Requirements

### Requirement: Customer retrieval
系统 SHALL 支持查询客户信息，包含关联资产列表。

#### Scenario: Get customer by ID
- GIVEN 客户存在
- WHEN 用户请求客户详情
- THEN 系统返回完整客户信息
- AND 包含关联项目和合同列表
- AND 包含关联资产列表（按到期时间升序）

## ADDED Requirements

### Requirement: Customer assets tab
客户详情页 SHALL 包含"资产与托管记录"Tab。

#### Scenario: Display assets tab in customer detail
- GIVEN 用户查看客户详情
- WHEN 用户切换到"资产与托管记录"Tab
- THEN 系统展示该客户的所有托管资产
- AND 支持在 Tab 内直接新增/编辑/删除资产记录
