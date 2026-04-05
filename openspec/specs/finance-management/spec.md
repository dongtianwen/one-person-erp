# finance-management Specification

## Purpose
收支记录管理，财务统计，利润核算，支持一人软件公司财务透明化。

## Requirements

### Requirement: Finance record creation
系统 SHALL 支持创建收入和支出记录。

#### Scenario: Create income record
- GIVEN 用户已登录
- WHEN 用户创建收入记录
- AND 选择关联合同
- AND 输入金额、分类、描述、发生日期
- THEN 系统创建收入记录
- AND 初始状态为"待确认"
- AND 发票号码唯一性校验（如提供）

#### Scenario: Create expense record
- GIVEN 用户已登录
- WHEN 用户创建支出记录
- AND 选择支出分类
- AND 输入金额、描述、发生日期
- THEN 系统创建支出记录
- AND 初始状态为"待确认"

#### Scenario: Income must link to contract
- GIVEN 用户创建收入记录
- WHEN 用户未选择关联合同
- THEN 系统拒绝创建
- AND 提示"收入记录必须关联合同"

### Requirement: Finance record retrieval
系统 SHALL 支持查询财务记录。

#### Scenario: Get finance record by ID
- GIVEN 财务记录存在
- WHEN 用户请求记录详情
- THEN 系统返回完整财务记录信息
- AND 包含关联合同信息

#### Scenario: List finance records with filtering
- GIVEN 系统中存在多个财务记录
- WHEN 用户请求财务记录列表
- THEN 系统返回分页结果
- AND 支持按类型（收入/支出）筛选
- AND 支持按分类筛选
- AND 支持按时间范围筛选
- AND 支持按状态筛选

### Requirement: Finance record update
系统 SHALL 支持更新财务记录，但有安全限制。

#### Scenario: Update pending finance record
- GIVEN 财务记录状态为"待确认"
- WHEN 用户修改记录信息
- THEN 系统允许修改
- AND 更新修改时间

#### Scenario: Prevent update confirmed record
- GIVEN 财务记录状态为"已确认"
- WHEN 用户尝试修改记录
- THEN 系统拒绝修改
- AND 提示"已确认的记录不可修改，请创建冲销记录"

#### Scenario: Reverse confirmed record
- GIVEN 财务记录状态为"已确认"
- WHEN 用户需要修正错误
- THEN 系统创建一笔反向记录（金额取反）
- AND 原记录保持不变（审计追踪）
- AND 用户可创建新的正确记录

### Requirement: Finance statistics
系统 SHALL 提供财务统计分析。

#### Scenario: Monthly income/expense summary
- GIVEN 系统中存在财务记录
- WHEN 用户请求月度统计
- THEN 系统计算当月总收入
- AND 计算当月总支出
- AND 计算净利润: 总收入 - 总支出

#### Scenario: Category breakdown
- GIVEN 系统中存在财务记录
- WHEN 用户请求分类统计
- THEN 系统返回各分类收支金额
- AND 返回占比百分比

#### Scenario: Accounts receivable calculation
- GIVEN 系统中存在生效合同和收入记录
- WHEN 用户请求应收账款
- THEN 系统计算: 已生效合同总金额 - 已确认收入总额
- AND 返回应收账款金额

### Requirement: Invoice management
系统 SHALL 管理发票信息。

#### Scenario: Record invoice number
- GIVEN 用户创建或更新财务记录
- WHEN 用户提供发票号码
- THEN 系统存储发票号码
- AND 校验发票号码唯一性

#### Scenario: Update finance status to invoiced
- GIVEN 财务记录状态为"已确认"
- WHEN 用户标记为"已开票"
- THEN 系统更新记录状态
- AND 记录开票时间
