## Why

v1.x 已积累完整的经营数据（客户、项目、合同、财务、交付），但缺乏统一留痕底座和仪表盘聚合层。关键经营信息（报告、纪要、模板）修改后无法回溯历史版本；首页需跨表 join 汇总数据，性能差且维护难；日常操作（工具入口、客户线索跟进）无系统化记录，依赖人工记忆。v2.2 需要建立 snapshot 留痕底座 + summary 聚合层 + 仪表盘 + 留痕闭环 + 台账管理，使高频动作能在系统内闭环完成。

## What Changes

- 新增 `entity_snapshots` 统一快照表，支持报告/纪要/模板的版本留痕与回溯
- 新增 `dashboard_summary` 统一键值聚合表，关键经营事件触发局部刷新，首页仅读此表
- 新增首页仪表盘 API（`GET /api/v1/dashboard/summary`），零跨表 join
- 新增 `meeting_minutes` 纪要表，关联项目/客户，保存自动触发 snapshot
- 扩展模板类型枚举（方案/合同/交付/复盘/报价），模板保存触发 snapshot
- 新增 `tool_entries` 工具入口台账表，记录动作-工具-状态-回填
- 新增 `leads` 客户线索台账表，轻量跟进记录（不扩展为 CRM）
- 报告保存触发 snapshot，提供版本对比 API
- snapshot/summary 写入失败时主业务不回滚，API 返回 warning_code

## Capabilities

### New Capabilities
- `entity-snapshot`: 统一快照底座——create_snapshot / get_latest_snapshot / get_snapshot_history / save_with_snapshot / get_version_diff，支持多实体类型版本留痕与回溯链
- `dashboard-summary`: 仪表盘聚合层——dashboard_summary 键值表 + 关键事件触发刷新 + 全量重建接口，首页零跨表 join
- `meeting-minutes`: 会议纪要——纪要 CRUD，必须关联项目或客户，保存自动触发 snapshot
- `tool-entry-ledger`: 工具入口台账——动作-工具-状态-回填四字段 CRUD，状态流转
- `customer-lead-ledger`: 客户线索台账——来源/状态/下次动作三字段最小集，状态流转（初步接触→意向确认→转化为客户→无效）

### Modified Capabilities
- `dashboard`: 首页 API 改为仅读 dashboard_summary 表，不再跨表 join
- `template-management`: 模板类型枚举扩展（新增交付/复盘/报价），保存触发 snapshot
- `report-generation`: 报告保存触发 snapshot，新增版本对比 API

## Impact

- **数据库**：4 个新表（entity_snapshots, dashboard_summary, meeting_minutes, tool_entries, leads），1 个字段扩展（templates.template_type 枚举值追加）
- **后端 API**：新增 5 个端点（dashboard/summary, minutes, tool-entries, leads, snapshot 版本对比），修改 2 个端点（报告保存、模板保存需触发 snapshot）
- **前端**：首页仪表盘重构为六组 widget，新增纪要/工具入口/线索管理页面
- **常量**：constants.py 新增 entity_type 枚举、warning_code、metric_key、SUMMARY_TRIGGER_*、状态枚举
- **迁移**：4 个迁移脚本（cluster_a1, a2, c, d）
