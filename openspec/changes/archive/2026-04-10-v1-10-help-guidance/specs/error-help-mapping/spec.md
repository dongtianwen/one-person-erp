## ADDED Requirements

### Requirement: Error code registry
系统 SHALL 在 `backend/core/error_codes.py` 中集中定义所有业务错误码，包含错误码字符串和中文名称。

#### Scenario: Error codes cover all modules
- **WHEN** 查看 error_codes.py
- **THEN** 包含报价模块（QUOTE_STATUS_INVALID_TRANSITION, QUOTE_ALREADY_CONVERTED, QUOTE_NOT_ACCEPTED）、变更冻结（REQUIREMENT_FROZEN, CHANGE_ORDER_INVALID_TRANSITION）、里程碑（MILESTONE_NOT_COMPLETED, PAYMENT_STATUS_INVALID_TRANSITION）、项目关闭（PROJECT_CLOSE_CONDITIONS_NOT_MET, PROJECT_ALREADY_CLOSED）、发票（INVOICE_AMOUNT_EXCEEDS_CONTRACT, INVOICE_STATUS_INVALID_TRANSITION, INVOICE_CANNOT_DELETE）、通用（NOT_FOUND, VALIDATION_ERROR, DUPLICATE_ENTRY, FOREIGN_KEY_VIOLATION）共 14 个错误码

### Requirement: Help content mapping for error codes
系统 SHALL 在 `backend/core/help_content.py` 中为需要引导的错误码提供 reason、next_steps、doc_anchor 帮助内容。

#### Scenario: 10 error codes have help content
- **WHEN** 查看 help_content.py 的 HELP_CONTENT 字典
- **THEN** 包含 REQUIREMENT_FROZEN, CHANGE_ORDER_INVALID_TRANSITION, MILESTONE_NOT_COMPLETED, PROJECT_CLOSE_CONDITIONS_NOT_MET, PROJECT_ALREADY_CLOSED, INVOICE_AMOUNT_EXCEEDS_CONTRACT, INVOICE_STATUS_INVALID_TRANSITION, INVOICE_CANNOT_DELETE, QUOTE_ALREADY_CONVERTED, QUOTE_NOT_ACCEPTED 共 10 个错误码的完整帮助映射

#### Scenario: Help content has required structure
- **WHEN** 查看任一错误码的帮助内容
- **THEN** 包含 reason（字符串）、next_steps（数组，最多 5 条）、doc_anchor（可选字符串）

### Requirement: Help field injection in error responses
异常处理器 SHALL 在错误响应中追加可选的 help 字段，不修改 detail 和 code。

#### Scenario: Error code with help mapping
- **WHEN** 接口返回错误码 REQUIREMENT_FROZEN
- **THEN** 响应包含 `{"detail": "...", "code": "REQUIREMENT_FROZEN", "help": {"reason": "...", "next_steps": [...], "doc_anchor": "..."}}`

#### Scenario: Error code without help mapping
- **WHEN** 接口返回错误码 NOT_FOUND
- **THEN** 响应仅包含 `{"detail": "...", "code": "NOT_FOUND"}`，不含 help 字段

#### Scenario: 5xx errors exclude help
- **WHEN** 接口返回 HTTP 500 错误
- **THEN** 响应不包含 help 字段

#### Scenario: Detail and code not modified
- **WHEN** 异常处理器追加 help 字段
- **THEN** detail 和 code 的内容与追加前完全一致

### Requirement: get_help function
系统 SHALL 提供 `get_help(error_code)` 函数，返回错误码对应帮助内容，不存在时返回 None。

#### Scenario: Known error code
- **WHEN** 调用 get_help("REQUIREMENT_FROZEN")
- **THEN** 返回包含 reason、next_steps（最多 HELP_MAX_NEXT_STEPS 条）、doc_anchor 的字典

#### Scenario: Unknown error code
- **WHEN** 调用 get_help("UNKNOWN_CODE")
- **THEN** 返回 None

#### Scenario: Next steps capped at max
- **WHEN** 帮助内容的 next_steps 超过 HELP_MAX_NEXT_STEPS 条
- **THEN** 返回的 next_steps 截断为 HELP_MAX_NEXT_STEPS 条
