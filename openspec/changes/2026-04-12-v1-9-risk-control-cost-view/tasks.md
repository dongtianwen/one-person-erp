## 1. 前置检查与常量定义

- [ ] 1.1 运行全量测试确认 v1.0~v1.8 通过，记录快照
- [x] 1.2 在 backend/core/constants.py 追加 v1.9 常量（HOURS_PER_DAY / OVERDUE_* / CONSISTENCY_CHECK_TOLERANCE / FIXED_COST_* / GROSS_PROFIT_*）
- [x] 1.3 在 backend/models/enums.py 追加 FixedCostPeriod 和 FixedCostCategory 枚举

## 2. 数据库迁移（簇 A）

- [ ] 2.1 创建 backend/migrations/v1_9_migrate.py：迁移前记录快照（行数 + 抽样）
- [ ] 2.2 实现 CREATE TABLE fixed_costs（含 project_id 外键）
- [ ] 2.3 实现 CREATE TABLE input_invoices（含 project_id 外键）
- [ ] 2.4 实现 ALTER TABLE customers 新增 overdue_milestone_count / overdue_amount / risk_level
- [ ] 2.5 实现 ALTER TABLE projects 新增 cached_revenue 等 7 个缓存字段
- [ ] 2.6 创建 7 个新索引（fixed_costs 3个 + input_invoices 3个 + customers 1个）
- [ ] 2.7 实现迁移后验证（新表存在 / 新字段存在 / 索引存在 / 原数据一致）
- [ ] 2.8 创建 tests/test_migration_v19.py（11 个测试用例）
- [ ] 2.9 运行全量测试，更新 PROGRESS.md

## 3. 三表一致性校验——后端（簇 B）

- [ ] 3.1 创建 backend/core/consistency_utils.py：实现 get_contract_received_amount / get_contract_invoiced_amount_active / get_contract_verified_invoice_amount
- [ ] 3.2 实现 detect_payment_gap / detect_invoice_payment_mismatch
- [ ] 3.3 实现 check_contract_consistency（单合同四维度校验）
- [ ] 3.4 实现 check_all_contracts_consistency（全局汇总报告）
- [ ] 3.5 创建 API 路由：GET/POST /api/v1/finance/consistency-check
- [ ] 3.6 创建 tests/test_consistency.py（12 个测试用例）
- [ ] 3.7 运行全量测试，更新 PROGRESS.md

## 4. 收款逾期预警——后端（簇 C）

- [ ] 4.1 创建 backend/core/overdue_utils.py：实现 get_overdue_milestones
- [ ] 4.2 实现 calculate_customer_risk_level（严格按常量阈值）
- [ ] 4.3 实现 refresh_customer_risk_fields（原子事务）
- [ ] 4.4 实现 get_customer_risk_summary
- [ ] 4.5 创建 API 路由：GET /api/v1/finance/overdue-warnings、GET /api/v1/customers/{id}/risk-summary、POST /refresh
- [ ] 4.6 创建 tests/test_overdue.py（13 个测试用例）
- [ ] 4.7 运行全量测试，更新 PROGRESS.md

## 5. 固定成本登记——后端（簇 D）

- [ ] 5.1 创建 backend/core/fixed_cost_utils.py：实现 validate_fixed_cost_dates / is_cost_active_in_period
- [ ] 5.2 实现 get_monthly_fixed_costs（按零章 0.3 口径，原始金额不摊销）
- [ ] 5.3 实现 get_project_fixed_costs_total
- [ ] 5.4 创建 API 路由：POST/GET/PUT/DELETE /api/v1/fixed-costs、GET /summary、GET /projects/{id}/fixed-costs
- [ ] 5.5 创建 tests/test_fixed_costs.py（15 个测试用例）
- [ ] 5.6 运行全量测试，更新 PROGRESS.md

## 6. 项目粗利润视图——后端（簇 E）

- [ ] 6.1 创建 backend/core/profit_utils.py：实现 get_project_labor_cost（使用 HOURS_PER_DAY 常量）
- [ ] 6.2 实现 calculate_project_profit（含 warnings）
- [ ] 6.3 实现 refresh_project_profit_cache（原子事务写入缓存字段）
- [ ] 6.4 实现 get_profit_overview（优先读缓存）
- [ ] 6.5 创建 API 路由：GET/POST /api/v1/projects/{id}/profit、GET /api/v1/finance/profit-overview
- [ ] 6.6 创建 tests/test_profit.py（17 个测试用例）
- [ ] 6.7 运行全量测试，更新 PROGRESS.md

## 7. 进项发票记录——后端（簇 F）

- [ ] 7.1 创建 backend/core/input_invoice_utils.py：实现 calculate_input_invoice_amount
- [ ] 7.2 实现 get_project_input_invoice_total / get_input_invoice_summary
- [ ] 7.3 创建 API 路由：POST/GET/PUT/DELETE /api/v1/input-invoices、GET /projects/{id}/input-invoices、GET /summary
- [ ] 7.4 创建 tests/test_input_invoices.py（13 个测试用例）
- [ ] 7.5 运行全量测试，更新 PROGRESS.md

## 8. 前端联调（簇 G）

- [ ] 8.1 Finances.vue 新增"数据核查"Tab：差异列表 + 颜色标签 + 立即核查按钮 + 无差异展示
- [ ] 8.2 Finances.vue 新增"固定成本"Tab：CRUD + 月度汇总选择器 + 分类汇总 + 说明文字
- [ ] 8.3 Finances.vue 新增"进项发票"Tab：CRUD + 项目关联 + 日期范围汇总（Tab 标签区分进项/销项）
- [ ] 8.4 项目详情页新增"利润分析"Tab：收入/成本明细/粗利润/毛利率 + warnings 提示 + 刷新按钮
- [ ] 8.5 Dashboard.vue 新增"逾期预警"区块：逾期里程碑列表 + 天数颜色（红/橙/黄）
- [ ] 8.6 Dashboard.vue 新增"项目粗利润"Top 5 列表（读缓存）
- [ ] 8.7 Customers.vue 客户名称旁显示风险标签（warning 黄 / high 红 / normal 不显示）
- [ ] 8.8 验收：一致性校验无差异时展示"数据一致"不白屏 / 风险标签不拦截操作 / 固定成本有说明文字 / 无数据展示 0.00

## 9. 全局重构与验收（簇 H）

- [ ] 9.1 常量集中管理检查：HOURS_PER_DAY 只在 constants.py 定义，无硬编码 8
- [ ] 9.2 函数长度与复杂度检查：所有函数 ≤ 50 行，圈复杂度 < 10
- [ ] 9.3 独立函数可调用性验证：9 个核心函数可独立导入调用
- [ ] 9.4 事务一致性验证：客户风险刷新和利润缓存写入为原子事务
- [ ] 9.5 只读操作验证：一致性校验和逾期检测不产生写操作（测试覆盖）
- [ ] 9.6 日志覆盖验证：关键操作异常有日志记录
- [ ] 9.7 最终全量回归：pytest tests/ -v 要求 0 FAILED
- [ ] 9.8 完成 PROGRESS.md 验收清单并写入"v1.9 执行完成"
