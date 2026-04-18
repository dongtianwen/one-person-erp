<template>
  <div class="workflow-guide-page">
    <div class="page-header">
      <h2>业务流程与核心概念</h2>
      <PageHelpDrawer pageKey="workflow_guide" />
      <p class="page-desc">了解系统业务流程和关键术语定义</p>
    </div>

    <el-tabs v-model="activeTab" class="guide-tabs">
      <!-- Tab 1: 业务流程 -->
      <el-tab-pane label="业务流程" name="workflow">
        <div class="workflow-section">
          <!-- 桌面端：水平步骤条 -->
          <div class="workflow-steps-desktop">
            <div
              v-for="(step, idx) in WORKFLOW_STEPS"
              :key="step.id"
              class="workflow-step"
              :class="{ active: isStepActive(step.route), expanded: expandedStep === step.id }"
            >
              <div class="step-header" @click="toggleStep(step.id)">
                <div class="step-number" :class="{ active: isStepActive(step.route) }">{{ idx + 1 }}</div>
                <div class="step-info">
                  <div class="step-label">{{ step.label }} <span class="step-version">{{ step.version }}</span></div>
                  <div class="step-desc">{{ step.description }}</div>
                </div>
                <el-icon class="step-expand-icon" :class="{ rotated: expandedStep === step.id }">
                  <ArrowDown />
                </el-icon>
              </div>
              <transition name="expand">
                <div v-if="expandedStep === step.id" class="step-detail">
                  <div class="detail-section">
                    <div class="detail-label">关键操作</div>
                    <ul class="detail-list">
                      <li v-for="action in step.key_actions" :key="action">{{ action }}</li>
                    </ul>
                  </div>
                  <div v-if="step.triggers_next" class="detail-section">
                    <div class="detail-label">下一步触发条件</div>
                    <div class="detail-text">{{ step.triggers_next }}</div>
                  </div>
                  <el-button type="primary" link @click="$router.push(step.route)">
                    前往{{ step.label }} →
                  </el-button>
                </div>
              </transition>
              <div v-if="idx < WORKFLOW_STEPS.length - 1" class="step-connector" />
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- Tab 2: 核心概念 -->
      <el-tab-pane label="核心概念" name="concepts">
        <div class="concepts-grid">
          <div v-for="concept in CORE_CONCEPTS" :key="concept.term" class="concept-card" :id="'concept-' + concept.term">
            <div class="concept-term">{{ concept.term }}</div>
            <div class="concept-definition">{{ concept.definition }}</div>
            <div v-if="concept.key_rule" class="concept-key-rule">{{ concept.key_rule }}</div>
            <div class="concept-related">
              <span v-for="r in concept.related" :key="r" class="concept-tag">{{ r }}</span>
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowDown } from '@element-plus/icons-vue'
import { WORKFLOW_STEPS, CORE_CONCEPTS } from '../constants/help'
import PageHelpDrawer from '../components/PageHelpDrawer.vue'

const route = useRoute()
const activeTab = ref('workflow')
const expandedStep = ref(null)

const isStepActive = (stepRoute) => {
  return route.path.startsWith(stepRoute)
}

const toggleStep = (stepId) => {
  expandedStep.value = expandedStep.value === stepId ? null : stepId
}
</script>

<style scoped>
.workflow-guide-page {
  max-width: 960px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h2 {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 4px 0;
}

.page-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin: 0;
}

.guide-tabs :deep(.el-tabs__header) {
  margin-bottom: 20px;
}

/* ── 业务流程步骤 ─────────────────────────────────────── */

.workflow-steps-desktop {
  display: flex;
  flex-direction: column;
  gap: 0;
}

.workflow-step {
  position: relative;
  padding: 0;
}

.workflow-step.active > .step-header .step-label {
  color: var(--el-color-primary);
  font-weight: 600;
}

.step-header {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.15s;
}

.step-header:hover {
  background: var(--surface-card);
}

.step-number {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--surface-card);
  color: var(--text-secondary);
  font-size: 14px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: 1px solid var(--border-default);
  transition: all 0.15s;
}

.step-number.active {
  background: var(--el-color-primary);
  color: #fff;
  border-color: var(--el-color-primary);
}

.step-info {
  flex: 1;
  min-width: 0;
}

.step-label {
  font-size: 15px;
  font-weight: 500;
  color: var(--text-primary);
}

.step-version {
  font-size: 11px;
  color: var(--text-secondary);
  margin-left: 6px;
}

.step-desc {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 2px;
}

.step-expand-icon {
  color: var(--text-secondary);
  transition: transform 0.2s;
  flex-shrink: 0;
}

.step-expand-icon.rotated {
  transform: rotate(180deg);
}

.step-detail {
  padding: 0 16px 16px 62px;
  animation: slideDown 0.2s ease;
}

@keyframes slideDown {
  from { opacity: 0; transform: translateY(-8px); }
  to { opacity: 1; transform: translateY(0); }
}

.detail-section {
  margin-bottom: 12px;
}

.detail-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.detail-list {
  margin: 0;
  padding-left: 18px;
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.8;
}

.detail-text {
  font-size: 13px;
  color: var(--text-primary);
  line-height: 1.6;
  padding: 8px 12px;
  background: var(--surface-card);
  border-radius: 8px;
  border: 1px solid var(--border-default);
}

.step-connector {
  position: relative;
  height: 16px;
  margin-left: 31px;
  border-left: 2px dashed var(--border-default);
}

/* ── 核心概念 ─────────────────────────────────────────── */

.concepts-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.concept-card {
  background: var(--surface-card);
  border: 1px solid var(--border-default);
  border-radius: 12px;
  padding: 18px;
  transition: box-shadow 0.15s;
}

.concept-card:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
}

.concept-term {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 8px;
}

.concept-definition {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: 10px;
}

.concept-key-rule {
  font-size: 12px;
  color: #92400e;
  background: #fef3c7;
  border: 1px solid #fde68a;
  border-radius: 6px;
  padding: 6px 10px;
  margin-bottom: 10px;
  line-height: 1.5;
}

.concept-related {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.concept-tag {
  font-size: 11px;
  color: var(--el-color-primary);
  background: rgba(6, 182, 212, 0.08);
  border: 1px solid rgba(6, 182, 212, 0.2);
  border-radius: 4px;
  padding: 2px 8px;
  cursor: default;
}

/* ── 移动端适配 ───────────────────────────────────────── */

@media (max-width: 640px) {
  .workflow-guide-page {
    padding: 0 4px;
  }

  .step-detail {
    padding-left: 16px;
  }

  .concepts-grid {
    grid-template-columns: 1fr;
  }
}
</style>
