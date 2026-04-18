## MODIFIED Requirements

### Requirement: Report generation
系统 SHALL 提供 `generate_report` 函数，生成报告并写入 reports 表；报告保存 SHALL 自动触发 snapshot。

#### Scenario: Type not supported
- **WHEN** report_type 不在 REPORT_TYPE_WHITELIST
- **THEN** 抛出 REPORT_TYPE_NOT_SUPPORTED 错误

#### Scenario: Creates report record
- **WHEN** generate_report 被调用且参数有效
- **THEN** 创建 reports 记录，初始 status=generating

#### Scenario: Report status completed
- **WHEN** 报告生成成功
- **THEN** reports.status 更新为 completed，content 包含渲染结果

#### Scenario: Report content not null on completion
- **WHEN** 报告生成成功
- **THEN** content 字段不为 null

#### Scenario: Generation failure sets status failed
- **WHEN** 报告生成过程中抛出异常
- **THEN** reports.status 更新为 failed，error_message 写入错误信息

#### Scenario: LLM fill failed still completes
- **WHEN** LLM 填充失败
- **THEN** 报告仍 status=completed，分析段落显示 REPORT_LLM_FALLBACK_TEXT

#### Scenario: Uses default template when not specified
- **WHEN** template_id 为 null
- **THEN** 使用该 report_type 的默认模板（is_default=1）

#### Scenario: Version increment on regeneration
- **WHEN** 同一 entity 已存在 is_latest=1 的报告
- **THEN** 旧报告 is_latest=0，新报告 parent_report_id 指向旧报告，version_no = 旧版本 + 1，is_latest=1

#### Scenario: Report save triggers snapshot
- **WHEN** 报告生成成功（status=completed）
- **THEN** 自动调用 create_snapshot(entity_type="report", entity_id=报告id, content=报告内容)

#### Scenario: Report snapshot failure does not block save
- **WHEN** 报告保存成功但快照创建失败
- **THEN** 报告仍保存成功，API 返回 success=true + warning_code=SNAPSHOT_CREATE_FAILED

### Requirement: Report API endpoints
系统 SHALL 提供报告相关的 REST API 端点，包括版本对比。

#### Scenario: Generate report
- **WHEN** POST /api/v1/reports/generate 传入 report_type 和 entity_id
- **THEN** 返回 report_id, status, content（可能为 null）

#### Scenario: List reports
- **WHEN** GET /api/v1/reports?entity_type=&entity_id=&limit=10&offset=0
- **THEN** 返回 reports 数组和 total 总数

#### Scenario: Get report detail
- **WHEN** GET /api/v1/reports/{id}
- **THEN** 返回报告详情和 content

#### Scenario: Delete report
- **WHEN** DELETE /api/v1/reports/{id}
- **THEN** 返回 { deleted: true }

#### Scenario: Get report version diff
- **WHEN** GET /api/v1/reports/{id}/diff?version_a=1&version_b=2
- **THEN** 返回两个版本的 content 供前端对比

#### Scenario: Version not found in diff
- **WHEN** 请求的版本号不存在
- **THEN** 返回 404 错误
