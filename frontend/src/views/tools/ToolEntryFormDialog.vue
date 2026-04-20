<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑工具入口' : '创建工具入口'"
    width="480px"
    destroy-on-close
    @close="resetForm"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
      <el-form-item label="动作名称" prop="action_name">
        <el-input v-model="form.action_name" placeholder="例如：合同电子签" />
      </el-form-item>
      <el-form-item label="工具名称" prop="tool_name">
        <el-input v-model="form.tool_name" placeholder="例如：腾讯电子签" />
      </el-form-item>
      <el-form-item label="状态" prop="status">
        <el-select v-model="form.status" style="width: 100%">
          <el-option
            v-for="s in TOOL_ENTRY_STATUSES"
            :key="s.value"
            :label="s.label"
            :value="s.value"
          />
        </el-select>
      </el-form-item>
      <el-form-item label="已回填">
        <el-switch v-model="form.is_backfilled" />
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
import { createToolEntry, updateToolEntryStatus } from '../../api/ledger'
import { TOOL_ENTRY_STATUSES } from '../../constants/status'
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

const form = ref({
  action_name: '',
  tool_name: '',
  status: 'pending',
  is_backfilled: false,
  notes: '',
})

const rules = {
  action_name: [{ required: true, message: '请输入动作名称', trigger: 'blur' }],
  tool_name: [{ required: true, message: '请输入工具名称', trigger: 'blur' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
}

watch(visible, (val) => {
  if (val && props.editData) {
    isEdit.value = true
    form.value = {
      action_name: props.editData.action_name || '',
      tool_name: props.editData.tool_name || '',
      status: props.editData.status || 'pending',
      is_backfilled: props.editData.is_backfilled || false,
      notes: props.editData.notes || '',
    }
  } else if (val) {
    isEdit.value = false
    resetForm()
  }
})

function resetForm() {
  form.value = {
    action_name: '',
    tool_name: '',
    status: 'pending',
    is_backfilled: false,
    notes: '',
  }
}

async function handleSubmit() {
  try { await formRef.value.validate() } catch { return }
  submitting.value = true
  try {
    if (isEdit.value) {
      const result = await updateToolEntryStatus(props.editData.id, {
        status: form.value.status,
        is_backfilled: form.value.is_backfilled,
      })
      handleResponse(result.data)
    } else {
      const result = await createToolEntry({
        action_name: form.value.action_name,
        tool_name: form.value.tool_name,
      })
      handleResponse(result.data)
    }
    ElMessage.success(isEdit.value ? '更新成功' : '创建成功')
    visible.value = false
    emit('success')
  } catch { /* error handled by interceptor */ } finally {
    submitting.value = false
  }
}
</script>
