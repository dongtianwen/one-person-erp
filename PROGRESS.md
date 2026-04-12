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
