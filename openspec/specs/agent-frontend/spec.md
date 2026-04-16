## ADDED Requirements

### Requirement: QA assistant page
系统 SHALL 提供经营助手问答页面（路由 /assistant/qa）。

#### Scenario: API provider available shows QA interface
- **WHEN** LLM_PROVIDER=api 且 ExternalAPIProvider 可用
- **THEN** 显示完整问答界面：模型标签、对话气泡列表、输入框 + 发送按钮

#### Scenario: Non-api provider shows explanation
- **WHEN** LLM_PROVIDER != api 或 Provider 不可用
- **THEN** 显示说明页"此功能需接入外部模型，请在设置中配置 API Provider"，不显示输入框

#### Scenario: Chat bubbles display
- **WHEN** 用户发送问题并收到回答
- **THEN** 用户消息和助手回答交替显示为对话气泡

#### Scenario: History cleared on refresh
- **WHEN** 用户刷新或离开页面
- **THEN** 对话历史清空，不恢复

#### Scenario: Input disabled during request
- **WHEN** 请求发送中
- **THEN** 输入框禁用，显示 loading 状态

#### Scenario: Request failure display
- **WHEN** 请求失败
- **THEN** 显示"请求失败，请重试"，不追加气泡

### Requirement: Project report generation entry
项目详情页 SHALL 追加「生成项目复盘报告」按钮。

#### Scenario: Completed project shows report button
- **WHEN** 用户查看 status=completed 的项目详情
- **THEN** 显示「生成项目复盘报告」按钮

#### Scenario: Non-completed project hides button
- **WHEN** 用户查看 status != completed 的项目详情
- **THEN** 不显示报告生成按钮

#### Scenario: Report generation loading state
- **WHEN** 用户点击生成按钮
- **THEN** 按钮 loading，POST /api/v1/reports/generate（report_type=report_project）

#### Scenario: Report result display
- **WHEN** 报告生成完成
- **THEN** 弹窗展示报告内容（white-space: pre-wrap）+ 「历史报告」入口

### Requirement: Customer report generation entry
客户详情页 SHALL 追加「生成客户分析报告」按钮。

#### Scenario: Customer shows report button
- **WHEN** 用户查看客户详情
- **THEN** 显示「生成客户分析报告」按钮

#### Scenario: Customer report generation
- **WHEN** 用户点击生成按钮
- **THEN** POST /api/v1/reports/generate（report_type=report_customer），逻辑同项目报告

### Requirement: Report history dialog
系统 SHALL 提供报告历史弹窗。

#### Scenario: History list display
- **WHEN** 用户点击「历史报告」
- **THEN** 列表展示：生成时间、Provider、状态、版本号

#### Scenario: View historical report
- **WHEN** 用户点击某条历史报告
- **THEN** 展示该报告的 content

#### Scenario: Delete report
- **WHEN** 用户删除某条报告
- **THEN** 调用 DELETE /api/v1/reports/{id}

### Requirement: Delivery package QC entry
交付包详情页 SHALL 追加「运行质检分析」按钮。

#### Scenario: Any status package shows QC button
- **WHEN** 用户查看任何状态的交付包详情
- **THEN** 显示「运行质检分析」按钮

#### Scenario: QC analysis execution
- **WHEN** 用户点击质检按钮
- **THEN** POST /api/v1/agents/delivery-qc/run（body 带 package_id）

#### Scenario: QC result display
- **WHEN** 质检结果返回
- **THEN** 弹窗展示质检建议列表，支持就地确认

#### Scenario: QC all pass display
- **WHEN** 质检建议列表为空
- **THEN** 显示「✅ 质检通过，交付包完整」

### Requirement: Agent settings page QA section
Agent 设置页 SHALL 新增「自由问答」区域。

#### Scenario: Display API provider status
- **WHEN** 用户打开 Agent 设置页
- **THEN** 显示当前 api Provider 状态

#### Scenario: Unconfigured provider guidance
- **WHEN** api Provider 未配置
- **THEN** 展示配置指引（填写 LLM_API_BASE / LLM_API_KEY / LLM_API_MODEL）

#### Scenario: Key field write-only
- **WHEN** 显示 LLM_API_KEY 字段
- **THEN** key 字段只写不读，输入后存入 .env，不回显
