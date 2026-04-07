<template>
  <div>
    <el-table :data="orders" style="width:100%" size="small" v-if="orders.length">
      <el-table-column prop="order_no" label="变更单号" width="150">
        <template #default="{ row }">
          <span class="mono link-text" @click="goToContract(row)">{{ row.order_no }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="title" label="标题" min-width="140" show-overflow-tooltip />
      <el-table-column prop="amount" label="金额" width="100" align="right">
        <template #default="{ row }">
          <span class="mono">¥{{ (row.amount || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="statusColor[row.status] || 'info'">{{ statusLabels[row.status] || row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="contract_no" label="关联合同" width="150">
        <template #default="{ row }">
          <span class="mono link-text" @click="goToContract(row)">{{ row.contract_no }}</span>
        </template>
      </el-table-column>
    </el-table>
    <div v-else class="empty-hint">暂无变更单</div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getProjectChangeOrders } from '../../api/changeOrders'

const props = defineProps({ projectId: { type: Number, required: true } })
const router = useRouter()
const orders = ref([])

const statusLabels = { draft: '草稿', sent: '已发送', confirmed: '已确认', in_progress: '执行中', completed: '已完成' }
const statusColor = { draft: 'info', sent: '', confirmed: 'success', in_progress: 'primary', completed: '' }

const loadData = async () => {
  try { orders.value = await getProjectChangeOrders(props.projectId) } catch { /* handled */ }
}

const goToContract = (row) => {
  // Navigate to contracts page with contract_id param to open change order tab
  router.push({ path: '/contracts', query: { contract_id: row.contract_id, tab: 'change-orders' } })
}

watch(() => props.projectId, () => loadData(), { immediate: true })
</script>

<style scoped>
.empty-hint { color: #999; text-align: center; padding: 24px; }
.link-text { color: var(--el-color-primary); cursor: pointer; }
.link-text:hover { text-decoration: underline; }
</style>
