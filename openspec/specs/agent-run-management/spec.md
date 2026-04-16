## MODIFIED Requirements

### Requirement: Agent run lifecycle management
系统 SHALL 管理 Agent 运行的完整生命周期，支持 delivery_qc 类型。

#### Scenario: Create delivery QC agent run
- **WHEN** 用户触发交付质检分析
- **THEN** 系统创建 agent_runs 记录，agent_type=delivery_qc，status=running，created_at=当前时间

#### Scenario: Delivery QC agent type in whitelist
- **WHEN** 查看 AGENT_TYPE_WHITELIST
- **THEN** 包含 AGENT_TYPE_BUSINESS_DECISION, AGENT_TYPE_PROJECT_MANAGEMENT, AGENT_TYPE_DELIVERY_QC

#### Scenario: Concurrent run prevention for delivery QC
- **WHEN** 用户触发 delivery_qc 运行且存在 status=running 的 delivery_qc 记录
- **THEN** 系统返回 409，错误码 AGENT_ALREADY_RUNNING

#### Scenario: Delivery QC can run concurrently with other types
- **WHEN** business_decision 正在运行，用户触发 delivery_qc
- **THEN** delivery_qc 正常运行，不受影响
