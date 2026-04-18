export const DASHBOARD_WIDGET_GROUPS = [
  {
    key: 'client',
    label: '客户概览',
    metrics: ['client_count', 'client_risk_high_count'],
  },
  {
    key: 'project',
    label: '项目概览',
    metrics: ['project_active_count', 'project_at_risk_count'],
  },
  {
    key: 'contract',
    label: '合同概览',
    metrics: ['contract_active_count', 'contract_total_amount'],
  },
  {
    key: 'finance',
    label: '财务概览',
    metrics: ['finance_receivable_total', 'finance_overdue_total', 'finance_overdue_count'],
  },
  {
    key: 'delivery',
    label: '交付概览',
    metrics: ['delivery_in_progress_count', 'delivery_completed_this_month'],
  },
  {
    key: 'agent',
    label: '经营提醒',
    metrics: ['agent_pending_count', 'agent_high_priority_count'],
  },
]

export const METRIC_LABELS = {
  client_count: '客户总数',
  client_risk_high_count: '高风险客户',
  project_active_count: '进行中项目',
  project_at_risk_count: '风险项目',
  contract_active_count: '活跃合同',
  contract_total_amount: '合同总额',
  finance_receivable_total: '应收总额',
  finance_overdue_total: '逾期总额',
  finance_overdue_count: '逾期笔数',
  delivery_in_progress_count: '交付中项目',
  delivery_completed_this_month: '本月完成',
  agent_pending_count: '待处理建议',
  agent_high_priority_count: '高优先级建议',
}

export const METRIC_FORMATTERS = {
  client_count: (v) => v ?? '暂无数据',
  client_risk_high_count: (v) => v ?? '暂无数据',
  project_active_count: (v) => v ?? '暂无数据',
  project_at_risk_count: (v) => v ?? '暂无数据',
  contract_active_count: (v) => v ?? '暂无数据',
  contract_total_amount: (v) => (v !== null && v !== undefined) ? `¥${Number(v).toLocaleString()}` : '暂无数据',
  finance_receivable_total: (v) => (v !== null && v !== undefined) ? `¥${Number(v).toLocaleString()}` : '暂无数据',
  finance_overdue_total: (v) => (v !== null && v !== undefined) ? `¥${Number(v).toLocaleString()}` : '暂无数据',
  finance_overdue_count: (v) => v ?? '暂无数据',
  delivery_in_progress_count: (v) => v ?? '暂无数据',
  delivery_completed_this_month: (v) => v ?? '暂无数据',
  agent_pending_count: (v) => v ?? '暂无数据',
  agent_high_priority_count: (v) => v ?? '暂无数据',
}
