## ADDED Requirements

### Requirement: Quote amount calculation
系统 SHALL 提供统一的报价金额计算函数，所有金额四舍五入到 2 位小数。

#### Scenario: Full calculation with all fields
- **WHEN** 输入 estimate_days=10, daily_rate=1000, direct_cost=5000, risk_buffer_rate=0.10, discount_amount=1000, tax_rate=0.06
- **THEN** labor_amount = 10000.00, base_amount = 15000.00, buffer_amount = 1500.00, subtotal_amount = 16500.00, tax_amount = 990.00, total_amount = 16490.00

#### Scenario: Calculation without daily_rate
- **WHEN** daily_rate 为 None
- **THEN** labor_amount = 0.00, 计算链从 base_amount = direct_cost 继续

#### Scenario: Calculation without direct_cost
- **WHEN** direct_cost 为 None
- **THEN** direct_cost 按 0 处理，base_amount = labor_amount

#### Scenario: Precision always 2 decimal places
- **WHEN** 计算产生更多小数位
- **THEN** 每步 round(value, 2)

#### Scenario: No negative total
- **WHEN** discount_amount 大于 subtotal_amount + tax_amount
- **THEN** 系统拒绝，不允许负数结果

### Requirement: Quote preview endpoint
系统 SHALL 提供 POST /api/v1/quotes/preview 端点，纯计算不写库。

#### Scenario: Preview returns calculation result
- **WHEN** 用户提交报价参数到 preview 端点
- **THEN** 返回完整计算结果（labor_amount, base_amount, buffer_amount, subtotal_amount, tax_amount, total_amount）
- **AND** 不写入任何数据库记录

#### Scenario: Preview matches save logic
- **WHEN** 同一套参数分别用于 preview 和正式保存
- **THEN** 金额计算结果完全一致

#### Scenario: Preview rejects negative values
- **WHEN** 提交负数的 daily_rate / direct_cost / discount_amount / tax_rate / risk_buffer_rate
- **THEN** 返回 422 校验错误

### Requirement: Estimate days validation
系统 SHALL 校验预计工期。

#### Scenario: Estimate days must be positive
- **WHEN** estimate_days 为 0 或负数
- **THEN** 返回校验错误

#### Scenario: Estimate days exceeds max limit
- **WHEN** estimate_days 超过 365
- **THEN** 返回校验错误，提示最大允许 365 天
