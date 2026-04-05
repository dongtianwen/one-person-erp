## ADDED Requirements

### Requirement: Customer asset creation
系统 SHALL 支持在客户详情页为客户创建资产托管记录。

#### Scenario: Create asset with required fields
- GIVEN 用户已登录且查看客户详情
- WHEN 用户创建资产记录并提供资产类型和资产名称
- THEN 系统创建资产记录
- AND 关联当前客户

#### Scenario: Create asset with optional fields
- GIVEN 用户创建资产记录
- WHEN 用户填写到期日期、供应商、年费金额、账号信息、备注
- THEN 系统存储所有提供的信息
- AND 账号信息仅记录账号名，不存储密码

### Requirement: Customer asset retrieval
系统 SHALL 支持查询客户资产。

#### Scenario: List assets in customer detail
- GIVEN 客户存在且有关联资产
- WHEN 用户查看客户详情的"资产与托管记录"Tab
- THEN 系统展示该客户所有资产
- AND 按到期时间升序排列
- AND 到期前 30 天内高亮"即将到期"
- AND 已过期标红

#### Scenario: Assets sorted by expiry
- GIVEN 客户有多条资产记录
- WHEN 用户查看资产列表
- THEN 无到期日期的排在最后
- AND 有到期日期的按升序排列

### Requirement: Customer asset update
系统 SHALL 支持修改资产记录。

#### Scenario: Update asset information
- GIVEN 资产记录存在
- WHEN 用户修改资产信息
- THEN 系统更新记录
- AND 列表即时更新

### Requirement: Customer asset deletion
系统 SHALL 支持删除资产记录。

#### Scenario: Delete asset with confirmation
- GIVEN 资产记录存在
- WHEN 用户确认删除
- THEN 系统执行软删除
- AND 同步删除该资产关联的自动生成提醒

### Requirement: Asset expiry reminder
系统 SHALL 为即将到期的资产自动生成提醒。

#### Scenario: Auto generate reminder before expiry
- GIVEN 资产记录有到期日期
- AND 到期前 30 天内
- AND 尚未生成过提醒
- WHEN 事件驱动逾期检查触发
- THEN 系统在提醒管理中心生成"客户资产到期提醒"
- AND 提醒为普通提醒（非关键提醒），可删除

#### Scenario: Idempotent reminder generation
- GIVEN 资产已有到期提醒
- WHEN 事件驱动逾期检查再次触发
- THEN 系统不重复生成提醒
