## Context

数标云管 v1.x 已有完整的经营数据层（客户、项目、合同、财务、交付、里程碑），但存在三个结构性缺陷：
1. **无留痕**：报告/纪要/模板修改后历史版本丢失，无法回溯
2. **首页性能差**：dashboard API 需跨 6+ 张表 join 汇总，SQLite 单文件场景下随数据增长性能退化
3. **操作无记录**：工具使用、客户线索跟进依赖人工记忆，无系统化台账

当前技术栈：FastAPI + SQLAlchemy async + SQLite + Vue 3 + Element Plus。v2.2 在此基础上新增留痕底座和聚合层，不改变已有数据模型。

## Goals / Non-Goals

**Goals:**
- 建立统一快照底座（entity_snapshots），支持报告/纪要/模板的版本留痕与回溯链
- 建立仪表盘聚合层（dashboard_summary），关键经营事件触发局部刷新，首页零跨表 join
- 首页仪表盘展示六组经营状态（客户/项目/合同/财务/交付/提醒）
- 纪要/模板/报告保存自动触发 snapshot，失败不阻断主业务
- 工具入口台账 + 客户线索台账，最轻量 CRUD

**Non-Goals:**
- 不做营销 CRM（无漏斗阶段、意向分、触达记录）
- 不做实时推送/ WebSocket（summary 刷新后下次请求生效即可）
- 不做快照内容 diff 算法（仅返回两个版本 JSON，前端自行对比）
- 不修改 v1.x 已有字段和表结构

## Decisions

### D1: 统一快照表 vs 每实体独立快照表

**选择**：统一 `entity_snapshots` 表 + `entity_type` 枚举区分

**理由**：报告/纪要/模板的快照逻辑高度一致（版本号递增、is_latest 维护、回溯链），统一表减少代码重复，且 `save_with_snapshot` 可复用。entity_type 枚举（report/minutes/template）在 constants.py 定义。

**备选**：每实体独立表（report_snapshots, minutes_snapshots...）——字段冗余，维护成本高，拒绝。

### D2: dashboard_summary 键值模型 vs 宽表模型

**选择**：统一键值模型（metric_key + metric_value）

**理由**：
- 新增 metric 只需 INSERT 一行，无需 ALTER TABLE
- 后端 API 返回完整 metric 集合，前端按 `constants/dashboard.js` 静态常量分组展示
- 后端不感知分组逻辑，前后端解耦

**备选**：宽表模型（每列一个 metric）——每次新增 metric 需迁移，拒绝。

### D3: summary 刷新策略——事件驱动局部刷新 vs 定时全量重建

**选择**：事件驱动局部刷新为主 + 手动全量重建为辅

**理由**：
- 仅 5 类关键经营事件触发局部刷新（合同确认、收款录入、发票录入、交付完成、里程碑变更），避免无关写入触发刷新
- 全量重建接口供手动触发（如数据修复后），不自动定时执行
- 刷新失败返回 warning_code，不回滚主业务

**备选**：定时全量重建——延迟高、资源浪费，拒绝。

### D4: snapshot/summary 失败路径——主业务不回滚

**选择**：主业务成功后触发 snapshot/summary，失败时 API 返回 `success=true + warning_code`

**理由**：
- snapshot/summary 是辅助功能，不应阻断核心业务流程
- 前端按 warning_code 显示 toast 提示，不阻断用户操作
- 日志完整记录失败原因，便于排查

### D5: 纪要关联校验——业务层 vs 数据库层

**选择**：业务层校验（project_id / client_id 至少一个非空）

**理由**：保持迁移脚本简洁，避免数据库层 CHECK 约束与 ORM 冲突。

### D6: 执行顺序——Cluster 串行 + 并行

**选择**：A1 → A2 串行，B/C/D 在 A 完成后并行

**理由**：A1（snapshot）是 A2/C 的底层依赖；A2（summary）是 B 的底层依赖。B/C/D 之间无依赖，可并行。

## Risks / Trade-offs

- **[SQLite 写锁竞争]** summary 刷新与首页读取可能竞争 → 刷新操作使用小事务，单行 UPDATE，持锁时间极短
- **[snapshot 链断裂]** 并发写入同一实体快照时 is_latest 竞争 → 使用数据库层 `UPDATE ... SET is_latest=False WHERE entity_type=? AND entity_id=? AND is_latest=True` 原子操作
- **[summary 数据不一致]** 刷新失败导致 metric 过期 → 提供手动全量重建接口兜底
- **[metric_key 膨胀]** 新增 metric 需前后端同步 → 前端分组映射由静态常量控制，null 值降级显示"暂无数据"
- **[leads 表与 clients 表字段重复]** → 严格限定 leads 字段范围（source/status/next_action/client_id/project_id/notes），不重复 clients 已有字段
