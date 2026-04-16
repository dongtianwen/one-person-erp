## MODIFIED Requirements

### Requirement: ExternalAPIProvider scope constraint
ExternalAPIProvider SHALL 实现 enhance_suggestions、call_freeform 和 _call_llm_single_var 方法。

#### Scenario: Freeform method exists
- **WHEN** 审查 ExternalAPIProvider 类定义
- **THEN** 存在 call_freeform 方法，接受 messages 列表，返回模型原始文本

#### Scenario: Single var fill method exists
- **WHEN** 审查 ExternalAPIProvider 类定义
- **THEN** 存在 _call_llm_single_var 方法，接受 var_name 和 context，返回纯文本或 None

#### Scenario: Freeform call not on NullProvider
- **WHEN** 审查 NullProvider 类定义
- **THEN** 不存在 call_freeform 方法

#### Scenario: Freeform call not on OllamaProvider
- **WHEN** 审查 OllamaProvider 类定义
- **THEN** 不存在 call_freeform 方法

#### Scenario: Single var fill not on NullProvider
- **WHEN** 审查 NullProvider 类定义
- **THEN** 不存在 _call_llm_single_var 方法
