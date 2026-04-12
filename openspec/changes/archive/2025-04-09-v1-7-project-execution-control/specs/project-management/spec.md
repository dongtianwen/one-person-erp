## ADDED Requirements

### Requirement: Project close with mandatory conditions
系统 SHALL 支持关闭项目，但必须满足所有强制条件后才能执行关闭操作。

#### Scenario: Close check returns all conditions
- **WHEN** 用户请求项目的关闭条件检查
- **THEN** 系统返回所有关闭条件的满足状态：
  - all_milestones_completed: 所有里程碑是否已完成
  - final_acceptance_passed: 最终验收是否通过
  - payment_cleared: 款项是否结清
  - deliverables_archived: 交付物是否已归档
  - can_close: 是否可以关闭（所有条件均为 true 时为 true）
  - blocking_items: 未满足的条件列表

#### Scenario: Close blocked when conditions not met
- **WHEN** 用户尝试关闭项目
- **AND** 存在未满足的关闭条件
- **THEN** 系统返回 HTTP 409
- **AND** 错误消息列出所有未满足的条件

#### Scenario: Close success when all conditions met
- **WHEN** 用户关闭项目
- **AND** 所有关闭条件均已满足
- **THEN** 项目状态变更为 "completed"
- **AND** closed_at 写入当前时间戳
- **AND** close_checklist 写入所有条件的 JSON 快照

#### Scenario: Already closed project cannot be closed again
- **WHEN** 用户尝试关闭已关闭的项目（status = "completed"）
- **THEN** 系统返回 HTTP 409
- **AND** 错误消息提示项目已关闭

#### Scenario: Closed project core fields immutable
- **WHEN** 用户尝试修改已关闭项目的核心字段（name, customer_id, contract_id 等）
- **THEN** 系统返回 HTTP 409
- **AND** 错误消息提示不能修改已关闭的项目

## MODIFIED Requirements

### Requirement: Project status transition
系统 SHALL 支持项目状态流转，新增 "completed" 终态。

#### Scenario: Transition to completed
- **WHEN** 项目满足所有关闭条件
- **AND** 用户执行关闭操作
- **THEN** 项目状态变更为 "completed"
- **AND** "completed" 为终态，不允许再流转到其他状态
