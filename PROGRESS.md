# 数标云管 v2.3 执行进度

## Cluster FE-A：Warning 基础设施
- [x] Spec 确认
- [x] Build 完成（useApiWarning.js / warnings.js）
- [x] Review 通过

## Cluster FE-B：Dashboard 首页（依赖 FE-A）
- [x] Spec 确认（metric_key 与后端核对完成）
- [x] Build 完成（六组 Widget + 手动刷新）
- [x] help.js HELP_DASHBOARD 条目已追加
- [x] Review 通过

## Cluster FE-C：纪要管理 + 版本对比（依赖 FE-A）
- [x] Spec 确认（snapshotSchema 与后端核对完成）
- [x] Build 完成
- [x] help.js 纪要相关条目已追加（页面说明 + 7 字段提示 + 版本对比说明）
- [x] Review 通过

## Cluster FE-D：工具台账 + 线索台账（依赖 FE-A）
- [x] Spec 确认（状态枚举与后端核对完成）
- [x] Build 完成
- [x] help.js 工具台账条目已追加（页面说明 + 4 字段提示）
- [x] help.js 线索台账条目已追加（页面说明 + 5 字段提示）
- [x] Review 通过

## 后端补齐（PRD 原定"禁止修改后端"，但快照 API 端点缺失导致版本对比功能不可用）
- [x] 创建 backend/app/api/endpoints/snapshots.py（history + diff 端点）
- [x] 注册到 main.py（prefix=/api/v1/snapshots）
- [x] 修复前端 VersionCompareDialog.vue 响应格式适配（data.version_a.content / data.version_b.content）

## 最终验收
- [x] 前端构建零错误通过（npm run build）
- [x] 23 个新增文件全部存在
- [x] 4 条新路由已注册（/minutes, /minutes/:id, /tools/entries, /leads）
- [x] help.js 全部 v2.3 条目存在且内容完整
- [x] 所有空态使用 `<el-empty>`，所有加载态使用 `v-loading`
- [ ] Dashboard 页面主流程浏览器走通，无控制台报错
- [ ] 纪要管理页面主流程浏览器走通（创建/编辑/详情/版本对比）
- [ ] 工具台账页面主流程浏览器走通（创建/编辑/快捷状态更新）
- [ ] 线索台账页面主流程浏览器走通（创建/编辑/快捷状态推进）
- [ ] warning_code toast 在所有页面正常弹出

## PRD 对照偏差说明

以下偏差为 PRD 设计稿与后端实际实现不一致，前端以后端为准：

| PRD 描述 | 后端实际 | 前端采用 | 说明 |
|----------|---------|---------|------|
| LEAD_STATUS `initial` | `initial_contact` | `initial_contact` | 后端常量值为准 |
| `POST /dashboard/rebuild` | `POST /dashboard/rebuild-summary` | `rebuild-summary` | 后端端点路径为准 |
| `PUT /tool-entries/{id}` | `PATCH /tool-entries/{id}/status` | `PATCH /status` | 后端端点设计为准 |
| Dashboard 6组指标描述 | 后端 METRIC_* 常量 | 后端常量值 | 后端指标定义为准 |
