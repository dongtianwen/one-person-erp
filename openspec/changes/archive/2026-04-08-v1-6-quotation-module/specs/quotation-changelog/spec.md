## ADDED Requirements

### Requirement: Quotation change logging
系统 SHALL 记录报价单的每次重要变更。

#### Scenario: Log field update
- **WHEN** 用户修改报价单的核心字段（金额、工期、费率等）
- **THEN** 系统在 quotation_changes 中记录 change_type=field_update
- **AND** before_snapshot 包含修改前字段 JSON
- **AND** after_snapshot 包含修改后字段 JSON

#### Scenario: Log status change
- **WHEN** 报价单状态发生流转
- **THEN** 系统在 quotation_changes 中记录 change_type=status_change
- **AND** before_snapshot 包含原状态
- **AND** after_snapshot 包含新状态

#### Scenario: Log contract conversion
- **WHEN** 报价单被转为合同
- **THEN** 系统在 quotation_changes 中记录 change_type=converted
- **AND** after_snapshot 包含关联合同 ID

#### Scenario: Changes queryable by quotation
- **WHEN** 查询某个报价单的变更历史
- **THEN** 系统按 created_at 降序返回所有变更记录
