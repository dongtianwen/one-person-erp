<template>
  <div class="metric-item">
    <span class="metric-item-label">{{ label }}</span>
    <span class="metric-item-value">{{ displayValue }}</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { METRIC_LABELS, METRIC_FORMATTERS } from '../../constants/dashboard'

const props = defineProps({
  metricKey: { type: String, required: true },
  value: { type: [Number, String, null], default: null },
})

const label = computed(() => METRIC_LABELS[props.metricKey] || props.metricKey)
const displayValue = computed(() => {
  const formatter = METRIC_FORMATTERS[props.metricKey]
  if (formatter) return formatter(props.value)
  return props.value ?? '暂无数据'
})
</script>

<style scoped>
.metric-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}
.metric-item:last-child {
  border-bottom: none;
}
.metric-item-label {
  color: var(--el-text-color-regular);
  font-size: 13px;
}
.metric-item-value {
  font-weight: 600;
  font-size: 14px;
  color: var(--el-text-color-primary);
}
</style>
