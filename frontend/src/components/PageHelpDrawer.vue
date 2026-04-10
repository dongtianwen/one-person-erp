<template>
  <!-- 无对应内容时不渲染按钮，静默处理 -->
  <template v-if="pageData">
    <el-button class="page-help-trigger" @click="visible = true">
      ? 帮助
    </el-button>

    <el-drawer
      v-model="visible"
      :title="pageData.title"
      direction="rtl"
      :size="isMobile ? '100%' : '320px'"
      :close-on-click-modal="true"
    >
      <div class="help-drawer-content">
        <p class="help-description">{{ pageData.description }}</p>
        <div class="help-tips">
          <div v-for="(tip, idx) in pageData.tips.slice(0, 5)" :key="idx" class="help-tip-item">
            <span class="tip-bullet">{{ idx + 1 }}</span>
            <span class="tip-text">{{ tip }}</span>
          </div>
        </div>
      </div>
    </el-drawer>
  </template>
</template>

<script setup>
import { ref, computed } from 'vue'
import { PAGE_TIPS } from '../constants/help'

const props = defineProps({
  pageKey: { type: String, required: true },
})

const visible = ref(false)

const pageData = computed(() => PAGE_TIPS[props.pageKey] || null)

const isMobile = computed(() => window.innerWidth < 640)
</script>

<style scoped>
.page-help-trigger {
  font-size: 13px;
  color: var(--text-secondary);
  border: 1px solid var(--border-default);
  background: transparent;
  padding: 6px 12px;
  border-radius: 6px;
}

.page-help-trigger:hover {
  color: var(--el-color-primary);
  border-color: var(--el-color-primary-light-5);
  background: var(--el-color-primary-light-9);
}

.help-drawer-content {
  padding: 0 4px;
}

.help-description {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin: 0 0 20px 0;
}

.help-tips {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.help-tip-item {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}

.tip-bullet {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  font-size: 12px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.tip-text {
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.6;
  padding-top: 1px;
}
</style>
