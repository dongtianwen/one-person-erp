## Why

已完成的 v1.0 ~ v1.11 版本缺乏结构化模板和文本拼接引擎，无法为报价单和合同生成内容。本版本通过引入 Jinja2 模板系统，实现标准化、可配置的文档生成能力，减少手工录入错误，提升业务效率。

## What Changes

### Database Changes
- **NEW**: `templates` 表 - 存储报价单和合同的 Jinja2 模板
- **MODIFY**: `quotations` 表 - 新增 `generated_content`/`template_id`/`content_generated_at` 字段
- **MODIFY**: `contracts` 表 - 新增 `generated_content`/`template_id`/`content_generated_at` 字段

### Backend Changes
- **NEW**: 模板管理 API (`/api/v1/templates`) - CRUD + 设为默认
- **NEW**: 报价单生成 API (`POST /api/v1/quotations/{id}/generate`, `GET /api/v1/quotations/{id}/preview`, `PUT /api/v1/quotations/{id}/generated-content`, `POST /api/v1/projects/{id}/generate-quotation`)
- **NEW**: 合同生成 API (`POST /api/v1/contracts/{id}/generate`, `GET /api/v1/contracts/{id}/preview`, `PUT /api/v1/contracts/{id}/generated-content`, `POST /api/v1/quotations/{id}/generate-contract`)
- **NEW**: 核心工具函数 - `build_quotation_context`, `build_contract_context`, `render_template`, `validate_template_syntax`, `can_regenerate_content`
- **NEW**: 常量定义 - `TEMPLATE_TYPE_*`, `QUOTATION_REQUIRED_VARS`, `CONTRACT_REQUIRED_VARS` 等

### Frontend Changes
- **NEW**: 报价单详情页 - 生成内容、手工编辑、预览功能
- **NEW**: 项目详情页 - 一键生成报价按钮（去重检查）
- **NEW**: 报价单详情页（accepted） - 转合同并生成草稿按钮
- **NEW**: 合同详情页 - 生成/编辑/预览功能
- **NEW**: 模板管理页 - 列表、新建/编辑、设为默认、删除
- **NEW**: 变量提示 - 必填/可选变量分组显示

### Error Codes
- **NEW**: `TEMPLATE_NOT_FOUND`, `TEMPLATE_RENDER_FAILED`, `TEMPLATE_MISSING_REQUIRED_VARS`
- **NEW**: `CONTENT_FROZEN`, `CONTENT_ALREADY_EXISTS`
- **NEW**: `QUOTE_NO_QUOTATION_ID`, `TEMPLATE_IS_DEFAULT`, `DRAFT_ALREADY_EXISTS`

## Capabilities

### New Capabilities
- **template-management**: 模板管理能力，支持创建、编辑、删除、设为默认的报价单和合同模板
- **quotation-generation**: 报价单内容生成能力，支持从项目一键生成、预览、手工编辑
- **contract-generation**: 合同内容生成能力，支持从报价单转合同、生成、预览、手工编辑

### Modified Capabilities
无（现有能力的实现细节会修改，但需求规格不变）

## Impact

### Affected Code
- **新增文件**:
  - `backend/core/template_utils.py` - 模板渲染和上下文构建工具
  - `backend/core/constants.py` - 模板相关常量
  - `backend/core/help_content.py` - 新增错误码帮助内容
  - `tests/test_migration_v112.py` - 数据库迁移测试
  - `tests/test_templates.py` - 模板管理测试
  - `tests/test_quotation_generation.py` - 报价单生成测试
  - `tests/test_contract_generation.py` - 合同生成测试
  - `tests/test_template_vars_alignment.py` - 模板变量对齐测试

- **修改文件**:
  - `backend/migrations/` - 数据库迁移脚本（templates表、新增字段）
  - `backend/api/routes/` - 模板、报价单、合同相关路由
  - `backend/core/error_codes.py` - 新增错误码
  - `frontend/` - 前端页面和组件
  - `tests/` - 全量测试更新

### APIs
- **NEW**: `GET /api/v1/templates`, `POST /api/v1/templates`, `PUT /api/v1/templates/{id}`, `DELETE /api/v1/templates/{id}`, `PATCH /api/v1/templates/set-default`, `GET /api/v1/templates/default/{type}`
- **NEW**: `POST /api/v1/quotations/{id}/generate?force=false`, `GET /api/v1/quotations/{id}/preview`, `PUT /api/v1/quotations/{id}/generated-content`, `POST /api/v1/projects/{id}/generate-quotation`
- **NEW**: `POST /api/v1/contracts/{id}/generate?force=false`, `GET /api/v1/contracts/{id}/preview`, `PUT /api/v1/contracts/{id}/generated-content`, `POST /api/v1/quotations/{id}/generate-contract`

### Dependencies
- **NEW**: `jinja2>=3.1.0` - 模板引擎
- **NEW**: 数据库表 - `templates`, 修改 `quotations`, `contracts`

### Breaking Changes
**BREAKING**: `quotations` 和 `contracts` 表新增必填字段（`template_id`），数据库迁移需处理现有记录的兼容性

## Notes

- 不做 AI 自由生成、自动法律审查、自动电子签、富文本编辑器、模板市场
- 内容冻结规则：`quotations.status = accepted` 和 `contracts.status = active` 时内容不可重新生成或手工编辑
- 默认模板不可删除，非默认模板删除不影响已生成的内容快照
