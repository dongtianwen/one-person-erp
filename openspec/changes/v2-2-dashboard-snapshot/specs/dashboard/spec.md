## MODIFIED Requirements

### Requirement: Dashboard workflow entry
首页看板 SHALL 新增流程入口卡片，点击跳转到业务流程总览页面；首页仪表盘数据 SHALL 从 dashboard_summary 聚合表读取，零跨表 join。

#### Scenario: Workflow card on dashboard
- **WHEN** 用户访问首页看板
- **THEN** 看板中显示"业务流程"入口卡片，点击跳转到流程总览页面

#### Scenario: Navigation workflow link
- **WHEN** 查看顶部导航栏
- **THEN** 包含"业务流程"链接，点击跳转到流程总览页面

#### Scenario: Dashboard reads from summary table
- **WHEN** GET /api/v1/dashboard/summary 被调用
- **THEN** 仅读取 dashboard_summary 单表，不跨表 join

#### Scenario: Dashboard displays six widget groups
- **WHEN** 用户访问首页看板
- **THEN** 显示六组 widget：客户概览、项目概览、合同概览、财务概览、交付概览、经营提醒

#### Scenario: Missing metric shows fallback
- **WHEN** 某个 metric_key 在 dashboard_summary 表中不存在
- **THEN** 前端降级显示"暂无数据"
