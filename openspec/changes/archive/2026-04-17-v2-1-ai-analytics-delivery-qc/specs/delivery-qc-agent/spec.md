## ADDED Requirements

### Requirement: Delivery package evaluation rules
系统 SHALL 提供 `evaluate_delivery_package` 函数，对指定交付包执行完整性检查。

#### Scenario: Missing model version
- **WHEN** delivery_packages 未关联任何 model_versions
- **THEN** 生成 suggestion，suggestion_type=delivery_missing_model，priority=high，suggested_action=create_todo

#### Scenario: Missing dataset version
- **WHEN** delivery_packages 未关联任何 dataset_versions
- **THEN** 生成 suggestion，suggestion_type=delivery_missing_dataset，priority=medium，suggested_action=create_todo

#### Scenario: Missing acceptance record
- **WHEN** delivery_packages.status != accepted 且无对应 acceptances 记录
- **THEN** 生成 suggestion，suggestion_type=delivery_missing_acceptance，priority=high，suggested_action=create_reminder

#### Scenario: Version mismatch
- **WHEN** package_model_versions 关联的 model_version.status = deprecated
- **THEN** 生成 suggestion，suggestion_type=delivery_version_mismatch，priority=high，suggested_action=create_todo

#### Scenario: Empty package
- **WHEN** 交付包无任何关键内容或附件
- **THEN** 生成 suggestion，suggestion_type=delivery_empty_package，priority=high，suggested_action=create_todo

#### Scenario: Unbound project
- **WHEN** 交付包未绑定有效项目
- **THEN** 生成 suggestion，suggestion_type=delivery_unbound_project，priority=high，suggested_action=create_todo

#### Scenario: All checks pass
- **WHEN** 交付包通过所有完整性检查
- **THEN** 返回空列表

#### Scenario: Package not found
- **WHEN** package_id 不存在
- **THEN** 抛出 DELIVERY_QC_NO_PACKAGE 错误

### Requirement: Delivery QC agent run
系统 SHALL 扩展 Agent 运行支持 delivery_qc 类型。

#### Scenario: Run delivery QC agent
- **WHEN** POST /api/v1/agents/delivery-qc/run 传入 package_id
- **THEN** 创建 agent_runs 记录（agent_type=delivery_qc），执行质检规则，返回 agent_run_id, status, llm_provider_used, llm_enhanced, suggestions

#### Scenario: Suggestions written to agent_suggestions
- **WHEN** delivery QC 运行完成
- **THEN** 检测到的问题写入 agent_suggestions 表，关联 agent_run_id

#### Scenario: LLM enhancement for QC
- **WHEN** use_llm=true 且 Provider 可用
- **THEN** 质检建议经 LLM 语言增强（描述更自然）

#### Scenario: Without LLM uses rule text
- **WHEN** use_llm=false 或 Provider 不可用
- **THEN** 质检建议使用规则引擎原始文本

#### Scenario: Confirm QC suggestion creates action
- **WHEN** 用户确认质检建议
- **THEN** 通过 v2.0 confirm_suggestion 流程创建 agent_actions 记录（如 create_todo）
