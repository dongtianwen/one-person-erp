## Context

数标云管 v2.2 后端已完成全部 API 实现（Dashboard 汇总、纪要 CRUD + 快照版本对比、工具入口台账、客户线索台账），前端仅实现了 v2.2 之前版本的页面。v2.3 是纯前端版本，需要为 v2.2 后端能力补齐前端界面。

当前前端技术栈：Vue 3 Composition API + Element Plus + Vue Router + Axios。已有帮助系统（help.js）、PageHelpDrawer 组件、FieldTip 组件。

约束：严禁修改任何后端 Python 文件。

## Goals / Non-Goals

**Goals:**
- 建立全局统一的 warning_code 处理机制，避免各页面重复实现 toast 逻辑
- 实现 Dashboard 首页，展示六组经营指标 Widget，支持手动刷新
- 实现纪要管理页面（列表 + 详情 + 表单 + 版本对比），含项目/客户双选择器校验
- 实现工具入口台账页面，含状态 tab 筛选和快捷状态更新
- 实现客户线索台账页面，含状态 tab 筛选和快捷状态推进
- 所有新页面追加 help.js 帮助条目
- 所有新页面注册路由

**Non-Goals:**
- 不新增任何后端接口或数据库变更
- 不引入新的 UI 库或图表库
- 不修改现有页面的功能逻辑
- 不实现 Dashboard 数据图表可视化（仅展示数值指标）

## Decisions

### D1: Warning 基础设施采用 Composable 模式
- **选择**：创建 `useApiWarning` composable + `warnings.js` 常量映射
- **理由**：Vue 3 Composition API 的 composable 是共享逻辑的标准方式，各组件通过 `const { handleResponse } = useApiWarning()` 即可使用
- **替代方案**：Axios 拦截器全局处理 → 拒绝，因为 warning_code 不应阻断流程，需要组件级灵活控制

### D2: 版本对比组件通用化设计
- **选择**：`VersionCompareTable.vue` 通过 props 接收 schema 数组，支持 minutes/report/template 三种实体类型
- **理由**：v2.2 快照 API 是通用的（`/snapshots/{entity_type}/{entity_id}/history`），前端对比组件也应通用
- **替代方案**：每种实体类型单独实现对比组件 → 拒绝，重复代码过多

### D3: Dashboard Widget 分组常量化
- **选择**：`dashboard.js` 定义六组 Widget 的 metric_key 映射，与后端 constants.py 保持一致
- **理由**：metric_key 是前后端契约，硬编码在组件内会导致维护困难
- **替代方案**：从后端动态获取分组配置 → 拒绝，v2.2 后端不提供此接口，且 v2.3 禁止修改后端

### D4: 纪要表单项目/客户双选择器校验策略
- **选择**：前端自定义校验规则，提交时检查 project_id 和 client_id 至少一个非空
- **理由**：后端已实现此校验，前端应提前拦截避免无效请求
- **替代方案**：仅依赖后端校验 → 拒绝，用户体验差

### D5: 状态枚举集中管理
- **选择**：在 `status.js` 中追加 TOOL_ENTRY_STATUSES 和 LEAD_STATUSES 枚举
- **理由**：状态值必须与后端 constants.py 完全一致，集中管理便于核对
- **替代方案**：各组件内硬编码 → 拒绝，维护困难且易出错

## Risks / Trade-offs

- **[Risk] metric_key 与后端不一致** → Mitigation: 实现前必须读取后端 constants.py 核对所有 metric_key 字符串
- **[Risk] 版本对比组件 schema 不匹配后端快照结构** → Mitigation: 实现前读取后端快照模型字段，snapshotSchema.js 严格对齐
- **[Risk] 状态枚举值与后端不一致** → Mitigation: 实现前读取后端 constants.py 核对 TOOL_STATUS_* 和 LEAD_STATUS_*
- **[Trade-off] 纯前端实现意味着无法修复后端 bug** → 若发现后端接口缺失或行为异常，必须停止并报告，不得自行补充后端逻辑
- **[Trade-off] Dashboard 不做图表可视化** → 仅展示数值指标，后续版本可扩展
