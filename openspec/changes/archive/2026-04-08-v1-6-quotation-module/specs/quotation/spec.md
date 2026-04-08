## MODIFIED Requirements

### Requirement: Quotation creation
系统 SHALL 支持创建报价单，自动生成编号（BJ-YYYYMMDD-序号），必须关联客户，包含工期和金额计算字段。

#### Scenario: Create quotation with required fields
- **WHEN** 用户创建报价单并提供报价标题、关联客户、需求摘要、预计工期（天）、有效期至
- **THEN** 系统创建报价单，初始状态为"草稿"
- **AND** 自动生成编号 BJ-YYYYMMDD-序号（当日从 001 起）
- **AND** 自动计算报价金额（labor_amount / base_amount / buffer_amount / subtotal_amount / tax_amount / total_amount）
- **AND** valid_until 默认为创建日 + 30 天

#### Scenario: Create quotation with optional fields
- **WHEN** 用户创建报价单
- **AND** 填写日费率、直接成本、风险缓冲率、折扣金额、税率、备注、关联项目
- **THEN** 系统存储所有提供的信息并据此计算金额

#### Scenario: Quotation number uniqueness
- **WHEN** 同一天已有报价单
- **THEN** 序号自动递增，保证编号唯一

### Requirement: Quotation update
系统 SHALL 支持编辑报价单，但仅限草稿和已发送状态。accepted 后仅允许修改 notes。

#### Scenario: Update draft or sent quotation
- **WHEN** 报价单状态为"草稿"或"已发送"
- **AND** 用户修改报价内容
- **THEN** 系统更新报价单
- **AND** 重新计算金额
- **AND** 记录修改时间
- **AND** 在 quotation_changes 中记录变更日志

#### Scenario: Update accepted quotation notes only
- **WHEN** 报价单状态为"已接受"
- **AND** 用户仅修改 notes 字段
- **THEN** 系统更新 notes

#### Scenario: Prevent update accepted quotation core fields
- **WHEN** 报价单状态为"已接受"
- **AND** 用户尝试修改核心字段（标题、金额、工期、费率等）
- **THEN** 系统拒绝修改
- **AND** 提示"已接受的报价单核心内容不可修改"

#### Scenario: Prevent update expired quotation
- **WHEN** 报价单状态为"已过期"
- **AND** 用户尝试修改报价单
- **THEN** 系统拒绝修改

### Requirement: Quotation status transition
系统 SHALL 支持报价单状态流转，遵循严格白名单。

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

#### Scenario: Mark as accepted writes accepted_at
- **WHEN** 报价单转为 accepted
- **THEN** accepted_at 写入当前时间戳

#### Scenario: Mark as rejected writes rejected_at
- **WHEN** 报价单转为 rejected
- **THEN** rejected_at 写入当前时间戳

### Requirement: Quotation deletion
系统 SHALL 支持删除报价单，仅草稿状态可删除。

#### Scenario: Delete draft quotation
- **WHEN** 报价单状态为"草稿"
- **AND** 用户删除报价单
- **THEN** 系统执行删除

#### Scenario: Prevent delete non-draft quotation
- **WHEN** 报价单状态为 sent / accepted / rejected / expired / cancelled
- **AND** 用户尝试删除
- **THEN** 系统拒绝删除
- **AND** 提示"仅草稿状态可删除"
