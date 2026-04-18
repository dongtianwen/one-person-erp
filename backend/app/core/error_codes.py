"""v1.10 业务错误码定义——集中管理所有对外暴露的错误码。"""

ERROR_CODES: dict[str, str] = {
    # 报价模块（v1.6）
    "QUOTE_STATUS_INVALID_TRANSITION": "报价单状态流转不合法",
    "QUOTE_ALREADY_CONVERTED": "报价单已转换为合同，不可重复转换",
    "QUOTE_NOT_ACCEPTED": "仅已接受的报价单可转换合同",
    # 变更冻结（v1.7）
    "REQUIREMENT_FROZEN": "需求已冻结",
    "CHANGE_ORDER_INVALID_TRANSITION": "变更单状态流转不合法",
    # 里程碑收款（v1.7）
    "MILESTONE_NOT_COMPLETED": "里程碑未完成，不可触发收款流转",
    "PAYMENT_STATUS_INVALID_TRANSITION": "收款状态流转不合法",
    # 项目关闭（v1.7）
    "PROJECT_CLOSE_CONDITIONS_NOT_MET": "项目关闭条件未满足",
    "PROJECT_ALREADY_CLOSED": "项目已关闭",
    # 发票（v1.8）
    "INVOICE_AMOUNT_EXCEEDS_CONTRACT": "发票金额累计超过合同金额",
    "INVOICE_STATUS_INVALID_TRANSITION": "发票状态流转不合法",
    "INVOICE_CANNOT_DELETE": "已核销或已作废的发票不可删除",
    # 通用
    "NOT_FOUND": "记录不存在",
    "VALIDATION_ERROR": "输入数据校验失败",
    "DUPLICATE_ENTRY": "数据重复，违反唯一约束",
    "FOREIGN_KEY_VIOLATION": "关联数据不存在或被其他记录引用",
    # v1.11 数据标注与模型开发交付台账
    "DATASET_VERSION_FROZEN": "数据集版本核心字段已冻结",
    "MODEL_VERSION_FROZEN": "模型版本核心字段已冻结",
    "EXPERIMENT_FROZEN": "训练实验核心字段已冻结",
    "VERSION_IN_USE_CANNOT_DELETE": "版本正在被引用，不可删除",
    "DELIVERED_MODEL_CANNOT_DELETE": "已交付模型不可删除",
    "ACCEPTED_PACKAGE_CANNOT_DELETE": "已验收交付包不可删除",
    "DATASET_VERSION_IN_USE": "数据集版本正在使用中，不可手动设置in_use状态",
    "PACKAGE_EMPTY_CANNOT_READY": "交付包无关联内容，不可标记为ready",
    "PACKAGE_NOT_READY_CANNOT_DELIVER": "交付包未处于ready状态，不可交付",
    "PACKAGE_ALREADY_HAS_ACCEPTANCE": "交付包已有验收记录",
    "PACKAGE_ID_MISMATCH": "delivery_package_id与当前交付包不匹配",
    # v1.12 报价合同生成与模板系统
    "TEMPLATE_NOT_FOUND": "模板不存在",
    "TEMPLATE_RENDER_FAILED": "模板渲染失败",
    "TEMPLATE_MISSING_REQUIRED_VARS": "模板缺少必填变量",
    "CONTENT_FROZEN": "内容已冻结，不可重新生成或编辑",
    "CONTENT_ALREADY_EXISTS": "内容已存在，使用 force=true 覆盖",
    "QUOTE_NO_QUOTATION_ID": "报价单ID缺失",
    "TEMPLATE_IS_DEFAULT": "默认模板不可删除",
    "DRAFT_ALREADY_EXISTS": "该项目已有报价草稿",
    # v2.0 AI Agent 闭环
    "OLLAMA_UNAVAILABLE": "Ollama 服务不可用",
    "API_PROVIDER_UNAVAILABLE": "外部 LLM 服务不可用",
    "LLM_PARSE_FAILED": "LLM 返回解析失败",
    "AGENT_ALREADY_RUNNING": "同类型 Agent 正在运行中，请稍后重试",
    "SUGGESTION_NOT_PENDING": "该建议已被处理，不可重复确认",
    "ACTION_EXECUTION_FAILED": "动作执行失败",
    # v2.1 自由问答
    "QA_REQUIRES_API_PROVIDER": "经营问答功能需要接入外部大模型",
    "QA_CONTEXT_BUILD_FAILED": "经营数据上下文构建失败",
    # v2.1 深度报告
    "REPORT_TYPE_NOT_SUPPORTED": "报告类型不在支持列表中",
    "REPORT_ENTITY_NOT_FOUND": "生成报告的目标实体不存在",
    "REPORT_LLM_FILL_FAILED": "AI 分析段落填充失败",
    # v2.1 交付质检
    "DELIVERY_QC_NO_PACKAGE": "指定的交付包不存在",
    # v2.2 快照底座 + 仪表盘聚合层
    "SNAPSHOT_WRITE_FAILED": "快照写入失败",
    "SNAPSHOT_VERSION_NOT_FOUND": "快照版本不存在",
    "SUMMARY_REFRESH_FAILED": "仪表盘汇总数据刷新失败",
    "MINUTES_ASSOCIATION_REQUIRED": "纪要必须关联项目或客户",
    "TOOL_ENTRY_INVALID_TRANSITION": "工具入口状态流转不合法",
    "LEAD_INVALID_TRANSITION": "客户线索状态流转不合法",
}

ERROR_QA_REQUIRES_API_PROVIDER = "QA_REQUIRES_API_PROVIDER"
ERROR_QA_CONTEXT_BUILD_FAILED = "QA_CONTEXT_BUILD_FAILED"
ERROR_REPORT_TYPE_NOT_SUPPORTED = "REPORT_TYPE_NOT_SUPPORTED"
ERROR_REPORT_ENTITY_NOT_FOUND = "REPORT_ENTITY_NOT_FOUND"
ERROR_REPORT_LLM_FILL_FAILED = "REPORT_LLM_FILL_FAILED"
ERROR_DELIVERY_QC_NO_PACKAGE = "DELIVERY_QC_NO_PACKAGE"
