# v1.8 财务对接模块 — 技术设计

## Context

当前系统已有 `finance_records` 表存储收款记录，但发票相关字段（`invoice_no`, `invoice_direction` 等）作为该表的扩展字段存在，无法支持发票的完整生命周期管理。

代理记账会计需要以下数据：
1. 本期签订的合同列表
2. 本期收到的款项（关联合同和发票）
3. 本期开具的发票（销项）
4. 按会计期间汇总的对账报表

当前系统无法提供以上数据的标准化导出。

### 约束

- SQLite 数据库（不支持某些高级 SQL 特性）
- FastAPI 后端 + Streamlit 前端
- 代理记账公司使用金蝶/用友/畅捷通等财务软件

## Goals / Non-Goals

**Goals:**
1. 建立独立的发票台账表，支持发票完整生命周期
2. 提供通用格式（Excel/CSV）的财务数据导出
3. 实现按自然月的会计期间对账报表
4. 支持导出批次追溯

**Non-Goals:**
1. 不实现会计科目体系
2. 不生成记账凭证
3. 不对接税务局接口
4. 金蝶/用友/畅捷通专属格式仅预留常量，本版本不实现

## Decisions

### 1. 独立发票表 vs 扩展 finance_records

**决策：** 创建独立的 `invoices` 表

**理由：**
- 发票有独立的状态流转（draft → issued → received → verified/cancelled）
- 一张合同可对应多张发票（分批开票）
- 需要独立的时间戳字段追踪发票流转（issued_at, received_at, verified_at）
- 扩展 `finance_records` 会导致表职责不清

### 2. 发票编号格式

**决策：** `INV-YYYYMMDD-序号`（当日从 001 起）

**理由：**
- 包含日期便于人工查找
- 当日序号便于统计每日开票量
- 避免全局序号带来的并发问题

**实现：** 使用数据库事务保证原子性，查询当日最大序号后 +1

### 3. 会计期间计算方式

**决策：** 按交易日期所属自然月自动计算

**理由：**
- 与会计准则一致
- 无需人工指定期间，减少错误
- 便于按月统计和报表生成

### 4. 导出格式策略

**决策：** 本版本只实现 `generic` 格式（Excel/CSV），其他格式抛出 `NotImplementedError`

**理由：**
- 金蝶/用友/畅捷通需要客户的账套配置（科目代码、凭证字等）
- 本系统无会计科目体系，无法硬编码映射关系
- 通用格式可由代理记账会计二次加工

**扩展路径：** 后续版本可要求客户提供账套模板，按需实现

### 5. 累计金额校验时机

**决策：** 在创建和更新时校验，`cancelled` 状态不计入累计

**理由：**
- 防止超合同金额开票
- 作废发票不应影响累计金额
- 允许更新发票金额（需重新校验）

### 6. 对账状态 vs 发票状态

**决策：** `invoices.status` 和 `finance_records.reconciliation_status` 独立管理

**理由：**
- 发票核销是发票生命周期的一部分
- 对账确认是财务会计确认行为
- 两者业务含义不同，不应互相驱动

## 数据模型

### invoices 表

```sql
CREATE TABLE invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_no VARCHAR(30) NOT NULL UNIQUE,        -- INV-20240115-001
    contract_id INTEGER NOT NULL REFERENCES contracts(id) ON DELETE RESTRICT,
    invoice_type VARCHAR(20) NOT NULL DEFAULT 'standard',  -- standard/ordinary/electronic/small_scale
    invoice_date DATE NOT NULL,
    amount_excluding_tax DECIMAL(12,2) NOT NULL,
    tax_rate DECIMAL(5,4) NOT NULL DEFAULT 0.13,
    tax_amount DECIMAL(12,2) NOT NULL DEFAULT 0,
    total_amount DECIMAL(12,2) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',  -- draft/issued/received/verified/cancelled
    issued_at TIMESTAMP NULL,
    received_at TIMESTAMP NULL,
    received_by VARCHAR(100) NULL,
    verified_at TIMESTAMP NULL,
    notes TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### export_batches 表

```sql
CREATE TABLE export_batches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id VARCHAR(50) NOT NULL UNIQUE,         -- EXP-20240115-143052-ABC123
    export_type VARCHAR(30) NOT NULL,             -- contracts/payments/invoices
    target_format VARCHAR(20) NOT NULL DEFAULT 'generic',
    accounting_period VARCHAR(7) NULL,            -- YYYY-MM
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    record_count INTEGER NOT NULL DEFAULT 0,
    file_path TEXT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### finance_records 表扩展

```sql
ALTER TABLE finance_records ADD COLUMN invoice_id INTEGER NULL REFERENCES invoices(id) ON DELETE SET NULL;
ALTER TABLE finance_records ADD COLUMN accounting_period VARCHAR(7) NULL;
ALTER TABLE finance_records ADD COLUMN export_batch_id VARCHAR(50) NULL;
ALTER TABLE finance_records ADD COLUMN reconciliation_status VARCHAR(20) NOT NULL DEFAULT 'pending';
```

## 核心函数签名

### 发票管理 (`backend/core/invoice_utils.py`)

```python
def generate_invoice_no(db) -> str:
    """格式：INV-YYYYMMDD-序号，原子事务"""

def calculate_invoice_amount(amount_excluding_tax: Decimal, tax_rate: Decimal) -> dict:
    """返回 {tax_amount, total_amount}"""

def validate_invoice_amount(db, contract_id: int, new_amount: Decimal, exclude_invoice_id: int = None) -> bool:
    """校验累计金额是否超合同金额"""

def get_contract_invoiced_amount(db, contract_id: int, exclude_invoice_id: int = None) -> Decimal:
    """获取合同已开票总额（排除 cancelled）"""

def validate_invoice_transition(current: str, target: str) -> bool:
    """校验状态流转是否合法"""

def get_invoice_summary(db, start_date: str = None, end_date: str = None) -> dict:
    """按状态统计发票数量和金额"""
```

### 导出管理 (`backend/core/export_utils.py`)

```python
def generate_export_batch_id() -> str:
    """格式：EXP-YYYYMMDD-HHMMSS-随机6位"""

def calculate_accounting_period(d: date) -> str:
    """返回 YYYY-MM 格式"""

def export_to_excel(db, export_type: str, filters: dict, target_format: str) -> dict:
    """统一导出入口，返回 {batch_id, file_path, record_count}"""

def map_to_finance_format(data: list, target_format: str, export_type: str) -> list:
    """generic 实现，其他抛出 NotImplementedError"""

def save_export_file(batch_id: str, export_type: str, target_format: str, data: list) -> str:
    """保存 xlsx 文件到 exports/"""

def mark_records_as_exported(db, record_ids: list, batch_id: str, accounting_period: str) -> None:
    """更新已导出 finance_records"""
```

### 对账管理 (`backend/core/reconciliation_utils.py`)

```python
def get_period_date_range(accounting_period: str) -> tuple:
    """返回 (period_start: date, period_end: date)"""

def get_opening_balance(db, accounting_period: str) -> dict:
    """期初余额；第一期返回全零"""

def get_current_period_activity(db, accounting_period: str) -> dict:
    """统计本期合同、开票（排除cancelled）、收款数据"""

def get_closing_balance(db, accounting_period: str) -> dict:
    """期末余额 = 期初 + 本期合同 - 本期收款"""

def get_customer_breakdown(db, accounting_period: str) -> list:
    """按客户分解本期活动"""

def get_unreconciled_records(db, accounting_period: str) -> list:
    """返回 contract_id IS NULL 的收款记录"""

def generate_reconciliation_report(db, accounting_period: str) -> dict:
    """生成完整对账报表"""

def sync_reconciliation_status(db, accounting_period: str) -> int:
    """批量更新 reconciliation_status，返回更新记录数"""
```

## 迁移计划

### 阶段 1：数据库迁移

1. 创建 `invoices` 表
2. 创建 `export_batches` 表
3. 扩展 `finance_records` 表（检查字段是否存在）
4. 创建所有索引
5. 运行迁移验证测试

### 阶段 2：后端实现

1. 添加枚举类型（InvoiceType, InvoiceStatus, ReconciliationStatus）
2. 实现核心工具函数
3. 实现发票 CRUD 接口
4. 实现导出接口
5. 实现对账接口
6. 编写单元测试

### 阶段 3：前端实现

1. 合同详情页新增发票 Tab
2. 财务管理页新增导出区块
3. 财务管理页新增对账报表 Tab
4. 首页新增财务指标卡片

### 回滚策略

- 数据库迁移：保留原始表结构，新字段/表可独立删除
- 代码变更：Git revert 至 v1.7 tag

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| SQLite 并发写入冲突 | 发票编号生成使用事务隔离级别 |
| 导出大文件内存溢出 | 分批写入，限制单次导出记录数 |
| 会计期间跨期计算错误 | 单元测试覆盖边界情况（月末、季末、年末） |
| 累计金额校验遗漏 | 测试覆盖并发创建、更新、作废场景 |
| 与代理记账格式不匹配 | 提供 Excel 模板，允许会计二次加工 |

## Open Questions

1. **问题：** 单次导出的记录数上限是多少？
   - **建议：** 暂不限制，后续根据实际使用情况优化

2. **问题：** 导出文件保留多久？
   - **建议：** 永久保留，磁盘空间不足时手动清理

3. **问题：** 是否需要导出格式配置化？
   - **建议：** 本版本硬编码通用格式，后续版本考虑配置化
