## ADDED Requirements

### Requirement: Backup file verification
系统 SHALL 支持将备份文件加载为临时数据库并校验数据完整性。

#### Scenario: Verify backup integrity
- GIVEN 备份文件存在
- WHEN 用户触发备份校验
- THEN 系统将备份文件加载为临时数据库
- AND 验证各核心表记录数与备份时一致
- AND 校验通过显示"备份有效"
- AND 校验失败显示具体错误信息

#### Scenario: Verify does not affect running database
- GIVEN 系统正在运行
- WHEN 执行备份校验
- THEN 校验过程在临时路径操作
- AND 不影响当前运行的数据库

#### Scenario: Auto cleanup after verification
- GIVEN 备份校验完成（无论成功或失败）
- WHEN 校验流程结束
- THEN 系统自动清理临时文件

### Requirement: Backup verification report
系统 SHALL 展示各核心表的记录数对比报告。

#### Scenario: Display table record count comparison
- GIVEN 备份校验完成
- WHEN 用户查看校验报告
- THEN 系统展示各核心表（customers/projects/contracts/finance_records/reminders/file_indexes）的记录数
- AND 对比备份时记录数与校验时记录数

### Requirement: Backup history management
系统 SHALL 展示所有备份文件及其校验状态。

#### Scenario: List backup files
- GIVEN 系统中存在备份文件
- WHEN 用户查看备份历史
- THEN 系统展示所有备份文件列表
- AND 显示备份时间、文件大小
- AND 显示最后校验时间和校验结果（未校验/通过/失败）

#### Scenario: Manual trigger verification
- GIVEN 备份文件存在
- WHEN 用户点击"验证"按钮
- THEN 系统执行完整性校验
- AND 更新该备份文件的校验时间和结果

### Requirement: Backup creation unchanged
系统 SHALL 保持 v1.0 的一键备份功能不变。

#### Scenario: One-click backup still works
- GIVEN 用户在仪表盘页面
- WHEN 用户点击"备份数据库"
- THEN 系统创建 SQLite 备份，文件名含时间戳
- AND 不覆盖历史备份
