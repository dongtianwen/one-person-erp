<template>
  <div class="dashboard">
    <DashboardHeader
      :last-refresh-time="lastRefreshTime"
      :refreshing="refreshing"
      @refresh="handleRefresh"
    />
    <PageHelpDrawer pageKey="dashboard" />

    <DashboardGrid
      :metrics="summaryMetrics"
      :loading="summaryLoading"
    />

    <slot />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import DashboardHeader from './DashboardHeader.vue'
import DashboardGrid from './DashboardGrid.vue'
import { getDashboardSummary, rebuildDashboardSummary } from '../../api/dashboard'
import { useApiWarning } from '../../composables/useApiWarning'

const { handleResponse } = useApiWarning()

const summaryMetrics = ref({})
const summaryLoading = ref(false)
const refreshing = ref(false)
const lastRefreshTime = ref('')

const loadSummary = async () => {
  summaryLoading.value = true
  try {
    const { data } = await getDashboardSummary()
    handleResponse(data)
    summaryMetrics.value = data.metrics || {}
    lastRefreshTime.value = new Date().toLocaleString('zh-CN')
  } catch {
    summaryMetrics.value = {}
  } finally {
    summaryLoading.value = false
  }
}

const handleRefresh = async () => {
  refreshing.value = true
  try {
    const { data } = await rebuildDashboardSummary()
    handleResponse(data)
    await loadSummary()
  } catch {
    // error already handled by interceptor
  } finally {
    refreshing.value = false
  }
}

onMounted(() => { loadSummary() })

defineExpose({ loadSummary })
</script>
