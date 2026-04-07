## MODIFIED Requirements

### Requirement: Project retrieval
系统 SHALL 支持查询项目信息。项目详情接口返回中 SHALL 包含利润相关数据。

#### Scenario: Get project by ID
- GIVEN 项目存在
- WHEN 用户请求项目详情
- THEN 系统返回完整项目信息
- AND 包含关联任务列表
- AND 包含里程碑列表
- AND 包含关联客户信息

#### Scenario: List projects with filtering
- GIVEN 系统中存在多个项目
- WHEN 用户请求项目列表
- THEN 系统返回分页结果
- AND 支持按状态/客户/时间筛选
- AND 默认按创建时间倒序
- AND 每条记录追加 profit（Decimal）和 profit_margin（Decimal | null）字段
- AND profit 和 profit_margin 为实时计算，非数据库存储

## ADDED Requirements

### Requirement: Project profit endpoint
系统 SHALL 提供 `GET /api/v1/projects/{project_id}/profit` 独立接口，返回项目利润核算结果。

#### Scenario: Profit endpoint returns full profit data
- **WHEN** 请求有效项目的利润接口
- **THEN** 返回 project_id、project_name、income、cost、profit、profit_margin、currency

#### Scenario: Profit endpoint returns 404 for missing project
- **WHEN** 请求不存在项目的利润接口
- **THEN** 返回 HTTP 404
