# v1.8 财务对接模块 — 变更提案

## Why

当前系统已支持项目、合同、收款等核心业务，但缺少与专业财务软件（金蝶/用友/畅捷通）对接的能力。代理记账会计需要每月手动从系统提取数据，效率低下且易出错。

本版本新增**销项发票台账管理**、**财务数据通用格式导出**、**会计期间对账报表**三大能力，实现业务数据到财务软件的标准化输出。

## What Changes

### 新增能力

1. **独立发票台账表** - 区别于现有 `invoice-ledger` 规范（该规范仅定义 `finance_records` 表上的发票字段）
   - 新建 `invoices` 表，支持发票完整生命周期（草稿/开具/已收/已核销/作废）
   - 发票编号自动生成（INV-YYYYMMDD-序号）
   - 发票必须关联合同，累计金额校验（不超合同金额）
   - 税额自动计算（不含税金额 × 税率）

2. **财务数据导出**（通用 Excel/CSV 格式）
   - 导出类型：合同、收款、发票
   - 导出批次追溯：记录每次导出的时间范围、记录数、文件路径
   - 会计期间自动计算（YYYY-MM）
   - 本版本只实现 `generic` 格式，金蝶/用友/畅捷通格式预留常量但暂不实现

3. **会计期间对账**
   - 按自然月统计：期初余额、本期合同/开票/收款、期末余额
   - 客户维度分解
   - 未对账记录识别（无合同关联的收款）
   - 对账状态同步（pending → matched → verified）

### 数据库变更

- 新增 `invoices` 表（发票台账）
- 新增 `export_batches` 表（导出批次记录）
- `finance_records` 表新增字段：`invoice_id`, `accounting_period`, `export_batch_id`, `reconciliation_status`
- 新增索引以支持高效查询

### 前端变更

- 合同详情页新增"发票"Tab
- 财务管理页新增"数据导出"区块
- 财务管理页新增"对账报表"Tab
- 首页新增财务指标卡片

## Capabilities

### New Capabilities

- `invoice-management`: 独立发票台账管理，发票编号生成、金额校验、状态流转
- `finance-export`: 财务数据导出，支持合同/收款/发票三种类型，批次追溯
- `accounting-reconciliation`: 会计期间对账报表，支持客户维度分解和未对账记录识别

### Modified Capabilities

- `finance-management`: 新增 `invoice_id`, `accounting_period`, `export_batch_id`, `reconciliation_status` 字段支持

## Impact

### API 变更

新增接口：
- `POST /api/v1/invoices` - 创建发票
- `GET /api/v1/invoices` - 发票列表
- `GET /api/v1/invoices/{invoice_id}` - 发票详情
- `PUT /api/v1/invoices/{invoice_id}` - 更新发票
- `PATCH /api/v1/invoices/{invoice_id}` - 部分更新发票
- `DELETE /api/v1/invoices/{invoice_id}` - 删除发票
- `POST /api/v1/invoices/{invoice_id}/issue` - 开具发票
- `POST /api/v1/invoices/{invoice_id}/receive` - 确认收票
- `POST /api/v1/invoices/{invoice_id}/verify` - 核销发票
- `POST /api/v1/invoices/{invoice_id}/cancel` - 作废发票
- `GET /api/v1/contracts/{contract_id}/invoices` - 合关联票列表
- `GET /api/v1/invoices/summary` - 发票汇总统计
- `POST /api/v1/finance/export` - 创建导出批次
- `GET /api/v1/finance/export/batches` - 导出批次列表
- `GET /api/v1/finance/export/batches/{batch_id}` - 批次详情
- `GET /api/v1/finance/export/download/{batch_id}` - 下载导出文件
- `GET /api/v1/finance/reconciliation` - 对账期间列表
- `GET /api/v1/finance/reconciliation/{accounting_period}` - 对账报表
- `POST /api/v1/finance/reconciliation/sync` - 同步对账状态

### 数据库迁移

- 迁移脚本需检查字段是否存在（SQLite 不支持 `ADD COLUMN IF NOT EXISTS`）
- 迁移前后需记录快照以验证数据完整性

### 依赖变更

- 新增 `openpyxl` 库用于 Excel 导出

## 边界与约束

### 本版本不包含

- 完整记账凭证系统
- 会计科目体系
- 税务申报接口
- 银行流水自动对账
- 固定资产管理
- 进项发票认证、抵扣
- 总账/明细账/凭证链
- 金蝶/用友/畅捷通专属导出格式（仅预留常量）

### 核心规则

1. 发票必须关联已存在的合同（不允许孤立发票）
2. 同一合同下 `status != cancelled` 的发票累计金额不得超合同金额
3. `invoices.status` 与 `finance_records.reconciliation_status` 独立流转，不互相驱动
4. 会计期间按自然月界定（YYYY-MM）
5. 导出格式本版本只支持 `generic`，其他格式抛出 `NotImplementedError`
