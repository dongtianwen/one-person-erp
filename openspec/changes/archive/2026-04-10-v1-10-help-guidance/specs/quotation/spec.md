## MODIFIED Requirements

### Requirement: Quotation error responses include help field
报价相关错误响应 SHALL 追加 help 字段。

#### Scenario: QUOTE_ALREADY_CONVERTED with help
- **WHEN** 尝试转换已转换的报价单
- **THEN** 响应包含 help.reason 说明一对一转换限制，help.next_steps 引导查看已关联合同

#### Scenario: QUOTE_NOT_ACCEPTED with help
- **WHEN** 尝试转换未接受的报价单
- **THEN** 响应包含 help.reason 说明前置条件，help.next_steps 引导先执行接受操作

#### Scenario: detail and code unchanged
- **WHEN** 报价错误响应追加 help 字段
- **THEN** detail 和 code 的值与追加前完全一致
