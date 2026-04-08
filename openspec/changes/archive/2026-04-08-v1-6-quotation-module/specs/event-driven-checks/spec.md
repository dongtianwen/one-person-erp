## MODIFIED Requirements

### Requirement: Quotation expiry check
系统 SHALL 将所有过期的已发送报价单变更为"已过期"，并记录变更日志。

#### Scenario: Expire sent quotations past validity date
- **WHEN** 存在状态为"已发送"的报价单
- **AND** valid_until 日期已过（valid_until < 今日）
- **THEN** 系统将状态变更为"已过期"
- **AND** 写入 expired_at 时间戳
- **AND** 在 quotation_changes 中记录 change_type=status_change 的变更日志

#### Scenario: Draft quotations not auto-expired
- **WHEN** 存在状态为"草稿"的报价单
- **AND** valid_until 日期已过
- **THEN** 系统不自动将其标记为"已过期"（仅 sent 状态触发自动过期）
