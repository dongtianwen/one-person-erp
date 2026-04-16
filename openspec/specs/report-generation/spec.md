## ADDED Requirements

### Requirement: Reports table schema
系统 SHALL 创建 reports 表存储报告记录，支持版本管理。

#### Scenario: Reports table structure
- **WHEN** 数据库 schema 创建
- **THEN** reports 表 SHALL 存在，包含字段：id, report_type, entity_id, entity_type, template_id, parent_report_id, version_no, is_latest, content, llm_filled_vars, llm_provider, llm_model, status, error_message, generated_at, created_at

#### Scenario: Entity index exists
- **WHEN** 数据库 schema 创建
- **THEN** idx_reports_entity 索引 SHALL 存在于 (entity_type, entity_id, created_at DESC)

#### Scenario: Type status index exists
- **WHEN** 数据库 schema 创建
- **THEN** idx_reports_type_status 索引 SHALL 存在于 (report_type, status)

#### Scenario: Template foreign key
- **WHEN** reports 表创建
- **THEN** template_id 引用 templates(id)，ON DELETE SET NULL

#### Scenario: Parent report foreign key
- **WHEN** reports 表创建
- **THEN** parent_report_id 引用 reports(id)，ON DELETE SET NULL

### Requirement: Project report context builder
系统 SHALL 提供 `build_project_report_context` 函数，从数据库读取项目相关结构性数据。

#### Scenario: Context returns required fields
- **WHEN** build_project_report_context 被调用且 project_id 存在
- **THEN** 返回 context 包含：project_name, customer_name, generated_date, start_date, end_date, duration_days, contract_amount, received_amount, pending_amount, total_hours, milestone_completion_rate, change_count, acceptance_passed, gross_margin_rate, direct_cost, outsource_cost

#### Scenario: Project not found
- **WHEN** build_project_report_context 被调用且 project_id 不存在
- **THEN** 抛出 REPORT_ENTITY_NOT_FOUND 错误

### Requirement: Customer report context builder
系统 SHALL 提供 `build_customer_report_context` 函数，从数据库读取客户相关结构性数据。

#### Scenario: Context returns required fields
- **WHEN** build_customer_report_context 被调用且 customer_id 存在
- **THEN** 返回 context 包含：customer_name, generated_date, project_count, total_contract_amount, total_received_amount, total_pending, first_project_date, last_project_date, ltv_estimate, avg_project_amount, payment_on_time_rate

#### Scenario: Customer not found
- **WHEN** build_customer_report_context 被调用且 customer_id 不存在
- **THEN** 抛出 REPORT_ENTITY_NOT_FOUND 错误

### Requirement: LLM variable filling
系统 SHALL 提供 `fill_llm_vars` 函数，对报告中的 LLM 变量逐个填充。

#### Scenario: Provider none uses fallback
- **WHEN** LLM_PROVIDER=none
- **THEN** 所有 LLM 变量填入 REPORT_LLM_FALLBACK_TEXT

#### Scenario: Provider unavailable uses fallback
- **WHEN** Provider 不可用
- **THEN** 所有 LLM 变量填入 REPORT_LLM_FALLBACK_TEXT

#### Scenario: Successful filling
- **WHEN** Provider 可用且调用成功
- **THEN** LLM 变量填入模型返回的文本内容

#### Scenario: Partial failure fills fallback for failed vars
- **WHEN** 部分变量填充成功，部分失败
- **THEN** 成功变量填入内容，失败变量填入 REPORT_LLM_FALLBACK_TEXT，记录 WARNING(REPORT_LLM_FILL_FAILED)

#### Scenario: No exception on fill failure
- **WHEN** fill_llm_vars 执行
- **THEN** 不抛异常，所有失败均降级为 fallback 文本

### Requirement: Report generation
系统 SHALL 提供 `generate_report` 函数，生成报告并写入 reports 表。

#### Scenario: Type not supported
- **WHEN** report_type 不在 REPORT_TYPE_WHITELIST
- **THEN** 抛出 REPORT_TYPE_NOT_SUPPORTED 错误

#### Scenario: Creates report record
- **WHEN** generate_report 被调用且参数有效
- **THEN** 创建 reports 记录，初始 status=generating

#### Scenario: Report status completed
- **WHEN** 报告生成成功
- **THEN** reports.status 更新为 completed，content 包含渲染结果

#### Scenario: Report content not null on completion
- **WHEN** 报告生成成功
- **THEN** content 字段不为 null

#### Scenario: Generation failure sets status failed
- **WHEN** 报告生成过程中抛出异常
- **THEN** reports.status 更新为 failed，error_message 写入错误信息

#### Scenario: LLM fill failed still completes
- **WHEN** LLM 填充失败
- **THEN** 报告仍 status=completed，分析段落显示 REPORT_LLM_FALLBACK_TEXT

#### Scenario: Uses default template when not specified
- **WHEN** template_id 为 null
- **THEN** 使用该 report_type 的默认模板（is_default=1）

#### Scenario: Version increment on regeneration
- **WHEN** 同一 entity 已存在 is_latest=1 的报告
- **THEN** 旧报告 is_latest=0，新报告 parent_report_id 指向旧报告，version_no = 旧版本 + 1，is_latest=1

### Requirement: Report API endpoints
系统 SHALL 提供报告相关的 REST API 端点。

#### Scenario: Generate report
- **WHEN** POST /api/v1/reports/generate 传入 report_type 和 entity_id
- **THEN** 返回 report_id, status, content（可能为 null）

#### Scenario: List reports
- **WHEN** GET /api/v1/reports?entity_type=&entity_id=&limit=10&offset=0
- **THEN** 返回 reports 数组和 total 总数

#### Scenario: Get report detail
- **WHEN** GET /api/v1/reports/{id}
- **THEN** 返回报告详情和 content

#### Scenario: Delete report
- **WHEN** DELETE /api/v1/reports/{id}
- **THEN** 返回 { deleted: true }

### Requirement: LLM single variable fill method
支持报告的 Provider SHALL 实现 `_call_llm_single_var` 方法，针对单个报告变量生成文本。

#### Scenario: Single var fill success
- **WHEN** _call_llm_single_var 被调用且 Provider 可用
- **THEN** 返回纯文本字符串（非 JSON）

#### Scenario: Single var fill timeout
- **WHEN** _call_llm_single_var 调用超时
- **THEN** 返回 None

#### Scenario: Not on NullProvider
- **WHEN** 审查 NullProvider 类定义
- **THEN** 不存在 _call_llm_single_var 方法
