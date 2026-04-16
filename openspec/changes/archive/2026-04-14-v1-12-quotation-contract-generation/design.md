## Context

已完成 v1.0 ~ v1.11 版本的报价单和合同管理功能，但文档生成完全依赖手工录入。现有系统缺乏结构化模板支持，难以维护一致性和扩展性。

## Goals / Non-Goals

**Goals:**
- 通过 Jinja2 模板引擎实现标准化的报价单和合同生成
- 支持从项目一键生成报价、从报价转合同
- 内容生成后支持手工编辑和版本管理
- 模板可动态配置，不同场景可使用不同模板

**Non-Goals:**
- 不做 AI 自由生成（Claude/GPT）
- 不做自动法律审查
- 不做自动电子签
- 不做富文本编辑器（纯文本编辑）
- 不做模板市场（仅本地模板管理）
- 不修改现有报价单和合同的业务逻辑流程

## Decisions

### 1. 模板存储方案
**选择**: 将模板存储在 `templates` 表中，使用 Jinja2 渲染

**理由**:
- 结构化存储便于管理和版本控制
- 支持幂等性插入（重跑迁移不重复插入）
- 数据库约束（唯一索引）保证每个类型只有一个默认模板

**替代方案**:
- 文件系统存储: 难以版本控制和备份恢复
- 配置文件存储: 难以支持多模板切换
- 无模板: 回到手工录入，违背本版本目标

### 2. 内容存储策略
**选择**: 在 `quotations` 和 `contracts` 表新增 `generated_content`、`template_id`、`content_generated_at` 字段

**理由**:
- `generated_content` 存储快照，不直接修改源字段
- `template_id` 追踪内容来源，便于回溯
- `content_generated_at` 记录生成时间，便于版本管理

**关键规则**:
- 冻结状态（accepted/active）不允许重新生成或手工编辑
- 非空内容未传 `force=true` 返回 409
- 手工编辑不更新 `content_generated_at`（保留最后生成时间）

### 3. 模板变量验证
**选择**: 分离 `REQUIRED_VARS` 和 `OPTIONAL_VARS`，生成前校验必填字段

**理由**:
- 避免渲染时才发现缺失数据
- 提供清晰的错误信息（`TEMPLATE_MISSING_REQUIRED_VARS`）
- 运行时校验优于模板语法校验

**实现**: `render_template()` 函数先校验必填变量，再执行 Jinja2 渲染

### 4. 前端交互设计
**选择**:
- 报价单详情页：生成内容按钮（draft/sent 可用，accepted 显示"内容已冻结"）
- 内容展示：`white-space: pre-wrap` 保留格式，等宽字体
- 手工编辑：文本编辑模式，保存不触发重渲染
- 预览：弹窗展示，不写库

**理由**:
- 简单直接，符合用户心智模型
- 预览功能允许在冻结状态下查看内容
- 避免复杂编辑器带来的性能和维护成本

### 5. 草稿去重策略
**选择**: 一个项目同一时间只允许一份 `status=draft` 且 `template_id IS NOT NULL` 的报价草稿

**理由**:
- 防止重复生成导致数据混乱
- 提供清晰的错误信息（`DRAFT_ALREADY_EXISTS` 附带已有 ID）
- 用户可选择跳转到已有草稿或创建新草稿

**实现**: `has_generated_draft_quotation()` 函数检查项目是否已有草稿

## Risks / Trade-offs

### [Risk] 模板语法错误导致渲染失败
**缓解**: 使用 `jinja2.Environment().parse()` 在保存时校验语法，渲染时捕获异常返回 `TEMPLATE_RENDER_FAILED`

### [Risk] 用户误操作覆盖已编辑内容
**缓解**:
- 已有内容时弹出确认框
- 冻结状态下隐藏生成/编辑按钮
- `force=true` 需要用户主动确认

### [Risk] 模板变量与代码定义不一致
**缓解**:
- 将变量列表统一定义在 `constants.py`
- 新增 `tests/test_template_vars_alignment.py` 验证模板与常量对齐

### [Risk] 数据库迁移失败
**缓解**:
- 迁移脚本幂等设计（先查后插入）
- 迁移后运行全量测试验证
- 提供回滚脚本（假设可重建数据库）

### [Risk] 并发修改冲突
**缓解**:
- 事务保证原子性（创建报价/合同+生成内容）
- 冻结检查在事务前完成

### Trade-off: 不支持模板热更新
**说明**: 模板修改需要重启服务，但内容生成在应用层，因此无需重启即可使用新模板生成新内容

## Migration Plan

### 阶段 1: 数据库迁移
```sql
CREATE TABLE templates (...);
ALTER TABLE quotations ADD COLUMN ...;
ALTER TABLE contracts ADD COLUMN ...;
INSERT default templates (幂等);
```

### 阶段 2: 后端实现
1. 模板管理 API
2. 报价单生成 API
3. 合同生成 API
4. 核心工具函数
5. 测试覆盖

### 阶段 3: 前端实现
1. 报价单详情页
2. 项目详情页
3. 合同详情页
4. 模板管理页

### 阶段 4: 回归测试
```bash
pytest tests/ -v --tb=short
```

### Rollback Strategy
1. 删除 `templates` 表
2. 回滚 `quotations` 和 `contracts` 表的列
3. 删除新增的 API 路由
4. 删除新增的常量和工具函数

## Open Questions

1. **模板版本管理**: 是否需要支持模板版本历史？（当前版本暂不实现）
2. **模板权限控制**: 模板是否需要按用户/角色区分？（当前所有用户可管理）
3. **内容导出格式**: 是否支持 PDF 导出？（当前仅支持文本预览，后续可扩展）
4. **模板变量动态配置**: 是否需要支持从数据库读取变量值而非代码定义？（当前通过代码定义）

## Design References

- Jinja2 官方文档: https://jinja.palletsprojects.com/
- 现有 v1.6 报价单到合同转换逻辑
- 现有 v1.11 风险控制模块实现模式
