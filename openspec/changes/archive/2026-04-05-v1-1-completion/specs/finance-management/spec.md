## MODIFIED Requirements

### Requirement: Finance record creation
系统 SHALL 支持创建收入和支出记录，支出记录必须提供资金来源，特定资金来源需填写结算状态。

#### Scenario: Create income record
- GIVEN 用户已登录
- WHEN 用户创建收入记录
- AND 选择关联合同
- AND 输入金额、分类、描述、发生日期
- THEN 系统创建收入记录
- AND 初始状态为"待确认"
- AND 发票号码唯一性校验（如提供）

#### Scenario: Create expense record with funding source
- GIVEN 用户已登录
- WHEN 用户创建支出记录
- AND 选择支出分类
- AND 输入金额、描述、发生日期
- AND 选择资金来源（对公账户/个人垫付/报销/借款/借款归还/其他）
- THEN 系统创建支出记录
- AND 初始状态为"待确认"

#### Scenario: Create expense with personal advance requires settlement status
- GIVEN 用户创建支出记录
- WHEN 资金来源为"个人垫付"或"借款"
- AND 未填写业务说明或结算状态
- THEN 系统拒绝创建
- AND 提示"业务说明和结算状态为必填项"

#### Scenario: Income must link to contract
- GIVEN 用户创建收入记录
- WHEN 用户未选择关联合同
- THEN 系统拒绝创建
- AND 提示"收入记录必须关联合同"

### Requirement: Finance record update
系统 SHALL 支持更新财务记录，但有安全限制。已确认记录修改时自动记录变更日志。

#### Scenario: Update pending finance record
- GIVEN 财务记录状态为"待确认"
- WHEN 用户修改记录信息
- THEN 系统允许修改
- AND 更新修改时间

#### Scenario: Update confirmed record logs changes
- GIVEN 财务记录状态为"已确认"
- WHEN 用户修改记录信息
- THEN 系统允许修改
- AND 自动创建变更日志记录修改前后的字段值
- AND 记录修改时间和操作人

#### Scenario: Reverse confirmed record
- GIVEN 财务记录状态为"已确认"
- WHEN 用户需要修正错误
- THEN 系统创建一笔反向记录（金额取反）
- AND 原记录保持不变（审计追踪）
- AND 用户可创建新的正确记录
