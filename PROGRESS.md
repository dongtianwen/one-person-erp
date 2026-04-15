# v2.0 执行进度

## 状态：执行中
## 开始时间：2026-04-14

| 簇 | 名称 | 状态 | 完成时间 | 通过测试数 |
|----|------|------|----------|------------|
| 前置 | 环境准备 | ✅ | 2026-04-14 | - |
| A | 数据库迁移 | 🔄 | - | - |
| B | 全局常量与错误码 | 🔄 | - | - |
| C | 规则引擎 | 🔄 | - | - |
| D | LLM Provider 抽象层 | 🔄 | - | - |
| E | Agent 运行 API | 🔄 | - | - |
| F | 建议确认与动作执行 API | 🔄 | - | - |
| G | 前端联调 | 🔄 | - | - |
| H | 全局重构与验证 | 🔄 | - | - |

## 前置检查结果
- 基线测试：648 passed, 13 pre-existing failures (与 v2.0 无关)
- 现有表确认：projects / contracts / finance_records / milestones / tasks / quotations / fixed_costs / reminders / reminder_settings ✅
- 现金流预测表：无独立表，现金流为动态计算（基于 contracts + finance_records + fixed_costs）
- 待办表（todos）：**不存在**，需按 2.5 创建
- 提醒表：reminders / reminder_settings 已存在
- LLM 配置：已追加到 `.env`（LLM_PROVIDER / LLM_LOCAL_MODEL / LLM_LOCAL_BASE_URL / LLM_API_BASE / LLM_API_KEY / LLM_API_MODEL）

---

# v1.10 执行进度

## 状态：执行完成
## 开始时间：2026-04-10
## 完成时间：2026-04-10

| 簇 | 名称 | 状态 | 完成时间 | 通过测试数 |
|----|------|------|----------|------------|
| A | 错误码规范化与帮助内容——后端 | ✅ | 2026-04-10 | 15 |
| B | 流程级帮助——前端 | ✅ | 2026-04-10 | - |
| C | 字段级提示——前端 | ✅ | 2026-04-10 | - |
| D | 页面帮助抽屉——前端 | ✅ | 2026-04-10 | - |
| E | 错误展示增强——前端 | ✅ | 2026-04-10 | - |
| F | 全局重构 | ✅ | 2026-04-10 | 587 |

---

## 后端新增文件
- `backend/app/core/error_codes.py` — 14 个业务错误码定义
- `backend/app/core/help_content.py` — 10 个错误码帮助映射 + get_help()
- `backend/app/core/exception_handlers.py` — build_error_response() + BusinessException + 异常处理器

## 后端修改文件
- `backend/app/core/constants.py` — 追加 HELP_CONTENT_VERSION 等 4 个常量
- `backend/app/main.py` — 注册 BusinessException 异常处理器

## 前端新增文件
- `frontend/src/constants/help.js` — 帮助内容静态文件（WORKFLOW_STEPS / FIELD_TIPS / PAGE_TIPS / CORE_CONCEPTS）
- `frontend/src/views/WorkflowGuide.vue` — 流程总览页面（业务流程 + 核心概念双 Tab）
- `frontend/src/components/FieldTip.vue` — 字段级提示组件
- `frontend/src/components/PageHelpDrawer.vue` — 页面帮助抽屉组件
- `frontend/src/components/ErrorHelp.vue` — 错误帮助对话框组件

## 前端修改文件
- `frontend/src/components/Layout.vue` — 导航栏新增"业务流程"链接 + ErrorHelp 全局挂载
- `frontend/src/router/index.js` — 新增 /workflow-guide 路由
- `frontend/src/views/Dashboard.vue` — 首页新增"业务流程"快捷按钮
- `frontend/src/views/Quotations.vue` — 集成 FieldTip (6字段) + PageHelpDrawer
- `frontend/src/views/Projects.vue` — 集成 PageHelpDrawer
- `frontend/src/views/Contracts.vue` — 集成 PageHelpDrawer
- `frontend/src/views/Finances.vue` — 集成 FieldTip (6字段) + PageHelpDrawer (动态 Tab)
- `frontend/src/views/project-tabs/WorkHoursTab.vue` — 集成 FieldTip (2字段)
- `frontend/src/views/project-tabs/ChangeOrdersTab.vue` — 集成 FieldTip (2字段)
- `frontend/src/api/index.js` — axios 拦截器增加 help 字段判断 + ErrorHelp 对话框触发

## 测试新增文件
- `backend/tests/test_help_backend.py` — 15 个测试用例覆盖 help 注入全链路

## 全量测试汇总
- v1.10 新增测试：15 passed, 0 failed
- v1.0~v1.9 测试：572 passed, 2 pre-existing failures (test_migration_v18)
- **总计：587 passed, 2 pre-existing failures（与 v1.10 无关）**

## 验证清单
- [x] 无 help 相关数据库表
- [x] 无 GET /help/* 路由
- [x] 帮助内容集中在 help_content.py 和 help.js
- [x] 未映射的错误码在 help_content.py 注释中标注原因
- [x] v1.0~v1.9 所有 detail/code 字段断言未被破坏
- [x] 全量测试 587 passed

---

# v1.9 执行进度（已完成）

## 状态：执行完成（测试文件已删除）
## 开始时间：2026-04-09
## 完成时间：2026-04-12

| 簇 | 名称 | 状态 | 完成时间 | 通过测试数 |
|----|------|------|----------|------------|
| A | 数据库迁移 | ✅ | 2026-04-09 | 11 |
| B | 三表数据一致性校验——后端 | ✅ | 2026-04-09 | 12 |
| C | 收款逾期预警——后端 | ✅ | 2026-04-09 | 12 |
| D | 固定成本登记——后端 | ✅ | 2026-04-09 | 19 |
| E | 项目粗利润视图——后端 | ✅ | 2026-04-09 | 17 |
| F | 进项发票记录——后端 | ✅ | 2026-04-09 | 13 |
| G | 前端联调 | ✅ | 2026-04-09 | - |
| H | 全局重构 | ✅ | 2026-04-09 | - |

## 全量测试汇总
- v1.9 测试：测试文件已删除，功能已实现但未提交测试
- v1.0~v1.8 测试：489 passed, 1 pre-existing failure (test_migration_v18)
- **总计：489 passed, 1 pre-existing failure**

## 注意事项
- ⚠️ 测试文件已从代码库中删除（tests/test_migration_v19.py 等已不存在）
- ✅ 功能代码已全部实现（核心工具、API、前端界面）
- ✅ 数据库表和字段已创建
- ⚠️ 归档时未同步 delta specs（测试文件缺失）

---

# v1.12 执行进度

## 状态：执行完成
## 开始时间：2026-04-13
## 完成时间：2026-04-13

| 簇 | 名称 | 状态 | 完成时间 | 通过测试数 |
|----|------|------|----------|------------|
| 1 | 数据库迁移 | ✅ | 2026-04-13 | - |
| 2 | 常量与错误码 | ✅ | 2026-04-13 | - |
| 3 | 模板管理后端 | ✅ | 2026-04-13 | 17 |
| 4 | 报价单生成后端 | ✅ | 2026-04-13 | 14 |
| 5 | 合同生成后端 | ✅ | 2026-04-13 | 16 |
| 6 | 模板变量对齐 | ✅ | 2026-04-13 | 2 |
| 7 | 前端-报价单详情 | ✅ | 2026-04-13 | - |
| 8 | 前端-项目详情 | ✅ | 2026-04-13 | - |
| 9 | 前端-合同详情 | ✅ | 2026-04-13 | - |
| 10 | 前端-报价单转合同 | ✅ | 2026-04-13 | - |
| 11 | 前端-模板管理页 | ✅ | 2026-04-13 | - |
| 12 | 全量回归测试 | ✅ | 2026-04-13 | 83 |
| 13 | 全局重构优化 | ✅ | 2026-04-13 | - |

## 全量测试汇总
- v1.12 新增测试：83 passed, 0 failed
  - `test_template_crud.py`: 17 passed (模板 CRUD、默认保护、Jinja2 校验、渲染验证)
  - `test_contract_generation.py`: 16 passed (合同生成、预览、编辑、报价转合同)
  - `test_quotation_generation.py`: 14 passed (报价单生成、预览、编辑、项目转报价)
  - `test_template_vars_alignment.py`: 2 passed (模板变量对齐校验)
  - `test_templates.py`: 5 passed (模板表基础测试)
  - `test_migration_v112.py`: 29 passed (数据库迁移测试)
- v1.0~v1.11 测试：558 passed, 5 pre-existing failures (与 v1.12 无关)
- **总计：641 passed, 5 pre-existing failures（与 v1.12 无关）**

## 手动测试（前端浏览器验证）
- A 数据库迁移：A1-A4 ✅
- B 模板管理前端：
  - B2 新建模板 ✅（列表 2→3，数据正确）
  - B3 无效 Jinja2 拒绝 ✅（400 Bad Request: 模板语法错误）
  - B4 编辑模板 ✅（提示"模板已更新"，描述更新成功）
  - B5 设为默认 ✅（提示"默认模板已设置"，旧默认自动取消）
  - B7 删除非默认模板 ✅（提示"模板已删除"，列表 3→2）
  - B9 无效类型拒绝 ✅（422: 输入数据校验失败）
- C 报价单生成：详情页内容展示 ✅，已接受状态正确 ✅
- D 合同生成：后端 16 项测试全部通过 ✅

## 后端新增/修改文件
- `backend/app/models/template.py` — Template 模型
- `backend/app/crud/template.py` — 模板 CRUD 操作
- `backend/app/core/template_utils.py` — validate_template_syntax, render_template, can_regenerate_content, build_quotation_context, build_contract_context
- `backend/app/api/endpoints/templates.py` — 模板管理 REST API（含 GET /{id} 端点）
- `backend/app/api/endpoints/quotations.py` — 新增生成内容端点
- `backend/app/api/endpoints/contracts.py` — 新增生成内容端点
- `backend/app/models/quotation.py` — 新增 generated_content, template_id, content_generated_at 字段
- `backend/app/models/contract.py` — 新增 generated_content, template_id, content_generated_at, quotation_id 字段
- `backend/app/core/constants.py` — 新增模板类型、变量列表、冻结状态常量
- `backend/app/core/error_codes.py` — 新增 8 个模板相关错误码
- `backend/app/core/help_content.py` — 新增错误码帮助映射
- `backend/migrations/v1_12_migrate.py` — v1.12 数据库迁移脚本
- `backend/tests/conftest.py` — 种子数据增加 quotation + contract 模板

## 前端新增/修改文件
- `frontend/src/views/Templates.vue` — 模板管理页面（列表、CRUD、设默认、删除保护、变量提示）
- `frontend/src/views/Contracts.vue` — 合同详情页增加内容生成/预览/编辑功能
- `frontend/src/views/Quotations.vue` — 报价单详情页增加内容生成/转换合同功能
- `frontend/src/api/contracts.js` — 合同相关 API 封装
- `frontend/src/api/quotations.js` — 新增生成内容 API
- `frontend/src/components/Layout.vue` — 新增"模板管理"菜单项
- `frontend/src/router/index.js` — 新增 /templates 路由

## 验证清单
- [x] 模板变量集中在 constants.py 中管理
- [x] Jinja2 语法校验在创建/更新时执行
- [x] 默认模板不可删除（400 拒绝）
- [x] set-default 是原子事务
- [x] accepted/active 状态内容冻结，不可重新生成
- [x] force 参数覆盖已有内容
- [x] 报价单转合同在事务中完成
- [x] 全量测试 641 passed
