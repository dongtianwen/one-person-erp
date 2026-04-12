## MODIFIED Requirements

### Requirement: Finance management tabs
财务管理页 SHALL 在现有 Tab 基础上新增"数据核查"、"固定成本"、"进项发票"三个 Tab。

#### Scenario: Data consistency check tab
- **WHEN** 用户切换到"数据核查"Tab
- **THEN** 展示有差异的合同列表（差异类型标签 / 合同号 / 客户 / 差异金额）
- **AND** 差异类型颜色：payment_gap=橙 / invoice_gap=黄 / unlinked_payment=蓝 / mismatch=红
- **AND** 支持"立即核查"按钮
- **AND** 无差异时显示"数据一致，无问题"，不白屏

#### Scenario: Fixed cost management tab
- **WHEN** 用户切换到"固定成本"Tab
- **THEN** 展示固定成本条目列表，支持新增/编辑/删除
- **AND** 月度汇总含 YYYY-MM 选择器和分类汇总
- **AND** 汇总说明文字"以下为当月有效成本条目原始金额，非摊销后金额"

#### Scenario: Input invoice management tab
- **WHEN** 用户切换到"进项发票"Tab
- **THEN** Tab 标签注明"进项（收到的票）"
- **AND** 与"发票台账（开出的票）"区分清晰
- **AND** 支持新增/编辑/删除进项发票

#### Scenario: Project profit analysis tab
- **WHEN** 用户在项目详情页切换到"利润分析"Tab
- **THEN** 展示收入/成本明细/粗利润/毛利率
- **AND** has_complete_data=false 时展示黄色 warnings 提示条
- **AND** 支持"刷新计算"按钮

#### Scenario: Zero amount displays as 0.00
- **WHEN** 金额数据为空或零
- **THEN** 展示 0.00，不白屏不报错
