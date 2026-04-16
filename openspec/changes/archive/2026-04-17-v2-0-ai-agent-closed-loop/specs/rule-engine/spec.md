## ADDED Requirements

### Requirement: Overdue payment detection
规则引擎 SHALL 检测逾期回款，按逾期天数分级优先级。

#### Scenario: High risk overdue payment
- **WHEN** 合同 status=active 且回款日期已过 >= OVERDUE_PAYMENT_HIGH_RISK_DAYS（60天）且未收到款项
- **THEN** 生成 suggestion，suggestion_type=overdue_payment，priority=high

#### Scenario: Medium risk overdue payment
- **WHEN** 合同 status=active 且回款日期已过 >= OVERDUE_PAYMENT_WARNING_DAYS（30天）但 < HIGH_RISK_DAYS 且未收到款项
- **THEN** 生成 suggestion，suggestion_type=overdue_payment，priority=medium

#### Scenario: No overdue payment detected
- **WHEN** 所有 active 合同的回款日期未到期或已收到款项
- **THEN** 不生成 overdue_payment 类型建议

### Requirement: Profit anomaly detection
规则引擎 SHALL 检测最近 3 个月完成项目的毛利率异常。

#### Scenario: Profit below threshold
- **WHEN** 项目 status=completed 且在最近 3 个月内，毛利率 < (1 - PROFIT_ANOMALY_THRESHOLD_RATE) 即低于 85%
- **THEN** 生成 suggestion，suggestion_type=profit_anomaly，priority=medium

#### Scenario: Profit above threshold skipped
- **WHEN** 项目 status=completed 但毛利率正常（>= 85%）
- **THEN** 不生成 profit_anomaly 类型建议

### Requirement: Milestone risk detection
规则引擎 SHALL 检测里程碑逾期和即将到期风险。

#### Scenario: Milestone overdue
- **WHEN** milestone status != completed 且 due_date < today
- **THEN** 生成 suggestion，suggestion_type=milestone_risk，priority=high，suggested_action=create_reminder

#### Scenario: Milestone upcoming
- **WHEN** milestone status != completed 且 due_date 在 0 ~ MILESTONE_RISK_DAYS（7天）内
- **THEN** 生成 suggestion，suggestion_type=milestone_risk，priority=medium，suggested_action=create_reminder

#### Scenario: No milestone risk
- **WHEN** 所有未完成 milestone 的 due_date > today + MILESTONE_RISK_DAYS
- **THEN** 不生成 milestone_risk 类型建议

### Requirement: Cashflow warning detection
规则引擎 SHALL 检测未来 N 天内净现金流为负的情况。

#### Scenario: Cashflow negative
- **WHEN** 现金流预测表中未来 CASHFLOW_WARNING_DAYS（30天）内存在净现金流为负的记录
- **THEN** 生成 suggestion，suggestion_type=cashflow_warning，priority=high

#### Scenario: Cashflow table missing
- **WHEN** 现金流预测表不存在
- **THEN** 返回空列表，记录 DEBUG 日志，不报错

### Requirement: Task delay detection
规则引擎 SHALL 检测任务超期，支持按 project_id 过滤。

#### Scenario: Task delay detected
- **WHEN** task due_date < today 且 status != completed 且超期 >= TASK_DELAY_WARNING_DAYS（3天）
- **THEN** 生成 suggestion，suggestion_type=task_delay，priority=medium

#### Scenario: Task delay with project filter
- **WHEN** project_id 非 None 传入
- **THEN** 只返回该项目的任务延期建议

### Requirement: Change impact detection
规则引擎 SHALL 检测待处理的变更请求对 active 项目的影响。

#### Scenario: Change impact pending on active project
- **WHEN** requirement_changes/change_orders 中 status=pending 且关联项目 status=active
- **THEN** 生成 suggestion，suggestion_type=change_impact，priority=high，suggested_action=none

### Requirement: Rule engine composition
规则引擎 SHALL 提供组合函数，按 Agent 类型组合不同检测模块。

#### Scenario: Business decision rules composition
- **WHEN** run_business_decision_rules 被调用
- **THEN** 组合 overdue_payments + profit_anomaly + milestone_risk + cashflow_warning，按 priority 排序（high 在前）

#### Scenario: Project management rules composition
- **WHEN** run_project_management_rules 被调用
- **THEN** 组合 task_delay(project_id) + change_impact(project_id)

### Requirement: No hardcoded thresholds
规则引擎 SHALL 从 constants.py 引用所有阈值，禁止硬编码数字。

#### Scenario: All thresholds from constants
- **WHEN** 审查规则引擎源代码
- **THEN** 所有阈值引用均来自 constants.py 中的常量名
