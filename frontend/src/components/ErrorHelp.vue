<template>
  <el-dialog
    v-model="visible"
    title="操作失败"
    width="460px"
    :close-on-click-modal="true"
    align-center
    class="error-help-dialog"
  >
    <div v-if="helpData" class="error-help-content">
      <div class="error-reason">
        <el-icon :size="18" color="var(--el-color-warning)"><WarningFilled /></el-icon>
        <span>{{ helpData.reason }}</span>
      </div>
      <div v-if="helpData.next_steps?.length" class="error-next-steps">
        <div class="steps-title">下一步操作</div>
        <ol class="steps-list">
          <li v-for="(step, idx) in helpData.next_steps" :key="idx">{{ step }}</li>
        </ol>
      </div>
    </div>
    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'
import { WarningFilled } from '@element-plus/icons-vue'

const visible = ref(false)
const helpData = ref(null)

const show = (help) => {
  helpData.value = help
  visible.value = true
}

defineExpose({ show })
</script>

<style scoped>
.error-help-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.error-reason {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  font-size: 14px;
  color: var(--text-primary);
  line-height: 1.6;
}

.steps-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.steps-list {
  margin: 0;
  padding-left: 20px;
  font-size: 13px;
  color: var(--text-primary);
  line-height: 2;
}

.steps-list li {
  padding-left: 4px;
}
</style>
