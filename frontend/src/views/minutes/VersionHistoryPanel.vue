<template>
  <div class="version-history-panel">
    <h4 style="margin: 0 0 12px; font-size: 14px">版本历史</h4>
    <el-table :data="history" size="small" stripe v-loading="loading">
      <el-table-column prop="version_no" label="版本号" width="80" align="center">
        <template #default="{ row }">v{{ row.version_no }}</template>
      </el-table-column>
      <el-table-column prop="created_at" label="保存时间" width="180" />
      <el-table-column label="操作" width="100" align="center">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="$emit('compare', row)">对比</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && !history.length" description="暂无历史版本" :image-size="60" />
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { getSnapshotHistory } from '../../api/minutes'

const props = defineProps({
  entityType: { type: String, required: true },
  entityId: { type: [Number, String], required: true },
})

defineEmits(['compare'])

const history = ref([])
const loading = ref(false)

async function loadHistory() {
  loading.value = true
  try {
    const { data } = await getSnapshotHistory(props.entityType, props.entityId)
    history.value = data || []
  } catch {
    history.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => { loadHistory() })
watch(() => props.entityId, () => { loadHistory() })
</script>
