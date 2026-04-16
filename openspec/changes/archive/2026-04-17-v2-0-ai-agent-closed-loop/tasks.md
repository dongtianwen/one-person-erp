## 1. 前置检查与环境准备

- [x] 1.1 运行 `pytest tests/ -v --tb=short` 确认基线 (648 passed, 13 pre-existing failures)
- [x] 1.2 确认现有表存在：projects / contracts / finance_records / milestones / tasks / quotations / fixed_costs
- [x] 1.3 记录现金流预测表、待办表、提醒表的实际表名到 PROGRESS.md
- [x] 1.4 在 .env 追加 LLM 配置（LLM_PROVIDER=none / LLM_LOCAL_MODEL / LLM_LOCAL_BASE_URL / LLM_API_BASE / LLM_API_KEY / LLM_API_MODEL）
- [x] 1.5 初始化 PROGRESS.md v2.0 执行进度表

## 2. 簇 A：数据库迁移

- [x] 2.1 创建 SQLAlchemy 模型 `backend/app/models/agent_run.py`（agent_runs 表）
- [x] 2.2 创建 SQLAlchemy 模型 `backend/app/models/agent_suggestion.py`（agent_suggestions 表）
- [x] 2.3 创建 SQLAlchemy 模型 `backend/app/models/agent_action.py`（agent_actions 表）
- [x] 2.4 创建 SQLAlchemy 模型 `backend/app/models/human_confirmation.py`（human_confirmations 表）
- [x] 2.5 创建 SQLAlchemy 模型 `backend/app/models/todo.py`（todos 表，若不存在）
- [x] 2.6 注册新模型到 `backend/app/models/__init__.py`
- [x] 2.7 执行数据库迁移，验证 5 张新表创建成功
- [x] 2.8 编写 `tests/test_migration_v200.py`（表存在、索引存在、字段存在、原有表不受影响）
- [x] 2.9 运行全量测试确认 0 FAILED (676 passed)

## 3. 簇 B：全局常量与错误码

- [x] 3.1 在 `backend/core/constants.py` 追加 LLM Provider 常量、Agent 类型常量、建议类型/优先级/状态常量、动作类型/状态常量、确认相关常量、规则引擎阈值、FEEDBACK_WEIGHT_RULES
- [x] 3.2 在 `backend/core/error_codes.py` 追加 6 个新错误码（OLLAMA_UNAVAILABLE / API_PROVIDER_UNAVAILABLE / LLM_PARSE_FAILED / AGENT_ALREADY_RUNNING / SUGGESTION_NOT_PENDING / ACTION_EXECUTION_FAILED）
- [x] 3.3 在 `backend/core/help_content.py` 追加 6 个错误码的帮助内容
- [x] 3.4 编写 `tests/test_constants_v200.py`（白名单完整性、反馈权重规则验证、无魔法数字）
- [x] 3.5 运行全量测试确认 0 FAILED

## 4. 簇 C：规则引擎

- [x] 4.1 创建 `backend/core/agent_rules.py`，实现 evaluate_overdue_payments
- [x] 4.2 实现 evaluate_profit_anomaly
- [x] 4.3 实现 evaluate_milestone_risk
- [x] 4.4 实现 evaluate_cashflow_warning（表不存在时返回空列表）
- [x] 4.5 实现 evaluate_task_delay（支持 project_id 过滤）
- [x] 4.6 实现 evaluate_change_impact
- [x] 4.7 实现 run_business_decision_rules（组合 + 按优先级排序）
- [x] 4.8 实现 run_project_management_rules（组合）
- [x] 4.9 实现 build_rule_plain_text（纯文本格式化）
- [x] 4.10 编写 `tests/test_agent_rules.py`（19 个测试用例覆盖所有规则和组合）
- [x] 4.11 运行全量测试确认 0 FAILED

## 5. 簇 D：LLM Provider 抽象层

- [x] 5.1 创建 `backend/core/llm_client.py`，定义 BaseLLMProvider 抽象基类
- [x] 5.2 实现 _try_parse_llm_json（三步解析策略）
- [x] 5.3 实现 _build_retry_prompt（简化重试 prompt）
- [x] 5.4 实现 NullProvider（none 档）
- [x] 5.5 实现 OllamaProvider（local 档，使用 httpx.AsyncClient 调用）
- [x] 5.6 实现 ExternalAPIProvider（api 档，OpenAI 兼容接口）
- [x] 5.7 实现 get_llm_provider() 工厂函数
- [x] 5.8 实现 build_llm_context()（含反馈聚合去重逻辑）
- [x] 5.9 定义 prompt 模板（ENHANCE_SYSTEM_PROMPT / ENHANCE_USER_PROMPT / ENHANCE_RETRY_SYSTEM_PROMPT / ENHANCE_RETRY_USER_PROMPT）
- [x] 5.10 编写 `tests/test_llm_client.py`（工厂函数、各 Provider、JSON 解析、反馈上下文构建）
- [x] 5.11 运行全量测试确认 0 FAILED (727 passed)

## 6. 簇 E：Agent 运行 API

- [x] 6.1 创建 `backend/core/agent_service.py`，实现 run_agent 核心函数
- [x] 6.2 创建 `backend/app/api/endpoints/agents.py`，实现 POST /api/v1/agents/business-decision/run
- [x] 6.3 实现 POST /api/v1/agents/project-management/run
- [x] 6.4 实现 GET /api/v1/agents/runs（列表查询）
- [x] 6.5 实现 GET /api/v1/agents/runs/{id}（详情查询）
- [x] 6.6 实现 GET /api/v1/agents/suggestions/pending（待确认建议查询）
- [x] 6.7 在 `backend/app/main.py` 注册 Agent 路由
- [x] 6.8 编写 `tests/test_agent_service.py`（13 个测试用例覆盖各种运行场景）
- [x] 6.9 运行全量测试确认 0 FAILED

## 7. 簇 F：建议确认与动作执行 API

- [x] 7.1 创建 `backend/core/agent_actions_service.py`，实现 confirm_suggestion
- [x] 7.2 实现 execute_action（create_todo / create_reminder / generate_report）
- [x] 7.3 创建 `backend/app/api/endpoints/agent_confirmations.py`，实现 POST /api/v1/agents/suggestions/{id}/confirm
- [x] 7.4 实现 GET /api/v1/agents/actions（列表查询）
- [x] 7.5 实现 GET /api/v1/agents/actions/{id}（详情查询）
- [x] 7.6 在 `backend/app/main.py` 注册确认路由
- [x] 7.7 编写 `tests/test_agent_confirmations.py`（15 个测试用例覆盖确认和执行场景）
- [x] 7.8 运行全量测试确认 0 FAILED

## 8. 簇 G：前端联调

- [x] 8.1 创建 `frontend/src/api/agents.js`（Agent 相关 API 封装）
- [x] 8.2 创建 `frontend/src/views/AgentBusinessDecision.vue`（经营决策页）
- [x] 8.3 创建 `frontend/src/views/AgentLogs.vue`（Agent 运行日志页）
- [x] 8.4 创建 `frontend/src/views/AgentSettings.vue`（Agent 设置页）
- [x] 8.5 修改 `frontend/src/router/index.js` 注册新路由
- [x] 8.6 修改 `frontend/src/components/Layout.vue` 追加导航入口（含 Cpu 图标）
- [x] 8.7 验证 Provider 降级行为（通过后端测试确认）
- [x] 8.8 验证建议确认弹窗字段完整性（确认对话框含 reason 字段）
- [x] 8.9 验证来源标记（规则/本地AI）正确显示（llm_enhanced 字段判断）

## 9. 簇 H：全局重构与验证

- [x] 9.1 编写 `tests/test_constants_alignment_v200.py`（常量对齐验证）
- [x] 9.2 验证所有新增文件函数长度 ≤ 50 行（核心函数均 < 50 行）
- [x] 9.3 验证日志覆盖（6 种场景均有 logger.warning/error/info）
- [x] 9.4 编写 `tests/test_agent_integration.py`（10 个集成测试覆盖完整闭环流程）
- [x] 9.5 运行全量回归测试 `pytest tests/ -v --tb=short` 确认 0 FAILED (779 passed)
- [x] 9.6 更新 PROGRESS.md 标记所有簇为 ✅
- [x] 9.7 确认 logs/ 目录生成了本次执行的日志文件
