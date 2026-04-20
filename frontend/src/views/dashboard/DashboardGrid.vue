<template>
  <div class="dashboard-grid">
    <el-row :gutter="16">
      <el-col
        v-for="group in groups"
        :key="group.key"
        :xs="24"
        :sm="12"
        :md="8"
      >
        <DashboardWidget
          :group="group"
          :metrics="metrics"
          :loading="loading"
          style="margin-bottom: 16px"
        />
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import DashboardWidget from './DashboardWidget.vue'
import { DASHBOARD_WIDGET_GROUPS } from '../../constants/dashboard'

defineProps({
  metrics: { type: Object, default: () => ({}) },
  loading: { type: Boolean, default: false },
})

const groups = DASHBOARD_WIDGET_GROUPS
</script>
