## ADDED Requirements

### Requirement: Quotation list page
系统 SHALL 提供报价单列表页。

#### Scenario: Display quotation list
- **WHEN** 用户访问报价单列表页
- **THEN** 显示报价编号、客户、标题、总价、状态、有效期
- **AND** 支持按状态筛选

#### Scenario: Expired quotation highlighted
- **WHEN** 报价单状态为 expired
- **THEN** 列表中该行显示红色标记

#### Scenario: Non-draft quotations cannot be deleted from list
- **WHEN** 报价单状态为 accepted / rejected / expired / cancelled
- **THEN** 列表中不显示删除按钮

### Requirement: Quotation edit page
系统 SHALL 提供报价单编辑页。

#### Scenario: Edit form fields
- **WHEN** 用户创建或编辑报价单
- **THEN** 表单包含：标题、需求摘要、预计工期、日费率、直接成本、风险缓冲率、折扣金额、税率、有效期、备注

#### Scenario: Real-time preview
- **WHEN** 用户修改表单中的金额相关字段
- **THEN** 右侧或下方实时显示报价预览（人工成本、基础金额、缓冲金额、小计、税额、总价）
- **AND** 预览调用 POST /api/v1/quotes/preview

#### Scenario: Accepted quotation read-only
- **WHEN** 报价单状态为 accepted
- **THEN** 核心字段只读，仅备注字段可编辑
- **AND** 隐藏字段的旧值从 payload 中移除

#### Scenario: Preview shows dash when empty
- **WHEN** 预览中某些金额为空
- **THEN** 显示 "—"

### Requirement: Quotation detail page
系统 SHALL 提供报价单详情页。

#### Scenario: Show convert button for accepted quotation
- **WHEN** 报价单状态为 accepted
- **THEN** 显示"一键转合同"按钮

#### Scenario: Show contract reference after conversion
- **WHEN** 报价单已转合同
- **THEN** 显示关联合同编号，不可再次转换

#### Scenario: Expired quotation no action buttons
- **WHEN** 报价单状态为 expired
- **THEN** 显示"已过期"提示，不展示发送/确认按钮

#### Scenario: No data no crash
- **WHEN** 报价单数据为空或不存在
- **THEN** 页面不报错、不白屏，显示友好提示

### Requirement: Customer quotation tab
系统 SHALL 在客户详情页新增"报价"Tab。

#### Scenario: Show customer quotations
- **WHEN** 用户在客户详情页切换到"报价"Tab
- **THEN** 展示该客户所有报价单
- **AND** 支持按状态筛选
- **AND** 支持新建报价单

### Requirement: Dashboard quotation metrics
系统 SHALL 在看板新增报价指标。

#### Scenario: Show quotation metrics
- **WHEN** 用户访问看板
- **THEN** 显示本月发出报价数
- **AND** 显示报价转化率（accepted ÷ sent × 100%）

#### Scenario: Zero metrics when no data
- **WHEN** 本月无报价数据
- **THEN** 显示 0 或 0.00%
