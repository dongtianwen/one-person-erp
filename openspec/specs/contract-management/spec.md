# contract-management Specification

## Purpose
合同全生命周期管理，从报价到归档，追踪合同状态和金额。

## Requirements

### Requirement: Contract creation
系统 SHALL 支持创建合同并自动生成编号。

#### Scenario: Create contract with auto-generated number
- GIVEN 用户已登录
- WHEN 用户创建合同
- THEN 系统自动生成合同编号
- AND 编号格式: HT-YYYYMMDD-序号 (如 HT-20260404-001)
- AND 确保编号唯一性

#### Scenario: Create contract with required fields
- GIVEN 用户创建合同
- WHEN 用户提供合同标题、金额、关联客户
- THEN 系统创建合同记录
- AND 初始状态为"草稿"

#### Scenario: Create contract with optional fields
- GIVEN 用户创建合同
- WHEN 用户提供关联项目、签署日期、生效日期、到期日期、合同条款
- THEN 系统存储所有信息
- AND 校验到期日期不早于生效日期

### Requirement: Contract retrieval
系统 SHALL 支持查询合同信息。

#### Scenario: Get contract by ID
- GIVEN 合同存在
- WHEN 用户请求合同详情
- THEN 系统返回完整合同信息
- AND 包含关联财务记录列表

#### Scenario: List contracts with filtering
- GIVEN 系统中存在多个合同
- WHEN 用户请求合同列表
- THEN 系统返回分页结果
- AND 支持按状态/时间筛选
- AND 支持按合同编号/标题搜索

### Requirement: Contract status workflow
系统 SHALL 管理合同状态流转。

#### Scenario: Valid status transitions
- GIVEN 合同处于某一状态
- WHEN 用户尝试变更状态
- THEN 系统仅允许合法流转:
  - 草稿 → 生效 → 执行中 → 已完成
  - 任意状态 → 终止
- AND 记录状态变更日志

#### Scenario: Contract termination
- GIVEN 合同处于生效/执行中状态
- WHEN 用户将状态变更为"终止"
- THEN 系统要求填写终止原因
- AND 拒绝无原因的终止操作
- AND 记录终止时间

#### Scenario: Expiring contract notification
- GIVEN 合同设置了到期日期
- WHEN 当前日期距离到期日期 ≤ 7天
- THEN 系统标记合同为"即将到期"
- AND 在列表中高亮显示

### Requirement: Contract amount sync
系统 SHALL 同步合同金额至关联项目。

#### Scenario: Sync contract amount to project budget
- GIVEN 合同关联了项目
- WHEN 合同金额发生变更
- THEN 系统同步更新关联项目的预算金额
- AND 记录预算变更原因

### Requirement: Contract deletion
系统 SHALL 支持删除合同，但有安全限制。

#### Scenario: Delete draft contract
- GIVEN 合同状态为"草稿"
- WHEN 用户删除合同
- THEN 系统软删除合同
- AND 无关联财务记录时直接删除

#### Scenario: Prevent delete active contract
- GIVEN 合同状态为"生效"或"执行中"
- WHEN 用户尝试删除合同
- THEN 系统拒绝删除
- AND 提示"生效中的合同不可删除，请先终止"
