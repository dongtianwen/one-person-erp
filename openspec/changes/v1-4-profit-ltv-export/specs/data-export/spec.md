## ADDED Requirements

### Requirement: Export API endpoint
系统 SHALL 提供 `POST /api/v1/export/{export_type}` 接口，export_type 枚举严格限定为：finance_report、customers、projects、contracts、tax_ledger。请求体包含 format（xlsx/pdf）、year、month（与 quarter 互斥）、quarter。成功返回 HTTP 200 及文件流。

#### Scenario: Export invalid format returns 422
- **WHEN** 请求 format 非 xlsx 或 pdf
- **THEN** 返回 HTTP 422

#### Scenario: Export invalid export type returns 422
- **WHEN** export_type 不在枚举范围内
- **THEN** 返回 HTTP 422

#### Scenario: Export missing year returns 422
- **WHEN** 请求体缺少 year 参数
- **THEN** 返回 HTTP 422

#### Scenario: Export tax ledger requires quarter not month
- **WHEN** export_type 为 tax_ledger 且使用 month 而非 quarter
- **THEN** 返回验证错误

#### Scenario: Export success returns file
- **WHEN** 请求参数正确
- **THEN** 返回 HTTP 200，Content-Type 对应文件类型
- **AND** Content-Disposition 含正确文件名

### Requirement: Export empty data returns file with headers
数据为空时 SHALL 生成包含表头的空文件，返回 HTTP 200。

#### Scenario: Export finance report empty data returns file with headers
- **WHEN** 选定时间范围内无财务数据
- **THEN** 返回含表头的空 Excel/PDF 文件，HTTP 200

### Requirement: Export failure handling
导出失败时 SHALL 返回 HTTP 500，错误写入 RotatingFileHandler 日志，响应体含友好错误提示。

#### Scenario: Export failure writes to log
- **WHEN** 导出过程中发生异常
- **THEN** 错误信息写入日志文件
- **AND** 返回 HTTP 500 含友好提示

### Requirement: Finance report export columns
月度财务报表导出 SHALL 包含三个 Sheet：收支明细（日期/类型/分类/金额/资金来源/关联合同/发票号码/状态/备注）、分类汇总（分类/收入合计/支出合计/净额）、资金来源汇总（资金来源/支出合计/未结清笔数/未结清金额）。

#### Scenario: Export finance report xlsx success
- **WHEN** 导出月度财务报表为 Excel
- **THEN** 文件包含三个 Sheet，列定义与规范一致

#### Scenario: Export finance report pdf success
- **WHEN** 导出月度财务报表为 PDF
- **THEN** PDF 包含三段数据，列定义与规范一致

### Requirement: Customer export columns
客户列表导出 SHALL 包含列：客户名称/联系人/电话/公司名称/状态/来源渠道/合作项目数/历史合同总额/历史实收金额/首次合作日期/最近合作日期/创建日期。

#### Scenario: Export customers xlsx columns match spec
- **WHEN** 导出客户列表为 Excel
- **THEN** 列定义与规范完全一致

### Requirement: Project export includes profit columns
项目列表导出 SHALL 包含列：项目名称/关联客户/项目状态/预算金额/项目收入/项目成本/项目利润/利润率(%)/开始日期/结束日期/进度(%)。

#### Scenario: Export projects xlsx includes profit columns
- **WHEN** 导出项目列表
- **THEN** 包含项目收入、成本、利润、利润率列

### Requirement: Contract export includes receivable
合同列表导出 SHALL 包含列：合同编号/合同标题/关联客户/关联项目/合同金额/已收金额/应收账款/合同状态/签署日期/生效日期/到期日期。

#### Scenario: Export contracts xlsx includes receivable
- **WHEN** 导出合同列表
- **THEN** 包含已收金额和应收账款列

### Requirement: Tax ledger export with summary row
增值税发票台账导出 SHALL 包含列：日期/发票号码/发票方向(销项/进项)/发票类型/金额/税率/税额/关联合同/备注。底部包含汇总行：销项税合计/进项税合计（仅专用发票）/应纳税额。

#### Scenario: Export tax ledger xlsx includes summary row
- **WHEN** 导出增值税台账
- **THEN** 底部包含销项税合计、进项税合计（仅专用发票）、应纳税额汇总行

### Requirement: Export filename format
导出文件名 SHALL 格式为 `{模块名}_{年份}_{月份或季度}.{扩展名}`。月度类型使用月份，增值税台账使用 Q1/Q2/Q3/Q4 格式。

#### Scenario: Export filename monthly format
- **WHEN** 导出 2026 年 4 月财务报表为 Excel
- **THEN** 文件名为 finance_report_2026_04.xlsx

#### Scenario: Export filename quarterly format
- **WHEN** 导出 2026 年 Q1 增值税台账为 PDF
- **THEN** 文件名为 tax_ledger_2026_Q1.pdf

### Requirement: Export core functions are independently callable
`generate_excel`、`generate_pdf`、`get_export_filename` 三个核心函数 SHALL 在 `backend/core/export_utils.py` 中定义，可在测试中直接 import 调用，不依赖 FastAPI 应用启动。

#### Scenario: Generate excel empty data returns bytes with headers
- **WHEN** 调用 generate_excel 且数据为空
- **THEN** 返回非空 bytes，包含表头但无数据行

#### Scenario: Get export filename monthly
- **WHEN** 调用 get_export_filename("finance_report", "xlsx", 2026, month=4)
- **THEN** 返回 "finance_report_2026_04.xlsx"

#### Scenario: Get export filename quarterly
- **WHEN** 调用 get_export_filename("tax_ledger", "pdf", 2026, quarter=1)
- **THEN** 返回 "tax_ledger_2026_Q1.pdf"

### Requirement: Excel Chinese content readable
Excel 导出文件中的中文内容 SHALL 可被正确读取，不得出现乱码。

#### Scenario: Export excel Chinese content readable
- **WHEN** 导出包含中文数据的 Excel 文件
- **THEN** 用 openpyxl 读取后中文内容正确无误

### Requirement: PDF Chinese content no tofu
PDF 导出中的中文内容 SHALL 正确渲染，不得显示方块（tofu）或乱码。

#### Scenario: Export PDF Chinese content no tofu
- **WHEN** 导出包含中文数据的 PDF 文件
- **THEN** 中文字符正确显示，无方块或乱码

### Requirement: Data export page in frontend
前端 SHALL 新增数据导出页面，包含导出类型下拉、导出格式单选、时间范围选择（月度类型显示年份+月份，增值税台账显示年份+季度）、导出按钮。点击导出显示 loading，成功后浏览器自动下载，失败显示错误提示。

#### Scenario: Tax ledger shows quarter selector
- **WHEN** 选择增值税台账导出类型
- **THEN** 时间范围切换为年份+季度选择，月份选择消失

#### Scenario: Other types show month selector
- **WHEN** 选择非增值税台账的导出类型
- **THEN** 时间范围显示年份+月份选择，季度选择消失

#### Scenario: Export shows loading state
- **WHEN** 点击导出按钮
- **THEN** 出现 loading 状态

#### Scenario: Export success triggers download
- **WHEN** 导出成功
- **THEN** 浏览器触发文件下载，文件名符合命名规范

#### Scenario: Export failure shows error
- **WHEN** 导出失败
- **THEN** 显示"导出失败，请重试"，不下载文件

#### Scenario: Export request is POST with JSON content type
- **WHEN** Network 面板观察导出请求
- **THEN** 请求方法为 POST，Content-Type 为 application/json
