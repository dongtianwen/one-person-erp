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
}
