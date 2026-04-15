## Context

v1.0~v1.12 已建立完整的经营底座（项目、合同、报价、财务、里程碑、任务等模块），但系统缺乏自动感知经营异常并给出行动建议的能力。v2.0 在现有数据模型之上叠加 AI 智能体闭环层，通过规则引擎 + 三档 LLM Provider + 人工确认实现可审计的经营决策闭环。

**约束**:
- 所有 Agent 均为用户手动触发，不做自动触发
- LLM 仅做语言增强，不做自由问答、深度报告、增强分析
- 规则引擎为系统默认运行态，三档 Provider 均依赖此层
- 任意 Provider 不可用时降级为规则文本输出，不报错、不阻断
- 所有建议必须经用户确认才能执行动作
- Agent 可自动执行：创建待办、创建提醒；必须人工确认：修改合同、确认回款、关闭项目

## Goals / Non-Goals

**Goals:**
- 实现规则引擎驱动的异常检测（逾期回款、利润异常、里程碑风险、现金流预警、任务延期、变更影响）
- 实现三档 LLM Provider 架构（none / local-Ollama / api-外部），支持运行时切换
- 实现 JSON 解析增强策略（直接解析 → 括号提取 → 单次重试 → 降级）
- 实现建议确认与动作执行闭环，支持接受/拒绝/修改决策
- 实现结构化反馈注入（FEEDBACK_WEIGHT_RULES），历史偏好影响下次 LLM 上下文
- 前端完成经营决策页、运行日志页、项目智能分析、Agent 设置页

**Non-Goals:**
- 自由问答、深度报告、增强分析（v2.1）
- 自动触发（v2.1 或更晚）
- 多人协作、云同步、自动外发
- 知识图谱、交付质检智能体
- LLM 参与决策（决策逻辑全部在规则引擎层）

## Decisions

### 1. 规则引擎 vs LLM 职责分离

**Decision**: 规则引擎负责所有决策逻辑，LLM 仅做语言增强（改写建议文案）。

**Rationale**: 保证离线可用和经营安全。规则引擎基于真实经营数据和常量阈值做判断，LLM 不参与决策，避免因模型幻觉导致错误经营决策。

**Alternatives considered**: 让 LLM 做推理决策 → 拒绝，不可审计、不可复现、依赖外部服务。

### 2. 三档 Provider 工厂模式

**Decision**: 使用 `BaseLLMProvider` 抽象基类 + 三个具体实现（`NullProvider` / `OllamaProvider` / `ExternalAPIProvider`），通过 `get_llm_provider()` 工厂函数按 `.env` 配置实例化。

**Rationale**: 工厂模式保证 Provider 可替换、可测试。`NullProvider` 实现 none 档，保证无 LLM 依赖时系统正常工作。

### 3. OllamaProvider 使用 requests 而非 ollama SDK

**Decision**: `OllamaProvider` 直接使用 `requests.post` 调用 Ollama HTTP API，不使用 `ollama` Python SDK 的 `chat()` 函数。

**Rationale**: `requests` 支持标准 `timeout` 参数，精确控制 30 秒硬超时。`ollama` SDK 的 `chat()` 超时行为不明确。

### 4. JSON 解析三步策略

**Decision**: `_try_parse_llm_json` 实现三步：直接解析 → 正则提取 `[...]` → 返回 None（触发重试或降级）。重试时使用简化 prompt（few-shot + titles only）。

**Rationale**: 小模型常输出 markdown fence 或前缀文字，括号提取可覆盖大部分格式漂移。重试 prompt 更简单，减少格式漂移概率。

### 5. 反馈聚合：同组合去重取最近一条

**Decision**: `build_llm_context` 按 `(decision_type, suggestion_type)` 分组，每组只保留最近一条记录，不同组合各保留一条。

**Rationale**: 避免重复注入相同组合的历史反馈，保持 LLM 上下文简洁，token 用量可控。

### 6. 数据库模型：4 张核心表 + 1 张待办表

**Decision**: `agent_runs`（运行记录）→ `agent_suggestions`（建议）→ `agent_actions`（动作）→ `human_confirmations`（确认），外加 `todos` 表。

**Rationale**: 清晰的数据流：一次运行产生多条建议，每条建议对应 0-1 条确认，确认后触发 0-1 个动作。外键关系保证数据完整性。

### 7. 动作执行失败不回滚确认状态

**Decision**: `execute_action` 失败时记录 `status=failed` 和 `error_message`，但不回滚 `human_confirmations` 和 `suggestion.status`。

**Rationale**: 用户的确认决策是独立的经营行为，不应因系统动作失败而撤销。用户可在日志中查看失败详情并手动补录。

### 8. 并发锁：同类型 Agent 不允许并行运行

**Decision**: `run_agent` 开头检查同类型 `status=running` 记录，存在则返回 409 `AGENT_ALREADY_RUNNING`。

**Rationale**: 避免同一时刻多条规则引擎读取不一致的数据库快照。

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| Ollama 响应超过 30 秒超时 | `requests` 硬超时，降级为规则文本，记录 WARNING |
| LLM 返回非 JSON 格式 | 三步解析 + 单次重试，仍失败则降级 |
| 规则引擎阈值需要调优 | 全部阈值集中在 `constants.py`，无需改代码 |
| 反馈聚合注入过多 token | `FEEDBACK_CONTEXT_MAX_RECORDS=30` 限制查询量，聚合后条数通常 <10 |
| 动作执行失败导致数据不一致 | 不回滚确认状态，记录失败详情，用户可手动补录 |
| 前端 Provider 状态展示不准确 | 从 `agent_runs` 最近一条记录的 `llm_provider` 字段读取 |

## Migration Plan

1. 执行数据库迁移（簇 A）：创建 5 张新表
2. 部署后端代码（簇 B~F）：常量、规则引擎、LLM Provider、Agent API
3. 部署前端代码（簇 G）：新增页面和路由
4. 验证：`pytest tests/ -v`，手动触发 Agent 运行验证闭环

**Rollback**: 新表不影响现有功能，回滚只需恢复旧版代码。新表数据保留，后续版本可继续使用。

## Open Questions

- 现金流预测表的实际表名需要在前置检查阶段从 `PROGRESS.md` 确认
- 待办表（todos）和提醒表是否已存在，若不存在则按簇 A.2 创建
- 前端是否需要 Agent 运行进度轮询（SSE/WebSocket），还是仅用同步 API 响应
