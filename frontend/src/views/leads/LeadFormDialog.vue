<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑线索' : '创建线索'"
    width="520px"
    destroy-on-close
    @close="resetForm"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
      <el-form-item label="来源" prop="source">
        <el-select v-model="form.source" style="width: 100%">
          <el-option
            v-for="s in LEAD_SOURCES"
            :key="s.value"
            :label="s.label"
            :value="s.value"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="状态" prop="status">
        <el-select v-model="form.status" style="width: 100%">
          <el-option
            v-for="s in LEAD_STATUSES"
            :key="s.value"
            :label="s.label"
            :value="s.value"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="下次动作" prop="next_action">
        <el-input v-model="form.next_action" placeholder="例如：本周五发送方案报价" />
      </el-form-item>
      <el-form-item label="关联客户">
        <el-select
          v-model="form.client_id"
          clearable
          filterable
          placeholder="选择客户"
          :disabled="clientsLoading"
          style="width: 100%"
        >
          <el-option v-for="c in clients" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
        <div v-if="clientsError" style="color: var(--el-color-danger); font-size: 12px; margin-top: 4px">加载失败</div>
      </el-form-item>
      <el-form-item label="关联项目">
        <el-select
          v-model="form.project_id"
          clearable
          filterable
          placeholder="选择项目"
          :disabled="projectsLoading"
          style="width: 100%"
        >
          <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
        <div v-if="projectsError" style="color: var(--el-color-danger); font-size: 12px; margin-top: 4px">加载失败</div>
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="form.notes" type="textarea" :rows="2" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { createLead, updateLead } from '../../api/ledger'
import { getCustomers } from '../../api/customers'
import { getProjects } from '../../api/projects'
import { LEAD_STATUSES, LEAD_SOURCES } from '../../constants/status'
import { useApiWarning } from '../../composables/useApiWarning'

const { handleResponse } = useApiWarning()

const props = defineProps({
  editData: { type: Object, default: null },
})
const emit = defineEmits(['success'])

const visible = defineModel('modelValue', { type: Boolean })
const formRef = ref(null)
const submitting = ref(false)
const isEdit = ref(false)

const clients = ref([])
const projects = ref([])
const clientsLoading = ref(false)
const projectsLoading = ref(false)
const clientsError = ref(false)
const projectsError = ref(false)

const form = ref({
  source: 'other',
  status: 'initial_contact',
  next_action: '',
  client_id: null,
  project_id: null,
  notes: '',
})

const rules = {
  source: [{ required: true, message: '请选择来源', trigger: 'change' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
  next_action: [{ required: true, message: '请输入下次动作', trigger: 'blur' }],
}

watch(visible, async (val) => {
  if (val) {
    clientsLoading.value = true
    projectsLoading.value = true
    clientsError.value = false
    projectsError.value = false

    Promise.all([
      getCustomers().then(({ data }) => {
        clients.value = data?.items || data || []
      }).catch(() => {
        clientsError.value = true
      }).finally(() => { clientsLoading.value = false }),

      getProjects().then(({ data }) => {
        projects.value = data?.items || data || []
      }).catch(() => {
        projectsError.value = true
      }).finally(() => { projectsLoading.value = false }),
    ])

    if (props.editData) {
      isEdit.value = true
      form.value = {
        source: props.editData.source || 'other',
        status: props.editData.status || 'initial_contact',
        next_action: props.editData.next_action || '',
        client_id: props.editData.client_id || null,
        project_id: props.editData.project_id || null,
        notes: props.editData.notes || '',
      }
    } else {
      isEdit.value = false
      resetForm()
    }
  }
})

function resetForm() {
  form.value = {
    source: 'other',
    status: 'initial_contact',
    next_action: '',
    client_id: null,
    project_id: null,
    notes: '',
  }
}

async function handleSubmit() {
  try { await formRef.value.validate() } catch { return }
  submitting.value = true
  try {
    let result
    if (isEdit.value) {
      result = await updateLead(props.editData.id, form.value)
    } else {
      result = await createLead(form.value)
    }
    handleResponse(result.data)
    ElMessage.success(isEdit.value ? '更新成功' : '创建成功')
    visible.value = false
    emit('success')
  } catch { /* error handled */ } finally {
    submitting.value = false
  }
}
</script>
