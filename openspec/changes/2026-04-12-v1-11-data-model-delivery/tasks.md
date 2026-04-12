## 1. 数据库迁移（簇 A）

- [x] 1.1 创建 `backend/migrations/v1_11_migrate.py`，包含 8 张新表 + 3 张现有表 ALTER + 所有索引
- [x] 1.2 追加常量到 `backend/app/core/constants.py`（冻结字段、版本号正则、状态白名单、错误码）
- [x] 1.3 追加错误码到 `backend/app/core/error_codes.py`
- [x] 1.4 创建 `tests/test_migration_v111.py`，覆盖表存在性、字段存在性、索引、唯一约束、旧数据不变

## 2. 数据集台账——后端（簇 B）

- [x] 2.1 创建 `backend/app/models/dataset.py`（Dataset、DatasetVersion 模型）
- [x] 2.2 创建 `backend/app/core/dataset_utils.py`（validate_version_no、get_next_version_no、check_version_field_frozen、mark_version_in_use、unmark_version_in_use、can_delete_dataset_version、get_project_dataset_summary）
- [x] 2.3 创建 `backend/app/api/endpoints/datasets.py`（数据集 CRUD + 版本 CRUD + /ready + /archive 状态转换）
- [x] 2.4 创建 `tests/test_datasets.py`（13 个测试用例：版本号校验、冻结规则、in_use 保护、状态转换、404）

## 3. 标注任务记录——后端（簇 C）

- [x] 3.1 创建 `backend/app/models/annotation_task.py`（AnnotationTask 模型）
- [x] 3.2 创建 `backend/app/core/annotation_utils.py`（validate_annotation_task_transition、create_annotation_spec、get_task_specs、complete_quality_check）
- [x] 3.3 创建 `backend/app/api/endpoints/annotation_tasks.py`（CRUD + 状态转换 + /specs 端点）
- [x] 3.4 创建 `tests/test_annotation_tasks.py`（8 个测试用例：状态转换、返工原因、规范写入 requirements 表、语义边界）

## 4. 训练实验与模型版本——后端（簇 D）

- [x] 4.1 创建 `backend/app/models/training_experiment.py`（TrainingExperiment、ExperimentDatasetVersion 模型）
- [x] 4.2 创建 `backend/app/models/model_version.py`（ModelVersion 模型）
- [x] 4.3 创建 `backend/app/core/model_utils.py`（validate_model_version_no、check_experiment_field_frozen、check_model_version_field_frozen、link_dataset_version_to_experiment、unlink_dataset_version_from_experiment、get_experiment_traceability、get_model_version_traceability）
- [x] 4.4 创建 `backend/app/api/endpoints/training_experiments.py`（实验 CRUD + 数据集关联/解除 + 冻结校验）
- [x] 4.5 创建 `backend/app/api/endpoints/model_versions.py`（模型版本 CRUD + /ready + /deprecate + 冻结校验）
- [x] 4.6 创建 `tests/test_training_models.py`（11 个测试用例：in_use 自动设置、冻结规则、可追溯性、删除保护）

## 5. 交付包与验收——后端（簇 E）

- [x] 5.1 创建 `backend/app/models/delivery_package.py`（DeliveryPackage、PackageModelVersion、PackageDatasetVersion 模型）
- [x] 5.2 创建 `backend/app/core/delivery_utils.py`（can_mark_ready、deliver_package、create_package_acceptance、get_package_traceability）
- [x] 5.3 创建 `backend/app/api/endpoints/delivery_packages.py`（CRUD + 模型/数据集关联 + /deliver + /acceptance）
- [x] 5.4 创建 `tests/test_delivery_packages.py`（10 个测试用例：ready 前置检查、deliver 原子性、验收规则、删除保护、可追溯性）

## 6. 前端联调（簇 F）

- [x] 6.1 创建 `frontend/src/api/v111.js`（所有 v1.11 接口封装）
- [x] 6.2 在项目详情页新增「数据集」Tab：数据集列表 + 版本管理 + 冻结字段只读 + 元数据展示
- [x] 6.3 新增「标注任务」Tab：任务列表 + 状态流转操作 + 返工原因必填 + 规范列表
- [x] 6.4 新增「训练实验」Tab：实验列表 + 数据集版本关联（archived 不可选）+ 冻结字段只读
- [x] 6.5 新增「模型版本」Tab：版本列表 + 冻结字段只读 + delivered 隐藏删除按钮
- [x] 6.6 新增「交付包」Tab：包列表 + 关联内容 + deliver/验收按钮 + 完整追溯链展示

## 7. 全局重构与端到端验证（簇 G）

- [x] 7.1 确认常量引用一致性（业务代码引用 constants.py，无硬编码）
- [x] 7.2 检查函数长度 ≤ 50 行、圈复杂度 < 10
- [x] 7.3 创建 `tests/test_delivery_chain.py`（端到端交付链路测试：数据集→标注→实验→模型→交付→验收）
- [x] 7.4 添加日志覆盖（冻结拦截、事务失败）
- [x] 7.5 全量回归测试 `pytest tests/ -v --tb=short`，确认 0 FAILED
