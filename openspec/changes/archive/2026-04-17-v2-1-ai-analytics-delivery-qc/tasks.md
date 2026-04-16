## 1. 前置检查与数据库迁移

- [x] 1.1 运行全量测试确认基线：`pytest tests/ -v --tb=short`，要求 0 FAILED
- [x] 1.2 确认 v2.0 四张 Agent 表存在、v1.12 templates 表存在、v1.11 delivery_packages 相关表存在
- [x] 1.3 记录 delivery_packages 实际字段和 TEMPLATE_TYPE_WHITELIST 当前值到 PROGRESS.md
- [x] 1.4 新建 reports 表（含 idx_reports_entity 和 idx_reports_type_status 索引）
- [x] 1.5 扩展 constants.py：追加报告相关常量（TEMPLATE_TYPE_REPORT_PROJECT/CUSTOMER, REPORT_TYPE_*, REPORT_STATUS_*, PROJECT/CUSTOMER_REPORT_LLM_VARS, REPORT_LLM_FALLBACK_TEXT, QA_CONTEXT_MONTHS/MAX_PROJECTS/MAX_TOKENS_ESTIMATE/MAX_HISTORY_TURNS）
- [x] 1.6 扩展 constants.py：追加 Agent 类型常量（AGENT_TYPE_DELIVERY_QC）和质检建议类型常量（SUGGESTION_TYPE_DELIVERY_*）
- [x] 1.7 扩展 constants.py：更新 TEMPLATE_TYPE_WHITELIST 和 AGENT_TYPE_WHITELIST
- [x] 1.8 追加 error_codes.py：注册 6 个新错误码（QA_REQUIRES_API_PROVIDER, QA_CONTEXT_BUILD_FAILED, REPORT_TYPE_NOT_SUPPORTED, REPORT_ENTITY_NOT_FOUND, REPORT_LLM_FILL_FAILED, DELIVERY_QC_NO_PACKAGE）
- [x] 1.9 追加 help_content.py：为 6 个新错误码添加帮助内容
- [x] 1.10 写入默认报告模板（report_project / report_customer），幂等插入
- [x] 1.11 编写 test_migration_v210.py：验证 reports 表、索引、白名单扩展、默认模板、幂等性、现有表不受影响
- [x] 1.12 运行全量测试，0 FAILED，更新 PROGRESS.md

## 2. 自由问答后端

- [x] 2.1 实现 build_qa_context 函数（backend/core/qa_service.py）：构建固定经营数据包
- [x] 2.2 实现 ask_question 函数（backend/core/qa_service.py）：截断历史、构建 messages、调用 Provider
- [x] 2.3 实现 QA_SYSTEM_PROMPT 常量
- [x] 2.4 在 ExternalAPIProvider 中实现 call_freeform 方法
- [x] 2.5 创建 QA API 路由（backend/api/v1/qa.py）：POST /api/v1/qa/ask，含 Provider 守卫
- [x] 2.6 注册 QA 路由到 main.py
- [x] 2.7 编写 test_qa_service.py：验证 context 构建、Provider 限制、历史截断、call_freeform 不存在于 NullProvider/OllamaProvider
- [x] 2.8 运行全量测试，0 FAILED，更新 PROGRESS.md

## 3. 深度报告后端

- [x] 3.1 实现 build_project_report_context 函数（backend/core/report_service.py）
- [x] 3.2 实现 build_customer_report_context 函数（backend/core/report_service.py）
- [x] 3.3 实现 fill_llm_vars 函数（backend/core/report_service.py）：逐变量填充，失败降级
- [x] 3.4 实现 generate_report 函数（backend/core/report_service.py）：创建记录、获取模板、构建 context、填充 LLM 变量、渲染模板、版本管理
- [x] 3.5 实现 REPORT_VAR_PROMPTS 常量
- [x] 3.6 在 ExternalAPIProvider 中实现 _call_llm_single_var 方法
- [x] 3.7 创建 Reports API 路由（backend/api/v1/reports.py）：POST generate / GET list / GET detail / DELETE
- [x] 3.8 注册 Reports 路由到 main.py
- [x] 3.9 编写 test_report_service.py：验证 context 构建、LLM 填充降级、报告生成、版本管理
- [x] 3.10 运行全量测试，0 FAILED，更新 PROGRESS.md

## 4. 交付/质检智能体

- [x] 4.1 实现 evaluate_delivery_package 函数（追加到 backend/core/agent_rules.py）：6 条完整性检查规则
- [x] 4.2 实现 run_delivery_qc_rules 函数（追加到 backend/core/agent_rules.py）
- [x] 4.3 扩展 agent_service.py 的 run_agent：新增 delivery_qc 类型路由
- [x] 4.4 创建 Delivery QC API 路由（backend/api/v1/agents.py 或新文件）：POST /api/v1/agents/delivery-qc/run
- [x] 4.5 注册路由到 main.py（如需新文件）
- [x] 4.6 编写 test_delivery_qc.py：验证 6 条规则、空结果、404、Agent 运行记录、LLM 增强、确认流程
- [x] 4.7 运行全量测试，0 FAILED，更新 PROGRESS.md

## 5. 前端联调

- [x] 5.1 新增 QA 问答页（/assistant/qa）：Provider 判断、对话气泡、输入框、loading 状态
- [x] 5.2 项目详情页追加「生成项目复盘报告」按钮（仅 status=completed 显示）
- [x] 5.3 客户详情页追加「生成客户分析报告」按钮
- [x] 5.4 实现报告历史弹窗：列表（时间/Provider/状态/版本号）、查看、删除
- [x] 5.5 交付包详情页追加「运行质检分析」按钮和结果弹窗
- [x] 5.6 Agent 设置页扩展：新增「自由问答」区域（Provider 状态、配置指引、key 只写不读）
- [x] 5.7 更新路由配置
- [x] 5.8 新增前端 API 模块（qa API、reports API、delivery-qc API）

## 6. 全局重构与验证

- [x] 6.1 编写 test_constants_alignment_v210.py：验证白名单对齐、类型映射、方法存在性
- [x] 6.2 函数长度约束检查：所有新增函数 ≤ 50 行，超长函数提取子函数
- [x] 6.3 日志覆盖验证：LLM 填充失败(WARNING)、报告生成失败(ERROR)、质检 package 不存在(WARNING)、QA context 子查询失败(WARNING)、QA context 全部失败(ERROR)
- [x] 6.4 编写 test_v210_integration.py：完整报告流程（none/local/partial failure）、完整质检流程、QA 端点 403、历史截断
- [x] 6.5 最终全量回归：`pytest tests/ -v --tb=short`，0 FAILED
- [x] 6.6 更新 PROGRESS.md，所有簇状态为 ✅

## Task Dependencies

- [2] depends on [1]（常量和数据库迁移必须先完成）
- [3] depends on [1]（常量和模板必须先完成）
- [4] depends on [1]（常量和 Agent 表必须先完成）
- [5] depends on [2, 3, 4]（前端联调需要后端 API 就绪）
- [6] depends on [2, 3, 4, 5]（全局验证需要所有功能完成）
- [2], [3], [4] 可并行执行
