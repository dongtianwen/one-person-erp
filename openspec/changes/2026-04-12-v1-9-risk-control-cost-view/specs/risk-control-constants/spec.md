## ADDED Requirements

### Requirement: v1.9 constants definition
系统 SHALL 在 backend/core/constants.py 中追加以下常量，禁止修改已有常量：HOURS_PER_DAY=8、OVERDUE_PAYMENT_WARN_DAYS=0、CUSTOMER_OVERDUE_WARN_THRESHOLD=1、CUSTOMER_OVERDUE_HIGH_THRESHOLD=3、CUSTOMER_OVERDUE_HIGH_RATIO=0.30、CONSISTENCY_CHECK_TOLERANCE=0.01、FIXED_COST_PERIOD_WHITELIST、FIXED_COST_CATEGORY_WHITELIST、GROSS_PROFIT_DECIMAL_PLACES=2、GROSS_MARGIN_DECIMAL_PLACES=4。

#### Scenario: Hours per day constant exists
- **WHEN** 导入 constants.py
- **THEN** HOURS_PER_DAY = 8

#### Scenario: Existing constants unchanged
- **WHEN** 追加 v1.9 常量
- **THEN** 已有常量值不变
