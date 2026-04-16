## ADDED Requirements

### Requirement: v2.1 error codes registered
系统 SHALL 在 error_codes.py 中注册 v2.1 新增的 6 个错误码。

#### Scenario: QA error codes exist
- **WHEN** 查看 error_codes.py
- **THEN** 包含 QA_REQUIRES_API_PROVIDER 和 QA_CONTEXT_BUILD_FAILED

#### Scenario: Report error codes exist
- **WHEN** 查看 error_codes.py
- **THEN** 包含 REPORT_TYPE_NOT_SUPPORTED, REPORT_ENTITY_NOT_FOUND, REPORT_LLM_FILL_FAILED

#### Scenario: Delivery QC error code exists
- **WHEN** 查看 error_codes.py
- **THEN** 包含 DELIVERY_QC_NO_PACKAGE

### Requirement: v2.1 error codes help content
系统 SHALL 在 help_content.py 中为 v2.1 新增错误码提供帮助内容。

#### Scenario: QA_REQUIRES_API_PROVIDER help content
- **WHEN** 调用 get_help("QA_REQUIRES_API_PROVIDER")
- **THEN** 返回包含 reason、next_steps、doc_anchor 的字典，引导用户配置 api Provider

#### Scenario: QA_CONTEXT_BUILD_FAILED help content
- **WHEN** 调用 get_help("QA_CONTEXT_BUILD_FAILED")
- **THEN** 返回包含 reason、next_steps、doc_anchor 的字典，引导检查日志和数据库

#### Scenario: REPORT_TYPE_NOT_SUPPORTED help content
- **WHEN** 调用 get_help("REPORT_TYPE_NOT_SUPPORTED")
- **THEN** 返回包含 reason、next_steps、doc_anchor 的字典，列出支持的报告类型

#### Scenario: REPORT_ENTITY_NOT_FOUND help content
- **WHEN** 调用 get_help("REPORT_ENTITY_NOT_FOUND")
- **THEN** 返回包含 reason、next_steps、doc_anchor 的字典，引导确认 entity_id

#### Scenario: REPORT_LLM_FILL_FAILED help content
- **WHEN** 调用 get_help("REPORT_LLM_FILL_FAILED")
- **THEN** 返回包含 reason、next_steps、doc_anchor 的字典，说明降级为占位文本

#### Scenario: DELIVERY_QC_NO_PACKAGE help content
- **WHEN** 调用 get_help("DELIVERY_QC_NO_PACKAGE")
- **THEN** 返回包含 reason、next_steps、doc_anchor 的字典，引导确认 package_id
