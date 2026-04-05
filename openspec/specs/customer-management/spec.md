# customer-management Specification

## Purpose
管理客户信息、跟进记录、客户转化漏斗，支持一人软件公司的客户关系管理。

## Requirements

### Requirement: Customer creation
系统 SHALL 支持创建新客户记录。

#### Scenario: Create customer with required fields
- GIVEN 用户已登录
- WHEN 用户提供客户名称
- THEN 系统创建客户记录
- AND 返回创建成功的客户信息

#### Scenario: Create customer with duplicate detection
- GIVEN 用户尝试创建客户
- WHEN 相同公司+联系人已存在
- THEN 系统提示"该客户已存在"
- AND 拒绝创建重复客户

#### Scenario: Create customer with optional fields
- GIVEN 用户创建客户
- WHEN 用户提供联系人、电话、邮箱、公司名称、来源渠道
- THEN 系统存储所有提供的信息
- AND 电话格式校验（手机号格式）
- AND 邮箱格式校验

### Requirement: Customer retrieval
系统 SHALL 支持查询客户信息。

#### Scenario: Get customer by ID
- GIVEN 客户存在
- WHEN 用户请求客户详情
- THEN 系统返回完整客户信息
- AND 包含关联项目和合同列表

#### Scenario: List customers with pagination
- GIVEN 系统中存在多个客户
- WHEN 用户请求客户列表
- THEN 系统返回分页结果
- AND 默认每页20条
- AND 支持自定义每页数量

#### Scenario: Search customers
- GIVEN 系统中存在客户
- WHEN 用户输入搜索关键词
- THEN 系统在名称、电话、公司字段模糊匹配
- AND 返回匹配结果
- AND 搜索结果高亮关键词

#### Scenario: Filter customers
- GIVEN 系统中存在客户
- WHEN 用户按状态/来源/时间筛选
- THEN 系统返回符合条件的客户
- AND 支持多条件组合筛选

### Requirement: Customer update
系统 SHALL 支持更新客户信息。

#### Scenario: Update customer information
- GIVEN 客户存在
- WHEN 用户修改客户信息
- THEN 系统更新客户记录
- AND 记录修改历史（时间、修改人、修改内容）

#### Scenario: Update customer status to deal
- GIVEN 客户状态为"跟进"
- WHEN 用户将状态变更为"成交"
- THEN 系统提示关联合同
- AND 自动更新客户状态

#### Scenario: Update customer status to lost
- GIVEN 客户状态为"潜在"或"跟进"
- WHEN 用户将状态变更为"流失"
- THEN 系统要求填写流失原因
- AND 拒绝无原因的流失操作

### Requirement: Customer deletion
系统 SHALL 支持删除客户，但有安全限制。

#### Scenario: Soft delete customer
- GIVEN 客户存在
- WHEN 用户删除客户
- AND 客户无关联项目/合同
- THEN 系统执行软删除
- AND 客户标记为已删除，不物理删除

#### Scenario: Prevent delete with associations
- GIVEN 客户存在关联项目或合同
- WHEN 用户尝试删除客户
- THEN 系统拒绝删除
- AND 提示"该客户有关联项目/合同，无法删除"

### Requirement: Customer statistics
系统 SHALL 提供客户统计分析。

#### Scenario: Customer statistics by status
- GIVEN 系统中存在客户
- WHEN 用户请求客户统计
- THEN 系统返回按状态分组的客户数量
- AND 返回潜在/跟进/成交/流失各阶段数量

#### Scenario: Customer statistics by source
- GIVEN 系统中存在客户
- WHEN 用户请求客户统计
- THEN 系统返回按来源渠道分组的客户数量
- AND 返回推荐/网络/展会/社交媒体/其他各渠道数量

#### Scenario: Customer conversion rate
- GIVEN 系统中存在客户
- WHEN 用户请求转化率
- THEN 系统计算: 成交客户数 / 总客户数 × 100%
- AND 返回转化率百分比
