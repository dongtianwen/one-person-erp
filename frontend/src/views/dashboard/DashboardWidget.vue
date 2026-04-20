<template>
  <el-card class="dashboard-widget" v-loading="loading">
    <template #header>
      <span class="widget-title">{{ group.label }}</span>
    </template>
    <div class="widget-body">
      <MetricItem
        v-for="key in group.metrics"
        :key="key"
        :metric-key="key"
        :value="metrics[key]"
      />
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import MetricItem from './MetricItem.vue'

const props = defineProps({
  group: { type: Object, required: true },
  metrics: { type: Object, default: () => ({}) },
  loading: { type: Boolean, default: false },
})
</script>

<style scoped>
.dashboard-widget {
  height: 100%;
}
.widget-title {
  font-weight: 600;
  font-size: 15px;
}
.widget-body {
  min-height: 60px;
}
</style>
