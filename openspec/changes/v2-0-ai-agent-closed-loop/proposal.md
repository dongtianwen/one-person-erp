## Why

在 v1.0 ~ v1.12 已建立的经营底座（合同、报价、项目、财务、里程碑等）之上，系统缺乏自动感知异常并给出行动建议的能力。v2.0 新增 AI 智能体闭环层，实现「规则引擎感知 → LLM 语言增强 → 人工确认执行 → 反馈优化下次运行」的完整闭环，提升一人经营者的决策效率，同时通过规则引擎兜底和人工确认保证经营安全。

## What Changes

- 新增 4 张 Agent 核心表（agent_runs / agent_suggestions / agent_actions / human_confirmations）及待办表（todos）
- 新增规则引擎模块，按常量阈值检测逾期回款、利润异常、里程碑风险、现金流预警、任务延期、变更影响
- 新增三档 LLM Provider 架构（none / local-Ollama / api-外部），仅做语言增强，不做自由问答或报告生成
- 新增 Agent 运行 API（手动触发经营分析 / 项目分析），支持并发锁和降级策略
- 新增建议确认与动作执行 API，支持接受/拒绝/修改决策，自动创建待办/提醒
- 新增结构化反馈注入机制（FEEDBACK_WEIGHT_RULES），历史偏好影响下次 LLM 上下文
- 前端新增经营决策页、Agent 运行日志页、项目详情页智能分析入口、Agent 设置页

## Capabilities

### New Capabilities

- `agent-run-management`: Agent 运行生命周期管理，包括触发、记录、状态追踪、运行日志查询
- `rule-engine`: 规则引擎，读取经营数据按阈值生成结构化建议，全部阈值来自常量配置
- `llm-provider`: 三档 LLM Provider（none/local/api），JSON 解析增强策略，工厂模式调度
- `suggestion-confirmation`: 建议确认机制，人工决策写入反馈，支持字段级修改和优先级覆盖
- `agent-action-execution`: 动作执行引擎，自动创建待办/提醒/报告，失败不回滚确认状态
- `feedback-optimization`: 结构化反馈注入，历史决策影响下次 LLM 上下文生成的权重规则
- `agent-frontend`: 前端 Agent 相关页面（经营决策、运行日志、项目智能分析、Agent 设置）

### Modified Capabilities

<!-- No existing spec requirements change; v2.0 is purely additive -->

## Impact

- **后端新增文件**: `backend/core/agent_rules.py`, `backend/core/llm_client.py`, `backend/core/agent_service.py`, `backend/core/agent_actions_service.py`, `backend/api/v1/agents.py`, `backend/api/v1/agent_confirmations.py`
- **后端修改**: `backend/core/constants.py`（追加常量）, `backend/core/error_codes.py`（追加错误码）, `backend/core/help_content.py`（追加帮助内容）, `backend/main.py`（注册新路由）, `backend/app/models/`（新增 5 个模型）
- **数据库**: 新增 5 张表（agent_runs / agent_suggestions / agent_actions / human_confirmations / todos）
- **前端新增**: `frontend/src/views/AgentBusinessDecision.vue`, `frontend/src/views/AgentLogs.vue`, `frontend/src/views/AgentSettings.vue`
- **前端修改**: `frontend/src/views/Projects.vue`（追加项目智能分析按钮）, `frontend/src/router/index.js`, `frontend/src/api/`（新增 agent API 模块）
- **依赖**: 可能需要 `ollama` Python 包（local Provider）
