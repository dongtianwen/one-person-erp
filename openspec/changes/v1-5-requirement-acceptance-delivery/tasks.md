## 1. 数据库迁移（簇 A）

- [x] 1.1 迁移前快照
- [x] 1.2 创建迁移脚本 `backend/migrations/v1_5_migrate.py`
- [x] 1.3 迁移后验证
- [x] 1.4 创建测试 `tests/test_migration_v15.py`: 14 个测试用例全部通过
- [x] 1.5 全量回归: 157 passed, 0 FAILED

## 2. 常量与枚举定义

- [x] 2.1 追加 v1.5 常量到 `backend/core/constants.py`：REQUIREMENT_VERSION_PREFIX, REQUIREMENT_SUMMARY_MAX_LENGTH, CHANGE_ORDER_PREFIX, MAINTENANCE_REMINDER_DAYS_BEFORE, NOTES_SEPARATOR, CHANGE_ORDER_VALID_TRANSITIONS, FORBIDDEN_FIELD_PATTERNS
- [x] 2.2 追加枚举到 `backend/models/enums.py`：RequirementStatus, ChangeType, ConfirmMethod, AcceptanceResult, DeliverableType, DeliveryMethod, ReleaseType, DeployEnv, ChangeOrderStatus, MaintenanceType, MaintenanceStatus

## 3. FR-501 需求与变更管理——后端（簇 B）

- [x] 3.1 创建工具模块 `backend/core/requirement_utils.py`：实现 set_requirement_as_current() 和 can_modify_field() 函数
- [x] 3.2 实现需求版本 CRUD 路由：POST/GET list/GET detail/PUT/PATCH /api/v1/projects/{project_id}/requirements
- [x] 3.3 实现 set-current 端点：POST /api/v1/projects/{project_id}/requirements/{requirement_id}/set-current
- [x] 3.4 实现需求变更记录端点：POST /api/v1/projects/{project_id}/requirements/{requirement_id}/changes
- [x] 3.5 实现字段修改约束：confirmed 状态下 summary/version_no 不可修改（POST/PUT/PATCH 三处统一校验）
- [x] 3.6 创建测试 `tests/test_requirements.py`：19 个测试用例全部通过
- [x] 3.7 全量回归：189 passed, 0 FAILED

## 4. FR-502 验收管理——后端（簇 C）

- [x] 4.1 创建工具模块 `backend/core/acceptance_utils.py`：实现 create_payment_reminder_for_acceptance() 和 append_notes() 函数
- [x] 4.2 实现验收记录 CRUD 路由：POST/GET list/GET detail /api/v1/projects/{project_id}/acceptances
- [x] 4.3 实现 DELETE 返回 405：注册 DELETE 端点直接返回 HTTP 405
- [x] 4.4 实现 result 不可修改约束：PUT/PATCH 中检测 result 字段变更返回 422
- [x] 4.5 实现 append-notes 端点：PATCH /api/v1/projects/{project_id}/acceptances/{acceptance_id}/append-notes
- [x] 4.6 实现验收通过联动收款提醒：result=passed/conditional + trigger_payment_reminder=True 时事务内创建提醒
- [x] 4.7 创建测试 `tests/test_acceptances.py`：16 个测试用例全部通过
- [x] 4.8 全量回归：205 passed, 0 FAILED

## 5. FR-503 交付物管理——后端（簇 D）

- [x] 5.1 创建工具模块 `backend/core/deliverable_utils.py`：实现 contains_password_field() 函数（字段名子串匹配，不扫描值）
- [x] 5.2 实现交付物 CRUD 路由：POST/GET list/GET detail /api/v1/projects/{project_id}/deliverables
- [x] 5.3 实现 DELETE 返回 405
- [x] 5.4 实现 account_handover 类型处理：创建时事务内写入 account_handovers 数组
- [x] 5.5 实现密码字段检测：account_handover 条目提交时调用 contains_password_field()，拦截返回 422
- [x] 5.6 实现按 deliverable_type 筛选：GET 列表接口支持 query parameter
- [x] 5.7 创建测试 `tests/test_deliverables.py`：17 个测试用例全部通过
- [x] 5.8 全量回归：222 passed, 0 FAILED

## 6. FR-504 版本/发布记录——后端（簇 E）

- [x] 6.1 创建工具模块 `backend/core/release_utils.py`：实现 set_release_as_online() 函数
- [x] 6.2 实现版本发布 CRUD 路由：POST/GET list/GET detail /api/v1/projects/{project_id}/releases
- [x] 6.3 实现 DELETE 返回 405
- [x] 6.4 实现 set-online 端点：POST /api/v1/projects/{project_id}/releases/{release_id}/set-online
- [x] 6.5 实现 is_current_online 唯一性：创建/设置时事务内清除同项目其他记录
- [x] 6.6 实现列表 is_pinned 标记：is_current_online=True 的记录追加 is_pinned: true
- [x] 6.7 实现 version_no/release_date 不可修改约束：PUT/PATCH 检测返回 422
- [x] 6.8 项目详情追加 current_version 字段：GET /api/v1/projects/{project_id} 返回追加字段
- [x] 6.9 创建测试 `tests/test_releases.py`：14 个测试用例全部通过
- [x] 6.10 全量回归：236 passed, 0 FAILED

## 7. FR-505 变更单/增补单——后端（簇 F）

- [x] 7.1 创建工具模块 `backend/core/change_order_utils.py`：实现 generate_change_order_no()、validate_status_transition()、calculate_actual_receivable() 函数
- [x] 7.2 实现变更单 CRUD 路由：POST/GET list/GET detail/PUT/PATCH /api/v1/contracts/{contract_id}/change-orders
- [x] 7.3 实现 order_no 自动生成：事务内调用 generate_change_order_no()，格式 BG-YYYYMMDD-NNN
- [x] 7.4 实现状态流转校验：使用 CHANGE_ORDER_VALID_TRANSITIONS 字典，非法流转返回 422
- [x] 7.5 实现字段修改约束：confirmed 及以后状态不可修改 amount/description
- [x] 7.6 实现列表追加合计字段：confirmed_total 和 actual_receivable
- [x] 7.7 实现项目维度摘要端点：GET /api/v1/projects/{project_id}/change-orders/summary（只读）
- [x] 7.8 创建测试 `tests/test_change_orders.py`：22 个测试用例全部通过
- [x] 7.9 全量回归：258 passed, 0 FAILED

## 8. FR-506 售后/维护期管理——后端（簇 G）

- [x] 8.1 实现维护期 CRUD 路由：POST/GET list/GET detail /api/v1/projects/{project_id}/maintenance-periods
- [x] 8.2 实现日期校验：end_date < start_date 返回 422
- [x] 8.3 实现续期端点：POST /api/v1/projects/{project_id}/maintenance-periods/{period_id}/renew（事务内三步操作）
- [x] 8.4 实现 PATCH 限制：仅允许 service_description/annual_fee/notes，expired/renewed/terminated 状态拒绝
- [x] 8.5 扩展事件驱动检查：追加维护期到期过期 + 到期提醒生成（幂等）
- [x] 8.6 扩展看板接口：追加 active_maintenance_count 字段
- [x] 8.7 创建测试 `tests/test_maintenance.py`：18 个测试用例全部通过
- [x] 8.8 全量回归：276 passed, 0 FAILED

## 9. 前端联调（簇 H）

- [x] 9.1 项目详情页新增 6 个 Tab：[需求][验收][交付物][版本][售后][变更单摘要]
- [x] 9.2 项目详情页顶部追加"当前线上版本"显示
- [x] 9.3 实现需求管理 Tab：当前版本展示、历史版本折叠、新建版本、confirmed 只读、变更记录列表、is_billable 校验
- [x] 9.4 实现验收管理 Tab：验收列表、新建表单、result 联动提醒开关、无删除按钮、result 只读、追加备注
- [x] 9.5 实现交付物管理 Tab：交付物列表、新建表单、account_handover 条目、密码字段检测、类型筛选
- [x] 9.6 实现版本记录 Tab：置顶当前线上、新建版本、设为当前线上、version_no/release_date 只读
- [x] 9.7 实现变更单摘要 Tab（项目页只读）：展示关联合同变更单摘要，无写操作入口
- [x] 9.8 实现合同详情页变更单 Tab：完整 CRUD、金额合计展示、状态流转按钮、字段修改约束
- [x] 9.9 实现售后/维护期 Tab：列表排序、到期标色、新建表单、续期表单、PATCH 限制字段
- [x] 9.10 全量回归：`pytest tests/ -v` 要求 0 FAILED

## 10. 全局重构（簇 I）

- [x] 10.1 常量集中管理：确认 constants.py 包含 v1.5 常量，消除魔术数字
- [x] 10.2 函数长度与复杂度：所有函数 ≤ 50 行，圈复杂度 < 10
- [x] 10.3 独立函数可调用性：9 个核心函数可在测试中直接 import
- [x] 10.4 事务一致性验证：4 处事务操作均有原子性回滚测试
- [x] 10.5 事件驱动检查完整性：v1.1/v1.2/v1.5 覆盖验证
- [x] 10.6 日志覆盖：6 类操作均写入 RotatingFileHandler
- [x] 10.7 最终全量回归：`pytest tests/ -v` 要求 0 FAILED，输出记录到 PROGRESS.md
