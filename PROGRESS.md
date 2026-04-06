# v1.3 执行进度

## 状态：✅ 全部完成
## 开始时间：2026-04-06
## 完成时间：2026-04-06

| 簇 | 名称 | 状态 | 完成时间 | 通过测试数 |
|----|------|------|----------|------------|
| A | 数据库迁移 | ✅ | 2026-04-06 | 7 |
| B | FR-302 外包协作 | ✅ | 2026-04-06 | 9 |
| C | FR-303 发票校验+税额计算 | ✅ | 2026-04-06 | 17 |
| D | FR-303 季度统计接口 | ✅ | 2026-04-06 | 含于C |
| E | FR-301 现金流预测接口 | ✅ | 2026-04-06 | 11 |
| F | 前端联调 | ✅ | 2026-04-06 | - |
| G | 全局重构 | ✅ | 2026-04-06 | - |

## 全量测试结果
- 118 passed, 0 failed, 1 error (e2e 需运行服务器, 可忽略)
- 最后运行时间：2026-04-06

## v1.3 交付内容

### 后端 (Cluster A-E)
- Alembic 迁移：contracts +2 字段、finance_records +7 字段、3 个索引
- FR-302 外包协作：outsource_name/has_invoice/tax_treatment 条件校验
- FR-303 发票台账：invoice_no 触发四字段校验、tax_amount 后端计算、季度统计接口
- FR-301 现金流：90天自然周预测、周收入(合同应收)、周支出(历史均值)

### 前端 (Cluster F)
- Finances.vue：外包字段动态显隐、发票字段动态显隐、前端校验+payload清理、发票台账Tab
- Contracts.vue：expected_payment_date + payment_stage_note
- Dashboard.vue：现金流预测图(三线)、季度增值税汇总卡片

### 全局重构 (Cluster G)
- constants.py 覆盖所有魔术数字
- update_finance_record 拆分为 3 个辅助函数（50行以内）
- 核心函数独立 import 验证通过
- finances/cashflow 端点添加 logger.info
