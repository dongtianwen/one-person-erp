## ADDED Requirements

### Requirement: Startup full check
系统 SHALL 在后端服务每次启动时执行一次全量逾期检查。

#### Scenario: Full check on startup
- GIVEN 后端服务启动
- WHEN 服务完成初始化
- THEN 系统执行全量逾期检查（不受条数限制）
- AND 同一进程生命周期内仅执行一次
- AND 记录日志：触发来源=启动、开始时间、处理条数、结束时间

### Requirement: Dashboard triggered check
系统 SHALL 在前端每次调用仪表盘统计接口时执行限流逾期检查。

#### Scenario: Throttled check on dashboard request
- GIVEN 前端请求仪表盘统计接口
- WHEN 系统执行逾期检查
- THEN 仅处理检查日期前后 90 天窗口内的数据
- AND 单次检查最大处理 1000 条
- AND 超出部分顺延至下次触发
- AND 记录日志：触发来源=仪表盘、开始时间、处理条数、结束时间

### Requirement: Reminder overdue check
系统 SHALL 将所有过期的"待处理"提醒变更为"已逾期"。

#### Scenario: Overdue pending reminders
- GIVEN 存在状态为"待处理"的提醒
- AND 提醒日期已过
- WHEN 逾期检查触发
- THEN 系统将状态变更为"已逾期"

### Requirement: Quotation expiry check
系统 SHALL 将所有过期的有效报价单变更为"已过期"。

#### Scenario: Expire quotations past validity date
- GIVEN 存在状态为"草稿"或"已发送"的报价单
- AND 有效期至日期已过
- WHEN 逾期检查触发
- THEN 系统将状态变更为"已过期"

### Requirement: Customer asset reminder check
系统 SHALL 为即将到期的客户资产自动创建提醒。

#### Scenario: Generate asset expiry reminder
- GIVEN 存在客户资产记录有到期日期
- AND 到期前 30 天内
- AND 尚未生成过该资产的到期提醒
- WHEN 逾期检查触发
- THEN 系统创建"客户资产到期提醒"（类型=asset_expiry）
- AND 幂等保护，不重复生成

### Requirement: File index reminder check
系统 SHALL 为即将到期的文件索引自动创建提醒。

#### Scenario: Generate file expiry reminder
- GIVEN 存在文件索引记录有到期日期
- AND 到期前 30 天内
- AND 尚未生成过该文件的到期提醒
- WHEN 逾期检查触发
- THEN 系统创建"文件到期提醒"（类型=file_expiry）
- AND 幂等保护，不重复生成

### Requirement: Check execution logging
系统 SHALL 记录每次逾期检查的执行日志。

#### Scenario: Log check execution
- GIVEN 逾期检查触发
- WHEN 检查开始执行
- THEN 系统记录触发来源（启动/仪表盘）
- AND 记录开始时间
- AND 检查完成后记录处理条数和结束时间
