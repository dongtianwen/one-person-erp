<template>
  <div>
    <div class="tab-toolbar">
      <el-button type="primary" size="small" @click="openCreate"><el-icon><Plus /></el-icon> 新建服务期</el-button>
    </div>
    <el-table :data="sortedPeriods" style="width:100%" size="small" v-if="sortedPeriods.length"
      :row-class-name="rowClassName">
      <el-table-column prop="service_type" label="服务类型" width="100">
        <template #default="{ row }">
          <el-tag size="small">{{ typeLabels[row.service_type] || row.service_type }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="service_description" label="服务说明" min-width="140" show-overflow-tooltip />
      <el-table-column label="有效期" width="200">
        <template #default="{ row }">
          <span class="mono">{{ row.start_date }} ~ {{ row.end_date }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="annual_fee" label="年费" width="90" align="right">
        <template #default="{ row }">{{ row.annual_fee != null ? '¥' + Number(row.annual_fee).toLocaleString() : '—' }}</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="statusColor[row.status] || 'info'">{{ statusLabels[row.status] || row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140">
        <template #default="{ row }">
          <el-button v-if="row.status === 'active'" link size="small" type="primary" @click="openRenew(row)">续期</el-button>
          <el-button v-if="row.status === 'active'" link size="small" type="primary" @click="openEdit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div v-else class="empty-hint">暂无维护期记录</div>
    <!-- 新建服务期 -->
    <el-dialog v-model="showForm" title="新建服务期" width="520px" destroy-on-close append-to-body>
      <el-form :model="form" label-position="top">
        <el-form-item label="服务类型" required>
          <el-select v-model="form.service_type" style="width:100%">
            <el-option v-for="(label, val) in typeLabels" :key="val" :label="label" :value="val" />
          </el-select>
        </el-form-item>
        <el-form-item label="服务说明" required><el-input v-model="form.service_description" /></el-form-item>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:0 16px">
          <el-form-item label="开始日期" required><el-date-picker v-model="form.start_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
          <el-form-item label="结束日期" required><el-date-picker v-model="form.end_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
        </div>
        <el-form-item label="年费（选填）"><el-input-number v-model="form.annual_fee" :min="0" :precision="2" style="width:100%" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showForm = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>
    <!-- 续期表单 -->
    <el-dialog v-model="showRenew" title="续期" width="480px" destroy-on-close append-to-body>
      <el-form :model="renewForm" label-position="top">
        <el-form-item label="新开始日期">
          <el-input :model-value="renewForm.start_date" disabled />
        </el-form-item>
        <el-form-item label="新结束日期" required>
          <el-date-picker v-model="renewForm.end_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
        <el-form-item label="年费"><el-input-number v-model="renewForm.annual_fee" :min="0" :precision="2" style="width:100%" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRenew = false">取消</el-button>
        <el-button type="primary" @click="handleRenew">确认续期</el-button>
      </template>
    </el-dialog>
    <!-- PATCH 编辑（仅 service_description / annual_fee / notes） -->
    <el-dialog v-model="showEdit" title="编辑服务期" width="480px" destroy-on-close append-to-body>
      <el-form :model="editForm" label-position="top">
        <el-form-item label="服务说明"><el-input v-model="editForm.service_description" /></el-form-item>
        <el-form-item label="年费"><el-input-number v-model="editForm.annual_fee" :min="0" :precision="2" style="width:100%" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="editForm.notes" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEdit = false">取消</el-button>
        <el-button type="primary" @click="handleEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { getMaintenancePeriods, createMaintenancePeriod, renewMaintenance, patchMaintenance } from '../../api/maintenance'

const props = defineProps({ projectId: { type: Number, required: true } })
const periods = ref([])
const showForm = ref(false)
const showRenew = ref(false)
const showEdit = ref(false)
const renewTarget = ref(null)
const editTarget = ref(null)
const defaultForm = { service_type: 'warranty', service_description: '', start_date: '', end_date: '', annual_fee: null }
const form = ref({ ...defaultForm })
const renewForm = ref({ start_date: '', end_date: '', annual_fee: null })
const editForm = ref({ service_description: '', annual_fee: null, notes: '' })

const typeLabels = { warranty: '质保', maintenance: '维护', sla: 'SLA' }
const statusLabels = { active: '生效', expired: '已到期', renewed: '已续期', terminated: '已终止' }
const statusColor = { active: 'success', expired: 'danger', renewed: 'info', terminated: 'warning' }

const sortedPeriods = computed(() =>
  [...periods.value].sort((a, b) => (a.end_date || '').localeCompare(b.end_date || ''))
)

const rowClassName = ({ row }) => {
  if (row.status === 'expired') return 'row-expired'
  const today = new Date().toISOString().slice(0, 10)
  const thirtyDaysLater = new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10)
  if (row.status === 'active' && row.end_date <= thirtyDaysLater && row.end_date >= today) return 'row-near-expiry'
  return ''
}

const loadData = async () => {
  try { periods.value = await getMaintenancePeriods(props.projectId) } catch { /* handled */ }
}

const openCreate = () => { form.value = { ...defaultForm }; showForm.value = true }

const handleCreate = async () => {
  if (!form.value.service_description || !form.value.start_date || !form.value.end_date) {
    ElMessage.warning('请填写必填项'); return
  }
  if (form.value.end_date < form.value.start_date) {
    ElMessage.warning('结束日期不得早于开始日期'); return
  }
  try {
    await createMaintenancePeriod(props.projectId, form.value)
    ElMessage.success('服务期已创建')
    showForm.value = false
    await loadData()
  } catch { /* handled */ }
}

const openRenew = (row) => {
  renewTarget.value = row
  const nextStart = new Date(row.end_date)
  nextStart.setDate(nextStart.getDate() + 1)
  renewForm.value = {
    start_date: nextStart.toISOString().slice(0, 10),
    end_date: '',
    annual_fee: row.annual_fee
  }
  showRenew.value = true
}

const handleRenew = async () => {
  if (!renewForm.value.end_date) { ElMessage.warning('请填写结束日期'); return }
  try {
    await renewMaintenance(props.projectId, renewTarget.value.id, renewForm.value)
    ElMessage.success('续期成功')
    showRenew.value = false
    await loadData()
  } catch { /* handled */ }
}

const openEdit = (row) => {
  editTarget.value = row
  editForm.value = {
    service_description: row.service_description || '',
    annual_fee: row.annual_fee,
    notes: row.notes || ''
  }
  showEdit.value = true
}

const handleEdit = async () => {
  try {
    await patchMaintenance(props.projectId, editTarget.value.id, editForm.value)
    ElMessage.success('已更新')
    showEdit.value = false
    await loadData()
  } catch { /* handled */ }
}

watch(() => props.projectId, () => loadData(), { immediate: true })
</script>

<style scoped>
.tab-toolbar { margin-bottom: 12px; }
.empty-hint { color: #999; text-align: center; padding: 24px; }
:deep(.row-near-expiry) { background-color: #fdf6ec !important; }
:deep(.row-expired) { background-color: #fef0f0 !important; }
</style>
