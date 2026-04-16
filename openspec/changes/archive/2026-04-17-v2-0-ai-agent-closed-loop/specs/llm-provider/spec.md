## ADDED Requirements

### Requirement: Three-tier LLM provider architecture
系统 SHALL 支持三档 LLM Provider：none（纯规则）、local（Ollama）、api（外部 API）。

#### Scenario: Provider selection from environment
- **WHEN** .env 中 LLM_PROVIDER=none
- **THEN** get_llm_provider() 返回 NullProvider 实例

#### Scenario: Local provider selected
- **WHEN** .env 中 LLM_PROVIDER=local
- **THEN** get_llm_provider() 返回 OllamaProvider 实例

#### Scenario: API provider selected
- **WHEN** .env 中 LLM_PROVIDER=api
- **THEN** get_llm_provider() 返回 ExternalAPIProvider 实例

#### Scenario: Unknown provider falls back to null
- **WHEN** .env 中 LLM_PROVIDER 为不在白名单中的值
- **THEN** get_llm_provider() 返回 NullProvider 实例，记录 WARNING 日志

### Requirement: Provider availability check
每个 Provider SHALL 实现 is_available() 方法检测自身是否可用。

#### Scenario: Null provider always unavailable
- **WHEN** NullProvider.is_available() 被调用
- **THEN** 返回 False

#### Scenario: Ollama provider health check
- **WHEN** OllamaProvider.is_available() 被调用
- **THEN** 发送 GET {LLM_LOCAL_BASE_URL}/api/tags，超时 OLLAMA_HEALTH_CHECK_TIMEOUT 返回 False，异常静默记录 DEBUG

#### Scenario: External API provider validation
- **WHEN** ExternalAPIProvider.is_available() 被调用
- **THEN** LLM_API_BASE 或 LLM_API_KEY 为空时返回 False

### Requirement: JSON parsing three-step strategy
系统 SHALL 实现三步 JSON 解析策略：直接解析 → 括号提取 → 返回 None。

#### Scenario: Direct JSON parse success
- **WHEN** LLM 返回纯 JSON 文本
- **THEN** _try_parse_llm_json 直接解析成功并返回结果

#### Scenario: Bracket extraction success
- **WHEN** LLM 返回包含 markdown fence 或前缀文字的 JSON 数组
- **THEN** _try_parse_llm_json 使用正则提取 [...] 内容并解析成功

#### Scenario: Invalid input returns None
- **WHEN** LLM 返回无法解析的文本
- **THEN** _try_parse_llm_json 返回 None

### Requirement: LLM enhancement with retry
Provider SHALL 在主 prompt 解析失败时使用简化 prompt 重试最多 1 次。

#### Scenario: Enhancement success on first attempt
- **WHEN** _call_llm 第一次解析成功
- **THEN** 返回增强后的 suggestions，不执行重试

#### Scenario: Enhancement success on retry
- **WHEN** _call_llm 第一次解析失败但重试成功
- **THEN** 返回增强后的 suggestions

#### Scenario: Enhancement fails after retry
- **WHEN** _call_llm 第一次和重试均解析失败
- **THEN** 返回原始 suggestions（source 不变），记录 WARNING(LLM_PARSE_FAILED)

#### Scenario: Timeout degradation
- **WHEN** LLM 调用超时（>30 秒）
- **THEN** 返回原始 suggestions，记录 WARNING(OLLAMA_UNAVAILABLE 或 API_PROVIDER_UNAVAILABLE)，不重试

### Requirement: OllamaProvider uses requests directly
OllamaProvider SHALL 使用 requests.post 调用 Ollama HTTP API，不使用 ollama SDK chat()。

#### Scenario: Uses requests not SDK
- **WHEN** OllamaProvider._call_llm 被调用
- **THEN** 调用 requests.post 而非 ollama.chat

### Requirement: ExternalAPIProvider scope constraint
ExternalAPIProvider SHALL 只实现 enhance_suggestions，不实现自由问答或报告生成方法。

#### Scenario: No freeform methods
- **WHEN** 审查 ExternalAPIProvider 类定义
- **THEN** 不存在 ask / query / report 等方法

### Requirement: NullProvider returns original suggestions
NullProvider SHALL 返回原始 suggestions 不做修改。

#### Scenario: Null provider passthrough
- **WHEN** NullProvider.enhance_suggestions 被调用
- **THEN** 返回原始 suggestions 列表，source 保持 'rule' 不变

### Requirement: Provider 30-second hard timeout
所有 LLM 调用 SHALL 使用 30 秒硬超时，超时即降级不重试。

#### Scenario: Timeout enforced
- **WHEN** LLM 调用耗时超过 30 秒
- **THEN** 抛出超时异常被捕获，降级为规则文本，不重试
