<template>
  <el-dialog
    v-model="visible"
    title="版本对比"
    width="720px"
    destroy-on-close
  >
    <div style="display: flex; gap: 16px; align-items: center; margin-bottom: 16px">
      <span>版本 A：</span>
      <el-select v-model="selectedV1" @change="loadDiff" style="width: 180px">
        <el-option
          v-for="h in historyList"
          :key="h.version_no"
          :label="'v' + h.version_no + ' (' + h.created_at + ')'"
          :value="h.version_no"
        />
      </el-select>
      <span>版本 B：</span>
      <el-select v-model="selectedV2" @change="loadDiff" style="width: 180px">
        <el-option
          v-for="h in historyList"
          :key="h.version_no"
          :label="'v' + h.version_no + ' (' + h.created_at + ')'"
          :value="h.version_no"
        />
      </el-select>
    </div>

    <div v-loading="loading">
      <VersionCompareTable
        v-if="diffLoaded && !loading"
        :v1-json="v1Data"
        :v2-json="v2Data"
        :schema="schema"
      />
      <el-empty v-else-if="!loading && !diffLoaded" description="版本对比加载失败，请重试" />
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import VersionCompareTable from '../../components/VersionCompareTable.vue'
import { getSnapshotDiff } from '../../api/minutes'

const props = defineProps({
  entityType: { type: String, required: true },
  entityId: { type: [Number, String], required: true },
  historyList: { type: Array, default: () => [] },
  schema: { type: Array, default: () => [] },
})

const visible = defineModel('modelValue', { type: Boolean })
const loading = ref(false)
const diffLoaded = ref(false)
const v1Data = ref({})
const v2Data = ref({})

const selectedV1 = ref(0)
const selectedV2 = ref(0)

watch(visible, (val) => {
  if (val && props.historyList.length) {
    const max = Math.max(...props.historyList.map((h) => h.version_no))
    selectedV2.value = max
    selectedV1.value = max > 0 ? max - 1 : max
    loadDiff()
  }
})

async function loadDiff() {
  loading.value = true
  diffLoaded.value = false
  try {
    const { data } = await getSnapshotDiff(
      props.entityType,
      props.entityId,
      selectedV1.value,
      selectedV2.value
    )
    v1Data.value = data.version_a?.content || {}
    v2Data.value = data.version_b?.content || {}
    diffLoaded.value = true
  } catch {
    diffLoaded.value = false
  } finally {
    loading.value = false
  }
}
</script>
