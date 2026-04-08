## ADDED Requirements

### Requirement: Quotation item management
系统 SHALL 支持为报价单添加明细项。

#### Scenario: Add item to quotation
- **WHEN** 用户为报价单添加明细项（item_name, item_type, quantity, unit_price）
- **THEN** 系统创建明细项记录
- **AND** amount = round(quantity × unit_price, 2)

#### Scenario: Item type must be valid
- **WHEN** item_type 不在白名单（labor/design/testing/deployment/outsource/other）
- **THEN** 返回 422 校验错误

#### Scenario: Item quantity and price non-negative
- **WHEN** quantity 或 unit_price 为负数
- **THEN** 返回 422 校验错误

#### Scenario: Items ordered by sort_order
- **WHEN** 查询报价单明细项
- **THEN** 按 sort_order 升序返回

#### Scenario: Cascade delete with quotation
- **WHEN** 报价单被删除
- **THEN** 该报价单下所有明细项同步删除

### Requirement: Quotation item types
系统 SHALL 支持以下明细项类型：labor / design / testing / deployment / outsource / other。

#### Scenario: All item types accepted
- **WHEN** 使用白名单内的 item_type 创建明细项
- **THEN** 系统接受创建
