## MODIFIED Requirements

### Requirement: Change freeze error responses include help field
需求冻结错误响应 SHALL 追加 help 字段。

#### Scenario: REQUIREMENT_FROZEN with help
- **WHEN** 尝试修改已冻结的需求
- **THEN** 响应包含 help.reason 说明冻结原因，help.next_steps 引导通过变更单流程提交变更

#### Scenario: detail and code unchanged
- **WHEN** 需求冻结错误响应追加 help 字段
- **THEN** detail 和 code 的值与追加前完全一致
