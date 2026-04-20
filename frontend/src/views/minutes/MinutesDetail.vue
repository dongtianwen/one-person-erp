<template>
  <el-descriptions :column="1" border size="small">
    <el-descriptions-item label="标题">{{ data.title || '-' }}</el-descriptions-item>
    <el-descriptions-item label="参与人">{{ data.participants || '-' }}</el-descriptions-item>
    <el-descriptions-item label="结论">{{ data.conclusions || '-' }}</el-descriptions-item>
    <el-descriptions-item label="待办事项">{{ data.action_items || '-' }}</el-descriptions-item>
    <el-descriptions-item label="风险点">{{ data.risk_points || '-' }}</el-descriptions-item>
    <el-descriptions-item label="会议日期">{{ data.meeting_date || '-' }}</el-descriptions-item>
  </el-descriptions>
</template>

<script setup>
defineProps({
  data: { type: Object, default: () => ({}) },
})
</script>
