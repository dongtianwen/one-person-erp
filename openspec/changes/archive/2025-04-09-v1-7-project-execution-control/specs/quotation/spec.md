## MODIFIED Requirements

### Requirement: Quotation status transition
系统 SHALL 支持报价单状态流转，遵循严格白名单。当报价单转为"已接受"状态时，自动冻结关联项目的需求。

#### Scenario: Transition from draft
- **WHEN** 报价单状态为"草稿"
- **THEN** 允许流转到：已发送、已接受、已取消

#### Scenario: Transition from sent
- **WHEN** 报价单状态为"已发送"
- **THEN** 允许流转到：已接受、已拒绝、已取消

#### Scenario: Terminal states cannot transition
- **WHEN** 报价单状态为"已接受"/"已拒绝"/"已过期"/"已取消"
- **THEN** 不允许任何状态流转

#### Scenario: Expired only set by event-driven check
- **WHEN** 用户通过接口尝试设置 expired 状态
- **THEN** 系统拒绝，expired 仅由事件驱动逾期检查自动设置

#### Scenario: Mark as sent writes sent_at
- **WHEN** 报价单从 draft 转为 sent
- **THEN** sent_at 写入当前时间戳

#### Scenario: Mark as accepted writes accepted_at and freezes requirements
- **WHEN** 报价单转为 accepted
- **THEN** accepted_at 写入当前时间戳
- **AND** 如果报价单关联了项目，该项目的需求 SHALL 自动冻结
- **AND** 冻结后的需求变更必须通过变更单（change_orders）流程

#### Scenario: Mark as rejected writes rejected_at
- **WHEN** 报价单转为 rejected
- **THEN** rejected_at 写入当前时间戳
