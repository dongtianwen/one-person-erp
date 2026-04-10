## MODIFIED Requirements

### Requirement: Project error responses include help field
项目关闭相关错误响应 SHALL 追加 help 字段。

#### Scenario: PROJECT_CLOSE_CONDITIONS_NOT_MET with help
- **WHEN** 项目关闭条件未满足
- **THEN** 响应包含 help.reason 说明前置条件，help.next_steps 列出各项关闭条件检查步骤

#### Scenario: PROJECT_ALREADY_CLOSED with help
- **WHEN** 尝试关闭已关闭的项目
- **THEN** 响应包含 help.reason 说明不可重复关闭，help.next_steps 引导查看关闭快照

#### Scenario: detail and code unchanged
- **WHEN** 项目错误响应追加 help 字段
- **THEN** detail 和 code 的值与追加前完全一致
