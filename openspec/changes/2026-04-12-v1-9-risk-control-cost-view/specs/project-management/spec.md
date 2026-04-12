## MODIFIED Requirements

### Requirement: Project data model
项目数据模型 SHALL 包含粗利润缓存字段：cached_revenue（DECIMAL(12,2) NULL）、cached_labor_cost（DECIMAL(12,2) NULL）、cached_fixed_cost（DECIMAL(12,2) NULL）、cached_input_cost（DECIMAL(12,2) NULL）、cached_gross_profit（DECIMAL(12,2) NULL）、cached_gross_margin（DECIMAL(8,4) NULL）、profit_cache_updated_at（TIMESTAMP NULL）。缓存字段初始值为 NULL，通过 POST /api/v1/projects/{id}/profit/refresh 更新。

#### Scenario: Cache fields initially null
- **WHEN** 创建新项目
- **THEN** 所有 cached_* 字段为 NULL

#### Scenario: Cache fields updated on refresh
- **WHEN** 调用 profit/refresh 接口
- **THEN** 缓存字段更新为最新计算值
