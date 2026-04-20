<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑纪要' : '创建纪要'"
    width="560px"
    destroy-on-close
    @close="resetForm"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
      <el-form-item label="标题" prop="title">
        <el-input v-model="form.title" placeholder="纪要标题" />
      </el-form-item>
      <el-form-item label="参与人" prop="participants">
        <el-input v-model="form.participants" placeholder="多人以逗号分隔" />
      </el-form-item>
      <el-form-item label="结论" prop="conclusions">
        <el-input v-model="form.conclusions" type="textarea" :rows="3" placeholder="本次沟通达成的明确结论" />
      </el-form-item>
      <el-form-item label="待办事项" prop="action_items">
        <el-input v-model="form.action_items" type="textarea" :rows="3" placeholder="后续需跟进的具体行动项" />
      </el-form-item>
      <el-form-item label="风险点" prop="risk_points">
        <el-input v-model="form.risk_points" type="textarea" :rows="2" placeholder="沟通中识别到的风险或不确定因素" />
      </el-form-item>
      <el-form-item label="关联项目" prop="project_id">
        <el-select v-model="form.project_id" clearable placeholder="选择项目" filterable style="width: 100%">
          <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="关联客户" prop="client_id">
        <el-select v-model="form.client_id" clearable placeholder="选择客户" filterable style="width: 100%">
          <el-option v-for="c in customers" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="会议日期" prop="meeting_date">
        <el-date-picker v-model="form.meeting_date" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" style="width: 100%" />
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
import { createMinutes, updateMinutes } from '../../api/minutes'
import { getProjects } from '../../api/projects'
import { getCustomers } from '../../api/customers'
import { useApiWarning } from '../../composables/useApiWarning'

const { handleResponse } = useApiWarning()

const props = defineProps({
  editData: { type: Object, default: null },
})
const emit = defineEmits(['success'])

const visible = defineModel('modelValue', { type: Boolean })
const formRef = ref(null)
const submitting = ref(false)
const projects = ref([])
const customers = ref([])

const isEdit = ref(false)
const form = ref({
  title: '',
  participants: '',
  conclusions: '',
  action_items: '',
  risk_points: '',
  project_id: null,
  client_id: null,
  meeting_date: '',
})

const validateAssociation = (rule, value, callback) => {
  if (!form.value.project_id && !form.value.client_id) {
    callback(new Error('请关联项目或客户'))
  } else {
    callback()
  }
}

const rules = {
  title: [{ required: true, message: '请输入标题', trigger: 'blur' }],
  conclusions: [{ required: true, message: '请输入结论', trigger: 'blur' }],
  project_id: [{ validator: validateAssociation, trigger: 'change' }],
  client_id: [{ validator: validateAssociation, trigger: 'change' }],
}

watch(visible, async (val) => {
  if (val) {
    try {
      const [projRes, custRes] = await Promise.all([getProjects(), getCustomers()])
      projects.value = projRes.data?.items || projRes.data || []
      customers.value = custRes.data?.items || custRes.data || []
    } catch { /* ignore */ }

    if (props.editData) {
      isEdit.value = true
      form.value = {
        title: props.editData.title || '',
        participants: props.editData.participants || '',
        conclusions: props.editData.conclusions || '',
        action_items: props.editData.action_items || '',
        risk_points: props.editData.risk_points || '',
        project_id: props.editData.project_id || null,
        client_id: props.editData.client_id || null,
        meeting_date: props.editData.meeting_date || '',
      }
    } else {
      isEdit.value = false
      resetForm()
    }
  }
})

function resetForm() {
  form.value = {
    title: '',
    participants: '',
    conclusions: '',
    action_items: '',
    risk_points: '',
    project_id: null,
    client_id: null,
    meeting_date: '',
  }
}

async function handleSubmit() {
  try {
    await formRef.value.validate()
  } catch { return }

  submitting.value = true
  try {
    let result
    if (isEdit.value) {
      result = await updateMinutes(props.editData.id, form.value)
    } else {
      result = await createMinutes(form.value)
    }
    handleResponse(result.data)
    ElMessage.success(isEdit.value ? '更新成功' : '创建成功')
    visible.value = false
    emit('success')
  } catch {
    // error handled by interceptor
  } finally {
    submitting.value = false
  }
}
</script>
