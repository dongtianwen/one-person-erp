## Why

v1.0 已完成客户/项目/合同/财务等业务核心模块，v1.1 补齐了合规留痕能力。但当前缺少从客户报价到签约的完整业务链路（客户→报价→合同），也无法管理为客户托管的服务器、域名等资产。同时，v1.1 的提醒和报价逾期依赖定时任务，不适合本地单机夜间关机的使用场景，需要改为事件驱动机制。此外，NFR-LOG 要求的本地容错日志和备份验证能力尚未落地。

## What Changes

- **新增报价单模块**：创建/编辑/列表/筛选报价单，支持"一键转合同"，报价单编号自动生成（BJ-YYYYMMDD-序号）
- **新增客户资产子模块**：在客户详情页新增"资产与托管记录"Tab，记录服务器/域名/SSL证书/小程序/APP等托管资产，到期前 30 天自动生成提醒
- **事件驱动逾期检查**：废弃定时任务，改为服务启动时全量检查 + 仪表盘接口调用时限流检查（90天窗口/1000条上限）
- **本地容错日志系统**：RotatingFileHandler，logs/目录，10MB/文件，保留30个，强制记录数据库写入异常/文件IO异常/事件驱动执行记录/系统启停
- **备份可恢复验证**：将备份文件加载为临时数据库校验完整性，展示备份历史列表及校验状态

## Capabilities

### New Capabilities

- `quotation`: 报价单全生命周期管理（CRUD、状态流转、自动编号、一键转合同、过期处理）
- `customer-assets`: 客户资产托管记录管理（CRUD、到期提醒联动、嵌入客户详情页）
- `event-driven-checks`: 事件驱动逾期检查引擎（服务启动全量检查 + 仪表盘接口触发限流检查，覆盖提醒/报价单/资产/文件索引四类检查对象）
- `local-logging`: 本地容错日志系统（RotatingFileHandler、结构化格式、敏感信息过滤）
- `backup-verification`: 备份文件完整性校验（临时数据库加载、核心表记录数对比、校验历史管理）

### Modified Capabilities

- `dashboard`: 新增"报价转化率"指标和报价相关看板数据；仪表盘接口集成事件驱动逾期检查触发点B
- `customer-management`: 客户详情页新增"资产与托管记录"Tab，嵌入 customer-assets 子模块

## Impact

- **后端**：新增 2 个数据模型（quotations、customer_assets）及对应 CRUD/API/Schema；新增事件驱动检查服务和日志中间件；修改仪表盘接口
- **前端**：新增报价单管理页面；修改客户详情页新增资产 Tab；修改仪表盘新增报价转化率指标；新增备份验证 UI
- **数据库**：新建 quotations 表（索引：status, expiry_date）、customer_assets 表（索引：expiry_date, customer_id）；Alembic 迁移脚本
- **依赖**：无新增外部依赖（RotatingFileHandler 为 Python 标准库）
