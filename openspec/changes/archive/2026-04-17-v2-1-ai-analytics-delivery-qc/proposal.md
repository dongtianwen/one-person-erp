## Why

v2.0 已建立 AI 智能体闭环层（规则感知 → LLM 增强 → 人工确认 → 反馈优化），但经营者仍需手动翻阅多个页面才能回答经营问题、缺乏结构化的项目复盘与客户分析报告、交付包质检仅靠人工检查。v2.1 新增三项增强分析能力：经营数据自由问答、深度报告生成、交付/质检智能体，进一步提升一人经营者的决策效率和交付质量。

## What Changes

- 新增经营数据自由问答功能（仅 LLM_PROVIDER=api 可用），前端维护对话历史，后端注入固定经营数据包后调用外部 API 回答
- 新增深度报告生成功能，扩展 v1.12 模板系统支持 report_project / report_customer 两种类型，Jinja2 拼装结构性数据 + LLM 填充分析段落变量
- 新增 reports 表，独立于 quotations/contracts，支持版本管理（重新生成新增版本记录，不覆盖旧记录）
- 新增交付/质检智能体（AGENT_TYPE_DELIVERY_QC），复用 v2.0 四张 Agent 表，规则层检查交付包完整性，LLM 层增强质检描述
- 新增 6 条质检规则：模型版本缺失、数据集版本缺失、验收记录缺失、版本不一致、交付包为空、交付包未绑定项目
- 扩展 TEMPLATE_TYPE_WHITELIST 和 AGENT_TYPE_WHITELIST，新增报告相关常量和质检建议类型常量
- 新增 6 个错误码及对应帮助内容
- 前端新增问答页、报告生成入口（项目详情页 + 客户详情页）、交付包质检入口、Agent 设置页扩展

## Capabilities

### New Capabilities

- `qa-service`: 经营数据自由问答服务，构建固定经营数据上下文，仅 api Provider 可用，前端维护多轮对话历史不落库
- `report-generation`: 深度报告生成服务，支持项目复盘报告和客户分析报告，Jinja2 结构渲染 + LLM 分析段落填充，reports 表版本管理
- `delivery-qc-agent`: 交付/质检智能体，6 条完整性检查规则 + LLM 语言增强，复用 v2.0 Agent 闭环流程

### Modified Capabilities

- `template-management`: 扩展模板类型白名单，新增 report_project / report_customer 类型及默认模板
- `llm-provider`: 新增 call_freeform（自由问答）和 _call_llm_single_var（报告变量填充）方法
- `agent-run-management`: 扩展 Agent 类型路由，新增 delivery_qc 类型支持
- `rule-engine`: 新增交付包质检规则函数（evaluate_delivery_package）
- `agent-frontend`: 新增问答页、报告生成 UI、交付包质检 UI、Agent 设置页扩展
- `error-help-mapping`: 新增 6 个 v2.1 错误码的帮助内容

## Impact

- **后端新增文件**: `backend/core/qa_service.py`, `backend/core/report_service.py`, `backend/api/v1/qa.py`, `backend/api/v1/reports.py`
- **后端修改**: `backend/core/constants.py`（追加常量）, `backend/core/error_codes.py`（追加错误码）, `backend/core/help_content.py`（追加帮助内容）, `backend/core/agent_rules.py`（追加质检规则）, `backend/core/agent_service.py`（扩展 delivery_qc 路由）, `backend/core/llm_client.py`（新增方法）, `backend/main.py`（注册新路由）
- **数据库**: 新增 reports 表 + 2 个索引
- **前端新增**: 问答页 `/assistant/qa`
- **前端修改**: 项目详情页（追加报告生成按钮）、客户详情页（追加报告生成按钮）、交付包详情页（追加质检按钮）、Agent 设置页（扩展问答配置）、路由配置
- **测试**: 新增 `test_migration_v210.py`, `test_qa_service.py`, `test_report_service.py`, `test_delivery_qc.py`, `test_constants_alignment_v210.py`, `test_v210_integration.py`
