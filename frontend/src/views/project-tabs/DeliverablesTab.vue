<template>
  <div>
    <div class="tab-toolbar">
      <el-button type="primary" size="small" @click="openCreate"><el-icon><Plus /></el-icon> 新建交付物</el-button>
      <el-select v-model="typeFilter" placeholder="按类型筛选" clearable size="small" style="width:140px;margin-left:12px" @change="loadData">
        <el-option v-for="(label, val) in typeLabels" :key="val" :label="label" :value="val" />
      </el-select>
    </div>
    <el-table :data="deliverables" style="width:100%" size="small" v-if="deliverables.length">
      <el-table-column prop="name" label="交付物名称" min-width="140" />
      <el-table-column prop="deliverable_type" label="类型" width="100">
        <template #default="{ row }">
          <el-tag size="small" :type="typeTagColor[row.deliverable_type] || 'info'">{{ typeLabels[row.deliverable_type] || row.deliverable_type }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="delivery_date" label="交付日期" width="110" />
      <el-table-column prop="recipient_name" label="接收人" width="100" />
      <el-table-column prop="delivery_method" label="交付方式" width="90">
        <template #default="{ row }">{{ methodLabels[row.delivery_method] || row.delivery_method }}</template>
      </el-table-column>
    </el-table>
    <div v-else class="empty-hint">暂无交付物</div>
    <!-- 新建交付物 -->
    <el-dialog v-model="showForm" title="新建交付物" width="540px" destroy-on-close append-to-body>
      <el-form :model="form" label-position="top">
        <el-form-item label="交付物名称" required><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="类型" required>
          <el-select v-model="form.deliverable_type" style="width:100%" @change="onTypeChange">
            <el-option v-for="(label, val) in typeLabels" :key="val" :label="label" :value="val" />
          </el-select>
        </el-form-item>
        <el-form-item label="交付日期" required><el-date-picker v-model="form.delivery_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
        <el-form-item label="接收人" required><el-input v-model="form.recipient_name" /></el-form-item>
        <el-form-item label="交付方式" required>
          <el-select v-model="form.delivery_method" style="width:100%">
            <el-option v-for="(label, val) in methodLabels" :key="val" :label="label" :value="val" />
          </el-select>
        </el-form-item>
        <!-- 账号交接条目（仅 account_handover 类型） -->
        <template v-if="form.deliverable_type === 'account_handover'">
          <el-form-item label="账号条目">
            <div v-for="(item, idx) in form.account_handovers" :key="idx" class="account-row">
              <el-input v-model="item.platform_name" placeholder="平台名称" style="flex:1" />
              <el-input v-model="item.account_name" placeholder="账号" style="flex:1" />
              <el-button link type="danger" @click="form.account_handovers.splice(idx, 1)">移除</el-button>
            </div>
            <el-button size="small" @click="form.account_handovers.push({ platform_name: '', account_name: '' })">+ 添加账号</el-button>
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="showForm = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { getDeliverables, createDeliverable } from '../../api/deliverables'

const props = defineProps({ projectId: { type: Number, required: true } })
const deliverables = ref([])
const showForm = ref(false)
const typeFilter = ref('')
const defaultForm = { name: '', deliverable_type: 'document', delivery_date: '', recipient_name: '', delivery_method: 'email', account_handovers: [] }
const form = ref({ ...defaultForm })

const typeLabels = { document: '文档', source_code: '源码', account_handover: '账号交接', deployment: '部署包', other: '其他' }
const typeTagColor = { document: '', source_code: 'success', account_handover: 'warning', deployment: 'primary', other: 'info' }
const methodLabels = { email: '邮件', online: '在线', offline: '线下' }

const loadData = async () => {
  try {
    const params = {}
    if (typeFilter.value) params.deliverable_type = typeFilter.value
    deliverables.value = await getDeliverables(props.projectId, params)
  } catch { /* handled */ }
}

const onTypeChange = (val) => {
  if (val === 'account_handover') {
    form.value.account_handovers = [{ platform_name: '', account_name: '' }]
  } else {
    form.value.account_handovers = []
  }
}

const openCreate = () => {
  form.value = { ...defaultForm, account_handovers: [] }
  showForm.value = true
}

const handleCreate = async () => {
  if (!form.value.name || !form.value.delivery_date || !form.value.recipient_name) {
    ElMessage.warning('请填写必填项'); return
  }
  try {
    const payload = { ...form.value }
    if (payload.deliverable_type !== 'account_handover') {
      delete payload.account_handovers
    }
    await createDeliverable(props.projectId, payload)
    ElMessage.success('交付物已创建')
    showForm.value = false
    await loadData()
  } catch { /* handled */ }
}

watch(() => props.projectId, () => loadData(), { immediate: true })
</script>

<style scoped>
.tab-toolbar { margin-bottom: 12px; display: flex; align-items: center; }
.empty-hint { color: #999; text-align: center; padding: 24px; }
.account-row { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; }
</style>
