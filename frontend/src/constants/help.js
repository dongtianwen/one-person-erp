/**
 * v1.10 帮助内容静态文件——前端组件直接导入，不经过任何接口。
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
]

// ── 字段级提示 ────────────────────────────────────────────────

export const FIELD_TIPS = {
  quote: {
    estimate_days: '预计完成项目所需的工作天数，用于计算人工成本。',
    daily_rate: '每个工作日的费率（元/天），乘以工期得出人工费用。',
    risk_buffer_rate: '风险缓冲比例，如填 0.1 表示在基础金额上加 10% 缓冲。',
    valid_until: '报价有效截止日期，过期后状态自动变为已过期。',
    discount_amount: '在小计金额基础上直接减去的折扣金额（元）。',
    tax_rate: '增值税率，如 0.13 表示 13%，用于计算税额。',
  },
  contract: {
    sign_date: '合同正式签订日期，用于会计期间归属计算。',
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
]
