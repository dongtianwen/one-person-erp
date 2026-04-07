## ADDED Requirements

### Requirement: Project income calculation
系统 SHALL 通过独立函数 `calculate_project_income(project_id, db)` 计算项目收入，聚合 finance_records 中 record_type=INCOME、status=CONFIRMED、且 related_contract_id 对应合同的 project_id 匹配的记录金额之和。无符合记录时返回 Decimal("0.00")。

#### Scenario: Project income from confirmed contract income
- **WHEN** finance_records 中存在 record_type=INCOME、status=CONFIRMED 且关联合同属于该项目
- **THEN** calculate_project_income 返回这些记录的金额之和

#### Scenario: Project income excludes pending records
- **WHEN** finance_records 中存在 record_type=INCOME、status=PENDING 且关联合同属于该项目
- **THEN** 这些记录不计入项目收入

#### Scenario: Project income excludes unrelated contracts
- **WHEN** finance_records 中存在 record_type=INCOME、status=CONFIRMED 但关联合同不属于该项目
- **THEN** 这些记录不计入项目收入

#### Scenario: Project income returns zero when no records
- **WHEN** 项目没有任何符合条件收入记录
- **THEN** calculate_project_income 返回 Decimal("0.00")

### Requirement: Project cost calculation
系统 SHALL 通过独立函数 `calculate_project_cost(project_id, db)` 计算项目成本，聚合 finance_records 中 record_type=EXPENSE、status=CONFIRMED、related_project_id 等于该项目 ID 的记录金额之和。无符合记录时返回 Decimal("0.00")。

#### Scenario: Project cost from related project ID
- **WHEN** finance_records 中存在 record_type=EXPENSE、status=CONFIRMED、related_project_id=该项目 ID
- **THEN** calculate_project_cost 返回这些记录的金额之和

#### Scenario: Project cost excludes unrelated expenses
- **WHEN** finance_records 中存在 record_type=EXPENSE、status=CONFIRMED 但 related_project_id 不等于该项目 ID
- **THEN** 这些记录不计入项目成本

#### Scenario: Project cost returns zero when no records
- **WHEN** 项目没有任何符合条件支出记录
- **THEN** calculate_project_cost 返回 Decimal("0.00")

### Requirement: Project profit calculation
系统 SHALL 通过独立函数 `calculate_project_profit(project_id, db)` 返回包含 income、cost、profit、profit_margin 的字典。profit = round(income - cost, 2)。利润率：income > 0 时 round(profit / income * 100, 2)；income = 0 时返回 None。

#### Scenario: Project profit calculation
- **WHEN** 项目收入 50000.00，成本 8000.00
- **THEN** profit = 42000.00

#### Scenario: Project profit margin correct
- **WHEN** 项目收入 50000.00，利润 42000.00
- **THEN** profit_margin = 84.00

#### Scenario: Project profit margin null when income zero
- **WHEN** 项目收入为 0
- **THEN** profit_margin 返回 None，不得除以零

#### Scenario: Project profit all zero when no records
- **WHEN** 项目没有任何财务记录
- **THEN** income=0.00, cost=0.00, profit=0.00, profit_margin=None

### Requirement: Project profit API endpoint
系统 SHALL 提供 `GET /api/v1/projects/{project_id}/profit` 接口，返回 project_id、project_name、income、cost、profit、profit_margin、currency 字段。profit_margin 为 null 时接口返回 JSON null。

#### Scenario: Project profit API structure exact match
- **WHEN** 请求有效项目 ID 的利润数据
- **THEN** 返回包含 project_id、project_name、income、cost、profit、profit_margin、currency 的 JSON

#### Scenario: Project not found returns 404
- **WHEN** 请求不存在的 project_id
- **THEN** 返回 HTTP 404

### Requirement: Project list includes profit fields
项目列表接口 `GET /api/v1/projects` 的每条项目记录 SHALL 追加 profit 和 profit_margin 字段，为实时计算。列表性能要求：100 个项目的利润汇总 < 1 秒。

#### Scenario: Project list includes profit fields
- **WHEN** 请求项目列表
- **THEN** 每条项目记录包含 profit 和 profit_margin 字段
- **AND** 这些字段为实时计算，非数据库存储

### Requirement: Project profit panel in frontend
项目详情页 SHALL 新增"利润分析"卡片，展示项目收入/成本/利润/利润率。利润率为 null 时显示"—"。利润为负数时数值标红。接口失败时卡片显示"数据加载失败，请刷新"。

#### Scenario: Display profit panel with data
- **WHEN** 项目有收入和成本数据
- **THEN** 四个指标正确展示，利润率有百分号后缀

#### Scenario: Profit margin shows dash when no income
- **WHEN** 项目收入为 0
- **THEN** 利润率显示"—"

#### Scenario: Negative profit displayed in red
- **WHEN** 项目利润为负数
- **THEN** 利润数值标红显示

#### Scenario: Profit panel shows error on API failure
- **WHEN** 利润接口请求失败
- **THEN** 卡片显示"数据加载失败，请刷新"，不影响项目详情其他内容

### Requirement: Project list profit columns in frontend
项目列表页 SHALL 新增"利润"和"利润率"两列。利润率为 null 时显示"—"。利润为负时标红。列表支持按利润率升序/降序排序。

#### Scenario: Project list shows profit columns
- **WHEN** 查看项目列表
- **THEN** 列表包含"利润"和"利润率"两列
- **AND** 利润率为 null 时显示"—"
- **AND** 利润为负时标红
