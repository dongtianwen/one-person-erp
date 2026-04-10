## Why

v1.0~v1.9 积累了完整的业务功能（报价、合同、项目、发票、财务、风控），但用户在操作出错时只看到一句 `detail` 提示，缺乏原因解释和下一步操作引导。新用户不理解业务流程顺序，关键字段含义不明确。需要在不打扰正常操作的前提下，按场景提供操作辅助：错误解释与建议、流程总览、字段提示、页面帮助。

## What Changes

- **后端错误码规范化**：补齐错误响应 `code` 字段，建立 `error_codes.py` 错误码注册表
- **后端帮助内容映射**：新建 `help_content.py`，为 10 个业务错误码提供 reason + next_steps + doc_anchor
- **后端异常处理器增强**：现有异常处理器追加 `help` 字段（只追加，不修改 detail/code）
- **前端帮助内容静态文件**：新建 `help.js`，集中存储 WORKFLOW_STEPS / FIELD_TIPS / PAGE_TIPS / CORE_CONCEPTS
- **前端流程总览组件**：水平步骤条展示业务流程（报价→合同→项目→发票→收款→风控）
- **前端字段级提示组件**：`FieldTip.vue` 为关键字段提供 hover tooltip
- **前端页面帮助抽屉组件**：`PageHelpDrawer.vue` 右侧滑出页面说明
- **前端错误展示增强**：`ErrorHelp.vue` 对话框解析 help 字段，展示原因和步骤
- **前端核心概念 Tab**：流程图页面新增核心概念卡片列表

## Capabilities

### New Capabilities
- `error-help-mapping`: 后端错误码注册表 + 帮助内容映射 + 异常处理器追加 help 字段
- `field-tooltip`: 前端字段级提示组件（FieldTip.vue），内容来自静态 help.js
- `page-help-drawer`: 前端页面帮助抽屉组件（PageHelpDrawer.vue），内容来自静态 help.js
- `error-help-dialog`: 前端错误展示增强（ErrorHelp.vue + axios 拦截器），解析 help 字段展示对话框
- `workflow-overview`: 前端业务流程总览 + 核心概念 Tab，内容来自静态 help.js

### Modified Capabilities
- `invoice-management`: 错误响应追加 help 字段（INVOICE_AMOUNT_EXCEEDS_CONTRACT 等）
- `quotation`: 错误响应追加 help 字段（QUOTE_ALREADY_CONVERTED、QUOTE_NOT_ACCEPTED）
- `project-management`: 错误响应追加 help 字段（PROJECT_CLOSE_CONDITIONS_NOT_MET 等）
- `milestone-payment`: 错误响应追加 help 字段（MILESTONE_NOT_COMPLETED）
- `change-order-management`: 错误响应追加 help 字段（CHANGE_ORDER_INVALID_TRANSITION）
- `change-freeze`: 错误响应追加 help 字段（REQUIREMENT_FROZEN）
- `dashboard`: 新增流程入口卡片 + 导航栏新增"业务流程"链接

## Impact

- **后端文件**：新建 `core/error_codes.py`、`core/help_content.py`；修改 `core/exception_handlers.py`、`core/constants.py`
- **前端文件**：新建 `constants/help.js`、`components/FieldTip.vue`、`components/PageHelpDrawer.vue`、`components/ErrorHelp.vue`；修改 axios 拦截器、导航栏、Dashboard、各表单页面
- **无数据库变更**：帮助内容为纯静态文件，不建表、不建查询接口
- **无新 API 端点**：前端直接读 help.js，不经过后端接口
- **向后兼容**：help 字段为可选追加，现有 detail/code 字段不变，不影响已有断言
