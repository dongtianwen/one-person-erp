## Why

v2.2 已实现全部后端能力（Dashboard 汇总、纪要 CRUD + 快照版本对比、工具入口台账、客户线索台账），但前端页面完全缺失，用户无法通过界面使用这些功能。v2.3 需要将 v2.2 后端能力补齐对应前端页面，实现完整的前后端闭环。

## What Changes

- 新增 Warning 基础设施：统一 warning_code 处理 composable + 常量映射文件
- 新增 Dashboard 首页：六组 Widget 展示经营指标，支持手动刷新
- 新增纪要管理页面：列表 + 详情 + 创建/编辑表单 + 版本对比组件
- 新增工具入口台账页面：列表 + 状态 tab 筛选 + 快捷状态更新
- 新增客户线索台账页面：列表 + 状态 tab 筛选 + 快捷状态推进
- 新增路由注册：/dashboard、/minutes、/minutes/:id、/tools/entries、/leads
- 追加 help.js 帮助条目：Dashboard、纪要、工具台账、线索台账
- 新增常量文件：dashboard.js、snapshotSchema.js、warnings.js、status.js 追加

## Capabilities

### New Capabilities
- `warning-infrastructure`: 全局 warning_code 处理机制（composable + 常量映射），供所有页面统一使用
- `dashboard-page`: Dashboard 首页六组 Widget，展示客户/项目/合同/财务/交付/提醒指标，支持手动刷新
- `minutes-management`: 纪要管理页面（列表 + 详情 + 表单 + 版本对比），含项目/客户双选择器校验
- `tool-entries-page`: 工具入口台账页面，含状态 tab 筛选和快捷状态更新
- `leads-page`: 客户线索台账页面，含状态 tab 筛选和快捷状态推进

### Modified Capabilities
- `help-content`: 追加 v2.3 四个新页面的帮助条目（Dashboard、纪要、工具台账、线索台账）

## Impact

- **前端新增文件**：约 20+ 个 Vue 组件文件、4 个常量文件、1 个 composable
- **前端修改文件**：路由配置文件、help.js、status.js（追加枚举）
- **后端无变更**：v2.3 纯前端实现，严禁修改任何 Python 文件
- **依赖**：FE-A（Warning 基础设施）必须先行，FE-B/C/D 可并行
