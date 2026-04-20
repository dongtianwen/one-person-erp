## 1. FE-A Warning 基础设施（先行）

- [x] 1.1 读取后端 `constants.py` 核对所有 WARNING_CODE_* 常量值
- [x] 1.2 创建 `frontend/src/constants/warnings.js`，定义 WARNING_MESSAGES 映射（含兜底提示）
- [x] 1.3 创建 `frontend/src/composables/useApiWarning.js`，实现 handleResponse 逻辑
- [x] 1.4 验证 useApiWarning 可被 import 且无循环依赖

## 2. FE-B Dashboard 首页

- [x] 2.1 读取后端 `constants.py` 核对所有 METRIC_* 常量值
- [x] 2.2 创建 `frontend/src/constants/dashboard.js`，定义 DASHBOARD_GROUPS 六组映射
- [x] 2.3 创建 `frontend/src/views/dashboard/MetricItem.vue`（指标名称 + 指标值/暂无数据）
- [x] 2.4 创建 `frontend/src/views/dashboard/DashboardWidget.vue`（props: group，含 v-loading）
- [x] 2.5 创建 `frontend/src/views/dashboard/DashboardGrid.vue`（六列或三列两行布局）
- [x] 2.6 创建 `frontend/src/views/dashboard/DashboardHeader.vue`（标题 + 刷新按钮 + 最后刷新时间）
- [x] 2.7 创建 `frontend/src/views/dashboard/DashboardView.vue`（组装 + API 接入 + useApiWarning）
- [x] 2.8 注册 `/dashboard` 路由
- [x] 2.9 追加 `help.js` HELP_DASHBOARD 条目（页面说明 + 指标分组说明）

## 3. FE-C 纪要管理 + 版本对比

- [x] 3.1 读取后端 `constants.py` 核对 ENTITY_TYPE_* 常量值
- [x] 3.2 创建 `frontend/src/constants/snapshotSchema.js`，定义 minutes/report/template 字段 schema
- [x] 3.3 创建 `frontend/src/components/VersionCompareTable.vue`（通用，props: v1Json, v2Json, schema）
- [x] 3.4 创建 `frontend/src/views/minutes/VersionCompareDialog.vue`（版本选择器 + diff API 调用）
- [x] 3.5 创建 `frontend/src/views/minutes/VersionHistoryPanel.vue`（快照历史列表）
- [x] 3.6 创建 `frontend/src/views/minutes/MinutesFormDialog.vue`（含双选择器校验）
- [x] 3.7 创建 `frontend/src/views/minutes/MinutesDetail.vue`（展示五字段内容）
- [x] 3.8 创建 `frontend/src/views/minutes/MinutesDetailView.vue`（组装详情页）
- [x] 3.9 创建 `frontend/src/views/minutes/MinutesListView.vue`（列表页 + API 接入）
- [x] 3.10 注册 `/minutes` 和 `/minutes/:id` 路由
- [x] 3.11 追加 `help.js` 纪要相关条目（页面说明 + 7 字段提示 + 版本对比说明）

## 4. FE-D 工具入口台账

- [x] 4.1 读取后端 `constants.py` 核对 TOOL_STATUS_* 常量值
- [x] 4.2 在 `frontend/src/constants/status.js` 追加 TOOL_ENTRY_STATUSES 枚举
- [x] 4.3 创建 `frontend/src/views/tools/ToolEntryFormDialog.vue`（创建/编辑表单）
- [x] 4.4 创建 `frontend/src/views/tools/ToolEntriesView.vue`（列表页 + 状态 tab + 快捷按钮 + API 接入）
- [x] 4.5 注册 `/tools/entries` 路由
- [x] 4.6 追加 `help.js` HELP_TOOL_ENTRIES_PAGE 条目（页面说明 + 4 字段提示）

## 5. FE-D 客户线索台账

- [x] 5.1 读取后端 `constants.py` 核对 LEAD_STATUS_* 常量值
- [x] 5.2 在 `frontend/src/constants/status.js` 追加 LEAD_STATUSES 枚举
- [x] 5.3 创建 `frontend/src/views/leads/LeadFormDialog.vue`（含动态客户/项目选择器）
- [x] 5.4 创建 `frontend/src/views/leads/LeadsView.vue`（列表页 + 状态 tab + 快捷推进 + API 接入）
- [x] 5.5 注册 `/leads` 路由
- [x] 5.6 追加 `help.js` HELP_LEADS_PAGE 条目（页面说明 + 5 字段提示）

## 6. Review 与验证

- [ ] 6.1 Dashboard 页面主流程浏览器走通，无控制台报错
- [ ] 6.2 纪要管理页面主流程浏览器走通（创建/编辑/详情/版本对比）
- [ ] 6.3 工具台账页面主流程浏览器走通（创建/编辑/快捷状态更新）
- [ ] 6.4 线索台账页面主流程浏览器走通（创建/编辑/快捷状态推进）
- [ ] 6.5 warning_code toast 在所有页面正常弹出
- [ ] 6.6 help.js 全部 v2.3 条目存在且内容完整
- [ ] 6.7 所有空态使用 `<el-empty>`，所有加载态使用 `v-loading` 或 `<el-skeleton>`
