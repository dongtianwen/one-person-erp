<template>
  <!-- 无对应内容时不渲染，静默处理 -->
  <span v-if="tipText" class="field-tip-wrapper">
    <!-- 桌面端：❓ 图标 + hover tooltip -->
    <el-tooltip
      v-if="!isMobile"
      :content="tipText"
      placement="top"
      :show-after="300"
    >
      <span class="field-tip-icon" @click.stop>?</span>
    </el-tooltip>
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { FIELD_TIPS } from '../constants/help'

const props = defineProps({
  module: { type: String, required: true },
  field: { type: String, required: true },
})

const tipText = computed(() => {
  return FIELD_TIPS[props.module]?.[props.field] || ''
})

const isMobile = computed(() => window.innerWidth < 640)
</script>

<style scoped>
.field-tip-wrapper {
  display: inline-flex;
  align-items: center;
  margin-left: 4px;
}

.field-tip-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--el-color-primary-light-8);
  color: var(--el-color-primary);
  font-size: 11px;
  font-weight: 600;
  cursor: help;
  flex-shrink: 0;
  transition: background 0.15s;
}

.field-tip-icon:hover {
  background: var(--el-color-primary-light-6);
}
</style>
