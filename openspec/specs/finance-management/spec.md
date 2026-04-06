# finance-management Specification

## Purpose
收支记录管理，财务统计，利润核算，支持一人软件公司财务透明化。

## Requirements

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

### Requirement: Finance record creation with category-dependent validation
The system SHALL validate finance records differently based on category. When category is `outsourcing`, outsource_name, has_invoice, and tax_treatment MUST be non-NULL. When category is NOT outsourcing, those three fields SHALL be forced to NULL. When invoice_no is non-empty, invoice_direction, invoice_type, tax_rate MUST be non-NULL and tax_amount SHALL be calculated server-side. When invoice_no is empty, all four invoice fields SHALL be forced to NULL. These rules MUST apply identically to both POST (create) and PUT/PATCH (update) endpoints.

#### Scenario: Create with outsourcing category validates outsource fields
- **WHEN** POST /api/v1/finance/ with category=outsourcing
- **THEN** outsource_name, has_invoice, tax_treatment are all required

#### Scenario: Create with non-outsourcing category clears outsource fields
- **WHEN** POST /api/v1/finance/ with category != outsourcing
- **THEN** outsource_name, has_invoice, tax_treatment are stored as NULL

#### Scenario: Update switching category to non-outsourcing clears fields
- **WHEN** PUT /api/v1/finance/{id} changes category from outsourcing to other
- **THEN** outsource fields are cleared to NULL

#### Scenario: Update switching category to outsourcing validates fields
- **WHEN** PUT /api/v1/finance/{id} changes category to outsourcing with missing fields
- **THEN** HTTP 422 returned

#### Scenario: Create with invoice_no validates invoice fields
- **WHEN** POST /api/v1/finance/ with invoice_no non-empty
- **THEN** invoice_direction, invoice_type, tax_rate are required and tax_amount is auto-calculated

#### Scenario: Create without invoice_no clears invoice fields
- **WHEN** POST /api/v1/finance/ with invoice_no empty
- **THEN** invoice_direction, invoice_type, tax_rate, tax_amount are stored as NULL
