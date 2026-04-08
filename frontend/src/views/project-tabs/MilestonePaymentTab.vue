<!-- v1.7 里程碑收款绑定 Tab -->
<template>
  <div class="milestone-payment-tab">
    <!-- 收款汇总卡片 -->
    <el-card class="summary-card" shadow="never">
      <template #header>
        <span>收款汇总</span>
      </template>
      <el-row :gutter="16" v-loading="summaryLoading">
        <el-col :span="6">
          <div class="summary-item">
            <div class="summary-label">合同金额</div>
            <div class="summary-value mono">¥{{ formatNumber(summary.total_contract_amount) }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="summary-item">
            <div class="summary-label">里程碑总额</div>
            <div class="summary-value mono">¥{{ formatNumber(summary.total_milestone_amount) }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="summary-item success">
            <div class="summary-label">已到账</div>
            <div class="summary-value mono">¥{{ formatNumber(summary.received_amount) }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="summary-item warning">
            <div class="summary-label">待收款</div>
            <div class="summary-value mono">¥{{ formatNumber(summary.unpaid_amount) }}</div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 逾期未收款里程碑 -->
    <el-card v-if="summary.overdue_milestones?.length > 0" class="overdue-card" shadow="never">
      <template #header>
        <span class="overdue-title">⚠️ 逾期未收款里程碑 ({{ summary.overdue_milestones.length }})</span>
      </template>
      <el-table :data="summary.overdue_milestones" size="small" max-height="200">
        <el-table-column prop="title" label="里程碑" min-width="150" />
        <el-table-column prop="payment_amount" label="金额" width="100" align="right">
          <template #default="{ row }">
            <span class="mono">¥{{ formatNumber(row.payment_amount) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="payment_due_date" label="应付款日期" width="110" />
        <el-table-column label="逾期天数" width="80" align="right">
          <template #default="{ row }">
            <span class="mono text-danger">{{ row.days_overdue }} 天</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button
              v-if="row.payment_status === 'unpaid'"
              link
              type="primary"
              size="small"
              @click="markInvoiced(row)"
            >
              标记开票
            </el-button>
            <el-button
              v-if="row.payment_status === 'invoiced'"
              link
              type="success"
              size="small"
              @click="markReceived(row)"
            >
              标记到账
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 里程碑列表 -->
    <el-card shadow="never" style="margin-top: 16px;">
      <template #header>
        <span>里程碑收款状态</span>
      </template>
      <el-table :data="milestones" v-loading="loading" stripe>
        <el-table-column prop="title" label="里程碑" min-width="150" />
        <el-table-column prop="due_date" label="计划日期" width="110" />
        <el-table-column label="完成状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_completed ? 'success' : 'info'" size="small">
              {{ row.is_completed ? '已完成' : '进行中' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="payment_amount" label="收款金额" width="100" align="right">
          <template #default="{ row }">
            <span class="mono">{{ row.payment_amount ? '¥' + formatNumber(row.payment_amount) : '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="payment_due_date" label="应付款日期" width="110">
          <template #default="{ row }">
            <span class="mono">{{ row.payment_due_date || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="收款状态" width="90">
          <template #default="{ row }">
            <el-tag :type="paymentStatusType(row.payment_status)" size="small">
              {{ paymentStatusLabel(row.payment_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="payment_received_at" label="到账时间" width="160">
          <template #default="{ row }">
            <span class="mono">{{ formatDateTime(row.payment_received_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button
              link
              type="primary"
              size="small"
              :disabled="!row.is_completed || row.payment_status === 'received'"
              @click="handleMarkInvoiced(row)"
            >
              标记开票
            </el-button>
            <el-button
              link
              type="success"
              size="small"
              :disabled="row.payment_status !== 'invoiced'"
              @click="handleMarkReceived(row)"
            >
              标记到账
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as v17Api from '../../api/v17'
import { getMilestones } from '../../api/projects'

const props = defineProps({
  projectId: { type: Number, required: true }
})

const loading = ref(false)
const summaryLoading = ref(false)
const milestones = ref([])
const summary = ref({
  total_contract_amount: 0,
  total_milestone_amount: 0,
  received_amount: 0,
  invoiced_amount: 0,
  unpaid_amount: 0,
  overdue_milestones: []
})

const formatNumber = (num) => {
  if (num == null) return '0'
  return Number(num).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

const formatDateTime = (dt) => {
  if (!dt) return '-'
  return new Date(dt).toLocaleString('zh-CN')
}

const paymentStatusType = (status) => {
  const types = {
    unpaid: 'danger',
    invoiced: 'warning',
    received: 'success'
  }
  return types[status] || 'info'
}

const paymentStatusLabel = (status) => {
  const labels = {
    unpaid: '未付款',
    invoiced: '已开票',
    received: '已到账'
  }
  return labels[status] || status
}

const loadData = async () => {
  loading.value = true
  summaryLoading.value = true
  try {
    // 并行加载里程碑和汇总数据
    const [milestonesRes, summaryRes] = await Promise.all([
      getMilestones(props.projectId),
      v17Api.getProjectPaymentSummary(props.projectId)
    ])
    milestones.value = milestonesRes.data || []
    summary.value = summaryRes.data || summary.value
  } catch (err) {
    ElMessage.error('加载数据失败: ' + (err.response?.data?.detail || err.message))
  } finally {
    loading.value = false
    summaryLoading.value = false
  }
}

const handleMarkInvoiced = async (row) => {
  if (!row.is_completed) {
    ElMessage.warning('仅已完成的里程碑可以标记为已开票')
    return
  }
  try {
    await ElMessageBox.confirm(`确认标记 "${row.title}" 为已开票？`, '确认操作')
    await v17Api.markMilestoneInvoiced(row.id)
    ElMessage.success('已标记为已开票')
    loadData()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('操作失败: ' + (err.response?.data?.detail || err.message))
    }
  }
}

const markInvoiced = async (row) => {
  handleMarkInvoiced(row)
}

const handleMarkReceived = async (row) => {
  try {
    await ElMessageBox.confirm(`确认标记 "${row.title}" 为已到账？`, '确认操作')
    await v17Api.markMilestonePaymentReceived(row.id)
    ElMessage.success('已标记为已到账')
    loadData()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('操作失败: ' + (err.response?.data?.detail || err.message))
    }
  }
}

const markReceived = async (row) => {
  handleMarkReceived(row)
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.milestone-payment-tab {
  padding: 16px 0;
}

.summary-card {
  margin-bottom: 16px;
}

.summary-item {
  text-align: center;
  padding: 12px;
  border-radius: 4px;
  background: var(--el-bg-color-page);
}

.summary-item.success {
  background: #f0f9ff;
}

.summary-item.warning {
  background: #fef0f0;
}

.summary-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
}

.summary-value {
  font-size: 18px;
  font-weight: bold;
}

.overdue-card {
  border: 1px solid var(--el-color-danger);
  margin-bottom: 16px;
}

.overdue-title {
  color: var(--el-color-danger);
}

.text-danger {
  color: var(--el-color-danger);
}

.mono {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
}
</style>
