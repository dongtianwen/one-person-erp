## MODIFIED Requirements

### Requirement: Milestone error responses include help field
里程碑相关错误响应 SHALL 追加 help 字段。

#### Scenario: MILESTONE_NOT_COMPLETED with help
- **WHEN** 里程碑未完成时尝试触发收款流转
- **THEN** 响应包含 help.reason 说明完成前置条件，help.next_steps 引导前往里程碑列表完成标记

#### Scenario: detail and code unchanged
- **WHEN** 里程碑错误响应追加 help 字段
- **THEN** detail 和 code 的值与追加前完全一致
