## ADDED Requirements

### Requirement: Consistency check for single contract
系统 SHALL 提供对单个合同的只读一致性校验，覆盖四个维度：payment_gap（未收款差异）、invoice_gap（未开票差异）、unlinked_payment（收款未关联发票）、invoice_payment_mismatch（已核销发票与实收差异）。校验 SHALL 为纯只读操作，不修改任何数据库字段。

#### Scenario: No issues when fully paid and invoiced
- **WHEN** 合同已全额收款且全额开票
- **THEN** 返回空 issues 列表

#### Scenario: Payment gap detected
- **WHEN** 合同金额 100000，实收 80000，差额 20000 > CONSISTENCY_CHECK_TOLERANCE
- **THEN** 返回 issue_type=payment_gap，gap_amount=20000

#### Scenario: Invoice gap excludes cancelled invoices
- **WHEN** 合同金额 100000，有一张 cancelled 发票 50000，一张 active 发票 30000
- **THEN** 已开票总额 = 30000（排除 cancelled），invoice_gap = 70000

#### Scenario: Gap below tolerance not reported
- **WHEN** 合同金额与实收差额 <= 0.01（CONSISTENCY_CHECK_TOLERANCE）
- **THEN** 不报告该差异

#### Scenario: Unlinked payment detected
- **WHEN** finance_records 中有 contract_id 但 invoice_id IS NULL 的记录
- **THEN** 返回 issue_type=unlinked_payment

#### Scenario: Invoice payment mismatch uses verified status
- **WHEN** 已核销发票总额（invoices.status='verified'）与实收总额差额 > CONSISTENCY_CHECK_TOLERANCE
- **THEN** 返回 issue_type=invoice_payment_mismatch

### Requirement: Consistency check for all contracts
系统 SHALL 提供对所有合同的只读一致性校验，返回汇总报告含 total_contracts_checked、contracts_with_issues、total_issue_count 及完整 issues 列表。

#### Scenario: All contracts summary counts correct
- **WHEN** 10 个合同中有 2 个存在问题，共 4 个 issues
- **THEN** summary.total_contracts_checked=10, summary.contracts_with_issues=2, summary.total_issue_count=4

#### Scenario: Empty database returns empty report
- **WHEN** 数据库无合同
- **THEN** 返回 total_contracts_checked=0, contracts_with_issues=0, total_issue_count=0

### Requirement: Consistency check produces no writes
所有一致性校验函数 SHALL 不产生任何数据库写操作。

#### Scenario: Verify no writes after check
- **WHEN** 执行一致性校验
- **THEN** 数据库中无任何字段被修改

### Requirement: Consistency check API endpoints
系统 SHALL 提供 GET /api/v1/finance/consistency-check（全局）、GET /api/v1/finance/consistency-check/{contract_id}（单合同）、POST /api/v1/finance/consistency-check/refresh（重新计算）接口。

#### Scenario: Refresh returns latest results
- **WHEN** POST /api/v1/finance/consistency-check/refresh
- **THEN** 重新计算并返回最新结果，不持久化到数据库
