<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-title-group">
        <h2>数据导出</h2>
        <span class="header-desc">导出财务报表、客户列表、项目列表等数据</span>
        <PageHelpDrawer pageKey="finance_export" />
      </div>
    </div>

    <div class="export-grid">
      <el-card class="export-card main-config">
        <template #header>
          <div class="card-header">
            <span class="card-title">基本配置</span>
          </div>
        </template>
        
        <el-form :model="form" label-position="top" class="export-form">
          <el-form-item label="导出类型" required>
            <el-select v-model="form.exportType" placeholder="选择导出类型" style="width: 100%" size="large">
              <template #prefix>
                <el-icon><component :is="typeIcons[form.exportType] || 'Download'" /></el-icon>
              </template>
              <el-option value="finance_report">
                <div class="select-option">
                  <el-icon><TrendCharts /></el-icon>
                  <span>月度财务报表</span>
                </div>
              </el-option>
              <el-option value="customers">
                <div class="select-option">
                  <el-icon><User /></el-icon>
                  <span>客户列表</span>
                </div>
              </el-option>
              <el-option value="projects">
                <div class="select-option">
                  <el-icon><Folder /></el-icon>
                  <span>项目列表</span>
                </div>
              </el-option>
              <el-option value="contracts">
                <div class="select-option">
                  <el-icon><Document /></el-icon>
                  <span>合同列表</span>
                </div>
              </el-option>
              <el-option value="tax_ledger">
                <div class="select-option">
                  <el-icon><Ticket /></el-icon>
                  <span>增值税发票台账</span>
                </div>
              </el-option>
            </el-select>
          </el-form-item>

          <el-form-item label="导出格式" required>
            <div class="format-cards">
              <div 
                class="format-card" 
                :class="{ active: form.format === 'xlsx' }"
                @click="form.format = 'xlsx'"
              >
                <div class="format-icon excel">X</div>
                <div class="format-info">
                  <div class="format-name">Excel</div>
                  <div class="format-ext">.xlsx</div>
                </div>
                <div class="check-mark"><el-icon><Check /></el-icon></div>
              </div>
              <div 
                class="format-card" 
                :class="{ active: form.format === 'pdf' }"
                @click="form.format = 'pdf'"
              >
                <div class="format-icon pdf">P</div>
                <div class="format-info">
                  <div class="format-name">PDF</div>
                  <div class="format-ext">.pdf</div>
                </div>
                <div class="check-mark"><el-icon><Check /></el-icon></div>
              </div>
            </div>
          </el-form-item>

          <!-- Time Range - Only for specific types -->
          <el-form-item 
            v-if="['finance_report', 'tax_ledger'].includes(form.exportType)" 
            label="时间范围" 
            required
            class="animate-fade-in"
          >
            <div class="time-range-group">
              <!-- Monthly types -->
              <template v-if="form.exportType === 'finance_report'">
                <el-date-picker
                  v-model="form.yearMonth"
                  type="month"
                  placeholder="选择年月"
                  value-format="YYYY-MM"
                  style="width: 100%"
                  size="large"
                />
              </template>
              <!-- Tax ledger type -->
              <template v-else>
                <div class="tax-range">
                  <el-date-picker
                    v-model="form.yearOnly"
                    type="year"
                    placeholder="年份"
                    value-format="YYYY"
                    style="width: 120px"
                    size="large"
                  />
                  <el-select v-model="form.quarter" placeholder="季度" style="flex: 1" size="large">
                    <el-option label="Q1 (1-3月)" :value="1" />
                    <el-option label="Q2 (4-6月)" :value="2" />
                    <el-option label="Q3 (7-9月)" :value="3" />
                    <el-option label="Q4 (10-12月)" :value="4" />
                  </el-select>
                </div>
              </template>
            </div>
          </el-form-item>
          
          <div v-else class="global-hint animate-fade-in">
            <el-icon><InfoFilled /></el-icon>
            <span>此项导出将包含系统内所有实时数据快照，无需选择时间范围。</span>
          </div>

          <div class="export-actions">
            <el-button 
              type="primary" 
              @click="handleExport" 
              :loading="exporting" 
              :disabled="!canExport"
              class="btn-export"
              size="large"
            >
              <el-icon><Download /></el-icon>
              <span>{{ exporting ? '正式导出中...' : '开始生成报表' }}</span>
            </el-button>
          </div>
        </el-form>
      </el-card>

      <div class="export-side">
        <el-card class="export-hint">
          <template #header>
            <div class="card-header">
              <el-icon><QuestionFilled /></el-icon>
              <span class="card-title">导出指南</span>
            </div>
          </template>
          <div class="hint-steps">
            <div class="hint-step">
              <div class="step-icon"><el-icon><TrendCharts /></el-icon></div>
              <div class="step-content">
                <div class="step-title">财务明细</div>
                <div class="step-desc">集成收支明细、分类汇总、资金汇总于一体。</div>
              </div>
            </div>
            <div class="hint-step">
              <div class="step-icon"><el-icon><User /></el-icon></div>
              <div class="step-content">
                <div class="step-title">客户与生命周期</div>
                <div class="step-desc">全面透视客户价值、合作频率及归档日期。</div>
              </div>
            </div>
            <div class="hint-step">
              <div class="step-icon"><el-icon><Folder /></el-icon></div>
              <div class="step-content">
                <div class="step-title">项目利润核算</div>
                <div class="step-desc">实时计算项目收支差额，展示精确毛利率。</div>
              </div>
            </div>
            <div class="hint-step warning">
              <div class="step-icon"><el-icon><Watch /></el-icon></div>
              <div class="step-content">
                <div class="step-title">自动纠偏</div>
                <div class="step-desc">即使数据部分缺失，系统也会尝试补全表头。</div>
              </div>
            </div>
          </div>
        </el-card>

        <div class="premium-badge">
          <el-icon><CircleCheckFilled /></el-icon>
          数据导出已通过银行级加密通道处理
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  Download, TrendCharts, User, Folder, Document, Ticket, 
  Check, InfoFilled, QuestionFilled, Watch, CircleCheckFilled 
} from '@element-plus/icons-vue'
import api from '../api'
import PageHelpDrawer from '../components/PageHelpDrawer.vue'

const typeIcons = {
  finance_report: 'TrendCharts',
  customers: 'User',
  projects: 'Folder',
  contracts: 'Document',
  tax_ledger: 'Ticket'
}

const form = ref({
  exportType: 'finance_report',
  format: 'xlsx',
  yearMonth: '',
  yearOnly: '',
  quarter: null,
})

const exporting = ref(false)

// Reset quarter when switching away from tax_ledger
watch(() => form.value.exportType, (newType) => {
  if (newType !== 'tax_ledger') {
    form.value.quarter = null
  }
})

const canExport = computed(() => {
  const type = form.value.exportType
  if (type === 'tax_ledger') {
    return !!(form.value.yearOnly && form.value.quarter)
  }
  if (type === 'finance_report') {
    return !!form.value.yearMonth
  }
  // 全局列表（customers, projects, contracts）不需要时间范围
  return true
})

const handleExport = async () => {
  if (!canExport.value) {
    ElMessage.warning('请选择完整的时间范围')
    return
  }

  exporting.value = true
  try {
    let year, month, quarter
    const now = new Date()
    if (form.value.exportType === 'tax_ledger') {
      year = parseInt(form.value.yearOnly)
      month = undefined
      quarter = form.value.quarter
    } else if (form.value.exportType === 'finance_report') {
      const [y, m] = form.value.yearMonth.split('-')
      year = parseInt(y)
      month = parseInt(m)
      quarter = undefined
    } else {
      // 对于全局列表，传递当前年份作为 placeholder（后端目前要求 year 为 int）
      year = now.getFullYear()
      month = undefined
      quarter = undefined
    }

    const response = await api.post(
      `/export/${form.value.exportType}`,
      { format: form.value.format, year, month, quarter },
      { responseType: 'blob' }
    )

    // Trigger download
    const blob = new Blob([response.data])
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url

    // Extract filename from Content-Disposition
    const disposition = response.headers['content-disposition']
    let fileLabel = month ? `${month}月` : (quarter ? `Q${quarter}` : '全部')
    let filename = `${form.value.exportType}_${year}_${fileLabel}.${form.value.format}`
    if (disposition) {
      const match = disposition.match(/filename\*=UTF-8''(.+?)(?:;|$)/)
      if (match) {
        filename = decodeURIComponent(match[1])
      }
    }

    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)

    ElMessage.success('导出成功')
  } catch (e) {
    if (e.response?.status === 422) {
      ElMessage.error('参数错误：' + (e.response.data?.detail || '请检查输入'))
    } else if (e.response?.status === 500) {
      ElMessage.error('导出失败，请重试')
    } else {
      ElMessage.error('导出失败，请重试')
    }
  } finally {
    exporting.value = false
  }
}
</script>

<style scoped>
.export-grid {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 24px;
}

.main-config {
  height: fit-content;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-title {
  font-weight: 600;
  font-size: 15px;
}

.select-option {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* Format Cards */
.format-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.format-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px;
  border: 2px solid var(--border-light, #f1f5f9);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  background: white;
}

.format-card:hover {
  border-color: var(--el-color-primary-light-5);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
}

.format-card.active {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}

.format-icon {
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  font-weight: 800;
  font-size: 20px;
  color: white;
}

.format-icon.excel { background: linear-gradient(135deg, #107c41, #21a366); }
.format-icon.pdf { background: linear-gradient(135deg, #e4393c, #ff4d4f); }

.format-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.format-ext {
  font-size: 12px;
  color: var(--text-tertiary);
}

.check-mark {
  position: absolute;
  top: -8px;
  right: -8px;
  width: 20px;
  height: 20px;
  background: var(--el-color-primary);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  transform: scale(0);
  transition: transform 0.2s;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.format-card.active .check-mark {
  transform: scale(1);
}

.tax-range {
  display: flex;
  gap: 12px;
  width: 100%;
}

.global-hint {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: var(--bg-soft, #f8fafc);
  border-radius: 8px;
  color: var(--text-secondary);
  font-size: 13px;
  margin-bottom: 24px;
  border-left: 4px solid var(--el-color-info);
}

.export-actions {
  margin-top: 12px;
}

.btn-export {
  width: 100%;
  height: 48px !important;
  font-weight: 600;
  letter-spacing: 1px;
}

/* Side Info */
.hint-steps {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.hint-step {
  display: flex;
  gap: 16px;
}

.step-icon {
  width: 32px;
  height: 32px;
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.hint-step.warning .step-icon {
  background: var(--el-color-warning-light-9);
  color: var(--el-color-warning);
}

.step-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 4px;
}

.step-desc {
  font-size: 12px;
  line-height: 1.5;
  color: var(--text-tertiary);
}

.premium-badge {
  margin-top: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-tertiary);
  padding: 12px;
  border: 1px dashed var(--border-light);
  border-radius: 8px;
}

.animate-fade-in {
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 992px) {
  .export-grid {
    grid-template-columns: 1fr;
  }
}
</style>
