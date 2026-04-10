## ADDED Requirements

### Requirement: Field tips data source
前端 SHALL 在 `frontend/src/constants/help.js` 中定义 FIELD_TIPS 常量，按模块分组提供字段提示文本。

#### Scenario: All required modules covered
- **WHEN** 查看 FIELD_TIPS 常量
- **THEN** 包含 quote、contract、invoice、milestone、change_order、work_hour、fixed_cost 共 7 个模块的提示

#### Scenario: Required fields covered per module
- **WHEN** 查看各模块字段
- **THEN** quote 包含 estimate_days/daily_rate/risk_buffer_rate/valid_until/discount_amount/tax_rate，invoice 包含 invoice_date/amount_excluding_tax/tax_rate/received_by，milestone 包含 payment_amount/payment_due_date/payment_status，change_order 包含 extra_days/extra_amount/status，work_hour 包含 hours_spent/deviation_note，fixed_cost 包含 period/effective_date/end_date

### Requirement: FieldTip component
系统 SHALL 提供 FieldTip.vue 组件，从 FIELD_TIPS 读取内容并在字段旁渲染提示图标。

#### Scenario: Field with tip content
- **WHEN** FieldTip 组件接收 module="quote" field="daily_rate"
- **THEN** 渲染 ❓ 图标，hover 时显示 tooltip "每个工作日的费率（元/天），乘以工期得出人工费用。"

#### Scenario: Field without tip content
- **WHEN** FieldTip 组件接收 module="quote" field="nonexistent"
- **THEN** 不渲染任何内容，静默处理

#### Scenario: Tooltip length limit
- **WHEN** 字段提示内容超过 HELP_FIELD_TIP_MAX_LENGTH 个中文字符
- **THEN** tooltip 内容不超过此限制

#### Scenario: Mobile fallback
- **WHEN** 在移动端使用 FieldTip
- **THEN** 不显示 hover tooltip，而是将提示内容截取前 15 字追加到 placeholder

### Requirement: FieldTip integration on forms
所有必须覆盖的字段 SHALL 在对应表单中渲染 FieldTip 组件。

#### Scenario: Quote form fields
- **WHEN** 打开报价单表单
- **THEN** estimate_days、daily_rate、risk_buffer_rate、valid_until、discount_amount、tax_rate 字段旁均有 FieldTip 组件
