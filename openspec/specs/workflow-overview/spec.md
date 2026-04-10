## ADDED Requirements

### Requirement: Workflow steps data source
前端 SHALL 在 `frontend/src/constants/help.js` 中定义 WORKFLOW_STEPS 常量，包含 6 个业务流程步骤。

#### Scenario: Six workflow steps defined
- **WHEN** 查看 WORKFLOW_STEPS 常量
- **THEN** 包含 quote、contract、project、invoice、finance、risk 共 6 个步骤，每步包含 id、label、version、description、key_actions、route、triggers_next

### Requirement: Core concepts data source
前端 SHALL 在 `frontend/src/constants/help.js` 中定义 CORE_CONCEPTS 常量，包含 8 个核心业务概念。

#### Scenario: Eight concepts defined
- **WHEN** 查看 CORE_CONCEPTS 常量
- **THEN** 包含客户、合同、项目、里程碑、需求、收款记录、销项发票、变更单共 8 个概念，每个包含 term、definition、related，可选 key_rule

### Requirement: Workflow overview page
系统 SHALL 提供业务流程总览页面，含两个 Tab：业务流程和核心概念。

#### Scenario: Navigate to workflow page
- **WHEN** 用户点击顶部导航栏"业务流程"链接或首页流程入口卡片
- **THEN** 显示业务流程总览页面

#### Scenario: Workflow steps display
- **WHEN** 用户查看"业务流程"Tab
- **THEN** 桌面端显示水平步骤条，移动端显示垂直列表，每步可展开/收起显示描述、关键操作、下一步触发条件、跳转链接

#### Scenario: Current page highlight
- **WHEN** 当前页面路由匹配某个流程步骤的 route
- **THEN** 该步骤自动高亮

#### Scenario: Core concepts display
- **WHEN** 用户查看"核心概念"Tab
- **THEN** 显示 8 个概念卡片，每张包含术语名称（加粗）、定义说明、关键规则（黄色标注）、相关概念标签

#### Scenario: Pure static no API calls
- **WHEN** 加载流程总览页面
- **THEN** 无任何接口调用，内容全部来自 help.js 静态导入
