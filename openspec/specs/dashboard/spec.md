# dashboard Specification

## Purpose
核心业务指标可视化，辅助一人软件公司经营决策。

## Requirements

### Requirement: Key metrics display
系统 SHALL 在仪表盘展示关键业务指标。

#### Scenario: Display current month revenue
- GIVEN 系统中存在财务记录
- WHEN 用户访问仪表盘
- THEN 系统展示本月已确认收入总额
- AND 数据实时更新

#### Scenario: Display current month expenses
- GIVEN 系统中存在财务记录
- WHEN 用户访问仪表盘
- THEN 系统展示本月已确认支出总额
- AND 数据实时更新

#### Scenario: Display current month profit
- GIVEN 系统中存在财务记录
- WHEN 用户访问仪表盘
- THEN 系统展示本月利润（收入 - 支出）
- AND 利润为负数时以红色显示

#### Scenario: Display active projects count
- GIVEN 系统中存在项目
- WHEN 用户访问仪表盘
- THEN 系统展示进行中项目数量
- AND 进行中项目定义: 状态非"交付"且非"暂停"

### Requirement: Revenue trend chart
系统 SHALL 展示营收趋势图。

#### Scenario: Monthly revenue trend
- GIVEN 系统中存在财务记录
- WHEN 用户访问仪表盘
- THEN 系统展示最近12个月营收折线图
- AND X轴为月份，Y轴为金额
- AND 同时展示收入和支出两条线

### Requirement: Customer conversion funnel
系统 SHALL 展示客户转化漏斗。

#### Scenario: Conversion funnel visualization
- GIVEN 系统中存在客户
- WHEN 用户访问仪表盘
- THEN 系统展示漏斗图: 潜在 → 跟进 → 成交
- AND 显示各阶段客户数量
- AND 显示阶段转化率（跟进/潜在、成交/跟进）

### Requirement: Project status distribution
系统 SHALL 展示项目状态分布。

#### Scenario: Project status pie chart
- GIVEN 系统中存在项目
- WHEN 用户访问仪表盘
- THEN 系统展示饼图
- AND 按状态分组: 需求/设计/开发/测试/交付/暂停
- AND 显示各状态项目数量和占比

### Requirement: Todo items display
系统 SHALL 展示待办事项。

#### Scenario: Display pending tasks
- GIVEN 系统中存在未完成任务
- WHEN 用户访问仪表盘
- THEN 系统展示状态为"待办"和"进行中"的任务
- AND 按优先级排序（紧急 > 高 > 中 > 低）
- AND 显示任务标题、所属项目、截止日期

#### Scenario: Display expiring contracts
- GIVEN 系统中存在即将到期的合同
- WHEN 用户访问仪表盘
- THEN 系统展示距离到期 ≤ 7天的合同
- AND 显示合同编号、标题、到期日期

### Requirement: Quick actions
系统 SHALL 提供快捷操作入口。

#### Scenario: Quick create customer
- GIVEN 用户在仪表盘页面
- WHEN 用户点击"新建客户"
- THEN 系统跳转至客户创建页面

#### Scenario: Quick create project
- GIVEN 用户在仪表盘页面
- WHEN 用户点击"新建项目"
- THEN 系统跳转至项目创建页面

#### Scenario: Quick create contract
- GIVEN 用户在仪表盘页面
- WHEN 用户点击"新建合同"
- THEN 系统跳转至合同创建页面
