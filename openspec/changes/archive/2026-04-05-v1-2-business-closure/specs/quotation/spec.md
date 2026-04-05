## ADDED Requirements

### Requirement: Quotation creation
系统 SHALL 支持创建报价单，自动生成编号（BJ-YYYYMMDD-序号），必须关联客户。

#### Scenario: Create quotation with required fields
- GIVEN 用户已登录
- WHEN 用户创建报价单并提供报价标题、关联客户、报价金额、有效期至
- THEN 系统创建报价单，初始状态为"草稿"
- AND 自动生成编号 BJ-YYYYMMDD-序号（当日从 001 起）

#### Scenario: Create quotation with optional fields
- GIVEN 用户创建报价单
- WHEN 用户填写报价内容（最多 5000 字符）和折扣说明（最多 500 字符）
- THEN 系统存储所有提供的信息

#### Scenario: Quotation number uniqueness
- GIVEN 同一天已有报价单
- WHEN 创建新报价单
- THEN 序号自动递增，保证编号唯一

### Requirement: Quotation retrieval
系统 SHALL 支持查询报价单。

#### Scenario: List quotations with filtering
- GIVEN 系统中存在多个报价单
- WHEN 用户请求报价单列表
- THEN 系统返回分页结果
- AND 支持按状态（草稿/已发送/已接受/已拒绝/已过期）筛选
- AND 支持按客户筛选
- AND 支持按时间范围筛选

#### Scenario: Get quotation detail
- GIVEN 报价单存在
- WHEN 用户请求报价单详情
- THEN 系统返回完整报价信息
- AND 包含关联客户信息
- AND 包含关联合同信息（如已转合同）

### Requirement: Quotation update
系统 SHALL 支持编辑报价单，但仅限草稿和已发送状态。

#### Scenario: Update draft or sent quotation
- GIVEN 报价单状态为"草稿"或"已发送"
- WHEN 用户修改报价内容
- THEN 系统更新报价单
- AND 记录修改时间

#### Scenario: Prevent update accepted quotation
- GIVEN 报价单状态为"已接受"
- WHEN 用户尝试修改报价单
- THEN 系统拒绝修改
- AND 提示"已接受的报价单不可编辑"

#### Scenario: Prevent update expired quotation
- GIVEN 报价单状态为"已过期"
- WHEN 用户尝试修改报价单
- THEN 系统拒绝修改

### Requirement: Quotation status transition
系统 SHALL 支持报价单状态流转。

#### Scenario: Mark as sent
- GIVEN 报价单状态为"草稿"
- WHEN 用户将状态改为"已发送"
- THEN 系统更新状态

#### Scenario: Mark as accepted
- GIVEN 报价单状态为"已发送"
- WHEN 用户将状态改为"已接受"
- THEN 系统更新状态

#### Scenario: Mark as rejected
- GIVEN 报价单状态为"已发送"
- WHEN 用户将状态改为"已拒绝"
- THEN 系统更新状态

#### Scenario: Auto expire on validity date passed
- GIVEN 报价单状态为"草稿"或"已发送"
- AND 有效期至日期已过
- WHEN 事件驱动逾期检查触发
- THEN 系统自动将状态变更为"已过期"

### Requirement: Convert quotation to contract
系统 SHALL 支持将已接受的报价单一键转为合同草稿。

#### Scenario: Convert accepted quotation
- GIVEN 报价单状态为"已接受"
- WHEN 用户点击"转合同"
- THEN 系统创建合同草稿
- AND 合同金额 = 报价金额
- AND 合同关联客户 = 报价关联客户
- AND 报价单关联合同自动填充
- AND 报价单状态锁定不可再编辑

#### Scenario: Prevent convert non-accepted quotation
- GIVEN 报价单状态非"已接受"
- WHEN 用户点击"转合同"
- THEN 系统拒绝操作
- AND 提示"仅已接受的报价单可转为合同"

### Requirement: Quotation deletion
系统 SHALL 支持删除报价单。

#### Scenario: Delete draft quotation
- GIVEN 报价单状态为"草稿"
- WHEN 用户删除报价单
- THEN 系统执行软删除

#### Scenario: Prevent delete non-draft quotation
- GIVEN 报价单状态非"草稿"
- WHEN 用户尝试删除
- THEN 系统拒绝删除
- AND 提示"仅草稿状态可删除"
