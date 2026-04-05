<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-left">
        <el-button link @click="router.back()" class="back-btn">
          <el-icon><ArrowLeft /></el-icon> 返回
        </el-button>
        <h2 v-if="customer">{{ customer.name }}</h2>
      </div>
      <el-tag v-if="customer" :type="statusTypes[customer.status] || 'info'" size="large" round>
        {{ statusLabels[customer.status] || customer.status }}
      </el-tag>
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
      </el-tabs>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import { getCustomer } from '../api/customers'

const route = useRoute()
const router = useRouter()
const customer = ref(null)
const projects = ref([])
const contracts = ref([])
const loading = ref(true)
const activeTab = ref('info')

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
  } catch {
    ElMessage.error('客户不存在或加载失败')
    router.back()
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
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
</style>
