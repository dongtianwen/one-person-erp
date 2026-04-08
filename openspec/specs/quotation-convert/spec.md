## ADDED Requirements

### Requirement: Convert quotation to contract
系统 SHALL 支持将已接受的报价单一键转为合同草稿。

#### Scenario: Convert accepted quotation successfully
- **WHEN** 报价单状态为 accepted
- **AND** 用户调用转合同接口
- **THEN** 系统创建合同草稿（status=draft）
- **AND** contracts.title = quotations.title
- **AND** contracts.customer_id = quotations.customer_id
- **AND** contracts.amount = quotations.total_amount
- **AND** contracts.notes = quotations.requirement_summary
- **AND** contracts.quotation_id = quotations.id
- **AND** contracts.sign_date = NULL

#### Scenario: Prevent convert non-accepted quotation
- **WHEN** 报价单状态非 accepted
- **THEN** 返回 422，提示"仅已接受的报价单可转为合同"

#### Scenario: Convert only once
- **WHEN** 报价单已关联合同（converted_contract_id 不为空）
- **AND** 用户再次调用转合同
- **THEN** 返回 422，提示"该报价单已转换过合同"

#### Scenario: Transaction atomic
- **WHEN** 转合同过程中任一步骤失败
- **THEN** 整个事务回滚，不产生部分数据

#### Scenario: Sets converted_contract_id on quotation
- **WHEN** 转合同成功
- **THEN** quotations.converted_contract_id 设为新建合同的 ID

#### Scenario: Log conversion in quotation_changes
- **WHEN** 转合同成功
- **THEN** quotation_changes 中新增 change_type=converted 记录

#### Scenario: Contract has quotation_id for reverse lookup
- **WHEN** 转合同成功
- **THEN** contracts.quotation_id 指向源报价单 ID
