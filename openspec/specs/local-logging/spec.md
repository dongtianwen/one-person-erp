## ADDED Requirements

### Requirement: Log file rotation
系统 SHALL 使用 RotatingFileHandler 管理日志文件。

#### Scenario: Log rotation by size
- GIVEN 日志文件正在写入
- WHEN 单个日志文件超过 10MB
- THEN 系统自动轮转到新文件
- AND 保留最近 30 个日志文件
- AND 日志文件存放在项目根目录 logs/ 文件夹

#### Scenario: Log directory auto creation
- GIVEN 系统启动
- WHEN logs/ 目录不存在
- THEN 系统自动创建 logs/ 目录

### Requirement: Log format
系统 SHALL 使用结构化日志格式。

#### Scenario: Structured log format
- GIVEN 系统记录日志
- WHEN 写入日志条目
- THEN 格式为：时间戳 | 级别 | 模块 | 消息
- AND 时间戳格式为 ISO 8601

### Requirement: Mandatory logging scope
系统 SHALL 强制记录以下范围的事件。

#### Scenario: Log database write exceptions
- GIVEN 数据库写入操作发生异常
- WHEN 异常被捕获
- THEN 系统将异常详情写入日志
- AND 向前端返回明确错误提示
- AND 禁止静默失败

#### Scenario: Log file IO exceptions
- GIVEN 文件 I/O 操作发生异常
- WHEN 异常被捕获
- THEN 系统将异常详情写入日志
- AND 向前端返回明确错误提示

#### Scenario: Log event-driven check execution
- GIVEN 事件驱动逾期检查执行
- WHEN 检查完成
- THEN 系统记录触发来源、处理条数、耗时

#### Scenario: Log system startup and shutdown
- GIVEN 后端服务启动或关闭
- WHEN 服务状态变更
- THEN 系统记录启停事件

### Requirement: Sensitive data exclusion
系统 SHALL 禁止在日志中记录敏感信息。

#### Scenario: Filter sensitive data from logs
- GIVEN 系统准备写入日志
- WHEN 日志内容包含密码、Token 或 API Key
- THEN 系统将敏感信息替换为 [REDACTED]
- AND 不影响日志其余内容的可读性
