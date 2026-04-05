## MODIFIED Requirements

### Requirement: Key metrics display
系统 SHALL 在仪表盘展示关键业务指标，包含报价转化率。

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

#### Scenario: Display quotation conversion rate
- GIVEN 系统中存在报价单
- WHEN 用户访问仪表盘
- THEN 系统展示报价转化率
- AND 计算方式：已接受数 / 总报价数（草稿除外）x 100%

## ADDED Requirements

### Requirement: Dashboard triggered overdue check
仪表盘统计接口 SHALL 触发事件驱动逾期检查（触发点B）。

#### Scenario: Dashboard API triggers check
- GIVEN 前端请求仪表盘统计接口
- WHEN 接口被调用
- THEN 系统先执行限流逾期检查
- THEN 返回仪表盘统计数据
