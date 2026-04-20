export const TOOL_ENTRY_STATUSES = [
  { value: 'pending', label: '待处理' },
  { value: 'in_progress', label: '进行中' },
  { value: 'done', label: '已完成' },
  { value: 'backfilled', label: '已回填' },
]

export const LEAD_STATUSES = [
  { value: 'initial_contact', label: '初步接触' },
  { value: 'intent_confirmed', label: '意向确认' },
  { value: 'converted', label: '已转化' },
  { value: 'invalid', label: '无效' },
]

export const LEAD_SOURCES = [
  { value: 'referral', label: '朋友介绍' },
  { value: 'website', label: '平台主动询价' },
  { value: 'event', label: '展会' },
  { value: 'cold_outreach', label: '主动拓展' },
  { value: 'other', label: '其他' },
]

export const TOOL_STATUS_TAG_TYPE = {
  pending: 'info',
  in_progress: 'primary',
  done: 'success',
  backfilled: 'warning',
}

export const LEAD_STATUS_TAG_TYPE = {
  initial_contact: 'info',
  intent_confirmed: 'primary',
  converted: 'success',
  invalid: 'danger',
}

export const LEAD_TRANSITIONS = {
  initial_contact: ['intent_confirmed', 'invalid'],
  intent_confirmed: ['converted', 'invalid'],
  converted: [],
  invalid: [],
}
