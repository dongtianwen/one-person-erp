<template>
  <div class="minutes-detail-view" v-loading="loading">
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
      <div style="display: flex; align-items: center; gap: 12px">
        <el-button :icon="ArrowLeft" @click="$router.push('/minutes')">返回列表</el-button>
        <h2 style="margin: 0; font-size: 18px">纪要详情</h2>
      </div>
      <div style="display: flex; gap: 8px">
        <el-button type="primary" @click="formVisible = true">编辑</el-button>
        <el-button type="danger" @click="handleDelete">删除</el-button>
      </div>
    </div>

    <el-empty v-if="!loading && !detail" description="纪要不存在" />
    <template v-else-if="detail">
      <MinutesDetail :data="detail" />

      <el-divider />

      <VersionHistoryPanel
        entity-type="minutes"
        :entity-id="id"
        @compare="openCompare"
      />

      <VersionCompareDialog
        v-model="compareVisible"
        entity-type="minutes"
        :entity-id="id"
        :history-list="historyList"
        :schema="minutesSchema"
      />
    </template>

    <MinutesFormDialog
      v-model="formVisible"
      :edit-data="detail"
      @success="loadDetail"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import MinutesDetail from './MinutesDetail.vue'
import VersionHistoryPanel from './VersionHistoryPanel.vue'
import VersionCompareDialog from './VersionCompareDialog.vue'
import MinutesFormDialog from './MinutesFormDialog.vue'
import { getMinutesDetail, deleteMinutes } from '../../api/minutes'
import { SNAPSHOT_SCHEMAS } from '../../constants/snapshotSchema'
import { useApiWarning } from '../../composables/useApiWarning'

const { handleResponse } = useApiWarning()
const route = useRoute()
const router = useRouter()
const id = Number(route.params.id)

const loading = ref(false)
const detail = ref(null)
const formVisible = ref(false)
const compareVisible = ref(false)
const historyList = ref([])
const minutesSchema = SNAPSHOT_SCHEMAS.minutes

async function loadDetail() {
  loading.value = true
  try {
    const { data } = await getMinutesDetail(id)
    detail.value = data
  } catch {
    detail.value = null
  } finally {
    loading.value = false
  }
}

function openCompare(row) {
  compareVisible.value = true
}

async function handleDelete() {
  try {
    await ElMessageBox.confirm('确定删除此纪要？', '确认', { type: 'warning' })
    const { data } = await deleteMinutes(id)
    handleResponse(data)
    ElMessage.success('删除成功')
    router.push('/minutes')
  } catch { /* cancelled or error */ }
}

onMounted(() => { loadDetail() })
</script>
