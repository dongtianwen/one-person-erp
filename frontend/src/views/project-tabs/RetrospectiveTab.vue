<!-- v2.0 项目复盘 Tab -->
<template>
  <div class="retrospective-tab">
    <div v-if="loading" class="loading-wrapper">
      <el-skeleton :rows="6" animated />
    </div>

    <template v-else>
      <!-- 无复盘时显示创建按钮 -->
      <div v-if="!currentRetro && !retrospectives.length" class="empty-state">
        <el-empty description="暂无复盘记录">
          <el-button type="primary" @click="handleCreate">
            <el-icon><EditPen /></el-icon> 创建复盘
          </el-button>
        </el-empty>
      </div>

      <!-- 复盘列表（多次复盘时切换） -->
      <div v-if="retrospectives.length > 1" class="retro-switcher">
        <span class="switch-label">历史复盘</span>
        <el-select
          :model-value="currentIndex"
          @change="handleSwitchRetro"
          size="small"
          style="width: 220px;"
        >
          <el-option
            v-for="(r, i) in retrospectives"
            :key="r.id"
            :label="'#' + (i + 1) + ' — ' + (r.submitted_at ? formatTime(r.submitted_at) : '草稿 ' + formatTime(r.created_at))"
            :value="i"
          />
        </el-select>
      </div>

      <!-- 数据看板区 -->
      <div v-if="currentRetro?.auto_metrics" class="metrics-dashboard">
        <el-row :gutter="16">
          <el-col :span="8">
            <el-card shadow="never" class="metric-card profit-card">
              <template #header><span class="card-title"><el-icon><Money /></el-icon> 利润</span></template>
              <div class="metric-grid">
                <div class="m-item"><span class="mk">合同额</span><span class="mv">¥{{ fmtAmt(m.profit.contract_amount) }}</span></div>
                <div class="m-item"><span class="mk">实收</span><span class="mv">¥{{ fmtAmt(m.profit.received_amount) }}</span></div>
                <div class="m-item"><span class="mk">成本</span><span class="mv">¥{{ fmtAmt(m.profit.total_cost) }}</span></div>
                <div class="m-item highlight"><span class="mk">利润</span><span class="mv">¥{{ fmtAmt(m.profit.gross_profit) }}</span></div>
                <div class="m-item full"><span class="mk">利润率</span><span class="mv rate">{{ m.profit.gross_margin != null ? (m.profit.gross_margin * 100).toFixed(1) + '%' : '-' }}</span></div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="8">
            <el-card shadow="never" class="metric-card schedule-card">
              <template #header><span class="card-title"><el-icon><Timer /></el-icon> 效率</span></template>
              <div class="metric-grid">
                <div class="m-item"><span class="mk">计划工期</span><span class="mv">{{ m.schedule.planned_days }} 天</span></div>
                <div class="m-item"><span class="mk">实际工期</span><span class="mv">{{ m.schedule.actual_days }} 天</span></div>
                <div class="m-item" :class="{ danger: m.schedule.delay_days > 0 }">
                  <span class="mk">延期</span><span class="mv">{{ m.schedule.delay_days > 0 ? m.schedule.delay_days + ' 天 ⚠️' : '无' }}</span>
                </div>
              </div>
            </el-card>
          </el-col>
          <el-col :span="8">
            <el-card shadow="never" class="metric-card quality-card">
              <template #header><span class="card-title"><el-icon><DataAnalysis /></el-icon> 质量</span></template>
              <div class="metric-grid">
                <div class="m-item"><span class="mk">变更次数</span><span class="mv">{{ m.change_orders.count }} 次</span></div>
                <div class="m-item"><span class="mk">首次通过率</span><span class="mv">{{ m.acceptance.first_pass_rate != null ? (m.acceptance.first_pass_rate * 100).toFixed(0) + '%' : '-' }}</span></div>
                <div class="m-item"><span class="mk">返工次数</span><span class="mv">{{ m.acceptance.rework_count }} 次</span></div>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>

      <!-- 手动填写区（仅 draft 可编辑） -->
      <div v-if="currentRetro && currentRetro.status === 'draft'" class="edit-section">
        <el-card shadow="never">
          <template #header><span class="card-title"><el-icon><Edit /></el-icon> 复盘内容</span></template>
          <el-form label-position="top" :model="form" style="max-width: 720px;">
            <el-form-item label="复盘总结">
              <el-input v-model="form.summary" type="textarea" :rows="3" placeholder="用2-3段话概括这个项目的整体情况..." />
            </el-form-item>
            <el-form-item label="做得好的地方">
              <el-input v-model="form.what_went_well" type="textarea" :rows="2" placeholder="哪些做法值得保留和复用？" />
            </el-form-item>
            <el-form-item label="需要改进的地方">
              <el-input v-model="form.what_to_improve" type="textarea" :rows="2" placeholder="下次可以怎么做更好？" />
            </el-form-item>
            <el-form-item label="行动清单">
              <div v-for="(action, ai) in form.improvement_actions" :key="ai" class="action-row">
                <el-input v-model="form.improvement_actions[ai]" placeholder="具体行动项...">
                  <template #append>
                    <el-button @click="removeAction(ai)" :icon="Delete" />
                  </template>
                </el-input>
              </div>
              <el-button size="small" plain @click="addAction" style="margin-top: 4px;">
                <el-icon><Plus /></el-icon> 添加行动项
              </el-button>
            </el-form-item>
          </el-form>
          <div class="form-actions">
            <el-button @click="handleSaveDraft">保存草稿</el-button>
            <el-button type="primary" @click="handleSubmit">提交复盘</el-button>
          </div>
        </el-card>
      </div>

      <!-- 已提交的只读展示 -->
      <div v-if="currentRetro && currentRetro.status === 'submitted'" class="readonly-section">
        <el-card shadow="never">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span class="card-title"><el-icon><Document /></el-icon> 复盘记录</span>
              <el-tag type="success" size="small" effect="dark">已提交 {{ currentRetro.submitted_at ? formatDate(currentRetro.submitted_at) : '' }}</el-tag>
            </div>
          </template>
          <div class="readonly-content" v-if="currentRetro.summary || currentRetro.what_went_well || currentRetro.what_to_improve">
            <section v-if="currentRetro.summary" class="rd-sec">
              <h4>总结</h4>
              <p>{{ currentRetro.summary }}</p>
            </section>
            <section v-if="currentRetro.what_went_well" class="rd-sec good">
              <h4>✅ 做得好的</h4>
              <p>{{ currentRetro.what_went_well }}</p>
            </section>
            <section v-if="currentRetro.what_to_improve" class="rd-sec improve">
              <h4>🔧 需要改进</h4>
              <p>{{ currentRetro.what_to_improve }}</p>
            </section>
            <section v-if="currentRetro.improvement_actions?.length" class="rd-sec actions">
              <h4>📋 行动清单</h4>
              <ol>
                <li v-for="(a, i) in currentRetro.improvement_actions" :key="i">{{ typeof a === 'string' ? a : a.text || '' }}</li>
              </ol>
            </section>
          </div>
          <el-empty v-else description="未填写详细内容" :image-size="80" />
        </el-card>
      </div>

      <!-- 再次创建新复盘按钮 -->
      <div v-if="currentRetro && currentRetro.status === 'submitted'" style="margin-top:16px;text-align:center;">
        <el-button plain @click="handleCreate">
          <el-icon><Plus /></el-icon> 再写一次复盘
        </el-button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import api from '../../api/index'
import {
  ElMessage,
} from 'element-plus'
import {
  EditPen, Money, Timer, DataAnalysis, Edit, Document, Plus, Delete,
} from '@element-plus/icons-vue'

const props = defineProps({
  projectId: { type: [Number, String], required: true },
})

const route = useRoute()
const loading = ref(false)
const retrospectives = ref([])
const currentIndex = ref(0)

const currentRetro = computed(() => retrospectives.value[currentIndex.value] || null)

const m = computed(() => currentRetro.value?.auto_metrics || {})

const form = ref({
  summary: '',
  what_went_well: '',
  what_to_improve: '',
  improvement_actions: [''],
})

watch(currentRetro, (val) => {
  if (val && val.status === 'draft') {
    form.value = {
      summary: val.summary || '',
      what_went_well: val.what_went_well || '',
      what_to_improve: val.what_to_improve || '',
      improvement_actions: (val.improvement_actions?.length ? [...val.improvement_actions] : ['']),
    }
  }
}, { immediate: true })

onMounted(() => {
  loadRetrospectives()
})

async function loadRetrospectives() {
  loading.value = true
  try {
    const res = await api.get(`/projects/${props.projectId}/retrospectives`)
    retrospectives.value = res.data || []
    if (retrospectives.value.length) {
      const submittedIdx = retrospectives.value.findIndex(r => r.status === 'submitted')
      if (submittedIdx >= 0) currentIndex.value = submittedIdx
      else currentIndex.value = 0
    }
  } catch (e) {
    console.error('加载复盘失败', e)
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  try {
    const res = await api.post(`/projects/${props.projectId}/retrospectives`)
    ElMessage.success('复盘已创建，自动指标已填充')
    await loadRetrospectives()
    const newIdx = retrospectives.value.findIndex(r => r.id === res.data.id)
    if (newIdx >= 0) currentIndex.value = newIdx
  } catch (e) {
    ElMessage.error('创建失败：' + (e.response?.data?.detail || e.message))
  }
}

async function handleSaveDraft() {
  try {
    await api.put(`/projects/retrospectives/${currentRetro.value.id}`, {
      summary: form.value.summary || null,
      what_went_well: form.value.what_went_well || null,
      what_to_improve: form.value.what_to_improve || null,
      improvement_actions: form.value.improvement_actions.filter(a => a.trim()),
    })
    ElMessage.success('草稿已保存')
    await loadRetrospectives()
  } catch (e) {
    ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message))
  }
}

async function handleSubmit() {
  try {
    await handleSaveDraft()
    await api.put(`/projects/retrospectives/${currentRetro.value.id}/submit`)
    ElMessage.success('复盘已提交 ✅')
    await loadRetrospectives()
  } catch (e) {
    ElMessage.error('提交失败：' + (e.response?.data?.detail || e.message))
  }
}

function handleSwitchRetro(idx) {
  currentIndex.value = idx
}

function addAction() {
  form.value.improvement_actions.push('')
}

function removeAction(idx) {
  form.value.improvement_actions.splice(idx, 1)
}

function fmtAmt(val) {
  if (val == null) return '0'
  if (val >= 10000) return (val / 10000).toFixed(1) + '万'
  return Number(val).toLocaleString()
}

function formatTime(t) {
  if (!t) return ''
  return t.replace('T', ' ').substring(0, 16)
}

function formatDate(t) {
  if (!t) return ''
  return t.substring(0, 10)
}
</script>

<style scoped>
.retrospective-tab { padding: 4px 0; }
.loading-wrapper { padding: 20px 0; }
.empty-state { padding: 40px 0; text-align: center; }

.retro-switcher {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}
.switch-label { font-size: 13px; color: #909399; font-weight: 600; }

.metrics-dashboard { margin-bottom: 16px; }
.metric-card { border-radius: 10px; }
.metric-card :deep(.el-card__header) { padding: 12px 16px; border-bottom: 1px solid #f0f0f0; }
.card-title { display: inline-flex; align-items: center; gap: 5px; font-size: 14px; font-weight: 600; color: #303133; }

.metric-grid { display: flex; flex-direction: column; gap: 8px; }
.m-item { display: flex; justify-content: space-between; align-items: center; font-size: 13px; }
.m-item.full { border-top: 1px dashed #ebeef5; padding-top: 6px; margin-top: 2px; }
.mk { color: #909399; }
.mv { color: #303133; font-weight: 600; font-family: 'SF Mono', Consolas, monospace; }
.m-item.highlight .mv { color: #67c23a; }
.m-item.danger .mv { color: #f56c6c; }
.mv.rate { color: #409eff !important; }

.edit-section { margin-bottom: 16px; }
.form-actions { display: flex; gap: 10px; margin-top: 16px; padding-top: 16px; border-top: 1px dashed #ebeef5; }

.readonly-section .readonly-content { max-width: 700px; }
.rd-sec { margin-bottom: 18px; }
.rd-sec:last-child { margin-bottom: 0; }
.rd-sec h4 { font-size: 14px; margin: 0 0 6px; color: #606266; }
.rd-sec p { margin: 0; font-size: 14px; line-height: 1.7; color: #303133; white-space: pre-wrap; }
.rd-sec.good h4 { color: #67c23a; }
.rd-sec.improve h4 { color: #e6a23c; }
.rd-sec.actions ol { margin: 0; padding-left: 20px; }
.rd-sec.actions li { font-size: 14px; line-height: 1.9; color: #606266; }

.action-row { margin-bottom: 6px; }

.profit-card :deep(.el-card__header) { background: #fdf6ec; }
.schedule-card :deep(.el-card__header) { background: #ecf5ff; }
.quality-card :deep(.el-card__header) { background: #f0f9eb; }
</style>
