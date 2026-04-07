## 1. 前置检查与常量定义

- [x] 1.1 运行 `pytest tests/ -v --tb=short` 确认 v1.0~v1.3 全量测试通过（0 FAILED）
- [x] 1.2 通过 PRAGMA table_info 确认 finance_records 和 contracts 表的 v1.3 新增字段已存在
- [x] 1.3 确认 logs/ 目录存在且 RotatingFileHandler 配置正确（10MB/文件，保留 30 个）
- [x] 1.4 确认 .env 文件存在且 SECRET_KEY 已配置
- [x] 1.5 在 `backend/core/constants.py` 追加 v1.4 常量：PROFIT_DECIMAL_PLACES、EXPORT_MAX_ROWS_PER_SHEET、EXPORT_DATE_FORMAT
- [x] 1.6 初始化 `PROGRESS.md` 文件（写入簇 A~F 进度表）

## 2. 簇 A：数据库迁移

- [x] 2.1 迁移前快照：记录 finance_records 当前总行数，随机抽取 5 条记录保存 id 及所有字段值
- [x] 2.2 创建迁移脚本 `backend/migrations/v1_4_migrate.py`：ALTER TABLE 新增 related_project_id 列 + CREATE INDEX
- [x] 2.3 执行迁移并验证五项检查（行数一致、抽样数据一致、默认 NULL、索引存在、外键约束）
- [x] 2.4 创建 `tests/test_migration_v14.py`（6 个测试用例）
- [x] 2.5 运行全量测试，确认 0 FAILED，更新 PROGRESS.md 簇 A 为 ✅

## 3. 簇 B：FR-401 项目利润核算——后端

- [x] 3.1 更新 finance_records ORM 模型：添加 related_project_id 字段
- [x] 3.2 更新 POST/PUT/PATCH 财务接口：支持 related_project_id 字段（验证项目存在，可传 null）
- [x] 3.3 创建 `backend/core/profit_utils.py`：实现 calculate_project_income、calculate_project_cost、calculate_project_profit 三个函数
- [x] 3.4 实现 `GET /api/v1/projects/{project_id}/profit` 接口
- [x] 3.5 扩展 `GET /api/v1/projects` 列表接口：追加 profit 和 profit_margin 字段
- [x] 3.6 创建 `tests/test_project_profit.py`（15 个测试用例）
- [x] 3.7 运行全量测试，确认 0 FAILED，更新 PROGRESS.md 簇 B 为 ✅

## 4. 簇 C：FR-402 客户生命周期价值——后端

- [x] 4.1 创建 `backend/core/customer_utils.py`：实现 calculate_customer_lifetime_value 函数
- [x] 4.2 实现 `GET /api/v1/customers/{customer_id}/lifetime-value` 接口
- [x] 4.3 扩展 `GET /api/v1/customers/{customer_id}` 详情接口：追加 lifetime_value 对象
- [x] 4.4 创建 `tests/test_customer_ltv.py`（13 个测试用例）
- [x] 4.5 运行全量测试，确认 0 FAILED，更新 PROGRESS.md 簇 C 为 ✅

## 5. 簇 D：FR-403 数据导出——后端

- [x] 5.1 安装 openpyxl 和 reportlab 依赖，更新 requirements.txt 并注释说明用途
- [x] 5.2 创建 `backend/core/export_utils.py`：实现 generate_excel、generate_pdf、get_export_filename 三个核心函数
- [x] 5.3 实现 generate_excel 的五种导出类型列定义（finance_report 三个 Sheet、customers、projects、contracts、tax_ledger）
- [x] 5.4 实现 generate_pdf：注册中文字体（SimHei/Microsoft YaHei），渲染五种导出类型
- [x] 5.5 实现 `POST /api/v1/export/{export_type}` 接口（参数验证、数据查询、文件生成、错误处理）
- [x] 5.6 创建 `tests/test_export.py`（18 个测试用例）
- [x] 5.7 运行全量测试，确认 0 FAILED，更新 PROGRESS.md 簇 D 为 ✅

## 6. 簇 E：前端联调

- [x] 6.1 项目详情页：新增"利润分析"卡片（收入/成本/利润/利润率，null 显示"—"，负数标红）
- [x] 6.2 项目列表页：新增"利润"和"利润率"两列（支持排序，null 显示"—"，负数标红）
- [x] 6.3 财务收支录入页：支出类型新增"关联项目"下拉（选填），收入类型隐藏
- [x] 6.4 客户详情页：新增"客户价值"面板（六项指标，null 显示"—"）
- [x] 6.5 新增数据导出页面：导出类型下拉、格式单选、时间范围联动（月度/季度）、loading 状态
- [x] 6.6 前端联调测试：验证所有 null 值展示为"—"、接口失败降级、文件下载
- [x] 6.7 运行全量测试，确认 0 FAILED，更新 PROGRESS.md 簇 E 为 ✅

## 7. 簇 F：全局重构

- [x] 7.1 常量集中管理：确认 constants.py 包含 v1.4 常量，代码中无魔术数字
- [x] 7.2 函数长度与复杂度：所有函数 ≤ 50 行，圈复杂度 < 10，超出者拆分
- [x] 7.3 独立函数可调用性验证：profit_utils、customer_utils、export_utils 函数可直接 import
- [x] 7.4 重复逻辑合并：利润接口和列表复用 calculate_project_profit，LTV 接口和详情复用 calculate_customer_lifetime_value
- [x] 7.5 日志覆盖验证：导出失败、generate_excel 异常、generate_pdf 异常、related_project_id 写入异常
- [x] 7.6 PDF 中文字体验证：确认中文渲染无方块、无乱码
- [x] 7.7 最终全量回归：`pytest tests/ -v` 结果 0 FAILED，输出记录到 PROGRESS.md
- [x] 7.8 更新 PROGRESS.md：簇 F 为 ✅，写入"v1.4 执行完成"及时间

## 8. 完成标准验证

- [x] 8.1 确认 PROGRESS.md 簇 A~F 全部 ✅
- [x] 8.2 确认 constants.py 无魔术数字
- [x] 8.3 确认 profit_utils.py、customer_utils.py、export_utils.py 存在且函数可独立调用
- [x] 8.4 确认 PDF 中文渲染正常
- [x] 8.5 确认 logs/ 目录有新日志
- [x] 8.6 确认 requirements.txt 已更新含注释
- [x] 8.7 确认所有接口字段名、错误文案、HTTP 状态码与 PRD 一致
