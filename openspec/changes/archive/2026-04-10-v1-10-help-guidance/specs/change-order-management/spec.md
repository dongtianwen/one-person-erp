## MODIFIED Requirements

### Requirement: Change order error responses include help field
变更单错误响应 SHALL 追加 help 字段。

#### Scenario: CHANGE_ORDER_INVALID_TRANSITION with help
- **WHEN** 变更单状态流转不合法
- **THEN** 响应包含 help.reason 说明终态限制，help.next_steps 列出各状态可执行操作

#### Scenario: detail and code unchanged
- **WHEN** 变更单错误响应追加 help 字段
- **THEN** detail 和 code 的值与追加前完全一致
