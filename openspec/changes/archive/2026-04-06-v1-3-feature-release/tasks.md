## 1. 簇 A：数据库迁移

- [x] 1.1 记录 finance_records 和 contracts 表迁移前快照（行数、PRAGMA table_info、抽样 5 条记录）
- [x] 1.2 创建 backend/migrations/v1_3_migrate.py（contracts 新增 2 字段、finance_records 新增 7 字段、3 个索引）
- [x] 1.3 执行迁移并验证 6 项检查（行数一致、抽样数据一致、新字段默认 NULL、索引存在）
- [x] 1.4 创建 tests/test_migration_v13.py（8 个测试用例）
- [x] 1.5 运行全量测试，确认 0 FAILED，更新 PROGRESS.md

## 2. 簇 B：FR-302 外包协作记录

- [x] 2.1 在 backend/models/enums.py 追加 FinanceCategory.OUTSOURCING 和 TaxTreatment 枚举
- [x] 2.2 在 finance_records 创建接口（POST）中添加外包字段条件校验逻辑
- [x] 2.3 在 finance_records 更新接口（PUT/PATCH）中添加外包字段条件校验逻辑（非外包时强制置 NULL）
- [x] 2.4 创建 tests/test_outsource.py（9 个测试用例）
- [x] 2.5 运行全量测试，确认 0 FAILED，更新 PROGRESS.md

## 3. 簇 C：FR-303 发票台账——字段校验 + 税额计算

- [x] 3.1 在 backend/models/enums.py 追加 InvoiceDirection 和 InvoiceType 枚举
- [x] 3.2 创建 backend/core/finance_utils.py，实现 calculate_tax_amount 函数（Decimal + round(x, 2)）
- [x] 3.3 在 finance_records 创建接口中添加发票字段校验逻辑（invoice_no 非空时校验、tax_amount 后端计算）
- [x] 3.4 在 finance_records 更新接口中添加发票字段校验逻辑（清空 invoice_no 时四个字段置 NULL）
- [x] 3.5 Pydantic Schema 中排除 tax_amount 的客户端写入
- [x] 3.6 创建 tests/test_tax_ledger.py（前 8 个测试用例）
- [x] 3.7 运行全量测试，确认 0 FAILED，更新 PROGRESS.md

## 4. 簇 D：FR-303 发票台账——季度统计接口

- [x] 4.1 在 backend/core/finance_utils.py 实现 get_quarter_date_range 函数
- [x] 4.2 在 backend/core/finance_utils.py 实现 calculate_quarterly_tax 函数
- [x] 4.3 创建 GET /api/v1/finance/tax-summary 路由（参数校验、调用核心函数、返回结构）
- [x] 4.4 在 tests/test_tax_ledger.py 追加 11 个季度统计测试用例
- [x] 4.5 运行全量测试，确认 0 FAILED，更新 PROGRESS.md

## 5. 簇 E：FR-301 现金流预测接口

- [x] 5.1 确认 backend/core/constants.py 包含全部约定常量（CASHFLOW_FORECAST_DAYS 等）
- [x] 5.2 创建 backend/core/cashflow_utils.py，实现 get_forecast_weeks 函数（90 天自然周分组）
- [x] 5.3 实现 calculate_weekly_income 函数（合同状态白名单、应收账款计算、按周分配）
- [x] 5.4 实现 calculate_weekly_expense 函数（最近 3 个月历史、月均/周均计算）
- [x] 5.5 创建 GET /api/v1/cashflow/forecast 路由（组装 forecast 数组和 summary）
- [x] 5.6 创建 tests/test_cashflow.py（11 个测试用例）
- [x] 5.7 运行全量测试，确认 0 FAILED，更新 PROGRESS.md

## 6. 簇 F：前端联调

- [x] 6.1 财务录入页——外包字段动态显隐（选外包显示三字段，切其他分类清空值和 payload）
- [x] 6.2 财务录入页——发票字段动态显隐（invoice_no 非空显示三字段，tax_amount 只读展示）
- [x] 6.3 财务录入页——前端表单校验（必填拦截、payload 清理，Network 面板验证）
- [x] 6.4 合同编辑页——expected_payment_date 日期选择器 + payment_stage_note 文本输入
- [x] 6.5 看板页——现金流折线图组件（三条线、X 轴周序号、Y 轴金额、无数据零曲线、错误提示）
- [x] 6.6 财务列表页——发票台账 Tab（筛选有发票号码记录、年份季度筛选、7 列展示）
- [x] 6.7 看板——季度增值税汇总卡片（三数值、无数据显示 0.00、免责提示语）
- [x] 6.8 运行全量测试，确认 0 FAILED，更新 PROGRESS.md

## 7. 簇 G：全局重构

- [x] 7.1 确认 constants.py 包含全部常量，搜索业务代码消除魔术数字
- [x] 7.2 检查所有函数 <= 50 行、圈复杂度 < 10，超出者拆分
- [x] 7.3 验证 6 个核心函数可独立 import 调用（不依赖 FastAPI 启动）
- [x] 7.4 检查日志覆盖（迁移、finance_records 异常、contracts 异常、forecast 异常、tax-summary 异常）
- [x] 7.5 最终全量回归测试，输出写入 PROGRESS.md，标记 v1.3 执行完成
