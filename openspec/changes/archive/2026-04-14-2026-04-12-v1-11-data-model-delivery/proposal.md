## Why

v1.0~v1.10 已覆盖报价、合同、项目执行、财务、发票等业务模块，但缺乏数据标注与模型开发交付的全链路追踪能力。AI 项目交付的核心链路——数据集版本管理、标注任务质检、训练实验追溯、模型版本管控、交付包验收——目前无系统支撑，依赖人工台账，存在断链和版本混乱风险。v1.11 补齐这一缺口。

## What Changes

- 新增 8 张数据库表：datasets、dataset_versions、annotation_tasks、training_experiments、experiment_dataset_versions、model_versions、delivery_packages、package_model_versions、package_dataset_versions
- 扩展现有表：acceptances 新增 delivery_package_id、deliverables 新增 delivery_package_id、requirements 新增 annotation_task_id
- 新增数据集台账 CRUD + 版本冻结机制（ready/in_use/archived 状态下核心字段不可改）
- 新增标注任务记录与状态流转（pending→in_progress→quality_check→completed/rework）
- 新增训练实验管理，关联数据集版本时自动设置 in_use 状态，关联后实验核心字段冻结
- 新增模型版本管理，版本号三段式（v\d+\.\d+\.\d+$），ready/delivered/deprecated 状态冻结
- 新增交付包管理，deliver 时批量更新模型版本状态为 delivered，验收通过时交付包自动 accepted
- 复用 v1.5 验收表（acceptances），通过 delivery_package_id 外键锁定关联，复用 requirements 表存储标注规范
- 前端项目详情页新增 5 个 Tab：数据集/标注任务/训练实验/模型版本/交付包

## Capabilities

### New Capabilities
- `dataset-ledger`: 数据集与数据集版本 CRUD，版本号格式校验，版本冻结规则（draft/ready/in_use/archived），in_use 自动设置，版本元数据（data_source/label_schema_version/change_summary）
- `annotation-task`: 标注任务 CRUD，状态流转校验（pending/in_progress/quality_check/completed/rework/cancelled），质检通过/返工事务，标注规范写入 requirements 表
- `training-experiment`: 训练实验 CRUD，关联/解除关联数据集版本（原子事务），实验冻结规则，实验可追溯性查询
- `model-version`: 模型版本 CRUD，三段式版本号，版本冻结规则（training/ready/delivered/deprecated），模型可追溯性查询
- `delivery-package`: 交付包 CRUD，关联模型/数据集版本，deliver 原子事务，验收记录（复用 acceptances 表），交付包可追溯性查询

### Modified Capabilities
- `acceptance-management`: 新增 delivery_package_id 必填字段，新增 acceptance_type 枚举值 dataset/model，支持通过交付包进行模型/数据集验收
- `deliverable-management`: 新增 delivery_package_id 可选外键，支持交付包关联交付物
- `requirement-management`: 新增 annotation_task_id 可选外键，新增 requirement_type 枚举值 annotation_spec，支持标注规范作为需求类型

## Impact

- **数据库**: 8 张新表 + 3 张现有表 ALTER（均为新增可空列，向后兼容）
- **后端 API**: 新增 ~20 个接口端点，分布在 5 个新 router 文件中
- **后端核心**: 新增 4 个 utils 文件（dataset_utils、annotation_utils、model_utils、delivery_utils）
- **后端常量**: constants.py 和 error_codes.py 新增约 20 个常量/错误码
- **前端**: 项目详情页新增 5 个 Tab，新增 API 调用模块（api/v111.js）
- **测试**: 新增 ~40 个测试用例，含端到端交付链路测试
- **依赖**: 无新外部依赖
