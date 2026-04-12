<!-- v1.7 项目级变更单管理 Tab -->
<template>
  <div class="change-orders-tab">
    <div class="tab-header">
      <el-alert
        v-if="isFrozen"
        type="warning"
        :closable="false"
        show-icon
      >
        <template #title>
          需求已冻结 - 所有需求变更必须通过变更单提交
        </template>
      </el-alert>
      <el-button
        type="primary"
        size="small"
        @click="openCreateDialog"
        :disabled="!isFrozen"
      >
        <el-icon><Plus /></el-icon>
        新建变更单
      </el-button>
    </div>

    <el-table :data="changeOrders" v-loading="loading" stripe>
      <el-table-column prop="id" label="ID" width="60" />
      <el-table-column prop="title" label="变更标题" min-width="160" />
      <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="statusType(row.status)">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="extra_days" label="额外天数" width="90" align="right">
        <template #default="{ row }">
          <span class="mono">{{ row.extra_days || '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="extra_amount" label="额外金额" width="100" align="right">
        <template #default="{ row }">
          <span class="mono">{{ row.extra_amount ? '¥' + Number(row.extra_amount).toLocaleString() : '-' }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="client_confirmed_at" label="确认时间" width="160">
        <template #default="{ row }">
          <span class="mono">{{ formatDateTime(row.client_confirmed_at) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status === 'pending'"
            link
            type="success"
            size="small"
            @click="handleConfirm(row)"
          >
            确认
          </el-button>
          <el-button
            v-if="row.status === 'pending'"
            link
            type="danger"
            size="small"
            @click="handleReject(row)"
          >
            拒绝
          </el-button>
          <el-button
            v-if="row.status === 'pending'"
            link
            type="info"
            size="small"
            @click="handleCancel(row)"
          >
            撤回
          </el-button>
          <span v-if="row.status !== 'pending'" class="text-muted">终态</span>
        </template>
      </el-table-column>
    </el-table>

    <!-- 创建变更单对话框 -->
    <el-dialog
      v-model="createDialogVisible"
      title="新建变更单"
      width="500px"
    >
      <el-form :model="formData" label-width="100px">
        <el-form-item label="变更标题" required>
          <el-input v-model="formData.title" placeholder="请输入变更标题" />
        </el-form-item>
        <el-form-item label="变更描述" required>
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="3"
            placeholder="请描述变更内容"
          />
        </el-form-item>
        <el-form-item>
          <template #label>额外天数 <FieldTip module="change_order" field="extra_days" /></template>
          <el-input-number v-model="formData.extra_days" :min="0" controls-position="right" />
        </el-form-item>
        <el-form-item>
          <template #label>额外金额 <FieldTip module="change_order" field="extra_amount" /></template>
          <el-input-number v-model="formData.extra_amount" :min="0" :precision="2" controls-position="right" />
          <span class="form-tip">允许为 0，但必须显式设置</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreate" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>

    <!-- 拒绝原因对话框 -->
    <el-dialog
      v-model="rejectDialogVisible"
      title="拒绝变更单"
      width="400px"
    >
      <el-input
        v-model="rejectReason"
        type="textarea"
        :rows="3"
        placeholder="请输入拒绝原因"
      />
      <template #footer>
        <el-button @click="rejectDialogVisible = false">取消</el-button>
        <el-button type="danger" @click="confirmReject" :loading="submitting">确定拒绝</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import FieldTip from '../../components/FieldTip.vue'
import * as v17Api from '../../api/v17'

const props = defineProps({
  projectId: { type: Number, required: true }
})

const loading = ref(false)
const changeOrders = ref([])
const isFrozen = ref(false)

// 创建对话框
const createDialogVisible = ref(false)
const submitting = ref(false)
const formData = ref({
  title: '',
  description: '',
  extra_days: 0,
  extra_amount: 0
})

// 拒绝对话框
const rejectDialogVisible = ref(false)
const rejectReason = ref('')
const currentOrder = ref(null)

const statusType = (status) => {
  const types = {
    pending: 'warning',
    confirmed: 'success',
    rejected: 'danger',
    cancelled: 'info'
  }
  return types[status] || 'info'
}

const statusLabel = (status) => {
  const labels = {
    pending: '待确认',
    confirmed: '已确认',
    rejected: '已拒绝',
    cancelled: '已撤回'
  }
  return labels[status] || status
}

const formatDateTime = (dt) => {
  if (!dt) return '-'
  return new Date(dt).toLocaleString('zh-CN')
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await v17Api.getProjectChangeOrders(props.projectId)
    // API 返回 {data: [...], is_frozen: ...}
    changeOrders.value = res.data?.data || []
    // 从 API 响应中获取冻结状态
    isFrozen.value = res.data?.is_frozen || false
  } catch (err) {
    ElMessage.error('加载变更单失败: ' + (err.response?.data?.detail || err.message))
  } finally {
    loading.value = false
  }
}

const openCreateDialog = () => {
  formData.value = {
    title: '',
    description: '',
    extra_days: 0,
    extra_amount: 0
  }
  createDialogVisible.value = true
}

const handleCreate = async () => {
  if (!formData.value.title || !formData.value.description) {
    ElMessage.warning('请填写变更标题和描述')
    return
  }
  submitting.value = true
  try {
    await v17Api.createProjectChangeOrder(props.projectId, formData.value)
    ElMessage.success('变更单创建成功')
    createDialogVisible.value = false
    loadData()
  } catch (err) {
    ElMessage.error('创建失败: ' + (err.response?.data?.detail || err.message))
  } finally {
    submitting.value = false
  }
}

const handleConfirm = async (row) => {
  try {
    await ElMessageBox.confirm('确认客户同意此变更单？', '确认操作')
    await v17Api.confirmChangeOrder(row.id)
    ElMessage.success('已确认')
    loadData()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('确认失败: ' + (err.response?.data?.detail || err.message))
    }
  }
}

const handleReject = (row) => {
  currentOrder.value = row
  rejectReason.value = ''
  rejectDialogVisible.value = true
}

const confirmReject = async () => {
  if (!rejectReason.value.trim()) {
    ElMessage.warning('请输入拒绝原因')
    return
  }
  submitting.value = true
  try {
    await v17Api.rejectChangeOrder(currentOrder.value.id, rejectReason.value)
    ElMessage.success('已拒绝')
    rejectDialogVisible.value = false
    loadData()
  } catch (err) {
    ElMessage.error('拒绝失败: ' + (err.response?.data?.detail || err.message))
  } finally {
    submitting.value = false
  }
}

const handleCancel = async (row) => {
  try {
    await ElMessageBox.confirm('确认撤回此变更单？', '确认操作')
    await v17Api.cancelChangeOrder(row.id)
    ElMessage.success('已撤回')
    loadData()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('撤回失败: ' + (err.response?.data?.detail || err.message))
    }
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.change-orders-tab {
  padding: 16px 0;
}

.tab-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.text-muted {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.form-tip {
  margin-left: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
