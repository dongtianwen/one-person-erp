## MODIFIED Requirements

### Requirement: Invoice error responses include help field
发票相关错误响应 SHALL 追加 help 字段，提供原因解释和下一步操作引导。

#### Scenario: INVOICE_AMOUNT_EXCEEDS_CONTRACT with help
- **WHEN** 创建发票时累计金额超过合同金额
- **THEN** 响应包含 help.reason 说明金额限制规则，help.next_steps 引导用户查看已开票进度

#### Scenario: INVOICE_STATUS_INVALID_TRANSITION with help
- **WHEN** 发票状态流转不合法
- **THEN** 响应包含 help.reason 说明状态流转顺序，help.next_steps 列出各状态可流转的目标

#### Scenario: INVOICE_CANNOT_DELETE with help
- **WHEN** 尝试删除已核销或已作废的发票
- **THEN** 响应包含 help.reason 说明删除限制，help.next_steps 提供替代方案

#### Scenario: detail and code unchanged
- **WHEN** 发票错误响应追加 help 字段
- **THEN** detail 和 code 的值与追加前完全一致
