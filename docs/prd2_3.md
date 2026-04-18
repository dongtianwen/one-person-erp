# 🎯 项目执行指令（给 Claude Code）

## 🧠 前置分析（编码前必须输出）
在编写任何代码前，先输出简要的技术风险分析与实现策略，包含以下三点：
1. 字段级版本对比组件的通用化设计策略（需支持纪要/报告/模板三种不同字段 schema）。
2. Dashboard warning_code toast 与各页面 warning_code toast 的统一处理方案。
3. 纪要创建表单中 project_id / client_id 双选择器的联动边界（至少一个非空的前端校验策略）。

不展开内部推理细节，直接给出结论性判断。

---

# 给 Claude Code 的项目提示词

## 🎯 项目概述
- **项目名称**：数标云管 v2.3
- **核心目标**：将 v2.2 已实现的全部后端能力补齐对应前端页面，不新增任何后端接口或数据库变更。
- **范围边界**：纯前端实现，禁止修改后端代码。如发现后端接口缺失，必须停止并报告，不得自行补充后端逻辑。

---

## 🛠️ 开发工作流：规格先行（Spec-First）
v2.3 为纯前端版本，不使用 pytest TDD。采用以下三阶段循环：

**规格定义（Spec）→ 实现（Build）→ 检查收口（Review）**

- **Spec 阶段**：输出页面组件树、API 接入点、交互行为、空态/异常态规格，等待确认后方可进入 Build。
- **Build 阶段**：按规格逐组件实现，每完成一个页面级组件输出简报后等待指令继续。
- **Review 阶段**：对照规格逐项检查，修复偏差，确认 warning_code 处理、空态、加载态、帮助内容全部覆盖。

---

## 📐 Cluster 划分与执行顺序

### 执行规则
- **Cluster FE-A（Warning 基础设施）必须先行完成**，FE-B / FE-C / FE-D 方可并行推进。
- 每个 Cluster 的 Review 阶段结束后，在浏览器中完整走一遍该页面的主流程，确认无控制台报错。
- 使用 `PROGRESS.md` 记录执行状态，提供中断恢复入点。

### Cluster 总览

| Cluster | 内容 | 依赖 |
|---------|------|------|
| FE-A | Warning 基础设施（toast 拦截器 + 通用 composable） | 无，先行 |
| FE-B | Dashboard 首页六组 Widget | 依赖 FE-A |
| FE-C | 纪要管理页面 + 版本对比组件 | 依赖 FE-A |
| FE-D | 工具入口台账页面 + 客户线索台账页面 | 依赖 FE-A |

---

## 🚨 全局前端约束

1. **技术栈**：Vue 3 Composition API + Element Plus，不引入任何新 UI 库或图表库。
2. **API 调用**：全部通过已有 axios 实例发起，不直接使用 fetch。
3. **路由**：新增页面路由统一注册到现有 Vue Router 配置文件，不新建路由文件。
4. **常量**：metric_key 映射、字段 schema、状态枚举从 `frontend/src/constants/` 读取，不在组件内硬编码。
5. **warning_code 处理**：统一通过 FE-A 定义的 composable 处理，各页面不自行实现 toast 逻辑。
6. **空态规范**：所有列表页在数据为空时显示 `<el-empty>`，不显示空白区域。
7. **加载态规范**：所有异步请求期间显示 `<el-skeleton>` 或 `v-loading` 指令，不留白。
8. **禁止修改后端**：v2.3 范围内严禁修改任何 Python 文件。

---

## 📖 帮助系统规范（v1.10 建立，v2.3 延续）

**帮助系统位置**：`frontend/src/constants/help.js`（纯 JS 静态常量，不建数据库表）

**规则**：
- v2.3 每个新增页面，必须在 `help.js` 中追加对应的帮助条目。
- 帮助条目结构遵循已有文件格式，**实现前必须先读取 `help.js` 确认现有结构，再追加**，禁止修改已有条目。
- 每个 Cluster 的 Build 阶段最后一步为追加帮助内容，Review 阶段必须验证帮助条目存在。

**v2.3 需追加的帮助条目规格**（以下为内容要求，格式以现有 `help.js` 为准）：

### Dashboard 页帮助内容
```
KEY: HELP_DASHBOARD
页面说明：仪表盘汇总当前经营状态，数据来源于各模块的关键业务事件（合同确认、收款录入、交付完成等），不实时计算，点击"手动刷新"可重新汇总最新数据。
指标分组说明：
  - 客户：活跃客户数、客户总数
  - 项目：进行中项目数、逾期项目数
  - 合同：生效合同数、待确认合同数
  - 财务：待收款金额、待开票数量
  - 交付：待交付数量、逾期里程碑数
  - 提醒：今日提醒数、逾期未处理提醒数
```

### 纪要页帮助内容
```
KEY: HELP_MINUTES_PAGE
页面说明：会议纪要记录每次客户或项目沟通的关键结论，必须关联项目或客户，确保信息可追溯、不丢失。

字段提示：
  HELP_MINUTES_FIELD_TITLE: 纪要标题，建议包含日期和主题，例如"2024-06-01 项目启动会"。
  HELP_MINUTES_FIELD_PARTICIPANTS: 参与人员，多人以逗号分隔。
  HELP_MINUTES_FIELD_CONCLUSIONS: 本次沟通达成的明确结论，避免模糊描述。
  HELP_MINUTES_FIELD_ACTION_ITEMS: 后续需跟进的具体行动项，建议注明负责人和截止时间。
  HELP_MINUTES_FIELD_RISK_POINTS: 沟通中识别到的风险或不确定因素。
  HELP_MINUTES_FIELD_PROJECT: 关联项目（与客户至少选一个）。
  HELP_MINUTES_FIELD_CLIENT: 关联客户（与项目至少选一个）。

版本对比说明：
  HELP_MINUTES_VERSION_COMPARE: 每次保存纪要后系统自动留存版本快照。点击"版本对比"可选择任意两个版本，变更字段以橙色高亮显示，未变更字段正常显示。
```

### 工具入口台账帮助内容
```
KEY: HELP_TOOL_ENTRIES_PAGE
页面说明：工具入口台账记录当前每类业务动作使用的外部工具及其完成状态，帮助追踪哪些动作已完成、哪些结果已回填到系统。

字段提示：
  HELP_TOOL_ENTRY_FIELD_ACTION_NAME: 业务动作名称，例如"合同电子签"、"发票开具"、"会议记录整理"。
  HELP_TOOL_ENTRY_FIELD_TOOL_NAME: 当前执行该动作所使用的外部工具，例如"腾讯电子签"、"企业微信"。
  HELP_TOOL_ENTRY_FIELD_STATUS: 动作当前状态。待处理：尚未开始；进行中：已发起但未完成；已完成：动作本身已完成；已回填：结果已录入系统。
  HELP_TOOL_ENTRY_FIELD_IS_BACKFILLED: 标记该动作的结果是否已回填到数据标云管对应模块。
```

### 客户线索台账帮助内容
```
KEY: HELP_LEADS_PAGE
页面说明：客户线索台账追踪潜在客户的跟进状态，不替代客户档案，仅记录正式成交前的轻量跟进信息。线索转化后可关联至客户模块。

字段提示：
  HELP_LEAD_FIELD_SOURCE: 线索来源渠道，例如"朋友介绍"、"平台主动询价"、"展会"。
  HELP_LEAD_FIELD_STATUS: 跟进状态。初步接触：已有初步沟通；意向确认：客户明确有采购意向；已转化：已成为正式客户；无效：确认不会成交。
  HELP_LEAD_FIELD_NEXT_ACTION: 下一步跟进动作，建议具体描述，例如"本周五发送方案报价"。
  HELP_LEAD_FIELD_CLIENT: 可选关联已有客户档案（线索转化后使用）。
  HELP_LEAD_FIELD_PROJECT: 可选关联已有项目（线索对应具体项目时使用）。
```

---

## 🤖 Cluster 详细规格

---

### Cluster FE-A：Warning 基础设施

**目标**：建立全局统一的 warning_code 处理机制，避免各页面重复实现 toast 逻辑。

---

#### FE-A Spec 阶段

**需要创建的文件**：

```
frontend/src/composables/useApiWarning.js
frontend/src/constants/warnings.js
```

**`warnings.js` 内容规格**：

```javascript
// 所有 warning_code 及其对应的中文提示信息
export const WARNING_MESSAGES = {
  SNAPSHOT_WRITE_FAILED: '版本留痕写入失败，数据已保存，可稍后在历史记录中手动重建。',
  SUMMARY_REFRESH_FAILED: '仪表盘数据刷新失败，经营数据已保存，可点击仪表盘手动刷新。',
  // 后续新增 warning_code 在此追加
}
```

**`useApiWarning.js` 规格**：

```javascript
// 用法：
// const { handleResponse } = useApiWarning()
// const result = await handleResponse(apiCall())
// handleResponse 负责：
//   1. 检测响应中是否含 warning_code
//   2. 若有，调用 ElMessage.warning 显示对应中文提示
//   3. 返回原始响应数据，不阻断调用方流程
export function useApiWarning() { ... }
```

**验收标准**：
- [ ] `useApiWarning` 可在任意组件内 import 使用
- [ ] warning_code 未在 WARNING_MESSAGES 中定义时，显示兜底提示"操作完成，但存在异常，请查看日志"
- [ ] 不影响正常响应的数据返回

---

#### FE-A Build 阶段

按规格实现两个文件，完成后输出简报：

```
✅ Cluster FE-A 完成
已创建：useApiWarning.js / warnings.js
等待指令继续 FE-B / FE-C / FE-D。
```

---

#### FE-A Review 阶段

- [ ] WARNING_MESSAGES 覆盖 v2.2 定义的全部 warning_code？
- [ ] 兜底提示存在且措辞合理？
- [ ] composable 可被 import 且无循环依赖？

> FE-A 无新增页面，不需要追加 help.js 条目。

---

### Cluster FE-B：Dashboard 首页六组 Widget

**后端接口**：
- `GET /api/v1/dashboard/summary` → 返回 `{ metrics: { metric_key: value, ... } }`
- `POST /api/v1/dashboard/rebuild` → 触发全量重建，返回标准响应（含可能的 warning_code）

---

#### FE-B Spec 阶段

**路由**：`/dashboard`（或系统现有首页路由，沿用现有配置）

**常量文件**：`frontend/src/constants/dashboard.js`

```javascript
// 六组 widget 的分组定义，后端不感知此结构
export const DASHBOARD_GROUPS = [
  {
    key: 'customers',
    label: '客户',
    metrics: ['METRIC_CUSTOMER_ACTIVE', 'METRIC_CUSTOMER_TOTAL'],  // 示例，以 v2.2 constants.py 实际定义为准
  },
  {
    key: 'projects',
    label: '项目',
    metrics: ['METRIC_PROJECT_ACTIVE', 'METRIC_PROJECT_OVERDUE'],
  },
  {
    key: 'contracts',
    label: '合同',
    metrics: ['METRIC_CONTRACT_ACTIVE', 'METRIC_CONTRACT_PENDING'],
  },
  {
    key: 'finance',
    label: '财务',
    metrics: ['METRIC_PAYMENT_PENDING', 'METRIC_INVOICE_PENDING'],
  },
  {
    key: 'delivery',
    label: '交付',
    metrics: ['METRIC_DELIVERY_PENDING', 'METRIC_MILESTONE_OVERDUE'],
  },
  {
    key: 'reminders',
    label: '提醒',
    metrics: ['METRIC_REMINDER_TODAY', 'METRIC_REMINDER_OVERDUE'],
  },
]
// ⚠️ metric key 字符串必须与后端 constants.py 中定义的完全一致，实现前必须核对
```

**组件树**：

```
DashboardView.vue
├── DashboardHeader.vue（标题 + 手动刷新按钮 + 最后刷新时间）
└── DashboardGrid.vue（六列或三列两行布局）
    └── DashboardWidget.vue × 6（每组一个，props: group）
        ├── widget 标题
        ├── MetricItem.vue × N（每个 metric_key 一行）
        │   ├── 指标名称（中文 label）
        │   └── 指标值（数值 / "暂无数据"）
        └── 加载骨架（v-loading）
```

**交互行为**：
- 页面加载时自动调用 `GET /api/v1/dashboard/summary`
- 每个 Widget 独立渲染，某 Widget 内 metric_value 为 null 时显示"暂无数据"，不影响其他 Widget
- 手动刷新按钮点击后调用 `POST /api/v1/dashboard/rebuild`，完成后重新 GET summary
- 刷新中按钮禁用并显示 loading 状态
- API 响应含 warning_code 时通过 `useApiWarning` 显示 toast

**空态**：summary 表为空（所有 metric_value 为 null）时，各 Widget 显示"暂无数据"，页面整体不报错。

---

#### FE-B Build 阶段

实现顺序：
1. `frontend/src/constants/dashboard.js`（核对 metric_key 与后端一致后实现）
2. `MetricItem.vue`
3. `DashboardWidget.vue`
4. `DashboardGrid.vue`
5. `DashboardHeader.vue`
6. `DashboardView.vue`（组装 + API 接入）
7. **追加 `help.js` 条目**：按本文档"帮助系统规范"中 `HELP_DASHBOARD` 的内容规格，在 `frontend/src/constants/help.js` 追加 Dashboard 页帮助条目，格式与现有条目保持一致。

每完成一个组件输出简报后等待指令。

---

#### FE-B Review 阶段

- [ ] metric_key 与后端 constants.py 完全一致？
- [ ] 六组 Widget 全部渲染，分组正确？
- [ ] null 值显示"暂无数据"而非空白或报错？
- [ ] 手动刷新完成后数据更新？
- [ ] warning_code toast 正常弹出？
- [ ] 加载态覆盖？
- [ ] **`help.js` 中 `HELP_DASHBOARD` 条目已追加，内容覆盖页面说明和指标分组说明？**

---

### Cluster FE-C：纪要管理页面 + 版本对比组件

**后端接口**：
- `GET /api/v1/minutes` → 纪要列表
- `POST /api/v1/minutes` → 创建纪要
- `GET /api/v1/minutes/{id}` → 纪要详情
- `PUT /api/v1/minutes/{id}` → 更新纪要
- `DELETE /api/v1/minutes/{id}` → 删除纪要
- `GET /api/v1/snapshots/{entity_type}/{entity_id}/history` → 快照历史列表
- `GET /api/v1/snapshots/{entity_type}/{entity_id}/diff?v1={n}&v2={m}` → 两版本 snapshot_json

---

#### FE-C Spec 阶段

**路由**：
- `/minutes` → 列表页
- `/minutes/:id` → 详情页（含版本历史与对比入口）

**字段 Schema 常量**：`frontend/src/constants/snapshotSchema.js`

```javascript
// 版本对比组件使用的字段 schema，定义各实体类型的可比较字段
export const SNAPSHOT_SCHEMAS = {
  minutes: [
    { key: 'title', label: '标题' },
    { key: 'participants', label: '参与人' },
    { key: 'conclusions', label: '结论' },
    { key: 'action_items', label: '待办事项' },
    { key: 'risk_points', label: '风险点' },
  ],
  report: [
    { key: 'title', label: '报告标题' },
    { key: 'body', label: '报告正文' },
    // 以 v2.2 报告结构为准，实现前核对
  ],
  template: [
    { key: 'title', label: '模板标题' },
    { key: 'template_type', label: '模板类型' },
    { key: 'body', label: '正文' },
    { key: 'variables', label: '变量定义' },
    { key: 'placeholders', label: '占位符配置' },
  ],
}
```

**组件树**：

```
MinutesListView.vue（列表页）
├── MinutesFilter.vue（按项目/客户筛选）
├── el-table（标题 / 关联项目 / 关联客户 / 创建时间 / 操作）
├── MinutesFormDialog.vue（创建/编辑对话框）
│   ├── el-input（标题）
│   ├── el-input（参与人，支持逗号分隔多人）
│   ├── el-input type=textarea（结论）
│   ├── el-input type=textarea（待办事项）
│   ├── el-input type=textarea（风险点）
│   ├── el-select（关联项目，可空）
│   ├── el-select（关联客户，可空）
│   └── 表单校验：项目和客户至少一个非空
└── el-empty（列表为空时）

MinutesDetailView.vue（详情页）
├── MinutesDetail.vue（展示五字段内容）
├── VersionHistoryPanel.vue（快照历史列表，含版本号/时间/对比按钮）
└── VersionCompareDialog.vue（版本对比对话框）
    └── VersionCompareTable.vue（字段级对比表格）
```

**VersionCompareTable.vue 规格（核心）**：
- Props：`v1Json: Object, v2Json: Object, schema: Array`
- 渲染一张表格，每行对应 schema 中的一个字段
- 列：字段名 / 版本 A 内容 / 版本 B 内容
- 若两列内容不同：该行背景色高亮（`#fff7e6` 浅橙色），并在字段名列显示"已变更"badge
- 若内容相同：正常显示
- 内容为数组或对象时，展示为格式化文本（`JSON.stringify(value, null, 2)`），不做深度对比

**VersionCompareDialog.vue 规格**：
- 打开时默认选中最新版本（v_latest）和前一版本（v_latest - 1）
- 提供两个版本号下拉选择器，可手动切换任意两个版本
- 切换后重新调用 diff 接口，更新对比表格
- 加载中显示 v-loading

**纪要表单校验规则**：
- 标题：必填
- 结论：必填
- 项目 + 客户：至少一个非空，两者均空时表单提交失败并提示"请关联项目或客户"
- 其余字段：选填

**空态与异常**：
- 列表为空：`<el-empty description="暂无会议纪要" />`
- 快照历史为空：提示"暂无历史版本"
- diff 接口失败：对话框内显示"版本对比加载失败，请重试"

---

#### FE-C Build 阶段

实现顺序：
1. `frontend/src/constants/snapshotSchema.js`
2. `VersionCompareTable.vue`（核心组件，先独立实现）
3. `VersionCompareDialog.vue`
4. `VersionHistoryPanel.vue`
5. `MinutesFormDialog.vue`（含双选择器校验）
6. `MinutesDetail.vue`
7. `MinutesDetailView.vue`（组装）
8. `MinutesListView.vue`（组装 + API 接入）
9. 注册路由
10. **追加 `help.js` 条目**：按本文档"帮助系统规范"中纪要相关条目的内容规格，在 `frontend/src/constants/help.js` 追加 `HELP_MINUTES_PAGE`、七个字段提示、`HELP_MINUTES_VERSION_COMPARE`，格式与现有条目保持一致。

每完成一个组件输出简报后等待指令。

---

#### FE-C Review 阶段

- [ ] 项目/客户双选择器：两者均空时表单提交被阻断并提示？
- [ ] 版本对比：变更字段高亮，未变更字段正常？
- [ ] 版本对比：版本号切换后重新请求 diff？
- [ ] 列表空态显示 `<el-empty>`？
- [ ] 快照历史为空时有提示？
- [ ] warning_code toast 正常弹出？
- [ ] `VersionCompareTable` 可被 report/template 页面复用（通过传入不同 schema）？
- [ ] **`help.js` 中纪要页条目已追加：页面说明、七个字段提示、版本对比说明均存在？**

---

### Cluster FE-D：工具入口台账 + 客户线索台账

**后端接口（工具入口）**：
- `GET /api/v1/tool-entries` → 列表（支持 `?status=` 筛选）
- `POST /api/v1/tool-entries` → 创建
- `PUT /api/v1/tool-entries/{id}` → 更新（含状态 + is_backfilled）
- `DELETE /api/v1/tool-entries/{id}` → 删除

**后端接口（线索）**：
- `GET /api/v1/leads` → 列表（支持 `?status=` 筛选）
- `POST /api/v1/leads` → 创建
- `PUT /api/v1/leads/{id}` → 更新
- `DELETE /api/v1/leads/{id}` → 删除

---

#### FE-D Spec 阶段

**路由**：
- `/tools/entries` → 工具入口台账列表页
- `/leads` → 客户线索台账列表页

**状态枚举常量**：`frontend/src/constants/status.js`（若已有此文件，追加至其中）

```javascript
// 以后端 constants.py 中的 TOOL_STATUS_* / LEAD_STATUS_* 为准，实现前核对
export const TOOL_ENTRY_STATUSES = [
  { value: 'pending', label: '待处理' },
  { value: 'in_progress', label: '进行中' },
  { value: 'done', label: '已完成' },
  { value: 'backfilled', label: '已回填' },
]

export const LEAD_STATUSES = [
  { value: 'initial', label: '初步接触' },
  { value: 'intent_confirmed', label: '意向确认' },
  { value: 'converted', label: '已转化' },
  { value: 'invalid', label: '无效' },
]
```

**工具入口台账组件树**：

```
ToolEntriesView.vue
├── el-tabs（按状态分 tab 筛选：全部/待处理/进行中/已完成/已回填）
├── ToolEntryFormDialog.vue（创建/编辑）
│   ├── el-input（动作名称，必填）
│   ├── el-input（工具名称，必填）
│   ├── el-select（状态）
│   ├── el-switch（已回填）
│   └── el-input（备注，选填）
├── el-table
│   ├── 动作名称 / 工具名称 / 状态 tag / 已回填标记 / 备注 / 操作
│   └── 操作列：编辑 / 更新状态（快捷按钮）/ 删除
└── el-empty（列表为空）
```

**快捷状态更新**：
- 表格操作列提供"标记已完成"和"标记已回填"两个快捷按钮（仅在对应状态可操作时显示）
- 点击后直接调用 PUT 接口更新单个字段，不打开编辑对话框

**客户线索台账组件树**：

```
LeadsView.vue
├── el-tabs（按状态分 tab 筛选：全部/初步接触/意向确认/已转化/无效）
├── LeadFormDialog.vue（创建/编辑）
│   ├── el-input（来源，必填）
│   ├── el-select（状态，必填）
│   ├── el-input（下次动作，必填）
│   ├── el-select（关联客户，可空，从 clients API 动态加载）
│   ├── el-select（关联项目，可空，从 projects API 动态加载）
│   └── el-input（备注，选填）
├── el-table
│   ├── 来源 / 状态 tag / 下次动作 / 关联客户 / 关联项目 / 创建时间 / 操作
│   └── 操作列：推进状态（快捷按钮）/ 编辑 / 删除
└── el-empty（列表为空）
```

**线索状态快捷推进**：
- 表格操作列提供"推进到下一阶段"快捷按钮（仅在非终态时显示）
- 状态流转顺序：初步接触 → 意向确认 → 已转化（终态）；无效为独立终态
- 点击后显示确认对话框，确认后调用 PUT 接口

**关联客户/项目选择器加载**：
- 打开 LeadFormDialog 时，并行请求 `GET /api/v1/customers` 和 `GET /api/v1/projects` 加载选项
- 请求中显示 loading，请求失败时选择器禁用并提示"加载失败"

**空态**：两个列表页均使用 `<el-empty>`，按当前 tab 状态给出对应描述（如"暂无待处理工具记录"）。

---

#### FE-D Build 阶段

实现顺序：
1. `frontend/src/constants/status.js`（追加枚举值，核对后端常量）
2. `ToolEntryFormDialog.vue`
3. `ToolEntriesView.vue`（组装 + API 接入）
4. 注册工具台账路由
5. `LeadFormDialog.vue`（含双选择器动态加载）
6. `LeadsView.vue`（组装 + API 接入）
7. 注册线索路由
8. **追加 `help.js` 条目**：按本文档"帮助系统规范"中工具台账和线索台账的内容规格，在 `frontend/src/constants/help.js` 追加 `HELP_TOOL_ENTRIES_PAGE`（含四个字段提示）和 `HELP_LEADS_PAGE`（含五个字段提示），格式与现有条目保持一致。

每完成一个页面输出简报后等待指令。

---

#### FE-D Review 阶段

- [ ] 工具台账：状态 tab 筛选生效？
- [ ] 工具台账：快捷"标记已完成"/"标记已回填"按钮仅在正确状态下显示？
- [ ] 线索台账：状态快捷推进，终态不再显示推进按钮？
- [ ] 线索台账：关联客户/项目选择器加载失败时禁用并提示？
- [ ] 两个列表页：空 tab 状态时显示对应空态描述？
- [ ] 状态枚举值与后端 constants.py 完全一致？
- [ ] **`help.js` 中 `HELP_TOOL_ENTRIES_PAGE` 条目已追加，含页面说明和四个字段提示？**
- [ ] **`help.js` 中 `HELP_LEADS_PAGE` 条目已追加，含页面说明和五个字段提示？**

---

## 📦 最终交付清单

**常量文件**：
- [ ] `frontend/src/constants/dashboard.js` — 六组 Widget 分组映射（metric_key 与后端一致）
- [ ] `frontend/src/constants/snapshotSchema.js` — 各实体类型版本对比字段 schema
- [ ] `frontend/src/constants/status.js` — 工具台账/线索台账状态枚举（追加）
- [ ] `frontend/src/constants/warnings.js` — warning_code 中文提示映射
- [ ] `frontend/src/constants/help.js` — 追加 v2.3 全部帮助条目（Dashboard / 纪要页 / 工具台账 / 线索台账）

**Composable**：
- [ ] `frontend/src/composables/useApiWarning.js` — 统一 warning_code 处理

**Dashboard 组件**：
- [ ] `DashboardView.vue`
- [ ] `DashboardHeader.vue`
- [ ] `DashboardGrid.vue`
- [ ] `DashboardWidget.vue`
- [ ] `MetricItem.vue`

**纪要组件**：
- [ ] `MinutesListView.vue`
- [ ] `MinutesDetailView.vue`
- [ ] `MinutesDetail.vue`
- [ ] `MinutesFormDialog.vue`
- [ ] `VersionHistoryPanel.vue`
- [ ] `VersionCompareDialog.vue`
- [ ] `VersionCompareTable.vue`（通用，可被 report/template 复用）

**工具台账组件**：
- [ ] `ToolEntriesView.vue`
- [ ] `ToolEntryFormDialog.vue`

**线索台账组件**：
- [ ] `LeadsView.vue`
- [ ] `LeadFormDialog.vue`

**路由注册**：
- [ ] `/dashboard` — Dashboard
- [ ] `/minutes` — 纪要列表
- [ ] `/minutes/:id` — 纪要详情
- [ ] `/tools/entries` — 工具入口台账
- [ ] `/leads` — 客户线索台账

---

## 📋 PROGRESS.md 模板

```markdown
# 数标云管 v2.3 执行进度

## Cluster FE-A：Warning 基础设施
- [ ] Spec 确认
- [ ] Build 完成（useApiWarning.js / warnings.js）
- [ ] Review 通过

## Cluster FE-B：Dashboard 首页（依赖 FE-A）
- [ ] Spec 确认（metric_key 与后端核对完成）
- [ ] Build 完成（六组 Widget）
- [ ] help.js HELP_DASHBOARD 条目已追加
- [ ] Review 通过

## Cluster FE-C：纪要管理 + 版本对比（依赖 FE-A）
- [ ] Spec 确认（snapshotSchema 与后端核对完成）
- [ ] Build 完成
- [ ] help.js 纪要相关条目已追加（页面说明 + 7 字段提示 + 版本对比说明）
- [ ] Review 通过

## Cluster FE-D：工具台账 + 线索台账（依赖 FE-A）
- [ ] Spec 确认（状态枚举与后端核对完成）
- [ ] Build 完成
- [ ] help.js 工具台账条目已追加（页面说明 + 4 字段提示）
- [ ] help.js 线索台账条目已追加（页面说明 + 5 字段提示）
- [ ] Review 通过

## 最终验收
- [ ] 四个页面主流程浏览器走通，无控制台报错
- [ ] warning_code toast 在所有页面正常弹出
- [ ] VersionCompareTable 在纪要详情页可用
- [ ] help.js 全部 v2.3 条目存在且内容完整
```

---

## ⚠️ 实现前必须核对的后端常量与前端现有文件

在 Spec 阶段和 Build 阶段开始前，**必须先读取以下文件，核对内容后再写前端常量**，禁止凭假设直接写死：

**后端 `constants.py`**：
1. 所有 `METRIC_*` metric_key 字符串的实际值
2. `TOOL_STATUS_*` 的实际字符串值
3. `LEAD_STATUS_*` 的实际字符串值
4. `ENTITY_TYPE_*` 的实际字符串值（用于 snapshot API 路径）
5. `WARNING_CODE_*` 的实际字符串值

**前端 `frontend/src/constants/help.js`**：
6. 读取现有文件，确认帮助条目的数据结构格式，追加时严格遵循同一格式

若 constants.py 中任何上述常量缺失或与本文档不符，必须停止并报告，不得自行定义。
若 help.js 文件不存在，必须停止并报告，不得自行创建新文件结构。

---

## 🎯 开始执行

请现在开始 **Cluster FE-A：Warning 基础设施**。

先创建 `PROGRESS.md`，再读取后端 `constants.py` 核对 warning_code 常量，以及 `frontend/src/constants/help.js` 确认现有帮助条目格式，然后实现 `warnings.js` 和 `useApiWarning.js`。
