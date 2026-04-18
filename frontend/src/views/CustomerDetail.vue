<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-left">
        <el-button link @click="router.back()" class="back-btn">
          <el-icon><ArrowLeft /></el-icon> 返回
        </el-button>
        <h2 v-if="customer">{{ customer.name }}</h2>
        <PageHelpDrawer pageKey="customer_detail" />
      </div>
      <el-tag v-if="customer" :type="statusTypes[customer.status] || 'info'" size="large" round>
        {{ statusLabels[customer.status] || customer.status }}
      </el-tag>
      <div style="display: flex; align-items: center; gap: 10px;">
        <el-button type="success" size="small" @click="handleGenerateCustomerReport" :loading="generatingReport">
          生成客户分析报告
        </el-button>
        <el-button size="small" @click="showReportHistory">历史报告</el-button>
      </div>
    </div>

    <div v-if="loading" v-loading="true" style="min-height: 200px"></div>

    <template v-else-if="customer">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="基本信息" name="info">
          <el-card class="info-card">
            <div class="info-grid">
              <div class="info-item">
                <span class="info-label">客户名称</span>
                <span class="info-value">{{ customer.name }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">联系人</span>
                <span class="info-value">{{ customer.contact_person || '-' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">电话</span>
                <span class="info-value mono">{{ customer.phone || '-' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">邮箱</span>
                <span class="info-value">{{ customer.email || '-' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">公司</span>
                <span class="info-value">{{ customer.company || '-' }}</span>
              </div>
              <div class="info-item">
                <span class="info-label">来源</span>
                <span class="info-value">{{ sourceLabels[customer.source] || customer.source }}</span>
              </div>
              <div class="info-item" v-if="customer.lost_reason">
                <span class="info-label">流失原因</span>
                <span class="info-value lost-reason">{{ customer.lost_reason }}</span>
              </div>
              <div class="info-item full-width" v-if="customer.notes">
                <span class="info-label">备注</span>
                <span class="info-value">{{ customer.notes }}</span>
              </div>
            </div>
          </el-card>
        </el-tab-pane>

        <!-- Customer Lifetime Value Panel -->
        <el-tab-pane label="客户价值" name="ltv">
          <el-card class="ltv-card">
            <div class="ltv-grid">
              <div class="ltv-item">
                <span class="ltv-label">历史合同总额</span>
                <span class="ltv-value mono">{{ ltvData.total_contract_amount !== null ? '¥' + Number(ltvData.total_contract_amount).toLocaleString() : '—' }}</span>
              </div>
              <div class="ltv-item">
                <span class="ltv-label">历史实收金额</span>
                <span class="ltv-value mono">{{ ltvData.total_received_amount !== null ? '¥' + Number(ltvData.total_received_amount).toLocaleString() : '—' }}</span>
              </div>
              <div class="ltv-item">
                <span class="ltv-label">合作项目数</span>
                <span class="ltv-value mono">{{ ltvData.project_count !== null ? ltvData.project_count : '—' }}</span>
              </div>
              <div class="ltv-item">
                <span class="ltv-label">平均项目金额</span>
                <span class="ltv-value mono">{{ ltvData.avg_project_amount !== null ? '¥' + Number(ltvData.avg_project_amount).toLocaleString() : '—' }}</span>
              </div>
              <div class="ltv-item">
                <span class="ltv-label">首次合作日期</span>
                <span class="ltv-value mono">{{ ltvData.first_cooperation_date || '—' }}</span>
              </div>
              <div class="ltv-item">
                <span class="ltv-label">最近合作日期</span>
                <span class="ltv-value mono">{{ ltvData.last_cooperation_date || '—' }}</span>
              </div>
            </div>
            <div v-if="ltvError" class="ltv-error">
              <el-alert title="数据加载失败，请刷新" type="error" :closable="false" />
            </div>
          </el-card>
        </el-tab-pane>

        <el-tab-pane :label="'关联项目 (' + projects.length + ')'" name="projects">
          <el-card>
            <div v-if="projects.length === 0" class="empty-hint">暂无关联项目</div>
            <el-table v-else :data="projects" style="width: 100%">
              <el-table-column prop="name" label="项目名称" min-width="140">
                <template #default="{ row }">
                  <span class="cell-name">{{ row.name }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="projectStatusTypes[row.status] || 'info'" size="small" round>
                    {{ projectStatusLabels[row.status] || row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="budget" label="预算" width="120">
                <template #default="{ row }">
                  <span class="mono">{{ row.budget ? '¥' + Number(row.budget).toLocaleString() : '-' }}</span>
                </template>
              </el-table-column>
              <el-table-column label="进度" width="140">
                <template #default="{ row }">
                  <div class="progress-cell">
                    <el-progress :percentage="row.progress || 0" :stroke-width="6" :show-text="false" />
                    <span class="mono progress-label">{{ row.progress || 0 }}%</span>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="时间" width="160">
                <template #default="{ row }">
                  <span class="mono date-text">{{ row.start_date || '-' }} ~ {{ row.end_date || '-' }}</span>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-tab-pane>

        <el-tab-pane :label="'关联合同 (' + contracts.length + ')'" name="contracts">
          <el-card>
            <div v-if="contracts.length === 0" class="empty-hint">暂无关联合同</div>
            <el-table v-else :data="contracts" style="width: 100%">
              <el-table-column prop="contract_no" label="合同编号" width="160">
                <template #default="{ row }">
                  <span class="mono contract-no">{{ row.contract_no }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="title" label="合同名称" min-width="140" />
              <el-table-column prop="amount" label="金额" width="120">
                <template #default="{ row }">
                  <span class="mono">¥{{ Number(row.amount).toLocaleString() }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="contractStatusTypes[row.status] || 'info'" size="small" round>
                    {{ contractStatusLabels[row.status] || row.status }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="签约日期" width="120">
                <template #default="{ row }">
                  <span class="mono">{{ row.signed_date || '-' }}</span>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-tab-pane>
        <el-tab-pane :label="'报价 (' + quotations.length + ')'" name="quotations">
          <el-card>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
              <el-select v-model="quoteStatusFilter" placeholder="状态筛选" clearable size="small" style="width: 130px" @change="loadQuotations">
                <el-option v-for="(label, val) in quoteStatusLabels" :key="val" :label="label" :value="val" />
              </el-select>
              <el-button type="primary" size="small" @click="goCreateQuote">
                <el-icon><Plus /></el-icon> 新建报价
              </el-button>
            </div>
            <div v-if="!quotations.length" class="empty-hint">暂无报价记录</div>
            <el-table v-else :data="quotations" size="small" style="width: 100%">
              <el-table-column prop="quote_no" label="报价编号" width="160">
                <template #default="{ row }">
                  <span class="mono contract-no" style="cursor: pointer" @click="goToQuotation(row)">{{ row.quote_no }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="title" label="标题" min-width="140" />
              <el-table-column prop="total_amount" label="总价" width="110" align="right">
                <template #default="{ row }">
                  <span class="mono">¥{{ Number(row.total_amount || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="status" label="状态" width="90">
                <template #default="{ row }">
                  <el-tag :type="quoteStatusTypes[row.status] || 'info'" size="small" round>{{ quoteStatusLabels[row.status] || row.status }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="valid_until" label="有效期" width="110">
                <template #default="{ row }">
                  <span class="mono" :style="{ color: row.status === 'expired' ? '#f43f5e' : '' }">{{ row.valid_until }}</span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="80">
                <template #default="{ row }">
                  <el-button link type="primary" size="small" @click="goToQuotation(row)">查看</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-tab-pane>

        <el-tab-pane :label="'资产与托管记录 (' + assets.length + ')'" name="assets">
          <el-card>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
              <span style="font-size: 14px; font-weight: 600">资产与托管记录</span>
              <el-button type="primary" size="small" @click="openCreateAsset()">
                <el-icon><Plus /></el-icon> 新增资产
              </el-button>
            </div>
            <div v-if="!assets.length" class="empty-hint">暂无资产记录</div>
            <el-table v-else :data="assets" size="small" style="width: 100%">
              <el-table-column prop="asset_type" label="类型" width="100">
                <template #default="{ row }">{{ assetTypeLabels[row.asset_type] || row.asset_type }}</template>
              </el-table-column>
              <el-table-column prop="name" label="名称" min-width="160" />
              <el-table-column prop="expiry_date" label="到期日期" width="120">
                <template #default="{ row }">
                  <span :style="{ color: row.expiry_date && new Date(row.expiry_date) < new Date() ? '#f43f5e' : row.expiry_date && (new Date(row.expiry_date) - new Date()) / 86400000 <= 30 ? '#f59e0b' : '' }">{{ row.expiry_date || '-' }}</span>
                </template>
              </el-table-column>
              <el-table-column prop="supplier" label="供应商" width="140">
                <template #default="{ row }">{{ row.supplier || '-' }}</template>
              </el-table-column>
              <el-table-column prop="annual_fee" label="年费" width="100">
                <template #default="{ row }">{{ row.annual_fee ? '¥' + Number(row.annual_fee).toLocaleString() : '-' }}</template>
              </el-table-column>
              <el-table-column label="操作" width="120">
                <template #default="{ row }">
                  <el-button link type="primary" size="small" @click="openEditAsset(row)">编辑</el-button>
                  <el-button link type="danger" size="small" @click="handleDeleteAsset(row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>

          <el-dialog v-model="assetFormVisible" :title="editingAssetId ? '编辑资产' : '新增资产'" width="520px" destroy-on-close>
            <el-form :model="assetForm" label-width="80px">
              <el-form-item label="资产类型" required>
                <el-select v-model="assetForm.asset_type" placeholder="选择类型" style="width: 100%">
                  <el-option v-for="(label, val) in assetTypeLabels" :key="val" :label="label" :value="val" />
                </el-select>
              </el-form-item>
              <el-form-item label="名称" required>
                <el-input v-model="assetForm.name" placeholder="资产名称" />
              </el-form-item>
              <el-form-item label="到期日期">
                <el-date-picker v-model="assetForm.expiry_date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" style="width: 100%" />
              </el-form-item>
              <el-form-item label="供应商">
                <el-input v-model="assetForm.supplier" placeholder="供应商名称" />
              </el-form-item>
              <el-form-item label="年费">
                <el-input-number v-model="assetForm.annual_fee" :min="0" :precision="2" style="width: 100%" />
              </el-form-item>
              <el-form-item label="账号信息">
                <el-input v-model="assetForm.account_info" placeholder="相关账号" />
              </el-form-item>
              <el-form-item label="备注">
                <el-input v-model="assetForm.notes" type="textarea" :rows="2" />
              </el-form-item>
            </el-form>
            <template #footer>
              <el-button @click="assetFormVisible = false">取消</el-button>
              <el-button type="primary" @click="submitAssetForm">确定</el-button>
            </template>
          </el-dialog>
        </el-tab-pane>
      </el-tabs>

      <el-dialog v-model="reportHistoryVisible" title="历史报告" width="600px" destroy-on-close>
        <el-table :data="reportHistory" size="small" v-if="reportHistory.length">
          <el-table-column label="生成时间" width="160">
            <template #default="{ row }">{{ row.generated_at || row.created_at }}</template>
          </el-table-column>
          <el-table-column prop="llm_provider" label="Provider" width="100" />
          <el-table-column prop="status" label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.status === 'completed' ? 'success' : row.status === 'failed' ? 'danger' : 'warning'" size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="version_no" label="版本" width="60" />
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="viewReport(row.id)">查看</el-button>
              <el-button link type="danger" size="small" @click="handleDeleteReport(row.id)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div v-else class="empty-hint">暂无历史报告</div>
      </el-dialog>

      <el-dialog v-model="reportContentVisible" title="报告内容" width="700px" destroy-on-close>
        <div style="white-space: pre-wrap; line-height: 1.8; font-size: 14px; max-height: 60vh; overflow-y: auto;">{{ reportContent }}</div>
      </el-dialog>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
onMounted(() => loadData())
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import { getCustomer } from '../api/customers'
import { getCustomerAssets, createCustomerAsset, updateCustomerAsset, deleteCustomerAsset } from '../api/customerAssets'
import { generateReport, listReports, getReport, deleteReport as deleteReportApi } from '../api/reports'
import api from '../api/index'

import { Plus } from '@element-plus/icons-vue'
import PageHelpDrawer from '../components/PageHelpDrawer.vue'

const route = useRoute()
const router = useRouter()
const customer = ref(null)
const projects = ref([])
const contracts = ref([])
const loading = ref(true)
const activeTab = ref('info')
const ltvData = ref({
  total_contract_amount: null,
  total_received_amount: null,
  project_count: null,
  avg_project_amount: null,
  first_cooperation_date: null,
  last_cooperation_date: null,
})
const ltvError = ref(false)
const generatingReport = ref(false)
const reportHistoryVisible = ref(false)
const reportHistory = ref([])
const reportContentVisible = ref(false)
const reportContent = ref('')

const statusLabels = { potential: '潜在', follow_up: '跟进', deal: '成交', lost: '流失' }
const statusTypes = { potential: 'info', follow_up: 'warning', deal: 'success', lost: 'danger' }
const sourceLabels = { referral: '推荐', network: '网络', exhibition: '展会', social: '社交媒体', other: '其他' }

const projectStatusLabels = { requirements: '需求', design: '设计', development: '开发', testing: '测试', delivery: '交付', paused: '暂停' }
const projectStatusTypes = { requirements: 'info', design: '', development: 'primary', testing: 'warning', delivery: 'success', paused: 'info' }

const contractStatusLabels = { draft: '草稿', active: '生效', executing: '执行中', completed: '已完成', terminated: '已终止' }
const contractStatusTypes = { draft: 'info', active: 'success', executing: '', completed: 'success', terminated: 'danger' }

const loadData = async () => {
  loading.value = true
  try {
    const { data } = await getCustomer(route.params.id)
    customer.value = data.customer
    projects.value = data.projects || []
    contracts.value = data.contracts || []
    loadAssets()
    loadLtv()
    loadQuotations()
  } catch {
    ElMessage.error('客户不存在或加载失败')
    router.back()
  } finally {
    loading.value = false
  }
}

const loadLtv = async () => {
  try {
    const { data } = await api.get(`/customers/${route.params.id}/lifetime-value`)
    ltvData.value = data
    ltvError.value = false
  } catch {
    ltvError.value = true
    ltvData.value = {
      total_contract_amount: null,
      total_received_amount: null,
      project_count: null,
      avg_project_amount: null,
      first_cooperation_date: null,
      last_cooperation_date: null,
    }
  }
}

const assets = ref([])

// Quotations Tab
const quotations = ref([])
const quoteStatusFilter = ref('')
const quoteStatusLabels = { draft: '草稿', sent: '已发送', accepted: '已接受', rejected: '已拒绝', expired: '已过期', cancelled: '已取消' }
const quoteStatusTypes = { draft: 'info', sent: 'primary', accepted: 'success', rejected: 'danger', expired: 'warning', cancelled: 'info' }

const loadQuotations = async () => {
  try {
    const api = (await import('../api/quotations.js')).default || (await import('../api/index.js')).default
    const { getQuotations } = await import('../api/quotations.js')
    const params = { customer_id: route.params.id, limit: 50 }
    if (quoteStatusFilter.value) params.status = quoteStatusFilter.value
    const { data } = await getQuotations(params)
    quotations.value = data.items || []
  } catch { quotations.value = [] }
}

const goCreateQuote = () => {
  router.push({ path: '/quotations', query: { customer_id: route.params.id } })
}

const goToQuotation = (row) => {
  router.push('/quotations')
}

const loadAssets = async () => {
  try {
    const { data } = await getCustomerAssets(route.params.id)
    assets.value = data
  } catch { /* ignore - first load might fail if no endpoint yet */
  }
}

const assetTypeLabels = { server: '服务器', domain: '域名', ssl: 'SSL证书', miniprogram: '小程序', app: 'APP', other: '其他' }
const assetFormVisible = ref(false)
const assetSubmitting = ref(false)
const editingAssetId = ref(null)
const assetForm = ref({ asset_type: '', name: '', expiry_date: '', supplier: '', annual_fee: null, account_info: '', notes: '' })

const openCreateAsset = () => {
  editingAssetId.value = null
  assetForm.value = { asset_type: '', name: '', expiry_date: '', supplier: '', annual_fee: null, account_info: '', notes: '' }
  assetFormVisible.value = true
}
const openEditAsset = (row) => {
  editingAssetId.value = row.id
  assetForm.value = { asset_type: row.asset_type, name: row.name, expiry_date: row.expiry_date || '', supplier: row.supplier || '', annual_fee: row.annual_fee || null, account_info: row.account_info || '', notes: row.notes || '' }
  assetFormVisible.value = true
}
const submitAssetForm = async () => {
  try {
    const payload = { ...assetForm.value }
    // Clean empty strings to null for optional numeric/date fields
    if (!payload.annual_fee) payload.annual_fee = null
    if (!payload.expiry_date) payload.expiry_date = null
    if (editingAssetId.value) {
      await updateCustomerAsset(route.params.id, editingAssetId.value, payload)
      ElMessage.success('资产已更新')
    } else {
      await createCustomerAsset(route.params.id, payload)
      ElMessage.success('资产已添加')
    }
    assetFormVisible.value = false
    loadAssets()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}
const handleDeleteAsset = async (row) => {
  try {
    await ElMessageBox.confirm('确认删除此资产记录？删除后关联提醒也会同步清除。', '删除确认', { type: 'warning' })
    await deleteCustomerAsset(route.params.id, row.id)
    ElMessage.success('资产已删除')
    loadAssets()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

const handleGenerateCustomerReport = async () => {
  generatingReport.value = true
  try {
    const { data } = await generateReport('report_customer', parseInt(route.params.id))
    if (data.content) {
      reportContent.value = data.content
      reportContentVisible.value = true
    }
    ElMessage.success('客户分析报告已生成')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '报告生成失败')
  } finally {
    generatingReport.value = false
  }
}

const showReportHistory = async () => {
  try {
    const { data } = await listReports({ entity_type: 'customer', entity_id: route.params.id })
    reportHistory.value = data.items || []
    reportHistoryVisible.value = true
  } catch (e) {
    ElMessage.error('加载报告历史失败')
  }
}

const viewReport = async (id) => {
  try {
    const { data } = await getReport(id)
    reportContent.value = data.content || '报告内容为空'
    reportContentVisible.value = true
  } catch (e) {
    ElMessage.error('加载报告失败')
  }
}

const handleDeleteReport = async (id) => {
  try {
    await ElMessageBox.confirm('确认删除此报告？', '删除确认', { type: 'warning' })
    await deleteReportApi(id)
    ElMessage.success('报告已删除')
    showReportHistory()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}

</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-left h2 {
  margin: 0;
}

.back-btn {
  font-size: 14px;
  color: var(--text-secondary);
}

.info-card {
  max-width: 700px;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px 32px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.info-item.full-width {
  grid-column: 1 / -1;
}

.info-label {
  font-size: 12px;
  color: var(--text-tertiary, #94a3b8);
  font-weight: 500;
}

.info-value {
  font-size: 14px;
  color: var(--text-primary);
}

.lost-reason {
  color: var(--el-color-danger, #f56c6c);
}

.empty-hint {
  text-align: center;
  padding: 40px 0;
  color: var(--text-tertiary, #94a3b8);
  font-size: 13px;
}

.cell-name {
  font-weight: 500;
}

.progress-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.progress-cell :deep(.el-progress) {
  flex: 1;
}

.progress-label {
  font-size: 12px;
  min-width: 36px;
  text-align: right;
  color: var(--text-secondary);
}

.date-text {
  font-size: 12px;
  color: var(--text-secondary);
}

.contract-no {
  font-weight: 600;
  color: var(--brand-cyan, #0891b2);
}

/* LTV Card Styles */
.ltv-card {
  max-width: 800px;
}

.ltv-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.ltv-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 16px;
  background: var(--bg-soft, #f8fafc);
  border-radius: 8px;
  border: 1px solid var(--border-light, #e2e8f0);
}

.ltv-label {
  font-size: 12px;
  color: var(--text-tertiary, #94a3b8);
  font-weight: 500;
}

.ltv-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.ltv-error {
  margin-top: 16px;
}

@media (max-width: 768px) {
  .ltv-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
