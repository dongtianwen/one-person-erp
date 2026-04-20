export const SNAPSHOT_SCHEMAS = {
  minutes: [
    { key: 'title', label: '标题' },
    { key: 'participants', label: '参与人' },
    { key: 'conclusions', label: '结论' },
    { key: 'action_items', label: '待办事项' },
    { key: 'risk_points', label: '风险点' },
  ],
  report: [
    { key: 'title', label: '报告标题' },
    { key: 'body', label: '报告正文' },
  ],
  template: [
    { key: 'title', label: '模板标题' },
    { key: 'template_type', label: '模板类型' },
    { key: 'body', label: '正文' },
    { key: 'variables', label: '变量定义' },
    { key: 'placeholders', label: '占位符配置' },
  ],
}
