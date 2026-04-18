## ADDED Requirements

### Requirement: Dashboard summary table schema
系统 SHALL 创建 dashboard_summary 键值聚合表，存储首页仪表盘所需的汇总数据。

#### Scenario: Summary table structure
- **WHEN** 数据库 schema 创建
- **THEN** dashboard_summary 表 SHALL 存在，包含字段：id, metric_key, metric_value, updated_at

#### Scenario: Metric key unique constraint
- **WHEN** 数据库 schema 创建
- **THEN** metric_key SHALL 有 UNIQUE 约束

#### Scenario: Metric key whitelist
- **WHEN** 查看 DASHBOARD_METRIC_KEY_WHITELIST
- **THEN** 包含以下分组键：client_count, client_risk_high_count, project_active_count, project_at_risk_count, contract_active_count, contract_total_amount, finance_receivable_total, finance_overdue_total, finance_overdue_count, delivery_in_progress_count, delivery_completed_this_month, agent_pending_count, agent_high_priority_count

### Requirement: Summary trigger on business events
系统 SHALL 在关键经营事件发生时触发 dashboard_summary 局部刷新。

#### Scenario: Contract confirmed triggers refresh
- **WHEN** 合同状态变更为 confirmed
- **THEN** 刷新 contract_active_count, contract_total_amount, finance_receivable_total

#### Scenario: Payment recorded triggers refresh
- **WHEN** 收款记录录入
- **THEN** 刷新 finance_receivable_total, finance_overdue_total, finance_overdue_count

#### Scenario: Invoice recorded triggers refresh
- **WHEN** 发票记录录入
- **THEN** 刷新 finance_receivable_total

#### Scenario: Delivery completed triggers refresh
- **WHEN** 交付里程碑完成
- **THEN** 刷新 delivery_in_progress_count, delivery_completed_this_month

#### Scenario: Milestone changed triggers refresh
- **WHEN** 里程碑状态变更
- **THEN** 刷新 project_at_risk_count, finance_overdue_total, finance_overdue_count

#### Scenario: Trigger failure does not block main business
- **WHEN** summary 刷新失败
- **THEN** 主业务不回滚，API 返回 success=true + warning_code=SUMMARY_REFRESH_FAILED

### Requirement: Full rebuild summary
系统 SHALL 提供全量重建 dashboard_summary 的接口。

#### Scenario: Full rebuild
- **WHEN** POST /api/v1/dashboard/rebuild-summary 被调用
- **THEN** 遍历所有 metric_key，从源表重新计算并 UPSERT 到 dashboard_summary

#### Scenario: Rebuild idempotent
- **WHEN** 多次调用 rebuild
- **THEN** 结果一致，不产生重复记录

### Requirement: Dashboard summary API
系统 SHALL 提供首页仪表盘汇总数据 API。

#### Scenario: Get summary
- **WHEN** GET /api/v1/dashboard/summary 被调用
- **THEN** 返回 dashboard_summary 表中所有 metric_key 和 metric_value 的键值对

#### Scenario: Missing metric key
- **WHEN** 某个 metric_key 在 dashboard_summary 表中不存在
- **THEN** 该键返回 null 值，前端降级显示"暂无数据"

#### Scenario: Zero cross-table joins
- **WHEN** GET /api/v1/dashboard/summary 执行
- **THEN** SQL 查询仅读取 dashboard_summary 单表，不跨表 join
