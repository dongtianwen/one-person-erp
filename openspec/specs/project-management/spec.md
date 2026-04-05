# project-management Specification

## Purpose
项目全生命周期管理，任务分解，进度追踪，支持一人软件公司高效交付。

## Requirements

### Requirement: Project creation
系统 SHALL 支持创建新项目并关联客户。

#### Scenario: Create project with required fields
- GIVEN 用户已登录且存在客户
- WHEN 用户提供项目名称、关联客户、描述
- THEN 系统创建项目记录
- AND 初始状态为"需求阶段"
- AND 进度初始化为 0%

#### Scenario: Create project with budget and dates
- GIVEN 用户创建项目
- WHEN 用户提供预算金额、开始日期、结束日期
- THEN 系统校验预算为正数
- AND 校验结束日期不早于开始日期
- AND 存储项目信息

### Requirement: Project retrieval
系统 SHALL 支持查询项目信息。

#### Scenario: Get project by ID
- GIVEN 项目存在
- WHEN 用户请求项目详情
- THEN 系统返回项目完整信息
- AND 包含关联任务列表
- AND 包含里程碑列表
- AND 包含关联客户信息

#### Scenario: List projects with filtering
- GIVEN 系统中存在多个项目
- WHEN 用户请求项目列表
- THEN 系统返回分页结果
- AND 支持按状态/客户/时间筛选
- AND 默认按创建时间倒序

### Requirement: Project status management
系统 SHALL 管理项目状态流转。

#### Scenario: Valid status transitions
- GIVEN 项目处于某一状态
- WHEN 用户尝试变更状态
- THEN 系统仅允许合法流转:
  - 需求 → 设计 → 开发 → 测试 → 交付
  - 任意状态 → 暂停
  - 暂停 → 恢复至原状态
- AND 记录状态变更日志（时间、操作人、原因）

#### Scenario: Auto-complete on milestones
- GIVEN 项目所有里程碑均标记为完成
- WHEN 系统检测里程碑状态
- THEN 项目进度自动更新为 100%
- AND 项目状态建议变更为"交付"

### Requirement: Task management
系统 SHALL 支持项目任务的增删改查。

#### Scenario: Create task
- GIVEN 项目存在
- WHEN 用户提供任务标题、描述、优先级
- THEN 系统创建任务
- AND 初始状态为"待办"
- AND 关联至所属项目

#### Scenario: Update task status
- GIVEN 任务存在
- WHEN 用户变更任务状态（待办→进行中→已完成/已取消）
- THEN 系统更新任务状态
- AND 记录变更时间
- AND 重新计算项目进度

#### Scenario: Task due date reminder
- GIVEN 任务设置了截止日期
- WHEN 当前日期距离截止日期 ≤ 3天 且任务未完成
- THEN 系统标记任务为"即将超期"
- AND 在列表中高亮显示（v1.1 推送通知）

### Requirement: Milestone management
系统 SHALL 支持项目关键节点管理。

#### Scenario: Create milestone
- GIVEN 项目存在
- WHEN 用户提供里程碑标题、计划日期
- THEN 系统创建里程碑
- AND 初始状态为"未完成"

#### Scenario: Complete milestone
- GIVEN 里程碑存在
- WHEN 用户标记里程碑为完成
- THEN 系统记录实际完成日期
- AND 自动更新项目进度
- AND 进度计算: (已完成里程碑数 / 总里程碑数) × 100%

### Requirement: Project deletion
系统 SHALL 支持删除项目，但有安全限制。

#### Scenario: Delete project
- GIVEN 项目存在
- WHEN 用户删除项目
- THEN 系统软删除项目
- AND 同时软删除关联任务和里程碑
- AND 若项目有关联合同，提示确认
