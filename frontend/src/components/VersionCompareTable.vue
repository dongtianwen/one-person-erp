<template>
  <el-table :data="rows" border size="small" class="version-compare-table">
    <el-table-column prop="field" label="字段名" width="140">
      <template #default="{ row }">
        <span>{{ row.label }}</span>
        <el-tag v-if="row.changed" size="small" type="warning" style="margin-left: 6px">已变更</el-tag>
      </template>
    </el-table-column>
    <el-table-column prop="v1" label="版本 A" min-width="200">
      <template #default="{ row }">
        <pre class="compare-cell" :class="{ changed: row.changed }">{{ formatValue(row.v1) }}</pre>
      </template>
    </el-table-column>
    <el-table-column prop="v2" label="版本 B" min-width="200">
      <template #default="{ row }">
        <pre class="compare-cell" :class="{ changed: row.changed }">{{ formatValue(row.v2) }}</pre>
      </template>
    </el-table-column>
  </el-table>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  v1Json: { type: Object, default: () => ({}) },
  v2Json: { type: Object, default: () => ({}) },
  schema: { type: Array, default: () => [] },
})

const rows = computed(() =>
  props.schema.map((field) => {
    const v1 = props.v1Json[field.key]
    const v2 = props.v2Json[field.key]
    const str1 = JSON.stringify(v1)
    const str2 = JSON.stringify(v2)
    return {
      field: field.key,
      label: field.label,
      v1,
      v2,
      changed: str1 !== str2,
    }
  })
)

function formatValue(val) {
  if (val === null || val === undefined) return '(空)'
  if (typeof val === 'object') return JSON.stringify(val, null, 2)
  return val
}
</script>

<style scoped>
.version-compare-table {
  width: 100%;
}
.compare-cell {
  margin: 0;
  font-family: inherit;
  font-size: 13px;
  white-space: pre-wrap;
  word-break: break-all;
}
.compare-cell.changed {
  background-color: #fff7e6;
  padding: 4px 8px;
  border-radius: 4px;
}
</style>
