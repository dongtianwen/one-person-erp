## MODIFIED Requirements

### Requirement: Key metrics display
系统仪表盘 SHALL 在现有指标基础上新增"逾期预警"区块和"项目粗利润"列表。

#### Scenario: Display overdue warning section
- **WHEN** 用户访问仪表盘
- **THEN** 展示逾期里程碑列表（项目名 / 客户 / 金额 / 逾期天数）
- **AND** 逾期天数 > 30 天标红，7-30 天标橙，< 7 天标黄

#### Scenario: Display project profit top 5
- **WHEN** 用户访问仪表盘
- **THEN** 展示项目粗利润 Top 5 列表（读 projects 缓存字段）
