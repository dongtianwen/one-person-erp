## ADDED Requirements

### Requirement: Delivery package QC rules
规则引擎 SHALL 提供交付包完整性检查规则，新增 delivery_qc 类型组合函数。

#### Scenario: Delivery QC rules composition
- **WHEN** run_delivery_qc_rules 被调用
- **THEN** 调用 evaluate_delivery_package(db, package_id)，返回检测结果列表

#### Scenario: Six QC suggestion types defined
- **WHEN** 查看 constants.py
- **THEN** 包含 SUGGESTION_TYPE_DELIVERY_MISSING_MODEL, SUGGESTION_TYPE_DELIVERY_MISSING_DATASET, SUGGESTION_TYPE_DELIVERY_MISSING_ACCEPTANCE, SUGGESTION_TYPE_DELIVERY_VERSION_MISMATCH, SUGGESTION_TYPE_DELIVERY_EMPTY_PACKAGE, SUGGESTION_TYPE_DELIVERY_UNBOUND_PROJECT

#### Scenario: All thresholds from constants
- **WHEN** 审查质检规则源代码
- **THEN** 所有阈值和类型引用均来自 constants.py 中的常量名
