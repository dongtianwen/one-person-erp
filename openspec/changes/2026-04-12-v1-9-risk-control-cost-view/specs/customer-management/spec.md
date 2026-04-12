## MODIFIED Requirements

### Requirement: Customer data model
客户数据模型 SHALL 包含 overdue_milestone_count（INTEGER，默认 0）、overdue_amount（DECIMAL(12,2)，默认 0）、risk_level（VARCHAR(20)，默认 normal，白名单：normal/warning/high）字段，用于风险展示。risk_level SHALL 不参与任何业务接口校验，仅影响看板展示颜色和预警列表。

#### Scenario: Customer risk fields default values
- **WHEN** 创建新客户
- **THEN** overdue_milestone_count=0, overdue_amount=0, risk_level='normal'

#### Scenario: Risk level display on customer list
- **WHEN** 客户 risk_level = warning
- **THEN** 客户列表页名称旁显示黄色警告标签

#### Scenario: Risk level does not disable operations
- **WHEN** 客户 risk_level = high
- **THEN** 所有操作按钮保持可用，不拦截任何提交
