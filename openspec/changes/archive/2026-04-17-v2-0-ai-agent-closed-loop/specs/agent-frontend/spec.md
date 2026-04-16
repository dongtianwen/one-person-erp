## ADDED Requirements

### Requirement: Business decision page
系统 SHALL 提供经营决策页面（路由 /agents/business-decision）。

#### Scenario: Run business decision analysis
- **WHEN** 用户点击「运行经营分析」按钮
- **THEN** 触发 POST /api/v1/agents/business-decision/run，展示返回的建议列表

#### Scenario: AI enhancement toggle
- **WHEN** 用户在运行分析时切换「启用 AI 增强」开关
- **THEN** use_llm 参数随请求发送，默认开（true）

### Requirement: Provider status display
经营决策页 SHALL 根据 agent_runs 最近一条记录的 llm_provider 显示当前模式标签。

#### Scenario: Rule mode display
- **WHEN** 最近运行记录 llm_provider=none 或 local/api 不可用
- **THEN** 显示「规则模式」，不可用时提示「本地模型未启动，已使用规则模式」

#### Scenario: Local AI mode display
- **WHEN** 最近运行记录 llm_provider=local 且 llm_enhanced=1
- **THEN** 显示「本地 AI 增强」

#### Scenario: Cloud AI mode display
- **WHEN** 最近运行记录 llm_provider=api 且 llm_enhanced=1
- **THEN** 显示「云端 AI 增强」

### Requirement: Suggestion list display
建议列表 SHALL 按优先级分组展示（高风险 / 中等风险 / 低优先级）。

#### Scenario: Grouped by priority
- **WHEN** 存在多条不同优先级的建议
- **THEN** 按 high / medium / low 分组显示，high 组在最前

#### Scenario: Suggestion card content
- **WHEN** 展示单条建议
- **THEN** 显示类型标签、优先级标签（high=红色）、标题、内容、来源标记（规则/本地AI/云端AI）

#### Scenario: Empty state display
- **WHEN** 无建议返回
- **THEN** 显示「当前无风险提示，经营状态良好」

### Requirement: Suggestion confirmation dialog
用户确认建议时 SHALL 展示确认弹窗，包含 reason_code、free_text_reason、inject_to_next_run、next_review_at 字段。

#### Scenario: Confirmation dialog fields
- **WHEN** 用户点击「接受」「拒绝」或「修改后接受」
- **THEN** 弹窗包含：reason_code 下拉、free_text_reason 文本域、inject_to_next_run 开关、next_review_at 日期选择

#### Scenario: inject_to_next_run default on
- **WHEN** 确认弹窗打开
- **THEN** inject_to_next_run 开关默认为开，标签「记入下次分析参考」

### Requirement: Project page AI analysis entry
项目详情页 SHALL 追加「项目智能分析」入口，仅 status=active 时显示。

#### Scenario: Active project shows analysis button
- **WHEN** 用户查看 status=active 的项目详情
- **THEN** 显示「项目智能分析」按钮

#### Scenario: Non-active project hides button
- **WHEN** 用户查看 status != active 的项目详情
- **THEN** 不显示「项目智能分析」按钮

#### Scenario: Project analysis result
- **WHEN** 用户点击项目智能分析按钮
- **THEN** 触发 POST /api/v1/agents/project-management/run（带 project_id），弹窗展示结果支持就地确认

### Requirement: Agent logs page
系统 SHALL 提供 Agent 运行日志页面（路由 /agents/logs）。

#### Scenario: Logs table columns
- **WHEN** 用户打开 Agent 运行日志页
- **THEN** 列表包含：运行时间、Agent 类型、状态、Provider 模式、建议数、LLM 增强状态

#### Scenario: Log detail expansion
- **WHEN** 用户展开某条运行记录
- **THEN** 展示建议详情、人工确认结果、inject_to_next_run 值、动作执行状态

### Requirement: Agent settings page
系统 SHALL 提供 Agent 设置页面（路由 /settings/agent）。

#### Scenario: Display current provider config
- **WHEN** 用户打开 Agent 设置页
- **THEN** 显示当前 LLM_PROVIDER 配置值（只读）

#### Scenario: Ollama connection status
- **WHEN** LLM_PROVIDER=local
- **THEN** 实时检测并展示 Ollama 连接状态

#### Scenario: API endpoint display
- **WHEN** LLM_PROVIDER=api
- **THEN** 展示 LLM_API_BASE（隐藏 key）

### Requirement: Navigation integration
Agent 相关页面 SHALL 集成到主导航中。

#### Scenario: Navigation entries
- **WHEN** 用户查看主导航
- **THEN** 包含「经营决策」「Agent 日志」入口
