/**
 * v2.2 帮助内容静态文件——前端组件直接导入，不经过任何接口。
 * 所有帮助内容集中在此文件：WORKFLOW_STEPS / FIELD_TIPS / PAGE_TIPS / CORE_CONCEPTS
 */

// ── 业务流程步骤 ──────────────────────────────────────────────

export const WORKFLOW_STEPS = [
  {
    id: 'quote',
    label: '报价',
    version: 'v1.6',
    description: '向客户提供报价，确认工期和费用',
    key_actions: ['创建报价单', '发送给客户', '客户接受后转合同'],
    route: '/quotations',
    triggers_next: '报价状态变为 accepted 时，可触发转合同',
  },
  {
    id: 'contract',
    label: '合同',
    version: 'v1.0',
    description: '正式合同签订，锁定项目范围和金额',
    key_actions: ['从报价单转换', '手动创建', '签订后关联项目'],
    route: '/contracts',
    triggers_next: '合同 active 后可创建关联项目',
  },
  {
    id: 'project',
    label: '项目执行',
    version: 'v1.7',
    description: '跟踪项目进度、里程碑、变更和工时',
    key_actions: ['设置里程碑', '记录工时', '提交变更单', '完成验收'],
    route: '/projects',
    triggers_next: '所有里程碑完成 + 验收通过 + 款项到账后可关闭项目',
  },
  {
    id: 'invoice',
    label: '发票',
    version: 'v1.8',
    description: '开具销项发票，关联合同和收款',
    key_actions: ['里程碑完成后开票', '确认客户收票', '财务核销'],
    route: '/finances',
    triggers_next: '发票核销后可纳入对账报表',
  },
  {
    id: 'finance',
    label: '收款与对账',
    version: 'v1.8',
    description: '记录实际收款，月末导出数据给代理记账',
    key_actions: ['记录收款', '月末导出Excel', '执行对账同步'],
    route: '/finances',
    triggers_next: '数据导出后交代理记账处理报税',
  },
  {
    id: 'risk',
    label: '风险监控',
    version: 'v1.9',
    description: '监控逾期收款、数据一致性和项目利润',
    key_actions: ['查看逾期预警', '运行数据核查', '查看项目粗利润'],
    route: '/finances',
  },
  {
    id: 'agent_decision',
    label: '智能决策',
    version: 'v2.0',
    description: 'AI 规则引擎扫描经营数据，生成建议并经人工确认后执行动作',
    key_actions: ['触发 Agent 运行', '查看生成的建议列表', '确认或拒绝每条建议', '系统自动执行已确认的动作'],
    route: '/agents/decision',
    triggers_next: '建议确认后可触发对应动作执行，高风险动作需二次确认',
  },
  {
    id: 'qa_assistant',
    label: '经营问答',
    version: 'v2.1',
    description: '用自然语言询问经营问题，AI 结合实时数据库回答（仅 api 档可用）',
    key_actions: ['输入经营相关问题', 'AI 注入实时数据上下文后回答', '多轮对话持续追问'],
    route: '/assistant/qa',
    triggers_next: '问答结果可作为决策参考，也可触发报告生成',
  },
  {
    id: 'deep_report',
    label: '深度报告',
    version: 'v2.1',
    description: '基于真实经营数据 + AI 分析，生成项目复盘或客户分析报告',
    key_actions: ['选择报告类型和目标实体', '系统拼装结构化数据', 'LLM 填充分析段落', '生成带版本号的完整报告'],
    route: '/projects',
    triggers_next: '报告中发现的经营问题可转化为待办或提醒',
  },
  {
    id: 'delivery_chain',
    label: '数据交付',
    version: 'v1.11',
    description: '管理数据集→训练实验→模型版本→交付包的完整交付链路',
    key_actions: ['创建数据集并上传文件', '创建数据集版本并冻结', '运行训练实验关联数据集', '记录产出的模型版本', '打包交付包并发起验收'],
    route: '/projects',
    triggers_next: '交付包验收通过后可触发里程碑收款流转',
  },
  {
    id: 'template_generation',
    label: '模板生成',
    version: 'v1.12',
    description: '用 Jinja2 模板一键生成报价单或合同正文，支持预览和手工编辑',
    key_actions: ['选择模板类型（方案/合同/交付）', '填写模板变量', '预览渲染结果', '确认生成内容快照', '需要时可手工编辑调整'],
    route: '/settings/templates',
    triggers_next: '报价单生成后可发送给客户，合同生成后可激活',
  },
  {
    id: 'help_guidance',
    label: '帮助引导',
    version: 'v1.10',
    description: '操作遇错时自动弹出错误解释和建议，各页面提供使用指引',
    key_actions: ['报错时查看错误解释弹窗', '点击字段旁的提示图标查看说明', '打开页面右上角帮助抽屉', '查看工作流引导了解完整业务流程'],
    route: '',
    triggers_next: '帮助内容随代码版本管理，无需额外配置',
  },
]

// ── 字段级提示 ────────────────────────────────────────────────

export const FIELD_TIPS = {
  quote: {
    estimate_days: '预计完成项目所需的工作天数，用于计算人工成本。',
    daily_rate: '每个工作日的费率（元/天），乘以工期得出人工费用。',
    risk_buffer_rate: '风险缓冲比例，如填 0.1 表示在基础金额上加 10% 缓冲。',
    valid_until: '报价有效截止日期，过期后状态自动变为已过期。',
    generated_content: '报价单生成的正文快照，基于模板渲染后存储。结构化字段变更不会自动回写此快照。',
    template_id: '生成所使用的模板 ID。为空表示该内容是手工编写而非模板生成。',
    content_generated_at: '最后一次生成时间戳。手工编辑不更新此时间，仅重新生成时更新。',
    discount_amount: '在小计金额基础上直接减去的折扣金额（元）。',
    tax_rate: '增值税率，如 0.13 表示 13%，用于计算税额。',
  },
  contract: {
    sign_date: '合同正式签订日期，用于会计期间归属计算。',
    generated_content: '合同生成的正文快照。合同激活(active)后此字段不可重新生成也不可手工编辑。',
    template_id: '生成所使用的模板 ID。为空表示手工编写。',
    content_generated_at: '最后一次生成时间戳。冻结状态下任何操作都不更新此时间。',
    amount: '合同总金额，所有发票累计开票额不得超过此金额。',
  },
  invoice: {
    invoice_date: '开票日期，用于会计期间归属，建议与实际开票一致。',
    amount_excluding_tax: '不含税金额，系统自动计算税额和价税合计。',
    tax_rate: '适用税率：一般纳税人 13%，小规模纳税人 3%。',
    received_by: '客户方收票联系人姓名或部门，便于回访确认。',
  },
  milestone: {
    payment_amount: '该里程碑对应的收款金额，完成后才能触发开票流程。',
    payment_due_date: '预计收款截止日期，超期未收款将出现在逾期预警中。',
    payment_status: 'unpaid=未付款，invoiced=已开票，received=款项已到账。',
  },
  change_order: {
    extra_days: '此次变更增加的预计工作天数，0 表示非工期变更。',
    extra_amount: '此次变更增加的费用（元），可为 0（非付费变更）。',
    status: 'pending=等待客户确认，confirmed=已确认可进入开发，rejected/cancelled=终态。',
  },
  work_hour: {
    hours_spent: '本次实际投入的工作小时数，用于计算项目工时成本。',
    deviation_note: '当实际工时超出预计 20% 时必填，说明超出原因。',
  },
  fixed_cost: {
    period: 'monthly=月费，quarterly=季费，yearly=年费，onetime=一次性费用。',
    effective_date: '该成本条目开始生效日期，月度汇总从此日期起统计。',
    end_date: '该成本条目失效日期，留空表示持续有效。',
  },
  agent: {
    run_status: 'Agent 运行状态：running=运行中, completed=已完成, failed=运行失败。同一类型不可并发。',
    suggestion_type: '建议类型分类：risk=风险预警, warning=一般警告, action=行动建议, info=信息提示。',
    confirmation_result: '用户对建议的确认结果：accepted=接受并执行, rejected=拒绝不执行。已处理的建议不可重复操作。',
  },
  report: {
    report_type: '报告类型：report_project=项目复盘报告, report_customer=客户价值分析报告。每种类型使用不同模板和分析维度。',
    entity_id: '目标实体的 ID，对于项目报告是 project_id，对于客户报告是 client_id。实体必须存在才能生成报告。',
    version_no: '报告版本号，同一实体多次生成时自动递增。可通过版本号对比历史版本的差异。',
  },
  delivery_qc: {
    package_id: '质检目标的交付包 ID，关联到具体的交付包记录。交付包不存在则无法执行质检。',
    qc_result: '质检结果：pass=全部通过, fail=存在缺失项, partial=部分通过。基于规则层检查，不含文件内容审查。',
  },
  dataset: {
    name: '数据集名称，用于标识一组相关数据的集合。',
    data_type: '数据类型分类（image/text/audio/tabular 等），决定前端展示方式。',
    project_id: '关联的项目 ID，一个数据集属于一个项目。',
  },
  dataset_version: {
    version_no: '版本号，同一数据集多次提交时自动递增。',
    status: '版本状态：draft=草稿(可编辑), ready=就绪(可用于训练), in_use=被实验引用(不可删), archived=已归档。',
    sample_count: '样本数量，用于估算训练数据规模。',
    label_schema_version: '对应标注规范版本号，确保标注一致性。',
  },
  annotation_task: {
    task_type: '标注任务类型（classification/detection/segmentation 等）。',
    status: '任务状态：pending=待处理, running=进行中, completed=已完成, failed=失败。',
    quality_score: '质检评分（0~100），低于阈值需返工重新标注。',
  },
  training_experiment: {
    framework: '训练框架（pytorch/tensorflow/mxnet 等），决定实验环境配置。',
    hyperparameters: '超参数 JSON 字符串，记录学习率、批大小等关键训练参数。',
    status: '实验状态：planning=规划中, running=训练中, completed=已完成, cancelled=已取消。关联数据集后核心配置冻结。',
  },
  model_version: {
    version_no: '模型版本号，同一次实验可产出多个版本，按顺序递增。',
    metrics: '评估指标 JSON 字符串（accuracy/f1/recall 等），记录模型在测试集上的表现。',
    status: '模型状态：ready=待交付, delivered=已交付, deprecated=已废弃。delivered 后核心字段冻结。',
  },
  delivery_package: {
    package_type: '交付包类型（model=模型包/dataset=数据包/documentation=文档包）。',
    status: '交付状态：preparing=准备中, delivered=已交付, accepted=验收通过。验收通过后不可修改。',
  },
  template: {
    template_type: '模板类型枚举：proposal=方案, contract=合同, delivery=交付。后续扩展：retrospective=复盘, quotation_calc=报价计算。',
    content: 'Jinja2 模板正文，包含 {{variable}} 占位符。变量必须在对应类型的 REQUIRED_VARS 白名单中。',
    is_default: '是否为默认模板。默认模板不可删除，生成时优先选用。可通过「设为默认」切换。',
  },
  finance_all: {
    type: '收支类型：income=收入(正数绿色), expense=支出(负数红色)。',
    category: '费用分类，如人工成本、外包、差旅、设备、房租等。',
    funding_source: '资金来源：公司账户/垫付/借款等。影响结算和报销流程。',
    settlement_status: '结算状态，标识该笔款项是否已完成对账或报销。',
  },
  finance_export: {
    export_type: '导出数据类型：contracts=合同, payments=收款记录, invoices=发票数据。',
    target_format: '目标格式：当前仅支持 generic(通用CSV)，金蝶/用友格式暂未开放。',
  },
  finance_consistency: {
    gap: '差异金额（合同金额 - 已收款）。正值=未收足，负值=多收。',
  },
  finance_reconciliation: {
    reconciliation_period: '对账周期，通常按月度或季度进行收支核对汇总。',
    breakdown: '客户维度分解，按客户汇总收支数据，用于核对各客户的往来余额。',
  },
  project_tasks: {
    task_name: '任务名称，建议使用动词+名词格式（如"完成需求分析"）。',
    task_status: '任务状态：todo=待办, in_progress=进行中, done=完成, blocked=阻塞。',
    assignee: '任务负责人，可分配给项目成员或外部协作者。',
    due_date: '截止日期，逾期任务会在提醒模块中高亮显示。',
  },
  project_milestones: {
    milestone_name: '里程碑名称，代表项目关键节点（如"原型交付"、"UAT验收"）。',
    planned_date: '计划完成日期，用于跟踪进度偏差。',
    actual_date: '实际完成日期，晚于计划则标记延期。',
    payment_ratio: '该里程碑对应的收款比例（%），累计不应超过 100%。',
  },
  project_requirements: {
    requirement_title: '需求标题，简明描述功能点或用户故事。',
    priority: '需求优先级：P0=必须, P1=重要, P2=一般, P3=可选。',
    status: '需求状态：draft=草稿, approved=已批准, developing=开发中, verified=已验证, done=已完成。',
  },
  project_acceptances: {
    acceptance_name: '验收项名称，对应具体的功能点或交付物。',
    acceptance_result: '验收结果：pass=通过, fail=不通过, pending=待验。',
    signed_at: '客户签字确认时间，签字后不可修改验收结果。',
  },
  project_deliverables: {
    deliverable_name: '交付物名称，如文档、代码包、设计稿等。',
    version: '交付物版本号，同一交付物多次提交自动递增。',
    delivery_status: '交付状态：pending=待交付, delivered=已交付, accepted=客户已接收。',
  },
  project_releases: {
    release_version: '版本号，遵循语义化格式（如 v1.2.3）。',
    release_notes: '版本说明，记录本次发布的主要变更内容。',
    release_date: '发布日期，标记版本正式上线的时间。',
  },
  project_maintenance: {
    ticket_title: '工单标题，描述客户反馈的问题或新需求。',
    severity: '严重程度：critical=致命, high=严重, medium=一般, low=轻微。',
    sla_response_time: 'SLA 响应时限，不同严重等级有不同响应承诺。',
  },
  project_change_summary: {
    change_type: '变更类型：scope=范围, schedule=进度, cost=成本, resource=资源。',
    impact_level: '影响程度：low=低, medium=中, high=高。高影响需走正式审批。',
  },
  project_milestone_payment: {
    payment_amount: '本次收款金额，应与里程碑约定的付款比例一致。',
    payment_method: '收款方式：bank_transfer=银行转账, cash=现金, check=支票, other=其他。',
    received_date: '实际到账日期，与计划收款日的差异影响现金流预测。',
  },
}

// ── 页面帮助 ──────────────────────────────────────────────────

export const PAGE_TIPS = {
  quote_list: {
    title: '报价单',
    description: '管理向客户提供的报价，报价被接受后可一键转换为合同。',
    tips: [
      '报价状态流转：草稿 → 已发送 → 已接受/已拒绝',
      '只有「已接受」状态的报价单才能转换为合同',
      '报价超过有效期会自动标记为已过期',
      '已接受的报价单核心字段不可修改，只能改备注',
    ],
  },
  project_list: {
    title: '项目管理',
    description: '管理所有项目，跟踪项目状态、进度和关键指标。',
    tips: [
      '项目状态流转：意向 → 进行中 → 已交付 → 已关闭',
      '点击"管理"按钮进入项目详情，可管理里程碑、任务、工时等',
      '项目关联报价单被接受后，需求自动冻结',
      '关闭项目前需满足：里程碑完成、验收通过、款项到账',
    ],
  },
  project_detail: {
    title: '项目详情',
    description: '跟踪单个项目的执行状态、里程碑、工时和变更情况。',
    tips: [
      '项目关联报价被接受后，需求自动冻结，变更须通过变更单提交',
      '里程碑完成后才能触发对应收款流转',
      '关闭项目前需满足：所有里程碑完成、验收通过、款项到账、有交付物',
      '工时记录超出预计 20% 时，偏差备注为必填项',
    ],
  },
  project_tasks_tab: {
    title: '任务',
    description: '管理项目任务，跟踪任务状态、负责人和截止日期。',
    tips: [
      '任务状态：待办 → 进行中 → 完成 → 阻塞',
      '逾期任务会在提醒模块中高亮显示',
      '任务可关联里程碑，完成后自动更新进度',
    ],
  },
  project_milestones_tab: {
    title: '里程碑',
    description: '管理项目里程碑，里程碑是项目的关键节点。',
    tips: [
      '里程碑完成后可触发对应的收款流转',
      '收款比例累计不应超过 100%',
      '实际完成日期晚于计划日期会标记延期',
    ],
  },
  project_requirements_tab: {
    title: '需求',
    description: '管理项目需求，记录功能点和优先级。',
    tips: [
      '需求优先级：P0(必须) > P1(重要) > P2(一般) > P3(可选)',
      '项目关联报价被接受后，需求自动冻结',
      '变更需求需通过变更单提交',
    ],
  },
  project_acceptances_tab: {
    title: '验收',
    description: '记录项目验收项和验收结果。',
    tips: [
      '验收结果：通过 / 不通过 / 待验',
      '客户签字确认后不可修改验收结果',
      '所有验收项通过后才能关闭项目',
    ],
  },
  project_deliverables_tab: {
    title: '交付物',
    description: '管理项目交付物，如文档、代码包、设计稿等。',
    tips: [
      '同一交付物多次提交会自动递增版本号',
      '交付状态：待交付 → 已交付 → 客户已接收',
      '关闭项目前需至少有一个交付物',
    ],
  },
  project_releases_tab: {
    title: '版本',
    description: '管理项目版本发布记录。',
    tips: [
      '版本号遵循语义化格式（如 v1.2.3）',
      '版本说明记录本次发布的主要变更',
      '发布日期标记版本正式上线的时间',
    ],
  },
  project_maintenance_tab: {
    title: '售后',
    description: '管理项目售后工单和问题跟踪。',
    tips: [
      '严重程度：致命 > 严重 > 一般 > 轻微',
      '不同严重等级有不同的 SLA 响应时限',
      '工单可关联具体的交付物或版本',
    ],
  },
  project_change_summary_tab: {
    title: '变更单摘要',
    description: '查看项目变更单的汇总信息。',
    tips: [
      '变更类型：范围变更 / 进度变更 / 成本变更 / 资源变更',
      '高影响变更需走正式审批流程',
      '变更单关联报价被接受后自动生效',
    ],
  },
  project_change_orders_tab: {
    title: '变更单管理',
    description: '管理项目变更单，记录需求变更和影响。',
    tips: [
      '需求冻结后才能创建变更单',
      '变更单状态：待确认 → 已确认 / 已拒绝 / 已撤回',
      '确认后自动更新项目工期和金额',
    ],
  },
  project_work_hours_tab: {
    title: '工时记录',
    description: '记录项目实际工时，计算人力成本。',
    tips: [
      '工时偏差率 = (实际工时 - 预计工时) / 预计工时',
      '偏差超过阈值时需填写偏差备注',
      '人力成本 = 实际工时 / 8 × 日费率',
    ],
  },
  project_milestone_payment_tab: {
    title: '里程碑收款',
    description: '管理里程碑对应的收款记录。',
    tips: [
      '收款金额应与里程碑约定的付款比例一致',
      '实际到账日期影响现金流预测',
      '收款方式支持银行转账、现金、支票等',
    ],
  },
  project_datasets_tab: {
    title: '数据集',
    description: '管理项目中的数据集及其版本。',
    tips: [
      '每个数据集可有多个版本，每次提交产生新版本号',
      '版本状态变为 ready 后核心字段自动冻结',
      '被训练实验引用的版本不可删除',
    ],
  },
  project_annotation_tasks_tab: {
    title: '标注任务',
    description: '管理数据标注任务的执行情况。',
    tips: [
      '标注任务负责"怎么做"，需求规范负责"做什么"',
      '质检不合格的任务需标记返工',
      '任务完成后可关联到对应的数据集版本',
    ],
  },
  project_training_experiments_tab: {
    title: '训练实验',
    description: '管理模型训练实验的配置和产出。',
    tips: [
      '关联数据集版本后，核心配置自动冻结',
      '一次实验可产出多个模型版本',
      '实验状态支持：规划中 / 训练中 / 已完成 / 已取消',
    ],
  },
  project_model_versions_tab: {
    title: '模型版本',
    description: '管理训练实验产出的模型版本。',
    tips: [
      '每个版本独立记录评估指标',
      '状态为已交付后核心字段冻结',
      '模型版本可打包到交付包中',
    ],
  },
  project_delivery_packages_tab: {
    title: '交付包',
    description: '将模型版本、数据集版本等打包形成交付单元。',
    tips: [
      '交付包类型：模型包 / 数据包 / 文档包',
      '必须通过验收才能关闭交付流程',
      '验收记录通过 delivery_package_id 关联',
    ],
  },
  contract_detail: {
    title: '合同详情',
    description: '查看合同信息、关联发票和收款记录。',
    tips: [
      '合同关联的所有发票金额累计不得超过合同总金额',
      '发票状态：草稿 → 已开票 → 客户已收 → 已核销',
      '已核销和已作废的发票不可删除',
    ],
  },
  finance_export: {
    title: '财务导出',
    description: '将业务数据导出为 Excel 文件，供代理记账使用。',
    tips: [
      '当前支持通用 Excel 格式，交代理记账导入其财务软件',
      '每次导出生成唯一批次号，可追溯导出记录',
      '导出失败时批次记录保留但无下载链接',
    ],
  },
  reconciliation: {
    title: '对账报表',
    description: '按自然月查看合同、收款、发票的汇总对账数据。',
    tips: [
      '期初余额 = 上月期末余额；系统第一期期初为 0',
      '「未对账记录」= 有合同但未关联发票的收款，需人工确认',
      '此报表为业务视角汇总，非会计准则下的财务报表',
    ],
  },
  consistency_check: {
    title: '数据核查',
    description: '检查合同、收款、发票三张表的数据是否一致。',
    tips: [
      '核查为只读操作，不会修改任何数据',
      '「未收款差异」= 合同金额 > 实收总额',
      '「核销差异」= 已核销发票总额与实收金额不一致',
      '差异金额低于 0.01 元不报告',
    ],
  },
  profit_view: {
    title: '利润分析',
    description: '查看项目的粗利润估算（业务视角，非会计利润）。',
    tips: [
      '收入基准为实收金额，不是合同金额',
      '工时成本 = 实际工时（小时）÷ 8 × 日费率',
      '无工时记录或无日费率时，工时成本显示为空',
      '固定成本和进项发票需手动关联到项目才计入',
    ],
  },
  agent_decision: {
    title: 'AI 经营决策',
    description: '规则引擎扫描经营数据后生成结构化建议，经人工确认后由系统执行对应动作，形成可审计的经营闭环。',
    tips: [
      '点击「运行决策」手动触发 Agent，系统不会自动运行',
      '三档 Provider：none=纯规则输出, local=Ollama 本地增强, api=外部 API 增强',
      '所有建议必须逐条确认或拒绝，不可批量操作',
      '低风险动作（创建待办、创建提醒）自动执行；高风险动作（修改合同、关闭项目）需二次确认',
      '每次运行的完整记录保留在「Agent 日志」页面中',
    ],
  },
  agent_logs: {
    title: 'Agent 运行日志',
    description: '查看 AI 智能体的历史运行记录，包括触发的建议列表、用户的确认决策和系统执行的动作结果。',
    tips: [
      '日志按时间倒序排列，最新的运行记录在最上方',
      '点击单条日志可展开查看该次运行的所有建议详情',
      '每条建议都记录了用户的确认/拒绝决策及时间戳',
      '已完成的运行不可删除，仅做只读查阅',
    ],
  },
  qa_assistant: {
    title: '经营问答助手',
    description: '用自然语言向 AI 提问经营相关的问题，系统会注入当前数据库中的实时经营数据作为上下文来回答。',
    tips: [
      '此功能仅在 LLM_PROVIDER=api 时可用，local/none 档不显示入口',
      '对话历史由前端维护，每次发送时将完整历史传给后端，不落库存储',
      'AI 回答基于实时数据库快照，但可能存在几分钟的数据延迟',
      '适合问：「本月利润多少」「哪个客户贡献最大」「逾期款项有哪些」等问题',
    ],
  },
  datasets: {
    title: '数据集管理',
    description: '管理项目中使用的数据集及其版本，追踪从原始数据到训练就绪的完整链路。',
    tips: [
      '每个数据集可有多个版本，每次提交产生新版本号',
      '版本状态变为 ready 或更高时核心字段自动冻结',
      '被训练实验引用(in_use)的版本不可删除',
      '可在项目详情的数据集 Tab 中查看和管理',
    ],
  },
  annotation_tasks: {
    title: '标注任务',
    description: '记录数据标注任务的执行情况、质检结果和返工记录。',
    tips: [
      '标注任务负责"怎么跑"，需求规范(requirements)负责"是什么"',
      '质检不合格的任务需标记返工并重新执行',
      '任务完成后可关联到对应的数据集版本',
    ],
  },
  training_experiments: {
    title: '训练实验',
    description: '记录模型训练实验的配置、过程和产出结果。',
    tips: [
      '一旦关联了数据集版本，实验的核心配置(project_id/framework/hyperparameters)将冻结',
      '实验可产出多个模型版本，每个版本独立记录评估指标',
      '实验状态支持 planning/running/completed/cancelled 四种流转',
      '完成的实验可作为模型版本的来源',
    ],
  },
  templates: {
    title: '模板管理',
    description: '管理 Jinja2 文本模板，用于一键生成报价单和合同正文。',
    tips: [
      '模板使用 {{variable}} 占位符，变量来自系统真实数据自动拼装',
      '必填变量缺失时无法生成，可选变量缺失用空字符串代替',
      '默认模板不可删除，但可设为非默认后再删除',
      '删除非默认模板不影响历史已生成的内容快照',
      '模板类型分为方案/合同/交付三类，每类使用不同的变量白名单',
    ],
  },
  finance_all: {
    title: '全部记录',
    description: '查看所有收支记录，支持按类型、状态、资金来源筛选。',
    tips: [
      '收入显示为绿色正数，支出显示为红色负数',
      '资金来源为公司账户的记录直接入账，垫付/借款需后续结算',
      '结算状态标识该笔款项是否已完成对账或报销',
    ],
  },
  invoice_ledger: {
    title: '发票台账',
    description: '按季度查看销项发票（开给客户的）和进项发票（收到的）汇总。',
    tips: [
      '销项发票来自合同关联的发票记录',
      '可按年份和季度筛选，用于税务申报核对',
      '税额自动按税率计算',
    ],
  },
  fixed_costs: {
    title: '固定成本',
    description: '管理周期性固定支出，如房租、工资、服务费等。',
    tips: [
      '周期类型：月度/季度/年度，影响月度汇总计算',
      '生效日期和截止日期决定该成本在哪些月份有效',
      '月度汇总显示当月有效成本条目的原始金额',
    ],
  },
  input_invoices: {
    title: '进项发票',
    description: '管理收到的供应商发票，用于增值税抵扣。',
    tips: [
      '进项发票可用于增值税抵扣',
      '发票号、供应商、金额为必填项',
      '可关联到项目或固定成本',
    ],
  },
  file_indexes: {
    title: '文件索引',
    description: '管理系统中所有上传文件的索引记录，支持按类型和关联实体检索。',
    tips: [
      '文件索引记录元数据信息，不存储实际文件内容',
      '可按 file_type 和关联实体(project/customer/contract) 过滤',
      '删除文件索引不影响已生成的报告或模板内容',
    ],
  },
  dashboard: {
    title: '首页仪表盘',
    description: '经营数据总览面板，展示收入、支出、项目、客户等关键指标和趋势图表。',
    tips: [
      '指标卡片点击可跳转到对应详情页面',
      '营收趋势图展示近 12 个月的收支对比',
      '现金流预测展示未来 90 天的净额趋势',
      '逾期预警显示超期未收款的里程碑',
    ],
  },
  customer_list: {
    title: '客户管理',
    description: '管理所有客户信息，客户是合同、报价单、项目的签约主体。',
    tips: [
      '一个客户可关联多份合同和多个项目',
      '删除客户前需确认无关联的合同和项目',
      '客户详情页可查看该客户下的全部经营数据',
    ],
  },
  customer_detail: {
    title: '客户详情',
    description: '查看单个客户的完整信息，包括关联的合同、项目和 LTV 分析。',
    tips: [
      'LTV（客户生命周期价值）基于该客户的所有实收金额计算',
      '可在此页面快速创建该客户的新合同或项目',
      '客户状态变更会影响相关项目的可用操作',
    ],
  },
  reminders: {
    title: '提醒事项',
    description: '管理各类经营提醒，包括年报、税务、合同到期、任务截止等。',
    tips: [
      '支持设置关键(is_critical)提醒，优先级更高',
      '过期提醒会以红色高亮显示',
      '提醒类型包括年报/税务/合同到期/任务截止/文件到期/自定义',
      '可在创建时指定关联实体（项目/合同/文件）以便快速跳转',
    ],
  },
  company_settings: {
    title: '公司设置',
    description: '配置公司基本信息和 AI 智能体参数。',
    tips: [
      '公司名称用于自动填充模板变量 {{company_name}}',
      'LLM Provider 配置影响 AI 决策和问答功能的可用性',
      '切换 Provider 后需重启后端服务生效',
      'Agent 运行间隔控制自动触发的频率',
    ],
  },
  workflow_guide: {
    title: '业务流程引导',
    description: '查看完整的业务流程步骤说明，了解从报价到收款的标准操作路径。',
    tips: [
      '流程按推荐顺序排列，每步标注版本号',
      'triggers_next 字段说明该步骤完成后建议的下一步操作',
      '可结合各页面的帮助抽屉深入了解具体操作',
      '不同版本的新功能会在流程中自然衔接',
    ],
  },
}

// ── 核心概念 ──────────────────────────────────────────────────

export const CORE_CONCEPTS = [
  {
    term: '客户（Customer）',
    definition: '合同的签约主体（公司或个人），不是具体联系人。一个客户可对应多份合同和多个项目。',
    related: ['合同', '报价单', '发票', '收款'],
  },
  {
    term: '合同（Contract）',
    definition: '与客户签订的正式服务协议。合同金额是收款和发票的核对基准，不等于实收金额。',
    related: ['发票', '收款', '项目'],
    key_rule: '所有发票金额累计不得超过合同金额',
  },
  {
    term: '项目（Project）',
    definition: '合同的执行单元。通常一份合同对应一个项目。是里程碑、工时、变更单、验收的归属容器。',
    related: ['合同', '里程碑', '工时记录', '变更单'],
    key_rule: '项目关闭需满足：里程碑全完成、验收通过、款项到账、有交付物',
  },
  {
    term: '里程碑（Milestone）',
    definition: '项目中的阶段性交付节点，必须绑定收款金额。完成后才能触发开票和收款流转。',
    related: ['项目', '收款'],
    key_rule: '里程碑未完成不可触发开票，完成后才可标记收款状态',
  },
  {
    term: '需求（Requirement）',
    definition: '项目的功能需求记录。报价被客户接受后自动冻结，冻结后变更须走变更单流程。',
    related: ['项目', '报价单', '变更单'],
    key_rule: '冻结后直接修改需求会报错 REQUIREMENT_FROZEN',
  },
  {
    term: '收款记录（FinanceRecord）',
    definition: '实际到账的款项。是粗利润计算的收入基准（不用合同金额）。可关联发票，也可不关联。',
    related: ['合同', '发票', '项目'],
    key_rule: '无合同关联的收款记录会出现在数据核查的「未对账记录」中',
  },
  {
    term: '销项发票（Invoice）',
    definition: '你开给客户的发票。必须关联合同，累计金额不超合同总额。已核销（verified）为终态。',
    related: ['合同', '收款'],
    key_rule: 'invoices.status=verified 是「已核销」的唯一来源，用于数据一致性校验',
  },
  {
    term: '变更单（ChangeOrder）',
    definition: '需求冻结后，新增或修改需求的正式入口。需客户确认（confirmed）才能进入开发。',
    related: ['需求', '项目'],
    key_rule: 'confirmed 的变更单才允许关联里程碑或纳入开发',
  },
  {
    term: 'Agent 运行（AgentRun）',
    definition: '一次完整的智能体执行过程。包含触发时间、使用的 Provider 类型、规则引擎扫描结果、生成的建议列表以及用户确认后执行的动作记录。',
    related: ['建议', '动作执行', '人工确认'],
    key_rule: '同一类型的 Agent 不可并发运行，必须等上一次完成后才能再次触发',
  },
  {
    term: '建议（Suggestion）',
    definition: '规则引擎读取真实经营数据后，按预定义阈值判断输出的结构化建议。每条建议包含类型（risk/warning/action/info）、标题、描述和置信度。',
    related: ['Agent运行', '人工确认', '动作执行'],
    key_rule: '每条建议必须经用户明确确认（accepted）或拒绝（rejected）后才可执行或跳过对应的动作',
  },
  {
    term: '动作执行（ActionExecution）',
    definition: '用户确认建议后系统实际执行的操作记录。包括创建待办、创建提醒、修改合同状态等。高风险动作需要二次确认。',
    related: ['Agent运行', '建议', '人工确认'],
    key_rule: '高风险动作（修改合同金额、关闭项目、变更项目范围）在确认后还需二次确认才真正执行',
  },
  {
    term: '深度报告（Report）',
    definition: '基于数据库中的结构性真实数据（工时、里程碑、收款、变更记录等）拼装框架，再由 LLM 填充分析段落生成的文档。支持项目复盘和客户分析两类。',
    related: ['项目', '客户', '模板管理'],
    key_rule: '同一实体多次生成会产生版本链（version_no 递增），LLM 填充失败时降级为占位文本但不阻断生成',
  },
  {
    term: '交付质检（DeliveryQC）',
    definition: '对交付包进行完整性检查和质量评估的能力。规则层检查交付包是否包含模型版本、验收记录、数据集版本等必要要素，LLM 层负责语言化描述质检结论。',
    related: ['交付包', '项目', '验收'],
    key_rule: '仅做元数据和状态层面的规则检查，不读取实际文件内容，不做主观质量评判',
  },
  {
    term: '数据集（Dataset）',
    definition: '一组相关数据的逻辑集合，归属于某个项目。可包含多个版本，每个版本代表一次数据提交。',
    related: ['数据集版本', '训练实验', '项目'],
    key_rule: '数据集删除时必须无关联的版本和实验引用',
  },
  {
    term: '数据集版本（DatasetVersion）',
    definition: '数据集的一次具体提交记录，包含样本数、数据来源、标注规范版本等元数据。status 达到 ready 后核心字段冻结。',
    related: ['数据集', '训练实验'],
    key_rule: '冻结状态下(version_no/sample_count/file_path 等)不可修改，仅 notes 和 change_summary 可编辑',
  },
  {
    term: '标注任务（AnnotationTask）',
    definition: '数据标注任务的执行记录，描述一批数据如何标注、谁来质检、质量标准是什么。与需求规范(annotation_spec)分离：任务管"怎么做"，规范管"是什么"。',
    related: ['数据集', '需求', '项目'],
    key_rule: '质检不合格的任务必须标记返工，不能直接标记完成',
  },
  {
    term: '训练实验（TrainingExperiment）',
    definition: '模型训练实验的完整记录，包括框架选择、超参数配置、关联的数据集版本和产出的模型列表。',
    related: ['数据集版本', '模型版本', '项目'],
    key_rule: '关联任意数据集版本后，project_id/framework/hyperparameters 冻结不可改（EXPERIMENT_FROZEN）',
  },
  {
    term: '模型版本（ModelVersion）',
    definition: '一次训练实验产出的具体模型版本，包含文件路径、评估指标和交付状态。',
    related: ['训练实验', '交付包'],
    key_rule: '状态为 delivered 后核心字段冻结（MODEL_VERSION_FROZEN），仅 notes 可编辑',
  },
  {
    term: '交付包（DeliveryPackage）',
    definition: '将模型版本、数据集版本、文档等打包形成的交付单元，用于发起验收流程。',
    related: ['模型版本', '验收记录', '项目'],
    key_rule: '必须通过验收(acceptance)才能关闭交付流程，验收记录通过 delivery_package_id 关联',
  },
  {
    term: '模板（Template）',
    definition: '基于 Jinja2 语法的文本模板，定义报价单或合同的正文格式和变量占位符。系统根据白名单变量自动拼装数据后渲染输出。',
    related: ['报价单', '合同', '模板管理'],
    key_rule: '必填变量缺失无法生成(TEMPLATE_MISSING_REQUIRED_VARS)，模板语法错误渲染失败(TEMPLATE_RENDER_FAILED)',
  },
  {
    term: '内容冻结（ContentFreeze）',
    definition: '报价单状态为 accepted 或合同状态为 active 时，generated_content 不可重新生成且不可手工编辑的保护机制。',
    related: ['报价单', '合同', '模板'],
    key_rule: '冻结状态下即使 force=true 也拒绝重新生成，返回 CONTENT_FROZEN 错误；但 GET /preview 预览仍允许',
  },
  {
    term: '内容快照（ContentSnapshot）',
    definition: '模板渲染后存储在 quotations/contracts 表 generated_content 字段中的文本副本。是生成时刻的快照，之后结构化字段变更不会自动回写。',
    related: ['报价单', '合同', '模板'],
    key_rule: '手工编辑快照不更新 content_generated_at 时间戳；重新生成(force=true)会覆盖旧快照并更新时间戳',
  },
]
