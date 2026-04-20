<template>
  <div class="dashboard-header">
    <h2 style="margin: 0; font-size: 18px">经营仪表盘</h2>
    <div class="dashboard-header-actions">
      <span v-if="lastRefreshTime" class="last-refresh">
        最后刷新：{{ lastRefreshTime }}
      </span>
      <el-button
        type="primary"
        :icon="Refresh"
        :loading="refreshing"
        @click="$emit('refresh')"
      >
        手动刷新
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { Refresh } from '@element-plus/icons-vue'

defineProps({
  lastRefreshTime: { type: String, default: '' },
  refreshing: { type: Boolean, default: false },
})

defineEmits(['refresh'])
</script>

<style scoped>
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.dashboard-header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.last-refresh {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
