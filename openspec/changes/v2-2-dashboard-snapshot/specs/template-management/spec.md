## MODIFIED Requirements

### Requirement: System stores templates for document generation
系统 SHALL 存储 Jinja2 模板用于文档生成，模板类型白名单扩展为包含报告类型及交付/复盘/报价类型；模板保存 SHALL 自动触发 snapshot。

#### Scenario: Template table structure
- **WHEN** database schema is created
- **THEN** templates table SHALL exist with columns: id, name, template_type, content, is_default, description, created_at, updated_at

#### Scenario: Default templates
- **WHEN** system initializes
- **THEN** 默认模板 SHALL 存在：quotation、contract、report_project、report_customer、delivery、retrospective、quotation_calc 各一个
- **THEN** 每个默认模板 SHALL 有 is_default = 1
- **THEN** 每个默认模板 SHALL 有 unique constraint on (template_type, is_default) WHERE is_default = 1

#### Scenario: Template type whitelist includes all types
- **WHEN** 查看 TEMPLATE_TYPE_WHITELIST
- **THEN** 包含 "quotation", "contract", "report_project", "report_customer", "delivery", "retrospective", "quotation_calc"

#### Scenario: Report templates idempotent insert
- **WHEN** 系统初始化且默认模板已存在
- **THEN** 不重复插入，先查 template_type + is_default=1 存在则跳过

#### Scenario: Template save triggers snapshot
- **WHEN** 模板内容保存成功
- **THEN** 自动调用 create_snapshot(entity_type="template", entity_id=模板id, content=模板内容)

#### Scenario: Template snapshot failure does not block save
- **WHEN** 模板保存成功但快照创建失败
- **THEN** 模板仍保存成功，API 返回 success=true + warning_code=SNAPSHOT_CREATE_FAILED

### Requirement: System enforces template variable consistency
系统 SHALL 定义和强制模板变量一致性，报告模板无必填变量校验。

#### Scenario: Report project template variables
- **WHEN** 渲染 report_project 模板
- **THEN** 结构性变量由代码拼装（project_name, customer_name, generated_date, start_date, end_date, duration_days, contract_amount, received_amount, pending_amount, total_hours, milestone_completion_rate, change_count, acceptance_passed, gross_margin_rate, direct_cost, outsource_cost）
- **THEN** LLM 变量由 fill_llm_vars 填充（analysis_summary, risk_retrospective, improvement_suggestions）
- **THEN** 无必填变量校验（required_vars=[]），LLM 变量已有兜底

#### Scenario: Report customer template variables
- **WHEN** 渲染 report_customer 模板
- **THEN** 结构性变量由代码拼装（customer_name, generated_date, project_count, total_contract_amount, total_received_amount, total_pending, first_project_date, last_project_date, ltv_estimate, avg_project_amount, payment_on_time_rate）
- **THEN** LLM 变量由 fill_llm_vars 填充（value_assessment, relationship_summary, next_action_suggestions）
- **THEN** 无必填变量校验（required_vars=[]），LLM 变量已有兜底
