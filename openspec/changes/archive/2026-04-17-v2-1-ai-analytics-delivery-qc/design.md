## Context

v2.0 已建立 AI 智能体闭环层（规则引擎 → LLM 增强 → 人工确认 → 反馈优化），四张 Agent 核心表（agent_runs / agent_suggestions / agent_actions / human_confirmations）和三档 LLM Provider（none / local / api）已就绪。v1.12 模板系统支持 quotation / contract 两种类型。v1.11 交付包管理（delivery_packages / model_versions / dataset_versions）已就绪。

v2.1 在此基础上新增三项增强分析能力：经营数据自由问答、深度报告生成、交付/质检智能体。

**约束**:
- 自由问答仅 LLM_PROVIDER=api 可用，local/none 不显示入口
- 报告生成中 LLM 仅填充分析段落变量，结构性数据由代码拼装
- 交付/质检不做 LLM 自主判断交付物内容质量，不读取实际文件内容
- 多轮对话由前端维护，后端不落库
- 报告重新生成新增版本记录，不覆盖旧记录

## Goals / Non-Goals

**Goals:**
- 实现经营数据自由问答（固定数据包注入 + api Provider 调用，前端维护对话历史）
- 实现深度报告生成（Jinja2 结构渲染 + LLM 分析段落填充，reports 表版本管理）
- 实现交付/质检智能体（6 条完整性规则 + LLM 语言增强，复用 v2.0 Agent 闭环）
- 扩展模板类型白名单和 Agent 类型白名单
- 新增 6 个错误码及帮助内容
- 前端新增问答页、报告生成入口、交付包质检入口、Agent 设置页扩展

**Non-Goals:**
- 多轮对话落库、跨会话历史持久化
- LLM 自主判断交付物内容质量
- 报告自动推送、多人协作
- 问题路由识别、按问题类型动态选择数据
- 自动触发 Agent 运行

## Decisions

### 1. 自由问答：固定数据包注入 vs 动态数据检索

**Decision**: 采用固定数据包注入模式，`build_qa_context` 从 DB 读取近 3 个月财务摘要 + 活跃项目列表 + 逾期合同，序列化为 JSON 注入 system prompt。

**Rationale**: 一人公司经营数据量有限，固定数据包 token 估算 ≤ 2000，无需复杂的数据检索路由。动态检索需要问题分类和 SQL 生成，增加复杂度和不可控性。

**Alternatives considered**: 动态 SQL 生成 → 拒绝，安全风险高、复杂度大、小数据量无必要。

### 2. 报告生成：Jinja2 + LLM 混合渲染

**Decision**: 结构性数据（工时、金额、日期等）由代码拼装到 Jinja2 context，LLM 仅填充 3 个分析段落变量（项目报告）或 3 个分析段落变量（客户报告）。

**Rationale**: 结构性数据必须精确，不能依赖 LLM 生成。分析性文本需要 LLM 的语言能力。两者分离保证数据准确性和分析灵活性的平衡。

**Alternatives considered**: 全部由 LLM 生成 → 拒绝，数据准确性无法保证；全部由模板生成 → 拒绝，分析段落缺乏智能。

### 3. 报告版本管理：追加 vs 覆盖

**Decision**: 重新生成报告时新增版本记录（version_no 递增），旧记录 is_latest=0，不覆盖。

**Rationale**: 报告是经营复盘的重要记录，保留历史版本可追溯分析变化。覆盖会丢失历史信息。

**Alternatives considered**: 覆盖更新 → 拒绝，丢失历史版本。

### 4. 自由问答 Provider 限制：双重保护

**Decision**: 前端判断 LLM_PROVIDER=api 且 Provider 可用时显示入口，后端 POST /api/v1/qa/ask 在非 api 档返回 403。

**Rationale**: 自由问答完全依赖外部 LLM 的通用问答能力，local/none 档无法提供可靠回答。双重保护避免绕过前端直接调用后端。

**Alternatives considered**: local 档降级回答 → 拒绝，小模型自由问答质量不可控，可能误导经营决策。

### 5. 交付质检规则：纯规则检查 + LLM 增强

**Decision**: 质检规则检查交付包完整性（关联模型版本、数据集版本、验收记录等），LLM 仅做语言增强（质检报告语言化 + 缺失项描述增强），不读取实际文件内容。

**Rationale**: 文件内容分析需要多模态能力且不可控，完整性检查基于数据库关联关系即可。复用 v2.0 Agent 闭环流程（规则 → LLM 增强 → 确认 → 执行）。

**Alternatives considered**: LLM 分析文件内容 → 拒绝，不可控、不可审计、依赖外部服务。

### 6. reports 表独立于 quotations/contracts

**Decision**: 新建 reports 表，独立于 quotations/contracts 表，不共享 generated_content 字段。

**Rationale**: 报告的数据模型（版本管理、LLM 填充变量、报告类型）与报价/合同差异大，独立表避免耦合。

### 7. LLM 单变量填充：逐变量调用 vs 一次性调用

**Decision**: 对每个 LLM 变量单独调用 `_call_llm_single_var`，携带完整 context，返回纯文本。

**Rationale**: 逐变量调用允许部分失败（某变量填充失败不影响其他变量），且单变量输出更可控。一次性调用需要 JSON 格式输出，小模型格式漂移风险高。

**Alternatives considered**: 一次性调用返回 JSON → 拒绝，格式漂移风险高，部分失败难以处理。

## Risks / Trade-offs

| Risk | Mitigation |
|------|-----------|
| 自由问答数据包超过 token 限制 | QA_CONTEXT_MAX_TOKENS_ESTIMATE=2000，活跃项目限制 QA_CONTEXT_MAX_PROJECTS=10 |
| LLM 分析段落填充失败 | 降级为占位文本 REPORT_LLM_FALLBACK_TEXT，报告仍生成，不阻断 |
| 报告模板变量与实际数据不匹配 | 代码拼装 context 时确保所有模板变量有值，LLM 变量有兜底 |
| 交付包质检规则依赖字段名 | 前置检查记录 delivery_packages 实际字段到 PROGRESS.md |
| 历史对话过长消耗 token | QA_MAX_HISTORY_TURNS=10 截断最早轮次 |
| call_freeform 仅 ExternalAPIProvider | 测试验证 NullProvider/OllamaProvider 不存在此方法 |

## Migration Plan

1. 执行数据库迁移（簇 A）：创建 reports 表 + 2 个索引，扩展白名单常量，写入默认报告模板
2. 部署后端代码（簇 B~D）：自由问答服务、报告服务、交付质检智能体
3. 部署前端代码（簇 E）：问答页、报告入口、质检入口、设置页扩展
4. 全局验证（簇 F）：常量对齐、函数长度、日志覆盖、集成测试
5. 最终回归：`pytest tests/ -v`，0 FAILED

**Rollback**: reports 表不影响现有功能，回滚只需恢复旧版代码。reports 表数据保留，后续版本可继续使用。

## Open Questions

- delivery_packages 实际字段名需在前置检查阶段确认并记录到 PROGRESS.md
- TEMPLATE_TYPE_WHITELIST 当前值需在前置检查阶段确认
- package_model_versions / package_dataset_versions 关联表是否存在，需确认
