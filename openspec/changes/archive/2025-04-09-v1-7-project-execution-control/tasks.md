## 1. 前置检查

- [x] 1.1 运行全量测试确认 v1.0 ~ v1.6 通过（pytest tests/ -v --tb=short）
- [x] 1.2 通过 PRAGMA table_info 确认所有必需表存在
- [x] 1.3 确认 logs/ 目录存在且 RotatingFileHandler 配置正确
- [x] 1.4 确认 .env 文件存在且 SECRET_KEY 已配置
- [x] 1.5 创建 PROGRESS.md 记录执行进度

## 2. 数据库迁移 (Cluster A)

- [x] 2.1 迁移前记录快照：change_orders, milestones, projects 表行数和字段
- [x] 2.2 创建迁移脚本 backend/migrations/v1_7_migrate.py
- [x] 2.3 扩展 change_orders 表：status, extra_days, extra_amount, client_confirmed_at, client_rejected_at, rejection_reason
- [x] 2.4 扩展 milestones 表：payment_amount, payment_due_date, payment_received_at, payment_status
- [x] 2.5 扩展 projects 表：close_checklist, closed_at, estimated_hours, actual_hours
- [x] 2.6 创建 work_hour_logs 表
- [x] 2.7 创建所有索引：change_orders(status), milestones(payment_status), work_hour_logs(project_id, log_date)
- [x] 2.8 执行迁移脚本
- [x] 2.9 迁移后验证：所有新表、新字段、新索引存在
- [x] 2.10 验证原有数据行数和抽样记录一致
- [x] 2.11 创建测试文件 tests/test_migration_v17.py
- [x] 2.12 运行迁移测试，要求 0 FAILED
- [x] 2.13 更新 PROGRESS.md：簇 A 完成

## 3. 变更冻结机制 - 后端 (Cluster B)

- [x] 3.1 新增枚举 ChangeOrderStatus 到 backend/models/enums.py
- [x] 3.2 新增常量到 backend/core/constants.py：CHANGE_ORDER_STATUS_WHITELIST
- [x] 3.3 创建 backend/core/change_order_utils.py
- [x] 3.4 实现 is_project_requirements_frozen() 函数
- [x] 3.5 实现 validate_change_order_transition() 函数
- [x] 3.6 实现 confirm_change_order() 函数（原子事务）
- [x] 3.7 实现 reject_change_order() 函数（原子事务）
- [x] 3.8 创建 POST /api/v1/projects/{project_id}/change-orders 接口
- [x] 3.9 创建 GET /api/v1/projects/{project_id}/change-orders 接口
- [x] 3.10 创建 GET /api/v1/change-orders/{co_id} 接口
- [ ] 3.11 创建 PATCH /api/v1/change-orders/{co_id}/confirm 接口
- [ ] 3.12 创建 PATCH /api/v1/change-orders/{co_id}/reject 接口
- [ ] 3.13 创建 PATCH /api/v1/change_orders/{co_id}/cancel 接口
- [x] 3.14 需求修改接口增加冻结检查（返回 HTTP 409）
- [x] 3.15 报价 accepted 后触发需求冻结逻辑
- [x] 3.16 创建测试文件 tests/test_change_freeze.py
- [x] 3.17 运行全量测试，要求 0 FAILED
- [x] 3.18 更新 PROGRESS.md：簇 B 完成

## 4. 里程碑收款绑定 - 后端 (Cluster C)

- [x] 4.1 创建 backend/core/milestone_payment_utils.py
- [x] 4.2 实现 validate_payment_transition() 函数
- [x] 4.3 实现 get_project_payment_summary() 函数
- [x] 4.4 实现 get_overdue_payment_milestones() 函数
- [x] 4.5 创建 PATCH /api/v1/milestones/{milestone_id}/payment-invoiced 接口
- [x] 4.6 创建 PATCH /api/v1/milestones/{milestone_id}/payment-received 接口
- [x] 4.7 创建 GET /api/v1/projects/{project_id}/payment-summary 接口
- [x] 4.8 里程碑创建/更新接口支持 payment_amount 和 payment_due_date
- [x] 4.9 创建测试文件 tests/test_milestone_payment.py
- [x] 4.10 运行全量测试，要求 0 FAILED
- [x] 4.11 更新 PROGRESS.md：簇 C 完成

## 5. 项目关闭强制条件 - 后端 (Cluster D)

- [x] 5.1 新增常量 PROJECT_CLOSE_CHECKLIST 到 backend/core/constants.py
- [x] 5.2 创建 backend/core/project_close_utils.py
- [x] 5.3 实现 check_project_close_conditions() 函数（严格按 acceptances 表判定）
- [x] 5.4 实现 close_project() 函数（原子事务）
- [x] 5.5 创建 GET /api/v1/projects/{project_id}/close-check 接口
- [x] 5.6 创建 POST /api/v1/projects/{project_id}/close 接口
- [x] 5.7 已关闭项目核心字段修改拦截
- [x] 5.8 创建测试文件 tests/test_project_close.py
- [x] 5.9 运行全量测试，要求 0 FAILED
- [x] 5.10 更新 PROGRESS.md：簇 D 完成

## 6. 前端联调 (Cluster E)

- [ ] 6.1 项目详情页新增"变更单"Tab
- [ ] 6.2 变更单列表展示（状态/描述/额外费用/操作按钮）
- [ ] 6.3 需求冻结状态下编辑入口显示"已冻结"标识
- [ ] 6.4 变更单操作按钮动态显示（pending 显示确认/拒绝/撤回）
- [ ] 6.5 里程碑列表新增收款状态列
- [ ] 6.6 一键标记开票/到账按钮（非 completed 禁用）
- [ ] 6.7 收款汇总区块展示
- [ ] 6.8 逾期未收款里程碑红色高亮
- [ ] 6.9 项目详情页新增"关闭项目"按钮
- [ ] 6.10 关闭条件检查面板展示（绿色=满足/红色=未满足）
- [ ] 6.11 所有条件满足时激活"确认关闭"按钮
- [ ] 6.12 已关闭项目显示"已完成"标识
- [ ] 6.13 首页新增"当前进行中项目"看板区块
- [ ] 6.14 WIP 超限时显示黄色警告（不拦截操作）
- [ ] 6.15 项目详情页新增"工时记录"Tab
- [ ] 6.16 工时记录表单（日期/小时数/任务描述/偏差备注）
- [ ] 6.17 偏差备注必填校验（基于 deviation_exceeds_threshold）
- [ ] 6.18 预计工时 vs 实际工时展示
- [ ] 6.19 前端验收测试
- [ ] 6.20 运行全量测试，要求 0 FAILED
- [ ] 6.21 更新 PROGRESS.md：簇 E 完成

## 7. 工时偏差记录 (Cluster F)

- [x] 7.1 新增常量 WORK_HOUR_DEVIATION_THRESHOLD 到 backend/core/constants.py
- [x] 7.2 新增常量 WIP_DISPLAY_LIMIT 到 backend/core/constants.py
- [x] 7.3 创建 backend/core/work_hour_utils.py
- [x] 7.4 实现 calculate_deviation() 函数
- [x] 7.5 实现 check_deviation_exceeds_threshold() 函数
- [x] 7.6 创建 POST /api/v1/projects/{project_id}/work-hours 接口
- [x] 7.7 创建 GET /api/v1/projects/{project_id}/work-hours 接口
- [x] 7.8 创建 GET /api/v1/projects/{project_id}/work-hours/summary 接口
- [x] 7.9 创建 PATCH /api/v1/projects/{project_id}/estimated-hours 接口
- [x] 7.10 后端校验：deviation_exceeds_threshold=true 时 deviation_note 必填
- [x] 7.11 创建测试文件 tests/test_work_hours.py
- [x] 7.12 运行全量测试，要求 0 FAILED
- [x] 7.13 更新 PROGRESS.md：簇 F 完成

## 8. 全局重构 (Cluster G)

- [x] 8.1 验证 WIP_DISPLAY_LIMIT 未出现在后端校验逻辑中
- [x] 8.2 验证 WORK_HOUR_DEVIATION_THRESHOLD 只在 work_hour_utils.py 中引用
- [x] 8.3 检查所有函数长度 ≤ 50 行
- [x] 8.4 检查所有函数圈复杂度 < 10
- [x] 8.5 验证独立函数可调用性（7个核心函数）
- [x] 8.6 验证事务一致性（3个关键事务）
- [x] 8.7 验证日志覆盖（5个关键位置）
- [x] 8.8 最终全量回归测试：pytest tests/ -v --tb=short
- [x] 8.9 确认 0 FAILED
- [x] 8.10 更新 PROGRESS.md：簇 G 完成

## 9. 完成验证

- [ ] 9.1 簇 A ~ G 全部状态为 ✅
- [ ] 9.2 pytest tests/ -v 结果：0 FAILED
- [ ] 9.3 backend/core/constants.py 已追加 v1.7 常量
- [ ] 9.4 WIP_DISPLAY_LIMIT 未出现在后端校验逻辑中
- [ ] 9.5 WORK_HOUR_DEVIATION_THRESHOLD 只在 work_hour_utils.py 中引用一处
- [ ] 9.6 变更冻结在报价 accepted 后自动生效
- [ ] 9.7 冻结后变更同时写 change_orders 和 requirement_changes
- [ ] 9.8 里程碑收款状态流转符合约束
- [ ] 9.9 final_acceptance_passed 判定严格来自 acceptances 表最新记录
- [ ] 9.10 WIP 看板超限显示警告，不拦截任何操作
- [ ] 9.11 工时偏差阈值由后端统一计算并通过接口字段返回
- [ ] 9.12 logs/ 目录产生了日志文件
- [ ] 9.13 所有接口字段名、错误文案、HTTP 状态码与 PRD 一致
- [ ] 9.14 在 PROGRESS.md 写入"v1.7 执行完成"并记录时间
