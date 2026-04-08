## 1. 数据库迁移（簇 A）

- [x] 1.1 创建迁移脚本 `backend/migrations/v1_6_migrate.py`：记录 customers/projects/contracts 快照（行数 + 抽样）
- [x] 1.2 创建 quotations 表（含 quote_no UNIQUE、customer_id/project_id FK、所有金额/状态/时间戳字段）
- [x] 1.3 创建 quotation_items 表（含 quotation_id FK ON DELETE CASCADE、item_type/sort_order/amount 字段）
- [x] 1.4 创建 quotation_changes 表（含 quotation_id FK、change_type/before_snapshot/after_snapshot）
- [x] 1.5 ALTER TABLE contracts ADD COLUMN quotation_id（IF NOT EXISTS 检查）
- [x] 1.6 创建全部 8 个索引
- [x] 1.7 迁移后验证：三张新表存在、索引存在、原有表行数一致、抽样字段值一致、contracts.quotation_id 存在
- [x] 1.8 创建测试 `tests/test_migration_v16.py`：表存在、索引存在、行数不变、字段值不变、FK 约束、UNIQUE 约束
- [x] 1.9 运行全量测试，确认 0 FAILED

## 2. 常量与枚举

- [x] 2.1 在 `app/core/constants.py` 追加 v1.6 常量：QUOTE_NO_PREFIX / QUOTE_VALID_DAYS_DEFAULT / QUOTE_DECIMAL_PLACES / QUOTE_ESTIMATE_MAX_DAYS / QUOTE_EXPIRE_WINDOW_DAYS / QUOTE_VALID_TRANSITIONS
- [x] 2.2 在 `app/models/enums.py` 追加枚举：QuoteStatus / QuoteItemType / QuoteChangeType

## 3. 报价金额计算引擎（簇 C）

- [x] 3.1 创建 `app/core/quote_utils.py`，实现 `calculate_quote_amount()` 函数
- [x] 3.2 实现 `generate_quote_no()` 函数（迁移到 quote_utils，保持事务内执行防并发）
- [x] 3.3 实现 `build_quote_preview()` 函数（纯计算不写库）
- [x] 3.4 实现 `can_edit_quote()` 和 `can_delete_quote()` 辅助函数
- [x] 3.5 创建测试 `tests/test_quote_utils.py`：全字段计算、无 daily_rate、无 direct_cost、精度、负数拒绝、estimate_days 校验
- [x] 3.6 创建测试 `tests/test_quote_preview.py`：preview 端点返回计算结果、不写库、结构匹配、精度、负值拒绝

## 4. 报价模型与 Schema 重构

- [x] 4.1 重构 `app/models/quotation.py`：扩展字段（estimate_days, daily_rate, direct_cost, risk_buffer_rate, discount_amount, tax_rate, subtotal_amount, tax_amount, total_amount, labor_amount, buffer_amount, base_amount, requirement_summary, notes, sent_at, accepted_at, rejected_at, expired_at, converted_contract_id, project_id）
- [x] 4.2 创建 `app/models/quotation_item.py` 和 `app/models/quotation_change.py` 模型
- [x] 4.3 重构 `app/schemas/quotation.py`：Create/Update/Response Schema 适配新字段
- [x] 4.4 创建 `app/schemas/quotation_item.py` Schema

## 5. 报价 CRUD 与 API（簇 B）

- [x] 5.1 重构 `app/crud/quotation.py`：CRUD 操作适配新模型
- [x] 5.2 创建 `app/crud/quotation_item.py`：明细项 CRUD
- [x] 5.3 创建 `app/crud/quotation_change.py`：变更日志 CRUD
- [x] 5.4 重构 `app/api/endpoints/quotations.py`：CRUD + 状态流转（send/accept/reject/cancel）+ 预览 + 明细项
- [x] 5.5 创建测试 `tests/test_quotes.py`：编号自动生成、默认 draft、列表排序、详情查询、更新 draft、拒绝更新 accepted 核心字段、允许更新 accepted notes、删除 draft、拒绝删除非 draft、状态流转校验、事件驱动过期

## 6. 报价转合同（簇 D）

- [x] 6.1 在 `quote_utils.py` 实现 `convert_quote_to_contract()` 函数（单事务：创建合同 + 更新报价 + 写日志）
- [x] 6.2 在 `quotations.py` 端点添加 POST /api/v1/quotes/{quote_id}/convert-to-contract
- [x] 6.3 创建测试 `tests/test_quote_convert.py`：转换成功、仅 accepted 可转、只能转一次、事务原子、日志记录、字段映射
- [x] 6.4 创建测试 `tests/test_quote_changes.py`：索引存在、枚举定义、字段修改日志、状态变更日志、转合同日志

## 7. 事件驱动逾期检查扩展

- [x] 7.1 修改 `app/services/overdue_check.py` 的 `_check_expired_quotations`：仅处理 sent 状态（不再处理 draft）、写入 expired_at、写入 quotation_changes 日志
- [x] 7.2 验证现有测试通过

## 8. 前端联调（簇 E）

- [x] 8.1 实现报价列表页：编号、客户、标题、总价、状态、有效期；状态筛选；过期标红；非 draft 不可删除
- [x] 8.2 实现报价编辑页：表单字段 + 实时预览 + accepted 后核心字段只读 + 隐藏字段旧值移除
- [x] 8.3 实现报价详情页：完整内容 + accepted 显示转合同按钮 + 已转显示合同编号 + expired 显示已过期
- [x] 8.4 客户详情页新增"报价"Tab：该客户报价列表 + 状态筛选 + 新建入口
- [x] 8.5 看板新增报价指标卡片：本月发出报价数 + 报价转化率（无数据时显示 0）
- [x] 8.6 前端验收：动态字段隐藏移除旧值、预览空值显示"—"、无数据不白屏

## 9. 全局重构（簇 F）

- [x] 9.1 确认 `constants.py` 无魔术数字、无硬编码前缀
- [x] 9.2 函数长度 ≤ 50 行、圈复杂度 < 10，超出者拆分
- [x] 9.3 验证 quote_utils.py 所有函数可独立 import 调用
- [x] 9.4 验证事务一致性（创建编号、接受、转合同均为单事务）
- [x] 9.5 验证日志覆盖（创建/更新失败、编号生成失败、转换失败、计算失败、过期批处理失败）
- [x] 9.6 最终全量回归 `pytest tests/ -v`：0 FAILED，输出写入 PROGRESS.md
