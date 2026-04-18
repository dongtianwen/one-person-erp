<template>
  <div>
    <div class="tab-toolbar">
      <PageHelpDrawer pageKey="project_requirements_tab" />
      <el-button type="primary" size="small" @click="showForm = true"><el-icon><Plus /></el-icon> 新建版本</el-button>
    </div>
    <!-- 当前版本 -->
    <el-card v-if="currentVersion" class="current-card" shadow="hover">
      <template #header><span style="font-weight:600">当前版本 <el-tag size="small" type="success" round>当前</el-tag></span></template>
      <div class="req-summary">{{ currentVersion.summary }}</div>
      <div class="req-meta">
        <span class="mono">{{ currentVersion.version_no }}</span>
        <el-tag size="small" :type="currentVersion.confirm_status === 'confirmed' ? 'success' : 'info'">
          {{ currentVersion.confirm_status === 'confirmed' ? '已确认' : '待确认' }}
        </el-tag>
      </div>
      <!-- 变更记录 -->
      <div v-if="currentChanges.length" style="margin-top:12px">
        <div style="font-weight:500;margin-bottom:8px">变更记录</div>
        <div v-for="c in currentChanges" :key="c.id" class="change-item">
          <el-tag size="small" type="warning">{{ c.change_type }}</el-tag>
          <span>{{ c.title }}</span>
          <el-tag v-if="c.is_billable" size="small" type="danger">收费</el-tag>
        </div>
      </div>
    </el-card>
    <!-- 历史版本 -->
    <el-collapse v-if="historyVersions.length" style="margin-top:16px">
      <el-collapse-item :title="`历史版本 (${historyVersions.length})`">
        <div v-for="r in historyVersions" :key="r.id" class="history-item">
          <span class="mono">{{ r.version_no }}</span>
          <el-tag size="small" :type="r.confirm_status === 'confirmed' ? 'success' : 'info'">{{ r.confirm_status }}</el-tag>
          <el-button link size="small" type="primary" @click="setCurrent(r.id)">设为当前</el-button>
        </div>
      </el-collapse-item>
    </el-collapse>
    <div v-if="!requirements.length" class="empty-hint">暂无需求版本</div>
    <!-- 新建表单 -->
    <el-dialog v-model="showForm" title="新建需求版本" width="500px" destroy-on-close append-to-body>
      <el-form :model="form" label-position="top">
        <el-form-item label="版本号" required><el-input v-model="form.version_no" placeholder="如 v1.0" /></el-form-item>
        <el-form-item label="需求摘要" required><el-input v-model="form.summary" type="textarea" :rows="4" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showForm = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import PageHelpDrawer from '../../components/PageHelpDrawer.vue'
import { getRequirements, createRequirement, setCurrentRequirement } from '../../api/requirements'

const props = defineProps({ projectId: { type: Number, required: true } })
const requirements = ref([])
const showForm = ref(false)
const form = ref({ version_no: '', summary: '' })

const currentVersion = computed(() => requirements.value.find(r => r.is_current) || null)
const historyVersions = computed(() => requirements.value.filter(r => !r.is_current))
const currentChanges = ref([])

const loadData = async () => {
  try {
    requirements.value = await getRequirements(props.projectId)
    if (currentVersion.value) {
      const { getRequirementDetail } = await import('../../api/requirements')
      const detail = await getRequirementDetail(props.projectId, currentVersion.value.id)
      currentChanges.value = detail.changes || []
    }
  } catch { /* handled */ }
}

const handleCreate = async () => {
  if (!form.value.version_no || !form.value.summary) { ElMessage.warning('请填写版本号和摘要'); return }
  try {
    await createRequirement(props.projectId, form.value)
    ElMessage.success('版本已创建')
    showForm.value = false
    form.value = { version_no: '', summary: '' }
    await loadData()
  } catch { /* handled */ }
}

const setCurrent = async (id) => {
  try {
    await setCurrentRequirement(props.projectId, id)
    ElMessage.success('已切换当前版本')
    await loadData()
  } catch { /* handled */ }
}

watch(() => props.projectId, () => loadData(), { immediate: true })
</script>

<style scoped>
.current-card { margin-bottom: 12px; }
.req-summary { white-space: pre-wrap; margin: 8px 0; font-size: 14px; }
.req-meta { display: flex; align-items: center; gap: 8px; margin-top: 8px; }
.change-item { display: flex; align-items: center; gap: 8px; padding: 4px 0; }
.history-item { display: flex; align-items: center; gap: 8px; padding: 6px 0; border-bottom: 1px solid #f0f0f0; }
.empty-hint { color: #999; text-align: center; padding: 24px; }
.tab-toolbar { margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }
</style>
