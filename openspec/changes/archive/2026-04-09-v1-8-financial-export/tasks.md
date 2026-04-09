# v1.8 财务对接模块 — 实施任务清单

## 0. 前置检查

- [x] 0.1 运行全量测试确认 v1.0-v1.7 通过 (`pytest tests/ -v --tb=short`)
- [x] 0.2 确认数据库表存在 (通过 PRAGMA table_info 验证)
- [x] 0.3 确认 logs/ 目录存在且配置正确
- [x] 0.4 确认 .env 文件存在且 SECRET_KEY 已配置
- [x] 0.5 创建 PROGRESS.md 记录执行进度

## 1. 数据库迁移 (Cluster A)

- [x] 1.1 迁移前记录快照 (finance_records 行数、字段、抽样记录)
- [x] 1.2 创建迁移脚本 `backend/migrations/v1_8_migrate.py`
- [x] 1.3 创建 `invoices` 表 (发票台账表)
- [x] 1.4 创建 `export_batches` 表 (导出批次记录表)
- [x] 1.5 扩展 `finance_records` 表 (invoice_id, accounting_period, export_batch_id, reconciliation_status)
- [x] 1.6 创建所有索引 (invoices, finance_records, export_batches)
- [x] 1.7 迁移后验证 (表存在、字段存在、索引存在、原数据未变)
- [x] 1.8 创建测试文件 `tests/test_migration_v18.py`
- [x] 1.9 运行迁移测试, 要求 0 FAILED (23 passed)

## 2. 常量定义 (前置任务)

- [x] 2.1 追加常量到 `backend/core/constants.py` (发票管理常量、导出格式常量)
- [x] 2.2 新增枚举到 `backend/models/enums.py` (InvoiceType, InvoiceStatus, ReconciliationStatus)

## 3. 发票台账管理——后端 (Cluster B)

- [x] 3.1 创建 `backend/crud/invoice_utils.py` 核心工具函数
- [x] 3.2 实现 `generate_invoice_no` (发票编号生成, 原子事务)
- [x] 3.3 实现 `calculate_invoice_amount` (税额和价税合计计算)
- [x] 3.4 实现 `validate_invoice_amount` (累计金额校验)
- [x] 3.5 实现 `get_contract_invoiced_amount` (获取合同已开票总额)
- [x] 3.6 实现 `validate_invoice_transition` (状态流转校验)
- [x] 3.7 实现 `get_invoice_summary` (发票汇总统计)
- [x] 3.8 实现 `POST /api/v1/invoices` (创建发票)
- [x] 3.9 实现 `GET /api/v1/invoices` (发票列表, 分页和筛选)
- [x] 3.10 实现 `GET /api/v1/invoices/{invoice_id}` (发票详情)
- [x] 3.11 实现 `PUT /api/v1/invoices/{invoice_id}` (更新发票)
- [x] 3.12 实现 `PATCH /api/v1/invoices/{invoice_id}` (部分更新发票)
- [x] 3.13 实现 `DELETE /api/v1/invoices/{invoice_id}` (删除发票)
- [x] 3.14 实现 `POST /api/v1/invoices/{invoice_id}/issue` (开具发票)
- [x] 3.15 实现 `POST /api/v1/invoices/{invoice_id}/receive` (确认收票)
- [x] 3.16 实现 `POST /api/v1/invoices/{invoice_id}/verify` (核销发票)
- [x] 3.17 实现 `POST /api/v1/invoices/{invoice_id}/cancel` (作废发票)
- [x] 3.18 实现 `GET /api/v1/contracts/{contract_id}/invoices` (合同关联票列表)
- [x] 3.19 实现 `GET /api/v1/invoices/summary` (发票汇总统计)
- [x] 3.20 创建测试文件 `tests/test_invoices.py`
- [x] 3.21 运行发票测试, 要求 0 FAILED (25 passed)

## 4. 财务数据导出——后端 (Cluster C)

- [x] 4.1 创建 `exports/` 目录
- [x] 4.2 添加依赖 `openpyxl` 用于 Excel 导出
- [x] 4.3 创建 `backend/core/export_utils.py` 核心工具函数
- [x] 4.4 实现 `generate_export_batch_id` (批次 ID 生成)
- [x] 4.5 实现 `calculate_accounting_period` (会计期间计算)
- [x] 4.6 实现 `map_to_finance_format` (格式映射, generic 实现)
- [x] 4.7 实现 `save_export_file` (保存 Excel 文件)
- [x] 4.8 实现 `mark_records_as_exported` (标记已导出记录)
- [x] 4.9 实现 `export_to_excel` (统一导出入口, 原子事务)
- [x] 4.10 实现 `POST /api/v1/finance/export` (创建导出批次)
- [x] 4.11 实现 `GET /api/v1/finance/export/batches` (导出批次列表)
- [x] 4.12 实现 `GET /api/v1/finance/export/batches/{batch_id}` (批次详情)
- [x] 4.13 实现 `GET /api/v1/finance/export/download/{batch_id}` (下载导出文件)
- [x] 4.14 创建测试文件 `tests/test_finance_export.py`
- [x] 4.15 运行导出测试, 要求 0 FAILED (20 passed)

## 5. 会计期间对账——后端 (Cluster D)

- [x] 5.1 创建 `backend/core/reconciliation_utils.py` 核心工具函数
- [x] 5.2 实现 `get_period_date_range` (期间日期范围)
- [x] 5.3 实现 `get_opening_balance` (期初余额计算)
- [x] 5.4 实现 `get_current_period_activity` (本期活动统计)
- [x] 5.5 实现 `get_closing_balance` (期末余额计算)
- [x] 5.6 实现 `get_customer_breakdown` (客户维度分解)
- [x] 5.7 实现 `get_unreconciled_records` (未对账记录识别)
- [x] 5.8 实现 `generate_reconciliation_report` (完整对账报表)
- [x] 5.9 实现 `sync_reconciliation_status` (对账状态同步, 原子事务)
- [x] 5.10 实现 `GET /api/v1/finance/reconciliation` (对账期间列表)
- [x] 5.11 实现 `GET /api/v1/finance/reconciliation/{accounting_period}` (对账报表)
- [x] 5.12 实现 `POST /api/v1/finance/reconciliation/sync` (同步对账状态)
- [x] 5.13 创建测试文件 `tests/test_reconciliation.py`
- [x] 5.14 运行对账测试, 要求 0 FAILED (10 passed)

## 6. 前端联调 (Cluster E)

- [x] 6.1 合同详情页新增"发票"Tab
- [x] 6.2 发票列表展示 (状态颜色区分)
- [x] 6.3 新建发票表单 (含已开票进度条)
- [x] 6.4 发票金额超限前端校验
- [x] 6.5 verified/cancelled 发票隐藏编辑/删除按钮
- [x] 6.6 财务管理页新增"数据导出"区块
- [x] 6.7 导出选项表单 (导出类型、时间范围、目标格式)
- [x] 6.8 导出格式选择器 (generic 可选, 其他禁用显示"即将支持")
- [x] 6.9 导出历史列表
- [x] 6.10 财务管理页新增"对账报表"Tab
- [x] 6.11 会计期间选择器 (只展示有数据的期间)
- [x] 6.12 对账报表展示 (期初/本期/期末余额卡片)
- [x] 6.13 客户分解表格
- [x] 6.14 未对账记录列表
- [x] 6.15 同步对账状态按钮
- [x] 6.16 首页新增财务指标卡片 (本月开票/收款/应收/未开票)
- [x] 6.17 所有金额无数据时展示 0.00
- [x] 6.18 运行前端测试, 要求 0 FAILED

## 7. 全局重构 (Cluster F)

- [x] 7.1 验证常量集中管理 (无魔术数字)
- [x] 7.2 函数长度检查 (所有函数 ≤ 50 行)
- [x] 7.3 圈复杂度检查 (所有函数 < 10)
- [x] 7.4 独立函数可调用性验证
- [x] 7.5 事务一致性验证 (发票创建、状态流转、导出批次、对账同步)
- [x] 7.6 日志覆盖验证 (关键业务路径)
- [x] 7.7 最终全量回归测试 (`pytest tests/ -v --tb=short`)
- [x] 7.8 更新 PROGRESS.md 记录完成状态

## 8. 完成验证

- [x] 8.1 簇 A-F 全部状态为 ✅
- [x] 8.2 全量测试 0 FAILED
- [x] 8.3 常量已追加到 constants.py
- [x] 8.4 EXPORT_FORMAT_SUPPORTED 只含 generic
- [x] 8.5 发票编号唯一且格式正确
- [x] 8.6 发票累计金额不超合同金额
- [x] 8.7 verified/cancelled 发票不可删除
- [x] 8.8 导出批次可追溯
- [x] 8.9 对账第一期期初余额为 0
- [x] 8.10 cancelled 发票不计入本期开票统计
- [x] 8.11 invoices.status 与 reconciliation_status 独立流转
- [x] 8.12 exports/ 目录存在且有导出文件
- [x] 8.13 logs/ 目录本次执行产生了日志文件
- [x] 8.14 所有接口字段名、错误文案、HTTP 状态码与 PRD 一致
