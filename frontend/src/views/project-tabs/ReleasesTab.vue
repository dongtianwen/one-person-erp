<template>
  <div>
    <div class="tab-toolbar">
      <el-button type="primary" size="small" @click="openCreate"><el-icon><Plus /></el-icon> 新建版本</el-button>
    </div>
    <!-- 当前线上版本置顶 -->
    <el-card v-if="currentOnline" class="current-card" shadow="hover">
      <template #header>
        <span style="font-weight:600">当前线上版本 <el-tag size="small" type="success" round>当前线上</el-tag></span>
      </template>
      <div class="release-meta">
        <span class="mono">{{ currentOnline.version_no }}</span>
        <el-tag size="small">{{ currentOnline.release_date }}</el-tag>
        <el-tag size="small" type="info">{{ envLabels[currentOnline.deploy_env] || currentOnline.deploy_env }}</el-tag>
      </div>
      <div v-if="currentOnline.changelog" class="release-changelog">{{ currentOnline.changelog }}</div>
    </el-card>
    <!-- 其他版本按 release_date 倒序 -->
    <el-table :data="otherReleases" style="width:100%" size="small" v-if="otherReleases.length" :row-class-name="()=>'release-row'">
      <el-table-column prop="version_no" label="版本号" width="100" />
      <el-table-column prop="release_date" label="发布日期" width="110" />
      <el-table-column prop="release_type" label="类型" width="80">
        <template #default="{ row }">
          <el-tag size="small" :type="releaseTypeColor[row.release_type] || 'info'">{{ releaseTypeLabels[row.release_type] || row.release_type }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="deploy_env" label="环境" width="80">
        <template #default="{ row }">{{ envLabels[row.deploy_env] || row.deploy_env }}</template>
      </el-table-column>
      <el-table-column prop="changelog" label="更新日志" min-width="160" show-overflow-tooltip />
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button link size="small" type="primary" @click="handleSetOnline(row)">设为当前线上</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div v-if="!releases.length" class="empty-hint">暂无版本记录</div>
    <!-- 新建版本 -->
    <el-dialog v-model="showForm" title="新建版本" width="540px" destroy-on-close append-to-body>
      <el-form :model="form" label-position="top">
        <el-form-item label="版本号" required><el-input v-model="form.version_no" placeholder="如 v1.0.0" /></el-form-item>
        <el-form-item label="发布日期" required><el-date-picker v-model="form.release_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item>
        <el-form-item label="发布类型" required>
          <el-select v-model="form.release_type" style="width:100%">
            <el-option v-for="(label, val) in releaseTypeLabels" :key="val" :label="label" :value="val" />
          </el-select>
        </el-form-item>
        <el-form-item label="部署环境" required>
          <el-select v-model="form.deploy_env" style="width:100%">
            <el-option v-for="(label, val) in envLabels" :key="val" :label="label" :value="val" />
          </el-select>
        </el-form-item>
        <el-form-item label="更新日志"><el-input v-model="form.changelog" type="textarea" :rows="3" /></el-form-item>
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
import { getReleases, createRelease, setReleaseOnline } from '../../api/releases'

const props = defineProps({ projectId: { type: Number, required: true } })
const releases = ref([])
const showForm = ref(false)
const defaultForm = { version_no: '', release_date: '', release_type: 'minor', deploy_env: 'production', changelog: '' }
const form = ref({ ...defaultForm })

const releaseTypeLabels = { major: '大版本', minor: '小版本', hotfix: '热修复' }
const releaseTypeColor = { major: 'danger', minor: '', hotfix: 'warning' }
const envLabels = { development: '开发', staging: '预发', production: '生产' }

const currentOnline = computed(() => releases.value.find(r => r.is_pinned) || null)
const otherReleases = computed(() =>
  releases.value
    .filter(r => !r.is_pinned)
    .sort((a, b) => (b.release_date || '').localeCompare(a.release_date || ''))
)

const loadData = async () => {
  try { releases.value = await getReleases(props.projectId) } catch { /* handled */ }
}

const openCreate = () => { form.value = { ...defaultForm }; showForm.value = true }

const handleCreate = async () => {
  if (!form.value.version_no || !form.value.release_date) { ElMessage.warning('请填写版本号和发布日期'); return }
  try {
    await createRelease(props.projectId, form.value)
    ElMessage.success('版本已创建')
    showForm.value = false
    form.value = { ...defaultForm }
    await loadData()
  } catch { /* handled */ }
}

const handleSetOnline = async (row) => {
  try {
    await setReleaseOnline(props.projectId, row.id)
    ElMessage.success('已设为当前线上版本')
    await loadData()
  } catch { /* handled */ }
}

watch(() => props.projectId, () => loadData(), { immediate: true })
</script>

<style scoped>
.tab-toolbar { margin-bottom: 12px; }
.current-card { margin-bottom: 16px; }
.release-meta { display: flex; align-items: center; gap: 8px; }
.release-changelog { white-space: pre-wrap; margin-top: 8px; font-size: 14px; color: #666; }
.empty-hint { color: #999; text-align: center; padding: 24px; }
</style>
