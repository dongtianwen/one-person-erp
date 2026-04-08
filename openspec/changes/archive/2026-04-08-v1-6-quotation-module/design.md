## Context

数标云管 v1.0~v1.5 已实现客户/项目/合同/财务/需求管理。v1.5 引入了基础的报价模型（`models/quotation.py`、`crud/quotation.py`、`schemas/quotation.py`、`api/endpoints/quotations.py`），但功能简陋——仅有编号生成、CRUD 骨架和过期检查，缺少金额计算、明细项、变更日志、报价转合同、前端页面等完整业务能力。

现有代码结构：FastAPI + SQLAlchemy (async) + SQLite + Alembic。后端分层为 models → schemas → crud → api/endpoints，核心业务逻辑在 `app/core/` 下按领域拆分 utils 模块。逾期检查集中在 `app/services/overdue_check.py`。

## Goals / Non-Goals

**Goals:**

- 将报价模型从简单骨架升级为完整报价单（含金额计算引擎、明细项、变更日志）
- 实现报价金额计算全链路：labor → base → buffer → subtotal → tax → total，精度 2 位小数
- 实现报价预览接口（不写库，与保存共用计算逻辑）
- 实现 accepted 报价单一键转合同草稿（同事务原子操作）
- 扩展事件驱动逾期检查，增加 quotation_changes 日志写入
- 实现前端报价管理页面（编辑/详情/列表/客户Tab/看板指标）
- 保持与 v1.0~v1.5 的向后兼容（不破坏已有接口和模型）

**Non-Goals:**

- 不做客户线索管理
- 不做审批流/电子签名
- 不接入外部市场价格或 AI 自动定价
- 不做报价模板功能
- 不做多币种支持

## Decisions

### D1: 报价模型重构策略——原地扩展而非替换

**选择**: 在现有 `models/quotation.py` 基础上扩展字段，而非重建模型。

**理由**: v1.5 已有 quotation 模型、CRUD、schema、endpoint 骨架，替换会导致大量断点。扩展方案通过数据库迁移 ALTER TABLE 补充新字段（estimate_days, daily_rate, direct_cost 等），保持编号字段 `quotation_number` 不变（PRD 中 `quote_no` 映射到现有字段）。

**替代方案**: 新建 QuotationV2 模型 → 引入双版本并行复杂度，不符合渐进演进原则。

### D2: 金额计算逻辑独立为 `app/core/quote_utils.py`

**选择**: 将 calculate_quote_amount / build_quote_preview / can_edit_quote / can_delete_quote / convert_quote_to_contract 集中到 `app/core/quote_utils.py`。

**理由**: 与项目既有模式一致（finance_utils.py、profit_utils.py、cashflow_utils.py），保持核心业务逻辑与路由层分离，便于单元测试直接 import 调用。

**替代方案**: 放在 crud 层 → 违反项目分层约定，crud 层只做数据操作不做业务计算。

### D3: 数据库迁移使用独立脚本 `backend/migrations/v1_6_migrate.py`

**选择**: 沿用 v1.4/v1.5 的迁移模式，新建独立迁移脚本。

**理由**: 与项目迁移历史一致（v1_4_migrate.py、v1_5_migrate.py），迁移前记录快照，迁移后验证数据完整性。

### D4: 报价明细项使用独立表 quotation_items

**选择**: 创建 quotation_items 表，通过 quotation_id 外键关联。

**理由**: 一张报价单可包含多个明细行（labor/design/testing/deployment/outsource/other），符合关系模型。ON DELETE CASCADE 保证报价删除时明细项同步清理。

### D5: 变更日志使用 quotation_changes 快照表

**选择**: 每次变更记录 before/after JSON 快照到 quotation_changes 表。

**理由**: 与 PRD 要求一致，且审计追溯需要完整变更历史。JSON 快照方式比逐字段记录更简单、更通用。

### D6: 报价转合同使用同一事务

**选择**: 转合同操作在单一数据库事务中完成：创建合同 → 更新报价 converted_contract_id → 写入 quotation_changes 日志。

**理由**: 保证原子性——要么全部成功，要么全部回滚。避免出现合同创建成功但报价未标记的脏数据状态。

### D7: 前端报价预览使用专用 POST /api/v1/quotes/preview 端点

**选择**: 独立预览端点，不写库，返回计算结果。

**理由**: 前端编辑报价时可实时预览金额，不影响数据库。与正式保存共用 `calculate_quote_amount` 函数保证计算一致性。

## Risks / Trade-offs

- **[风险] 报价编号并发冲突** → 通过事务内 SELECT + INSERT 保证序号唯一（与现有 generate_quotation_number 逻辑一致）
- **[风险] 迁移脚本在已有数据上执行失败** → 迁移前记录快照，迁移后验证行数和抽样数据；迁移脚本使用 IF NOT EXISTS 保证幂等
- **[风险] contracts 表已有 quotation_id 列（如果前期实现已添加）** → 迁移脚本 ALTER TABLE 前先检查列是否存在，避免重复添加报错
- **[取舍] quotation_changes 使用 TEXT 存储 JSON 而非 JSON 列类型** → SQLite 对 JSON 列支持有限，TEXT + JSON 序列化更兼容
- **[取舍] accepted 报价单核心字段完全锁定** → 牺牲灵活性换取数据一致性，PRD 明确要求 accepted 后只允许改 notes
