## ADDED Requirements

### Requirement: ErrorHelp component
系统 SHALL 提供 ErrorHelp.vue 对话框组件，展示错误原因和有序步骤列表。

#### Scenario: Display help content
- **WHEN** ErrorHelp 对话框接收到 help 数据 `{"reason": "...", "next_steps": ["步骤1", "步骤2"]}`
- **THEN** 对话框标题为"操作失败"，显示 reason 文本和有序编号的 next_steps 列表

#### Scenario: Close dialog
- **WHEN** 用户点击关闭按钮
- **THEN** 对话框关闭

### Requirement: Axios interceptor help handling
现有 axios 响应拦截器 SHALL 根据 help 字段决定错误展示方式，全局统一处理。

#### Scenario: 4xx with help field
- **WHEN** 接口返回 HTTP 4xx 且响应包含 help 字段
- **THEN** 弹出 ErrorHelp 对话框，展示 help.reason 和 help.next_steps

#### Scenario: 4xx without help field
- **WHEN** 接口返回 HTTP 4xx 且响应不包含 help 字段
- **THEN** 保持现有行为，显示 ElMessage.error(detail)

#### Scenario: 5xx error
- **WHEN** 接口返回 HTTP 5xx
- **THEN** 显示 ElMessage.error("服务器错误，请稍后重试")，不展示 help

#### Scenario: Network error
- **WHEN** 请求因网络问题失败
- **THEN** 显示 ElMessage.error("网络连接失败，请检查网络")

### Requirement: Five key error scenarios
以下 5 个错误场景 SHALL 在前端正确触发 ErrorHelp 对话框。

#### Scenario: REQUIREMENT_FROZEN
- **WHEN** 接口返回 REQUIREMENT_FROZEN 错误
- **THEN** 弹出 ErrorHelp 对话框显示变更单引导步骤

#### Scenario: MILESTONE_NOT_COMPLETED
- **WHEN** 接口返回 MILESTONE_NOT_COMPLETED 错误
- **THEN** 弹出 ErrorHelp 对话框显示里程碑完成步骤

#### Scenario: PROJECT_CLOSE_CONDITIONS_NOT_MET
- **WHEN** 接口返回 PROJECT_CLOSE_CONDITIONS_NOT_MET 错误
- **THEN** 弹出 ErrorHelp 对话框显示关闭条件核查步骤

#### Scenario: INVOICE_AMOUNT_EXCEEDS_CONTRACT
- **WHEN** 接口返回 INVOICE_AMOUNT_EXCEEDS_CONTRACT 错误
- **THEN** 弹出 ErrorHelp 对话框显示已开票金额查看入口

#### Scenario: QUOTE_ALREADY_CONVERTED
- **WHEN** 接口返回 QUOTE_ALREADY_CONVERTED 错误
- **THEN** 弹出 ErrorHelp 对话框显示已关联合同入口
