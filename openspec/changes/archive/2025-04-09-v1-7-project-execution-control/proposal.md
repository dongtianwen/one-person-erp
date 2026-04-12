## Why

在已完成的 v1.0 ~ v1.6 代码库基础上，项目执行缺乏关键控制机制：
- 需求变更无正式流程，导致范围蔓延和工时失控
- 里程碑完成与收款节点脱节，应收账款跟踪困难
- 项目关闭无强制条件检查，可能存在未完成交付即关闭的风险
- 缺少工时偏差记录，无法评估项目健康度和改进报价精度

v1.7 旨在建立项目执行控制能力，确保项目按计划交付、及时收款、规范关闭。

## What Changes

### 新增功能
- **变更冻结机制**：报价确认后需求自动冻结，所有变更必须通过变更单（change_orders）流转且需客户确认
- **里程碑收款绑定**：里程碑与收款节点强绑定，只有已完成的里程碑才能触发收款状态流转
- **项目关闭强制条件**：项目关闭前必须满足全部条件（所有里程碑完成、最终验收通过、款项结清、交付物归档）
- **工时偏差记录**：记录每日工时，后端统一计算偏差率，超过阈值（20%）时强制填写原因
- **WIP 看板**：首页展示当前进行中项目，超过警戒线（2个）时显示警告（仅展示，不拦截操作）

### 数据库变更
- 扩展 `change_orders` 表：新增 status, extra_days, extra_amount, client_confirmed_at, client_rejected_at, rejection_reason 字段
- 扩展 `milestones` 表：新增 payment_amount, payment_due_date, payment_received_at, payment_status 字段
- 扩展 `projects` 表：新增 close_checklist, closed_at, estimated_hours, actual_hours 字段
- 新增 `work_hour_logs` 表：记录每日工时、任务描述、偏差备注
- 新增索引：change_orders(status), milestones(payment_status), work_hour_logs(project_id, log_date)

### API 变更
**新增接口**：
- `POST /api/v1/projects/{project_id}/change-orders` - 创建变更单
- `GET /api/v1/projects/{project_id}/change-orders` - 获取变更单列表
- `GET /api/v1/change-orders/{co_id}` - 获取变更单详情
- `PATCH /api/v1/change-orders/{co_id}/confirm` - 客户确认变更
- `PATCH /api/v1/change-orders/{co_id}/reject` - 客户拒绝变更
- `PATCH /api/v1/change-orders/{co_id}/cancel` - 撤销变更单
- `PATCH /api/v1/milestones/{milestone_id}/payment-invoiced` - 标记已开票
- `PATCH /api/v1/milestones/{milestone_id}/payment-received` - 标记已到账
- `GET /api/v1/projects/{project_id}/payment-summary` - 收款汇总
- `POST /api/v1/projects/{project_id}/close` - 关闭项目
- `GET /api/v1/projects/{project_id}/close-check` - 关闭条件检查
- `POST /api/v1/projects/{project_id}/work-hours` - 记录工时
- `GET /api/v1/projects/{project_id}/work-hours` - 工时记录列表
- `GET /api/v1/projects/{project_id}/work-hours/summary` - 工时汇总
- `PATCH /api/v1/projects/{project_id}/estimated-hours` - 更新预计工时

**行为变更**：
- 需求冻结状态下，直接修改需求接口返回 HTTP 409："需求已冻结，请通过变更单提交"
- 已关闭项目的核心字段不允许修改

### 前端变更
- 项目详情页新增"变更单"Tab
- 里程碑列表新增收款状态列和操作按钮
- 项目详情页新增"关闭项目"按钮和关闭条件检查面板
- 首页新增"当前进行中项目"看板区块
- 项目详情页新增"工时记录"Tab

## Capabilities

### New Capabilities
- `change-freeze`: 变更冻结机制 - 报价确认后需求冻结，变更单流转
- `milestone-payment`: 里程碑收款绑定 - 里程碑与收款状态关联
- `project-close`: 项目关闭强制条件 - 多条件校验后才能关闭项目
- `work-hour-logging`: 工时偏差记录 - 每日工时记录与偏差计算
- `wip-dashboard`: WIP 看板 - 进行中项目展示与警告

### Modified Capabilities
- `quotation`: 报价确认（status=accepted）后触发需求自动冻结
- `project-management`: 项目关闭增加强制条件校验

## Impact

### 受影响的模块
- **后端**：
  - 新增 `backend/core/change_order_utils.py`
  - 新增 `backend/core/milestone_payment_utils.py`
  - 新增 `backend/core/project_close_utils.py`
  - 新增 `backend/core/work_hour_utils.py`
  - 扩展 `backend/models/enums.py` - 新增 ChangeOrderStatus 枚举
  - 扩展 `backend/core/constants.py` - 新增 v1.7 常量
  - 迁移脚本 `backend/migrations/v1_7_migrate.py`

- **前端**：
  - 项目详情页新增变更单 Tab
  - 里程碑列表新增收款状态列
  - 项目详情页新增关闭入口和工时记录 Tab
  - 首页新增 WIP 看板区块

- **数据库**：
  - 4 个表扩展字段
  - 1 个新表
  - 5 个新索引

### 依赖
- 无新增外部依赖
- 依赖现有 quotations, projects, milestones, acceptances, deliverables 表

### 风险
- 需求冻结可能影响现有工作流，需确保 change_orders 流程顺畅
- 项目关闭条件严格，需确保数据完整性（如 final_acceptance 记录）
- 工时偏差阈值的 20% 为后端硬编码，后续可考虑配置化
