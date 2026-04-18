## 1. Cluster A1 — 统一快照底座

- [x] 1.1 创建 entity_snapshots 模型（id, entity_type, entity_id, version_no, content, is_latest, created_at）+ 索引
- [ ] 1.2 在 constants.py 新增 SNAPSHOT_ENTITY_TYPE_WHITELIST（report/minutes/template）和 WARNING_CODE 常量
- [ ] 1.3 实现 create_snapshot() 函数：原子 is_latest 切换 + version_no 递增
- [ ] 1.4 实现 get_latest_snapshot() 函数
- [ ] 1.5 实现 get_snapshot_history() 函数
- [ ] 1.6 实现 save_with_snapshot() 函数：主业务成功后触发快照，失败返回 warning_code
- [ ] 1.7 实现 get_version_diff() 函数
- [ ] 1.8 编写 snapshot 单元测试（create/get/history/diff/并发 is_latest 竞争）
- [ ] 1.9 迁移脚本 cluster_a1_migrate.py

## 2. Cluster A2 — 仪表盘聚合层

- [ ] 2.1 创建 dashboard_summary 模型（id, metric_key, metric_value, updated_at）+ UNIQUE 约束
- [ ] 2.2 在 constants.py 新增 DASHBOARD_METRIC_KEY_WHITELIST 和 SUMMARY_TRIGGER_* 映射
- [ ] 2.3 实现 refresh_summary_metrics() 函数：按 metric_key 列表局部刷新
- [ ] 2.4 实现 rebuild_all_summary() 函数：全量重建
- [ ] 2.5 在合同确认/收款录入/发票录入/交付完成/里程碑变更 5 处埋点调用 refresh_summary_metrics
- [ ] 2.6 实现 GET /api/v1/dashboard/summary 端点（零跨表 join）
- [ ] 2.7 实现 POST /api/v1/dashboard/rebuild-summary 端点
- [ ] 2.8 编写 summary 单元测试（局部刷新/全量重建/触发失败不回滚）
- [ ] 2.9 迁移脚本 cluster_a2_migrate.py

## 3. Cluster B — 首页仪表盘前端

- [ ] 3.1 在 frontend/src/constants/dashboard.js 定义六组 widget 静态映射
- [ ] 3.2 重构 DashboardPage 组件，从 /api/v1/dashboard/summary 读取数据
- [ ] 3.3 实现六组 widget 展示（客户/项目/合同/财务/交付/提醒）
- [ ] 3.4 null 值降级显示"暂无数据"
- [ ] 3.5 编写前端组件测试

## 4. Cluster C — 纪要 + 模板 snapshot 集成

- [ ] 4.1 创建 meeting_minutes 模型（id, title, content, project_id, client_id, meeting_date, participants, created_at, updated_at）
- [ ] 4.2 实现 minutes CRUD API（POST/GET/PUT/DELETE /api/v1/minutes）
- [ ] 4.3 实现 project_id/client_id 至少一个非空的业务层校验
- [ ] 4.4 纪要保存触发 create_snapshot(entity_type="minutes")
- [ ] 4.5 模板保存触发 create_snapshot(entity_type="template")
- [ ] 4.6 报告保存触发 create_snapshot(entity_type="report")
- [ ] 4.7 扩展 TEMPLATE_TYPE_WHITELIST 新增 delivery/retrospective/quotation_calc
- [ ] 4.8 新增报告版本对比 API（GET /api/v1/reports/{id}/diff?version_a=&version_b=）
- [ ] 4.9 编写纪要 + snapshot 集成测试
- [ ] 4.10 迁移脚本 cluster_c_migrate.py

## 5. Cluster D — 台账管理

- [ ] 5.1 创建 tool_entries 模型（id, action_name, tool_name, status, callback_note, created_at, updated_at）
- [ ] 5.2 实现 tool entries CRUD API（POST/GET/PATCH/DELETE /api/v1/tool-entries）
- [ ] 5.3 实现 TOOL_ENTRY_STATUS_WHITELIST 和状态流转校验
- [ ] 5.4 创建 leads 模型（id, source, status, next_action, client_id, project_id, notes, created_at, updated_at）
- [ ] 5.5 实现 leads CRUD API（POST/GET/PUT/DELETE /api/v1/leads）
- [ ] 5.6 实现 LEAD_SOURCE_WHITELIST / LEAD_STATUS_WHITELIST 和状态流转校验
- [ ] 5.7 编写台账单元测试（CRUD + 状态流转 + 转化关联）
- [ ] 5.8 迁移脚本 cluster_d_migrate.py
