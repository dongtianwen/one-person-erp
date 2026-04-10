## 1. 后端：错误码注册与帮助映射

- [x] 1.1 新建 `backend/core/error_codes.py`，定义 14 个业务错误码（报价/变更冻结/里程碑/项目关闭/发票/通用）
- [x] 1.2 追加 `backend/core/constants.py`：HELP_CONTENT_VERSION、HELP_MAX_NEXT_STEPS、HELP_FIELD_TIP_MAX_LENGTH、HELP_PAGE_TIP_MAX_ITEMS
- [x] 1.3 新建 `backend/core/help_content.py`，定义 HELP_CONTENT 字典（10 个错误码帮助映射）和 `get_help()` 函数
- [x] 1.4 修改现有异常处理器（`exception_handlers.py`），追加 `build_error_response()` 函数注入 help 字段
- [x] 1.5 编写 `tests/test_help_backend.py`：覆盖 help 注入、无 help 降级、next_steps 截断、detail/code 不变、5xx 排除等 11 个测试用例
- [x] 1.6 运行全量测试 `pytest tests/ -v`，确保 0 FAILED

## 2. 前端：帮助内容静态文件

- [x] 2.1 新建 `frontend/src/constants/help.js`，定义 WORKFLOW_STEPS（6 步流程）
- [x] 2.2 追加 FIELD_TIPS 到 help.js（7 个模块，覆盖所有必须字段）
- [x] 2.3 追加 PAGE_TIPS 到 help.js（7 个页面帮助）
- [x] 2.4 追加 CORE_CONCEPTS 到 help.js（8 个核心概念）

## 3. 前端：流程总览与核心概念

- [x] 3.1 新建流程总览页面组件，实现 Tab 切换（业务流程 / 核心概念）
- [x] 3.2 实现"业务流程"Tab：水平步骤条（桌面）/ 垂直列表（移动端），步骤展开/收起，当前路由高亮
- [x] 3.3 实现"核心概念"Tab：8 个概念卡片列表，术语加粗、关键规则黄色标注、相关概念标签
- [x] 3.4 顶部导航栏新增"业务流程"链接
- [x] 3.5 首页看板新增流程入口卡片，点击跳转流程总览页面
- [x] 3.6 验证纯静态展示，无任何 API 调用

## 4. 前端：字段级提示组件

- [x] 4.1 新建 `frontend/src/components/FieldTip.vue`，从 FIELD_TIPS 读取内容，渲染 ❓ 图标 + hover tooltip
- [x] 4.2 实现移动端降级：截取前 15 字追加到 placeholder
- [x] 4.3 在报价单表单集成 FieldTip（estimate_days / daily_rate / risk_buffer_rate / valid_until / discount_amount / tax_rate）
- [x] 4.4 在发票表单集成 FieldTip（invoice_date / amount_excluding_tax / tax_rate / received_by）
- [x] 4.5 在里程碑表单集成 FieldTip（payment_amount / payment_due_date / payment_status）
- [x] 4.6 在变更单表单集成 FieldTip（extra_days / extra_amount / status）
- [x] 4.7 在工时记录表单集成 FieldTip（hours_spent / deviation_note）
- [x] 4.8 在固定成本表单集成 FieldTip（period / effective_date / end_date）
- [x] 4.9 验证：无对应内容时静默不渲染，不报错

## 5. 前端：页面帮助抽屉

- [x] 5.1 新建 `frontend/src/components/PageHelpDrawer.vue`，从 PAGE_TIPS 读取内容，渲染"? 帮助"按钮 + 右侧滑出抽屉
- [x] 5.2 实现移动端全屏展示 + 明显关闭按钮
- [x] 5.3 在报价单列表页集成 PageHelpDrawer（pageKey="quote_list"）
- [x] 5.4 在项目详情页集成 PageHelpDrawer（pageKey="project_detail"）
- [x] 5.5 在合同详情页集成 PageHelpDrawer（pageKey="contract_detail"）
- [x] 5.6 在财务导出页集成 PageHelpDrawer（pageKey="finance_export"）
- [x] 5.7 在对账报表页集成 PageHelpDrawer（pageKey="reconciliation"）
- [x] 5.8 在数据核查页集成 PageHelpDrawer（pageKey="consistency_check"）
- [x] 5.9 在利润分析页集成 PageHelpDrawer（pageKey="profit_view"）
- [x] 5.10 验证：无对应内容时不渲染按钮，不报错

## 6. 前端：错误展示增强

- [x] 6.1 新建 `frontend/src/components/ErrorHelp.vue` 对话框，展示 reason + 有序 next_steps 列表
- [x] 6.2 修改现有 axios 响应拦截器：4xx 有 help → ErrorHelp 对话框，4xx 无 help → 保持 ElMessage，5xx → 通用提示，网络错误 → 网络提示
- [x] 6.3 验证 5 个关键场景：REQUIREMENT_FROZEN / MILESTONE_NOT_COMPLETED / PROJECT_CLOSE_CONDITIONS_NOT_MET / INVOICE_AMOUNT_EXCEEDS_CONTRACT / QUOTE_ALREADY_CONVERTED

## 7. 全局验证

- [x] 7.1 确认无 help 相关数据库表
- [x] 7.2 确认无 GET /help/* 路由
- [x] 7.3 确认帮助内容集中在 help_content.py 和 help.js，路由/视图层无硬编码帮助文字
- [x] 7.4 检查 error_codes.py 每个错误码是否需要 help 映射，未映射的注释原因
- [x] 7.5 运行全量测试 `pytest tests/ -v`，确保 0 FAILED，输出记录到 PROGRESS.md
- [x] 7.6 更新 PROGRESS.md 标记 v1.10 完成
