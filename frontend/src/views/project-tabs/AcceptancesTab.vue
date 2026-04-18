<template>
  <div>
    <div class="tab-toolbar">
      <PageHelpDrawer pageKey="project_acceptances_tab" />
      <el-button type="primary" size="small" @click="openCreate"><el-icon><Plus /></el-icon> 新建验收</el-button>
    </div>
    <el-table :data="acceptances" style="width:100%" size="small" v-if="acceptances.length">
      <el-table-column prop="acceptance_name" label="验收名称" min-width="140" />
      <el-table-column prop="acceptance_date" label="日期" width="110" />
      <el-table-column prop="acceptor_name" label="验收人" width="100" />
      <el-table-column prop="result" label="结果" width="100">
        <template #label>结果 <FieldTip module="project_acceptances" field="acceptance_result" /></template>
        <template #default="{ row }">
          <el-tag :type="resultType[row.result] || 'info'" size="small">{{ resultLabel[row.result] || row.result }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="confirm_method" label="确认方式" width="90" />
      <el-table-column label="操作" width="100">
        <template #default="{ row }">
          <el-button link size="small" type="primary" @click="openAppendNotes(row)">追加备注</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div v-else class="empty-hint">暂无验收记录</div>
    <!-- 新建验收 -->
    <el-dialog v-model="showForm" title="新建验收记录" width="520px" destroy-on-close append-to-body>
      <el-form :model="form" label-position="top">
        <el-form-item label="验收名称" required><el-input v-model="form.acceptance_name" /></el-form-item>
        <el-form-item label="验收日期" required><el-date-picker v-model="form.acceptance_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
        <el-form-item label="验收人" required><el-input v-model="form.acceptor_name" /></el-form-item>
        <el-form-item label="验收结果" required>
          <el-select v-model="form.result" style="width:100%" @change="onResultChange">
            <el-option label="通过" value="passed" /><el-option label="有条件通过" value="conditional" /><el-option label="不通过" value="failed" />
          </el-select>
        </el-form-item>
        <el-form-item label="确认方式" required>
          <el-select v-model="form.confirm_method" style="width:100%">
            <el-option label="线下" value="offline" /><el-option label="微信" value="wechat" /><el-option label="邮件" value="email" /><el-option label="系统" value="system" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.result === 'passed' || form.result === 'conditional'" label="触发收款提醒">
          <el-switch v-model="form.trigger_payment_reminder" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showForm = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>
    <!-- 追加备注 -->
    <el-dialog v-model="showNotes" title="追加备注" width="420px" destroy-on-close append-to-body>
      <el-input v-model="notesText" type="textarea" :rows="3" placeholder="输入新备注内容" />
      <template #footer>
        <el-button @click="showNotes = false">取消</el-button>
        <el-button type="primary" @click="handleAppendNotes">追加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import FieldTip from '../../components/FieldTip.vue'
import PageHelpDrawer from '../../components/PageHelpDrawer.vue'
import { getAcceptances, createAcceptance, appendAcceptanceNotes } from '../../api/acceptances'
import api from '../../api/index'

const props = defineProps({ projectId: { type: Number, required: true } })
const acceptances = ref([])
const showForm = ref(false)
const showNotes = ref(false)
const notesTarget = ref(null)
const notesText = ref('')
const defaultForm = { acceptance_name: '', acceptance_date: '', acceptor_name: '', result: 'passed', confirm_method: 'offline', trigger_payment_reminder: true }
const form = ref({ ...defaultForm })
const resultLabel = { passed: '通过', failed: '不通过', conditional: '有条件通过' }
const resultType = { passed: 'success', failed: 'danger', conditional: 'warning' }

const loadData = async () => {
  try { acceptances.value = await getAcceptances(props.projectId) } catch { /* handled */ }
}

const onResultChange = (val) => {
  if (val === 'failed') { form.value.trigger_payment_reminder = false }
}

const openCreate = () => { form.value = { ...defaultForm }; showForm.value = true }
const handleCreate = async () => {
  if (!form.value.acceptance_name || !form.value.acceptance_date || !form.value.acceptor_name) { ElMessage.warning('请填写必填项'); return }
  try {
    const payload = { ...form.value }
    if (payload.result === 'failed') delete payload.trigger_payment_reminder
    await createAcceptance(props.projectId, payload)
    ElMessage.success('验收记录已创建')
    showForm.value = false
    await loadData()
  } catch { /* handled */ }
}

const openAppendNotes = (row) => { notesTarget.value = row; notesText.value = ''; showNotes.value = true }
const handleAppendNotes = async () => {
  if (!notesText.value) { ElMessage.warning('请输入备注内容'); return }
  try {
    await appendAcceptanceNotes(props.projectId, notesTarget.value.id, { notes: notesText.value })
    ElMessage.success('备注已追加')
    showNotes.value = false
    await loadData()
  } catch { /* handled */ }
}

watch(() => props.projectId, () => loadData(), { immediate: true })
</script>

<style scoped>
.tab-toolbar { margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
.empty-hint { color: #999; text-align: center; padding: 24px; }
</style>
