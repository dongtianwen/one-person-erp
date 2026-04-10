<template>
  <div class="page-container">
    <div class="page-header">
      <div class="header-title-group">
        <span class="header-count mono">总计：{{ total }} 条记录</span>
        <PageHelpDrawer :pageKey="financeHelpKey" />
      </div>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>
        新建记录
      </el-button>
    </div>

    <el-card>
      <el-tabs v-model="activeTab">
        <el-tab-pane label="全部记录" name="all">
          <div class="filter-bar">
            <el-input
              v-model="searchQuery"
              placeholder="搜索财务描述..."
              style="width: 250px"
              clearable
              :prefix-icon="Search"
              @clear="loadData"
              @keyup.enter="loadData"
            />
            <el-select v-model="typeFilter" placeholder="类型" clearable style="width: 110px" @change="loadData">
              <el-option label="收入" value="income" />
              <el-option label="支出" value="expense" />
            </el-select>
            <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 130px" @change="loadData">
              <el-option v-for="(label, val) in statusLabels" :key="val" :label="label" :value="val" />
            </el-select>
            <el-button type="primary" @click="loadData">查询</el-button>
          </div>

      <!-- Funding Source Stats -->
      <div v-if="Object.keys(fundingStats.funding_sources || {}).length" class="stats-bar">
        <div v-for="(amount, source) in fundingStats.funding_sources" :key="source" class="stat-chip">
          <span class="stat-label">{{ fundingSourceLabels[source] || source }}</span>
          <span class="stat-value mono">¥{{ (amount || 0).toLocaleString() }}</span>
        </div>
        <div v-if="fundingStats.unclosed_advances > 0" class="stat-chip warning">
          <span class="stat-label">未报销垫付</span>
          <span class="stat-value mono">{{ fundingStats.unclosed_advances }} 笔</span>
        </div>
        <div v-if="fundingStats.unclosed_loans > 0" class="stat-chip warning">
          <span class="stat-label">未归还借款</span>
          <span class="stat-value mono">{{ fundingStats.unclosed_loans }} 笔</span>
        </div>
      </div>

      <el-table :data="records" style="width: 100%" v-loading="loading">
        <el-table-column type="selection" width="50" />
        <el-table-column prop="type" label="类型" width="60">
          <template #default="{ row }">
            <div class="type-indicator" :class="row.type">
              {{ row.type === 'income' ? '收' : '支' }}
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="金额" width="115" align="right">
          <template #default="{ row }">
            <span class="mono amount-cell" :class="row.type">
              {{ row.type === 'income' ? '+' : '-' }}¥{{ (row.amount || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="category" label="分类" width="90">
          <template #default="{ row }">
            {{ categoryLabels[row.category] || row.category }}
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="220" show-overflow-tooltip>
          <template #default="{ row }">
            <div style="display: flex; align-items: center; gap: 8px;">
              <div class="status-dot-wrapper">
                <div class="status-dot" :class="statusTypes[row.status] || 'info'"></div>
                <span class="status-dot-text">{{ statusLabels[row.status] || row.status }}</span>
              </div>
              <span style="font-weight: 500;">{{ row.description || '-' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="date" label="日期" width="100">
          <template #default="{ row }">
            <span class="mono">{{ row.date }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="invoice_no" label="发票号" width="110">
          <template #default="{ row }">
            <span class="mono">{{ row.invoice_no || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="funding_source" label="资金来源" width="90">
          <template #default="{ row }">
            <span v-if="row.funding_source">{{ fundingSourceLabels[row.funding_source] || row.funding_source }}</span>
            <span v-else class="text-tertiary">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="settlement_status" label="结算状态" width="90">
          <template #default="{ row }">
            <div v-if="needsSettlement(row)" class="status-dot-wrapper" style="background: transparent; border: none; padding: 0;">
              <div class="status-dot" :class="settlementType(row.settlement_status) || 'info'"></div>
              <span class="status-dot-text">{{ settlementLabels[row.settlement_status] || row.settlement_status }}</span>
            </div>
            <span v-else class="text-tertiary">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <div class="action-btns">
              <el-button link type="primary" size="small" @click="editRecord(row)">编辑</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="total"
          layout="total, prev, pager, next"
          @current-change="loadData"
        />
      </div>
        </el-tab-pane>

        <!-- v1.3 发票台账 Tab -->
        <el-tab-pane label="发票台账" name="invoice">
          <div class="filter-bar">
            <el-select v-model="invoiceYearFilter" placeholder="年份" clearable style="width: 110px" @change="loadInvoiceLedger">
              <el-option v-for="y in invoiceYearOptions" :key="y" :label="y + '年'" :value="y" />
            </el-select>
            <el-select v-model="invoiceQuarterFilter" placeholder="季度" clearable style="width: 130px" @change="loadInvoiceLedger">
              <el-option label="Q1 (1-3月)" :value="1" />
              <el-option label="Q2 (4-6月)" :value="2" />
              <el-option label="Q3 (7-9月)" :value="3" />
              <el-option label="Q4 (10-12月)" :value="4" />
            </el-select>
            <el-button type="primary" @click="loadInvoiceLedger">筛选</el-button>
          </div>
          <el-table :data="invoiceLedger" style="width: 100%" v-loading="invoiceLoading" size="small">
            <el-table-column prop="invoice_no" label="发票号码" width="140">
              <template #default="{ row }">
                <span class="mono">{{ row.invoice_no }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="date" label="日期" width="110">
              <template #default="{ row }">
                <span class="mono">{{ row.date }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="invoice_direction" label="方向" width="70">
              <template #default="{ row }">
                <el-tag :type="row.invoice_direction === 'output' ? 'success' : 'warning'" size="small" round>
                  {{ row.invoice_direction === 'output' ? '销项' : '进项' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="invoice_type" label="发票类型" width="120">
              <template #default="{ row }">
                {{ invoiceTypeLabels[row.invoice_type] || row.invoice_type }}
              </template>
            </el-table-column>
            <el-table-column prop="amount" label="金额" width="110" align="right">
              <template #default="{ row }">
                <span class="mono">{{ (row.amount || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="tax_rate" label="税率" width="70">
              <template #default="{ row }">
                <span class="mono">{{ row.tax_rate ? (Number(row.tax_rate) * 100).toFixed(0) + '%' : '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="tax_amount" label="税额" width="100">
              <template #default="{ row }">
                <span class="mono">{{ row.tax_amount ? '¥' + Number(row.tax_amount).toFixed(2) : '-' }}</span>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="!invoiceLoading && !invoiceLedger.length" class="empty-invoice">
            <span>暂无发票记录</span>
          </div>
        </el-tab-pane>

        <!-- v1.8 数据导出 Tab -->
        <el-tab-pane label="数据导出" name="export">
          <div class="export-section">
            <div class="export-form-card">
              <h3>创建导出批次</h3>
              <el-form :model="exportForm" label-position="top" style="max-width: 500px">
                <el-form-item label="导出类型">
                  <el-select v-model="exportForm.export_type" style="width: 100%">
                    <el-option label="合同数据" value="contracts" />
                    <el-option label="收款数据" value="payments" />
                    <el-option label="发票数据" value="invoices" />
                  </el-select>
                </el-form-item>
                <el-form-item label="时间范围">
                  <el-date-picker
                    v-model="exportDateRange"
                    type="daterange"
                    value-format="YYYY-MM-DD"
                    start-placeholder="开始日期"
                    end-placeholder="结束日期"
                    style="width: 100%"
                  />
                </el-form-item>
                <el-form-item label="目标格式">
                  <el-select v-model="exportForm.target_format" style="width: 100%">
                    <el-option label="通用格式" value="generic" />
                    <el-option label="金蝶 K3" value="kingdee_k3" disabled />
                    <el-option label="用友 U8" value="yonyou_u8" disabled />
                  </el-select>
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="handleCreateExport" :loading="exportLoading">创建导出批次</el-button>
                </el-form-item>
              </el-form>
            </div>

            <div class="export-history">
              <h3>导出历史</h3>
              <el-table :data="exportBatches" style="width: 100%" v-loading="exportLoading" size="small">
                <el-table-column prop="batch_id" label="批次号" width="180">
                  <template #default="{ row }"><span class="mono">{{ row.batch_id }}</span></template>
                </el-table-column>
                <el-table-column prop="export_type" label="类型" width="100" />
                <el-table-column prop="record_count" label="记录数" width="80" align="right">
                  <template #default="{ row }"><span class="mono">{{ row.record_count || 0 }}</span></template>
                </el-table-column>
                <el-table-column prop="target_format" label="格式" width="100" />
                <el-table-column prop="created_at" label="创建时间" width="160" />
                <el-table-column label="操作" width="100">
                  <template #default="{ row }">
                    <el-button link type="primary" size="small" @click="handleDownload(row)">下载</el-button>
                  </template>
                </el-table-column>
              </el-table>
              <div v-if="!exportBatches.length && !exportLoading" class="empty-hint">暂无导出记录</div>
            </div>
          </div>
        </el-tab-pane>

        <!-- v1.9 数据核查 Tab -->
        <el-tab-pane label="数据核查" name="consistency">
          <div class="consistency-section">
            <div class="consistency-toolbar">
              <el-button type="primary" size="small" @click="loadConsistencyCheck" :loading="consistencyLoading">立即核查</el-button>
            </div>
            <div v-if="consistencyLoading" style="padding: 32px 0; text-align: center;">
              <el-icon class="is-loading" :size="24"><Loading /></el-icon>
            </div>
            <div v-else-if="!consistencyData.contracts?.length" class="consistency-ok">
              <span>&#10003; 数据一致，无问题</span>
            </div>
            <div v-else>
              <el-table :data="consistencyData.contracts" style="width: 100%" size="small">
                <el-table-column prop="contract_no" label="合同号" width="140">
                  <template #default="{ row }"><span class="mono">{{ row.contract_no }}</span></template>
                </el-table-column>
                <el-table-column prop="customer_name" label="客户" width="120" />
                <el-table-column label="差异类型" min-width="200">
                  <template #default="{ row }">
                    <el-tag
                      v-for="issue in row.issues"
                      :key="issue.type"
                      size="small"
                      :type="consistencyIssueType(issue.type)"
                      style="margin-right: 4px;"
                    >{{ consistencyIssueLabel(issue.type) }}: ¥{{ (issue.gap || 0).toFixed(2) }}</el-tag>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </div>
        </el-tab-pane>

        <!-- v1.9 固定成本 Tab -->
        <el-tab-pane label="固定成本" name="fixed-costs">
          <div class="fixed-costs-section">
            <div class="fc-toolbar">
              <el-button type="primary" size="small" @click="openFcCreate"><el-icon><Plus /></el-icon> 新增成本</el-button>
              <el-select v-model="fcPeriod" placeholder="月度汇总" style="width: 140px" @change="loadFcSummary">
                <el-option v-for="p in fcPeriodOptions" :key="p" :label="p" :value="p" />
              </el-select>
            </div>

            <el-table :data="fcList" style="width: 100%" v-loading="fcLoading" size="small">
              <el-table-column prop="name" label="名称" min-width="120" />
              <el-table-column prop="category" label="分类" width="90">
                <template #default="{ row }">{{ fcCategoryLabels[row.category] || row.category }}</template>
              </el-table-column>
              <el-table-column prop="amount" label="金额" width="110" align="right">
                <template #default="{ row }"><span class="mono">¥{{ (row.amount || 0).toFixed(2) }}</span></template>
              </el-table-column>
              <el-table-column prop="period" label="周期" width="80">
                <template #default="{ row }">{{ fcPeriodLabels[row.period] || row.period }}</template>
              </el-table-column>
              <el-table-column prop="effective_date" label="生效日期" width="100">
                <template #default="{ row }"><span class="mono">{{ row.effective_date }}</span></template>
              </el-table-column>
              <el-table-column prop="end_date" label="截止日期" width="100">
                <template #default="{ row }"><span class="mono">{{ row.end_date || '-' }}</span></template>
              </el-table-column>
              <el-table-column label="操作" width="100">
                <template #default="{ row }">
                  <el-button link type="primary" size="small" @click="editFc(row)">编辑</el-button>
                  <el-button link type="danger" size="small" @click="deleteFc(row.id)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>

            <div v-if="fcSummary" class="fc-summary">
              <div class="fc-summary-hint">以下为当月有效成本条目原始金额，非摊销后金额</div>
              <div class="fc-summary-grid">
                <div v-for="(item, cat) in fcSummary.by_category || {}" :key="cat" class="fc-summary-item">
                  <span class="fc-summary-cat">{{ fcCategoryLabels[cat] || cat }}</span>
                  <span class="mono fc-summary-val">¥{{ (item.total_amount || 0).toFixed(2) }}</span>
                </div>
              </div>
              <div class="fc-summary-total">
                合计：<span class="mono">¥{{ (fcSummary.total_amount || 0).toFixed(2) }}</span>
              </div>
            </div>
          </div>
        </el-tab-pane>

        <!-- v1.9 进项发票（收到的票）Tab -->
        <el-tab-pane label="进项发票（收到的票）" name="input-invoices">
          <div class="input-invoices-section">
            <div class="ii-toolbar">
              <el-button type="primary" size="small" @click="openIiCreate"><el-icon><Plus /></el-icon> 新增进项发票</el-button>
            </div>

            <el-table :data="iiList" style="width: 100%" v-loading="iiLoading" size="small">
              <el-table-column prop="invoice_no" label="发票号" width="140">
                <template #default="{ row }"><span class="mono">{{ row.invoice_no }}</span></template>
              </el-table-column>
              <el-table-column prop="vendor_name" label="供应商" width="120" />
              <el-table-column prop="invoice_date" label="日期" width="100">
                <template #default="{ row }"><span class="mono">{{ row.invoice_date }}</span></template>
              </el-table-column>
              <el-table-column prop="amount_excluding_tax" label="不含税金额" width="110" align="right">
                <template #default="{ row }"><span class="mono">¥{{ (row.amount_excluding_tax || 0).toFixed(2) }}</span></template>
              </el-table-column>
              <el-table-column prop="tax_rate" label="税率" width="70">
                <template #default="{ row }"><span class="mono">{{ row.tax_rate ? (row.tax_rate * 100).toFixed(0) + '%' : '-' }}</span></template>
              </el-table-column>
              <el-table-column prop="total_amount" label="含税金额" width="110" align="right">
                <template #default="{ row }"><span class="mono">¥{{ (row.total_amount || 0).toFixed(2) }}</span></template>
              </el-table-column>
              <el-table-column prop="category" label="分类" width="80">
                <template #default="{ row }">{{ iiCategoryLabels[row.category] || row.category }}</template>
              </el-table-column>
              <el-table-column label="操作" width="100">
                <template #default="{ row }">
                  <el-button link type="primary" size="small" @click="editIi(row)">编辑</el-button>
                  <el-button link type="danger" size="small" @click="deleteIi(row.id)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
            <div v-if="!iiLoading && !iiList.length" class="empty-hint">暂无进项发票记录</div>
          </div>
        </el-tab-pane>

        <!-- v1.8 对账报表 Tab -->
        <el-tab-pane label="对账报表" name="reconciliation">
          <div class="reconciliation-section">
            <div class="period-selector">
              <span class="period-label">会计期间：</span>
              <el-select v-model="selectedPeriod" placeholder="选择期间" @change="loadReconciliationReport" style="width: 180px">
                <el-option v-for="p in availablePeriods" :key="p" :label="p" :value="p" />
              </el-select>
              <el-button type="primary" size="small" @click="handleSyncReconciliation" :loading="syncLoading">同步对账状态</el-button>
            </div>

            <div v-if="reconciliationReport" class="reconciliation-content">
              <div class="balance-cards">
                <div class="balance-card">
                  <span class="card-label">期初余额</span>
                  <span class="card-value mono">¥{{ (reconciliationReport.opening_balance?.total || 0).toFixed(2) }}</span>
                  <div class="card-detail">
                    <span>应收: {{ (reconciliationReport.opening_balance?.accounts_receivable || 0).toFixed(2) }}</span>
                    <span>未开票: {{ (reconciliationReport.opening_balance?.unbilled_amount || 0).toFixed(2) }}</span>
                  </div>
                </div>
                <div class="balance-card">
                  <span class="card-label">本期活动</span>
                  <span class="card-value highlight mono">¥{{ ((reconciliationReport.current_period?.contracts_amount || 0) - (reconciliationReport.current_period?.payments_amount || 0)).toFixed(2) }}</span>
                  <div class="card-detail">
                    <span>合同: {{ (reconciliationReport.current_period?.contracts_amount || 0).toFixed(2) }}</span>
                    <span>收款: {{ (reconciliationReport.current_period?.payments_amount || 0).toFixed(2) }}</span>
                    <span>开票: {{ (reconciliationReport.current_period?.invoices_amount || 0).toFixed(2) }}</span>
                  </div>
                </div>
                <div class="balance-card">
                  <span class="card-label">期末余额</span>
                  <span class="card-value primary mono">¥{{ (reconciliationReport.closing_balance?.total || 0).toFixed(2) }}</span>
                  <div class="card-detail">
                    <span>应收: {{ (reconciliationReport.closing_balance?.accounts_receivable || 0).toFixed(2) }}</span>
                    <span>未开票: {{ (reconciliationReport.closing_balance?.unbilled_amount || 0).toFixed(2) }}</span>
                  </div>
                </div>
              </div>

              <div class="breakdown-section">
                <h4>客户维度分解</h4>
                <el-table :data="reconciliationReport.breakdown || []" style="width: 100%" size="small">
                  <el-table-column prop="customer_name" label="客户名称" width="150" />
                  <el-table-column label="本期合同" width="120" align="right">
                    <template #default="{ row }"><span class="mono">¥{{ (row.contracts_amount_this_period || 0).toFixed(2) }}</span></template>
                  </el-table-column>
                  <el-table-column label="本期收款" width="120" align="right">
                    <template #default="{ row }"><span class="mono">¥{{ (row.payments_amount_this_period || 0).toFixed(2) }}</span></template>
                  </el-table-column>
                  <el-table-column label="本期开票" width="120" align="right">
                    <template #default="{ row }"><span class="mono">¥{{ (row.invoices_amount_this_period || 0).toFixed(2) }}</span></template>
                  </el-table-column>
                  <el-table-column label="应收余额" width="120" align="right">
                    <template #default="{ row }"><span class="mono">{{ (row.accounts_receivable || 0).toFixed(2) }}</span></template>
                  </el-table-column>
                </el-table>
              </div>

              <div v-if="reconciliationReport.unreconciled_records?.length" class="unreconciled-section">
                <h4>未对账记录</h4>
                <el-table :data="reconciliationReport.unreconciled_records" style="width: 100%" size="small">
                  <el-table-column prop="transaction_date" label="日期" width="100" />
                  <el-table-column prop="record_type" label="类型" width="60">
                    <template #default="{ row }">{{ row.record_type === 'payment' ? '收' : '支' }}</template>
                  </el-table-column>
                  <el-table-column prop="amount" label="金额" width="100" align="right">
                    <template #default="{ row }"><span class="mono">¥{{ (row.amount || 0).toFixed(2) }}</span></template>
                  </el-table-column>
                  <el-table-column prop="reason" label="原因" min-width="150" />
                </el-table>
              </div>
            </div>
            <div v-else-if="!reconciliationLoading" class="empty-hint">请选择会计期间查看对账报表</div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- v1.9 固定成本 Dialog -->
    <el-dialog v-model="fcDialogVisible" :title="fcEditingId ? '编辑固定成本' : '新增固定成本'" width="500px" destroy-on-close>
      <el-form :model="fcForm" label-position="top">
        <el-form-item label="名称" required>
          <el-input v-model="fcForm.name" placeholder="如：服务器费用" />
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="分类">
            <el-select v-model="fcForm.category" style="width: 100%">
              <el-option v-for="(label, val) in fcCategoryLabels" :key="val" :label="label" :value="val" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <template #label>周期 <FieldTip module="fixed_cost" field="period" /></template>
            <el-select v-model="fcForm.period" style="width: 100%">
              <el-option v-for="(label, val) in fcPeriodLabels" :key="val" :label="label" :value="val" />
            </el-select>
          </el-form-item>
        </div>
        <div class="form-grid">
          <el-form-item label="金额" required>
            <el-input-number v-model="fcForm.amount" :min="0.01" :precision="2" style="width: 100%" />
          </el-form-item>
          <el-form-item required>
            <template #label>生效日期 <FieldTip module="fixed_cost" field="effective_date" /></template>
            <el-date-picker v-model="fcForm.effective_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
        </div>
        <div class="form-grid">
          <el-form-item>
            <template #label>截止日期 <FieldTip module="fixed_cost" field="end_date" /></template>
            <el-date-picker v-model="fcForm.end_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" clearable />
          </el-form-item>
          <el-form-item label="关联项目">
            <el-select v-model="fcForm.project_id" placeholder="选填" clearable filterable style="width: 100%">
              <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item label="备注">
          <el-input v-model="fcForm.notes" type="textarea" :rows="2" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="fcDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleFcSubmit">{{ fcEditingId ? '保存' : '创建' }}</el-button>
      </template>
    </el-dialog>

    <!-- v1.9 进项发票 Dialog -->
    <el-dialog v-model="iiDialogVisible" :title="iiEditingId ? '编辑进项发票' : '新增进项发票'" width="500px" destroy-on-close>
      <el-form :model="iiForm" label-position="top">
        <div class="form-grid">
          <el-form-item label="发票号" required>
            <el-input v-model="iiForm.invoice_no" placeholder="发票编号" />
          </el-form-item>
          <el-form-item label="供应商" required>
            <el-input v-model="iiForm.vendor_name" placeholder="供应商名称" />
          </el-form-item>
        </div>
        <div class="form-grid">
          <el-form-item required>
            <template #label>日期 <FieldTip module="invoice" field="invoice_date" /></template>
            <el-date-picker v-model="iiForm.invoice_date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
          <el-form-item required>
            <template #label>不含税金额 <FieldTip module="invoice" field="amount_excluding_tax" /></template>
            <el-input-number v-model="iiForm.amount_excluding_tax" :min="0.01" :precision="2" style="width: 100%" />
          </el-form-item>
        </div>
        <div class="form-grid">
          <el-form-item>
            <template #label>税率 <FieldTip module="invoice" field="tax_rate" /></template>
            <el-select v-model="iiForm.tax_rate" style="width: 100%">
              <el-option label="13%" :value="0.13" />
              <el-option label="9%" :value="0.09" />
              <el-option label="6%" :value="0.06" />
              <el-option label="3%" :value="0.03" />
              <el-option label="1%" :value="0.01" />
            </el-select>
          </el-form-item>
          <el-form-item label="分类">
            <el-select v-model="iiForm.category" style="width: 100%">
              <el-option v-for="(label, val) in iiCategoryLabels" :key="val" :label="label" :value="val" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item label="关联项目">
          <el-select v-model="iiForm.project_id" placeholder="选填" clearable filterable style="width: 100%">
            <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="iiForm.notes" type="textarea" :rows="2" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="iiDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleIiSubmit">{{ iiEditingId ? '保存' : '创建' }}</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showDialog" :title="editingId ? '编辑记录' : '新建记录'" width="600px" destroy-on-close>
      <el-form :model="form" label-position="top">
        <div class="form-grid">
          <el-form-item label="类型" required>
            <el-select v-model="form.type" style="width: 100%">
              <el-option label="收入" value="income" />
              <el-option label="支出" value="expense" />
            </el-select>
          </el-form-item>
          <el-form-item label="金额" required>
            <el-input-number v-model="form.amount" :min="0" :precision="2" style="width: 100%" />
          </el-form-item>
        </div>
        <div class="form-grid">
          <el-form-item label="分类">
            <el-select v-model="form.category" style="width: 100%">
              <el-option v-for="(label, val) in categoryLabels" :key="val" :label="label" :value="val" />
            </el-select>
          </el-form-item>
          <el-form-item label="日期" required>
            <el-date-picker v-model="form.date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
          </el-form-item>
        </div>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="简要描述（选填）" />
        </el-form-item>
        <el-form-item label="关联合同">
          <el-select v-model="form.contract_id" placeholder="选择合同" filterable clearable style="width: 100%">
            <el-option v-for="c in contracts" :key="c.id" :label="`${c.title} (${c.contract_no})`" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.type === 'expense'" label="关联项目">
          <el-select v-model="form.related_project_id" placeholder="选择项目（选填）" filterable clearable style="width: 100%">
            <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
        </el-form-item>
        <div class="form-grid">
          <el-form-item label="发票号">
            <el-input v-model="form.invoice_no" placeholder="发票编号" clearable />
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="form.status" style="width: 100%">
              <el-option v-for="(label, val) in statusLabels" :key="val" :label="label" :value="val" />
            </el-select>
          </el-form-item>
        </div>
        <!-- v1.3 外包协作字段 -->
        <template v-if="form.category === 'outsourcing'">
          <el-form-item label="外包方姓名" required>
            <el-input v-model="form.outsource_name" placeholder="外包方姓名" />
          </el-form-item>
          <div class="form-grid">
            <el-form-item label="是否取得发票" required>
              <el-select v-model="form.has_invoice" placeholder="请选择" style="width: 100%">
                <el-option label="是" :value="true" />
                <el-option label="否" :value="false" />
              </el-select>
            </el-form-item>
            <el-form-item label="税务处理方式" required>
              <el-select v-model="form.tax_treatment" placeholder="请选择" style="width: 100%">
                <el-option label="已开票" value="invoiced" />
                <el-option label="代扣代缴" value="withholding" />
                <el-option label="无" value="none" />
              </el-select>
            </el-form-item>
          </div>
        </template>
        <!-- v1.3 发票台账字段 -->
        <template v-if="form.invoice_no">
          <div class="form-grid">
            <el-form-item label="发票方向" required>
              <el-select v-model="form.invoice_direction" placeholder="请选择" style="width: 100%">
                <el-option label="销项" value="output" />
                <el-option label="进项" value="input" />
              </el-select>
            </el-form-item>
            <el-form-item label="发票类型" required>
              <el-select v-model="form.invoice_type" placeholder="请选择" style="width: 100%">
                <el-option label="增值税专用发票" value="special" />
                <el-option label="增值税普通发票" value="general" />
                <el-option label="电子发票" value="electronic" />
              </el-select>
            </el-form-item>
          </div>
          <div class="form-grid">
            <el-form-item label="税率" required>
              <el-select v-model="form.tax_rate" placeholder="请选择" style="width: 100%">
                <el-option label="6%" :value="0.06" />
                <el-option label="3%" :value="0.03" />
                <el-option label="13%" :value="0.13" />
                <el-option label="1%" :value="0.01" />
                <el-option label="9%" :value="0.09" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="editingId && editingTaxAmount !== null" label="税额（自动计算）">
              <el-input :model-value="'¥' + Number(editingTaxAmount).toFixed(2)" disabled />
            </el-form-item>
          </div>
        </template>
        <!-- v1.1 资金来源 -->
        <el-form-item label="资金来源" :required="form.type === 'expense'">
          <el-select v-model="form.funding_source" placeholder="选择资金来源" clearable style="width: 100%">
            <el-option v-for="(label, val) in fundingSourceLabels" :key="val" :label="label" :value="val" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.funding_source === 'personal_advance' || form.funding_source === 'loan'" label="业务说明" required>
          <el-input v-model="form.business_note" type="textarea" :rows="2" placeholder="说明垫付或借款原因" />
        </el-form-item>
        <el-form-item v-if="form.funding_source === 'personal_advance' || form.funding_source === 'loan'" label="结算状态" required>
          <el-select v-model="form.settlement_status" placeholder="选择结算状态" style="width: 100%">
            <el-option v-for="(label, val) in settlementLabels" :key="val" :label="label" :value="val" />
          </el-select>
        </el-form-item>
        <el-form-item label="关联记录">
          <el-select v-model="form.related_record_id" placeholder="选择关联记录" filterable clearable style="width: 100%">
            <el-option v-for="r in records" :key="r.id" :label="`${r.type === 'income' ? '收' : '支'} ¥${(r.amount || 0).toLocaleString()} - ${r.description || r.date}`" :value="r.id" :disabled="r.id === editingId" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="form.related_record_id" label="关联说明" required>
          <el-input v-model="form.related_note" placeholder="说明关联关系，如'报销张三2026-03-01垫付'" />
        </el-form-item>
      </el-form>

      <!-- Change History -->
      <div v-if="editingId && changelogs.length" class="changelog-section">
        <div class="changelog-header">变更历史</div>
        <div class="changelog-list">
          <div v-for="log in changelogs" :key="log.id" class="changelog-item">
            <div class="changelog-field">{{ fieldLabels[log.field] || log.field }}</div>
            <div class="changelog-values">
              <span class="old-val">{{ log.old_value || '空' }}</span>
              <span class="arrow">→</span>
              <span class="new-val">{{ log.new_value || '空' }}</span>
            </div>
            <div class="changelog-time">{{ formatTime(log.created_at) }}</div>
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">{{ editingId ? '保存修改' : '创建记录' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Loading } from '@element-plus/icons-vue'
import FieldTip from '../components/FieldTip.vue'
import PageHelpDrawer from '../components/PageHelpDrawer.vue'
import api from '../api'
import {
  createExportBatch,
  getExportBatches,
  downloadExportFile as apiDownloadExportFile,
  getReconciliationPeriods,
  getReconciliationReport as apiGetReconciliationReport,
  syncReconciliationStatus
} from '../api/v18'
import {
  getConsistencyCheck,
  refreshConsistencyCheck as apiRefreshConsistency,
  getFixedCosts as apiGetFixedCosts,
  createFixedCost as apiCreateFixedCost,
  updateFixedCost as apiUpdateFixedCost,
  deleteFixedCost as apiDeleteFixedCost,
  getFixedCostSummary,
  getInputInvoices as apiGetInputInvoices,
  createInputInvoice as apiCreateInputInvoice,
  updateInputInvoice as apiUpdateInputInvoice,
  deleteInputInvoice as apiDeleteInputInvoice,
} from '../api/v19'

const records = ref([])
const fundingStats = ref({ funding_sources: {}, unclosed_advances: 0, unclosed_loans: 0 })
const contracts = ref([])
const projects = ref([])
const changelogs = ref([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const typeFilter = ref('')
const statusFilter = ref('')
const searchQuery = ref('')
const showDialog = ref(false)
const editingId = ref(null)
const defaultForm = { type: 'income', amount: 0, category: 'other', description: '', date: '', contract_id: null, invoice_no: '', status: 'pending', funding_source: 'company_account', business_note: '', related_record_id: null, related_note: '', settlement_status: null, outsource_name: '', has_invoice: null, tax_treatment: null, invoice_direction: null, invoice_type: null, tax_rate: null, related_project_id: null }
const form = ref({ ...defaultForm })

// v1.3 发票台账
const activeTab = ref('all')

// v1.10 帮助系统——根据当前 Tab 显示对应页面帮助
const financeHelpKeyMap = {
  export: 'finance_export',
  consistency: 'consistency_check',
  reconciliation: 'reconciliation',
}
const financeHelpKey = computed(() => financeHelpKeyMap[activeTab.value] || '')

const invoiceLedger = ref([])
const invoiceLoading = ref(false)
const invoiceYearFilter = ref(new Date().getFullYear())
const invoiceQuarterFilter = ref(null)
const invoiceYearOptions = [2024, 2025, 2026, 2027]
const invoiceTypeLabels = { special: '增值税专用', general: '增值税普通', electronic: '电子发票' }

// v1.8 数据导出
const exportForm = ref({ export_type: 'contracts', target_format: 'generic' })
const exportDateRange = ref([])
const exportBatches = ref([])
const exportLoading = ref(false)

// v1.8 对账报表
const availablePeriods = ref([])
const selectedPeriod = ref(null)
const reconciliationReport = ref(null)
const reconciliationLoading = ref(false)
const syncLoading = ref(false)

const loadInvoiceLedger = async () => {
  invoiceLoading.value = true
  try {
    const params = { skip: 0, limit: 100 }
    if (invoiceYearFilter.value) params.start_date = `${invoiceYearFilter.value}-01-01`
    if (invoiceYearFilter.value) params.end_date = `${invoiceYearFilter.value}-12-31`
    if (invoiceQuarterFilter.value) {
      const qEnd = [0, '03-31', '06-30', '09-30', '12-31'][invoiceQuarterFilter.value]
      const qStart = [0, '01-01', '04-01', '07-01', '10-01'][invoiceQuarterFilter.value]
      params.start_date = `${invoiceYearFilter.value}-${qStart}`
      params.end_date = `${invoiceYearFilter.value}-${qEnd}`
    }
    const { data } = await api.get('/finances', { params })
    invoiceLedger.value = (data.items || []).filter(r => r.invoice_no)
  } catch {
    invoiceLedger.value = []
  } finally {
    invoiceLoading.value = false
  }
}

// 编辑时展示后端计算的税额
const editingTaxAmount = computed(() => {
  if (!editingId.value) return null
  const record = records.value.find(r => r.id === editingId.value)
  return record?.tax_amount ?? null
})

// 切换分类时清空外包字段
watch(() => form.value.category, (newCat) => {
  if (newCat !== 'outsourcing') {
    form.value.outsource_name = ''
    form.value.has_invoice = null
    form.value.tax_treatment = null
  }
})

// 清空发票号时清空发票字段
watch(() => form.value.invoice_no, (newVal) => {
  if (!newVal) {
    form.value.invoice_direction = null
    form.value.invoice_type = null
    form.value.tax_rate = null
  }
})

const statusLabels = { pending: '待确认', confirmed: '已确认', invoiced: '已开票', paid: '已付款', cancelled: '已取消' }
const fundingSourceLabels = {
  company_account: '对公账户',
  personal_advance: '个人垫付',
  reimbursement: '报销',
  loan: '借款',
  loan_repayment: '借款归还',
  other: '其他',
}
const statusTypes = { pending: 'warning', confirmed: 'success', invoiced: 'info', paid: 'success', cancelled: 'danger' }
const categoryLabels = { development: '开发费', design: '设计费', maintenance: '维护费', server: '服务器', office: '办公', other: '其他', outsourcing: '外包费用', '项目收入': '项目收入', 人力: '人力', 外包: '外包' }
const fieldLabels = { type: '类型', amount: '金额', category: '分类', description: '描述', date: '日期', contract_id: '关联合同', invoice_no: '发票号', status: '状态' }

const settlementLabels = { open: '未结清', partial: '部分归还', closed: '已结清' }
const settlementTypes = { open: 'danger', partial: 'warning', closed: 'success' }
const needsSettlement = (row) => ['personal_advance', 'loan'].includes(row.funding_source) && row.settlement_status

const loadData = async () => {
  loading.value = true
  try {
    const params = { skip: (page.value - 1) * pageSize.value, limit: pageSize.value }
    if (typeFilter.value) params.type = typeFilter.value
    if (statusFilter.value) params.status = statusFilter.value
    if (searchQuery.value) params.search = searchQuery.value
    const { data } = await api.get('/finances', { params })
    records.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

const loadFundingStats = async () => {
  try {
    const now = new Date()
    const { data } = await api.get('/finances/stats/funding-source', {
      params: { year: now.getFullYear(), month: now.getMonth() + 1 }
    })
    fundingStats.value = data
  } catch { /* silently degrade */ }
}

const loadContracts = async () => {
  try {
    const { data } = await api.get('/contracts', { params: { skip: 0, limit: 100 } })
    contracts.value = data.items
  } catch {
    contracts.value = []
  }
}

const loadProjects = async () => {
  try {
    const { data } = await api.get('/projects', { params: { skip: 0, limit: 100 } })
    projects.value = data
  } catch {
    projects.value = []
  }
}

const openCreate = () => {
  editingId.value = null
  form.value = { ...defaultForm }
  showDialog.value = true
}

const editRecord = (row) => {
  editingId.value = row.id
  form.value = { ...row }
  changelogs.value = []
  showDialog.value = true
  loadChangelogs(row.id)
}

const loadChangelogs = async (recordId) => {
  try {
    const { data } = await api.get('/changelogs', { params: { entity_type: 'finance_record', entity_id: recordId } })
    changelogs.value = data
  } catch {
    changelogs.value = []
  }
}

const formatTime = (ts) => {
  if (!ts) return ''
  const d = new Date(ts)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
}

const handleSubmit = async () => {
  if (!form.value.amount || !form.value.date) { ElMessage.warning('请填写金额和日期'); return }
  if (form.value.type === 'expense' && !form.value.funding_source) { ElMessage.warning('支出记录必须填写资金来源'); return }
  if (['personal_advance', 'loan'].includes(form.value.funding_source) && !form.value.business_note) { ElMessage.warning('个人垫付/借款必须填写业务说明'); return }
  if (['personal_advance', 'loan'].includes(form.value.funding_source) && !form.value.settlement_status) { ElMessage.warning('个人垫付/借款必须填写结算状态'); return }
  if (form.value.related_record_id && !form.value.related_note) { ElMessage.warning('关联记录时必须填写关联说明'); return }
  // v1.3 外包字段校验
  if (form.value.category === 'outsourcing') {
    if (!form.value.outsource_name) { ElMessage.warning('外包费用必须填写外包方姓名'); return }
    if (form.value.has_invoice === null || form.value.has_invoice === undefined) { ElMessage.warning('外包费用必须填写是否取得发票'); return }
    if (!form.value.tax_treatment) { ElMessage.warning('外包费用必须填写税务处理方式'); return }
  }
  // v1.3 发票字段校验
  if (form.value.invoice_no) {
    if (!form.value.invoice_direction) { ElMessage.warning('填写发票号码时必须填写发票方向'); return }
    if (!form.value.invoice_type) { ElMessage.warning('填写发票号码时必须填写发票类型'); return }
    if (!form.value.tax_rate && form.value.tax_rate !== 0) { ElMessage.warning('填写发票号码时必须填写税率'); return }
  }
  // 构建 payload，清理不相关字段
  const payload = { ...form.value }
  if (payload.category !== 'outsourcing') {
    delete payload.outsource_name
    delete payload.has_invoice
    delete payload.tax_treatment
  }
  if (!payload.invoice_no) {
    delete payload.invoice_direction
    delete payload.invoice_type
    delete payload.tax_rate
  }
  delete payload.tax_amount
  try {
    if (editingId.value) {
      await api.put(`/finances/${editingId.value}`, payload)
      ElMessage.success('更新成功')
    } else {
      await api.post('/finances', payload)
      ElMessage.success('创建成功')
    }
    showDialog.value = false
    loadData()
  } catch { /* handled */ }
}

// v1.8 数据导出
const loadExportBatches = async () => {
  try {
    const { data } = await getExportBatches({ skip: 0, limit: 20 })
    exportBatches.value = data.items || data
  } catch (err) {
    console.error('Failed to load export batches:', err)
  }
}

const handleCreateExport = async () => {
  if (!exportDateRange.value || exportDateRange.value.length !== 2) {
    ElMessage.warning('请选择时间范围')
    return
  }
  exportLoading.value = true
  try {
    await createExportBatch({
      export_type: exportForm.value.export_type,
      start_date: exportDateRange.value[0],
      end_date: exportDateRange.value[1],
      target_format: exportForm.value.target_format
    })
    ElMessage.success('导出批次已创建')
    loadExportBatches()
  } catch (err) {
    console.error('Failed to create export:', err)
  } finally {
    exportLoading.value = false
  }
}

const handleDownload = async (row) => {
  try {
    const blob = await apiDownloadExportFile(row.batch_id)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${row.batch_id}.xlsx`
    a.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('下载已开始')
  } catch (err) {
    console.error('Failed to download:', err)
    ElMessage.error('下载失败')
  }
}

// v1.8 对账报表
const loadReconciliationPeriods = async () => {
  try {
    const { data } = await getReconciliationPeriods()
    availablePeriods.value = data.periods || []
    if (availablePeriods.value.length) {
      selectedPeriod.value = availablePeriods.value[availablePeriods.value.length - 1]
      loadReconciliationReport()
    }
  } catch (err) {
    console.error('Failed to load periods:', err)
  }
}

const loadReconciliationReport = async () => {
  if (!selectedPeriod.value) return
  reconciliationLoading.value = true
  try {
    const { data } = await apiGetReconciliationReport(selectedPeriod.value)
    reconciliationReport.value = data
  } catch (err) {
    console.error('Failed to load report:', err)
  } finally {
    reconciliationLoading.value = false
  }
}

const handleSyncReconciliation = async () => {
  syncLoading.value = true
  try {
    const { data } = await syncReconciliationStatus([])
    ElMessage.success(`已同步 ${data.updated_count || 0} 条记录`)
    loadReconciliationReport()
  } catch (err) {
    console.error('Failed to sync:', err)
  } finally {
    syncLoading.value = false
  }
}

onMounted(() => { loadData(); loadContracts(); loadProjects(); loadFundingStats(); loadInvoiceLedger(); loadExportBatches(); loadReconciliationPeriods(); loadConsistencyCheck(); loadFcList(); loadIiList() })

// ===== v1.9 数据核查 =====
const consistencyData = ref({})
const consistencyLoading = ref(false)
const consistencyIssueLabel = (type) => ({ payment_gap: '收款差异', invoice_gap: '开票差异', unlinked_payment: '未关联收款', invoice_payment_mismatch: '票款不匹配' }[type] || type)
const consistencyIssueType = (type) => ({ payment_gap: 'warning', invoice_gap: '', unlinked_payment: 'primary', invoice_payment_mismatch: 'danger' }[type] || 'info')
const loadConsistencyCheck = async () => {
  consistencyLoading.value = true
  try {
    const { data } = await getConsistencyCheck()
    consistencyData.value = data
  } catch {
    consistencyData.value = {}
  } finally {
    consistencyLoading.value = false
  }
}

// ===== v1.9 固定成本 =====
const fcList = ref([])
const fcLoading = ref(false)
const fcPeriod = ref('')
const fcSummary = ref(null)
const fcDialogVisible = ref(false)
const fcEditingId = ref(null)
const fcCategoryLabels = { office: '办公', cloud: '云服务', software: '软件', equipment: '设备', other: '其他' }
const fcPeriodLabels = { monthly: '月度', quarterly: '季度', yearly: '年度', onetime: '一次性' }
const fcPeriodOptions = (() => { const opts = []; const now = new Date(); for (let i = 0; i < 6; i++) { const d = new Date(now.getFullYear(), now.getMonth() - i, 1); opts.push(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`) } return opts })()
const defaultFcForm = { name: '', category: 'other', amount: 0, period: 'monthly', effective_date: '', end_date: '', project_id: null, notes: '' }
const fcForm = ref({ ...defaultFcForm })

const loadFcList = async () => {
  fcLoading.value = true
  try {
    const { data } = await apiGetFixedCosts()
    fcList.value = data
  } catch { fcList.value = [] } finally { fcLoading.value = false }
}
const loadFcSummary = async () => {
  if (!fcPeriod.value) return
  try {
    const { data } = await getFixedCostSummary(fcPeriod.value)
    fcSummary.value = data
  } catch { fcSummary.value = null }
}
const openFcCreate = () => { fcEditingId.value = null; fcForm.value = { ...defaultFcForm }; fcDialogVisible.value = true }
const editFc = (row) => { fcEditingId.value = row.id; fcForm.value = { ...row }; fcDialogVisible.value = true }
const deleteFc = async (id) => {
  try { await ElMessageBox.confirm('确定删除该固定成本？', '确认', { type: 'warning' }); await apiDeleteFixedCost(id); ElMessage.success('删除成功'); loadFcList() } catch { /* */ }
}
const handleFcSubmit = async () => {
  if (!fcForm.value.name || !fcForm.value.amount || !fcForm.value.effective_date) { ElMessage.warning('请填写必要信息'); return }
  try {
    if (fcEditingId.value) { await apiUpdateFixedCost(fcEditingId.value, fcForm.value); ElMessage.success('更新成功') }
    else { await apiCreateFixedCost(fcForm.value); ElMessage.success('创建成功') }
    fcDialogVisible.value = false; loadFcList(); if (fcPeriod.value) loadFcSummary()
  } catch { /* */ }
}

// ===== v1.9 进项发票 =====
const iiList = ref([])
const iiLoading = ref(false)
const iiDialogVisible = ref(false)
const iiEditingId = ref(null)
const iiCategoryLabels = { software: '软件', equipment: '设备', service: '服务', other: '其他' }
const defaultIiForm = { invoice_no: '', vendor_name: '', invoice_date: '', amount_excluding_tax: 0, tax_rate: 0.13, category: 'other', project_id: null, notes: '' }
const iiForm = ref({ ...defaultIiForm })

const loadIiList = async () => {
  iiLoading.value = true
  try { const { data } = await apiGetInputInvoices(); iiList.value = data } catch { iiList.value = [] } finally { iiLoading.value = false }
}
const openIiCreate = () => { iiEditingId.value = null; iiForm.value = { ...defaultIiForm }; iiDialogVisible.value = true }
const editIi = (row) => { iiEditingId.value = row.id; iiForm.value = { ...row }; iiDialogVisible.value = true }
const deleteIi = async (id) => {
  try { await ElMessageBox.confirm('确定删除该进项发票？', '确认', { type: 'warning' }); await apiDeleteInputInvoice(id); ElMessage.success('删除成功'); loadIiList() } catch { /* */ }
}
const handleIiSubmit = async () => {
  if (!iiForm.value.invoice_no || !iiForm.value.vendor_name || !iiForm.value.invoice_date || !iiForm.value.amount_excluding_tax) { ElMessage.warning('请填写必要信息'); return }
  try {
    if (iiEditingId.value) { await apiUpdateInputInvoice(iiEditingId.value, iiForm.value); ElMessage.success('更新成功') }
    else { await apiCreateInputInvoice(iiForm.value); ElMessage.success('创建成功') }
    iiDialogVisible.value = false; loadIiList()
  } catch { /* */ }
}
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-title-group {
  display: flex;
  align-items: baseline;
  gap: 10px;
}

.header-title-group h2 { margin: 0; }

.header-count {
  font-size: 13px;
  color: var(--text-tertiary);
}

.filter-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.type-indicator {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;
}

.type-indicator.income {
  background: var(--brand-emerald-glow);
  color: var(--brand-emerald);
}

.type-indicator.expense {
  background: var(--brand-rose-glow);
  color: var(--brand-rose);
}

.amount-cell {
  font-weight: 600;
}

.amount-cell.income { color: var(--brand-emerald); }
.amount-cell.expense {
  color: var(--el-color-danger);
}

/* Modern Status Dots - Scoped */
.status-dot-wrapper {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  background-color: var(--bg-soft, #f8fafc);
  border: 1px solid var(--border-light, #e2e8f0);
}
.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.status-dot.primary { background-color: var(--el-color-primary); box-shadow: 0 0 4px var(--el-color-primary); }
.status-dot.success { background-color: var(--el-color-success); box-shadow: 0 0 4px var(--el-color-success); }
.status-dot.warning { background-color: var(--el-color-warning); box-shadow: 0 0 4px var(--el-color-warning); }
.status-dot.danger { background-color: var(--el-color-danger); box-shadow: 0 0 4px var(--el-color-danger); }
.status-dot.info { background-color: var(--el-color-info); box-shadow: 0 0 4px var(--el-color-info); }

.status-dot-text {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
}

:deep(.action-btns .el-button + .el-button) {
  margin-left: 0 !important;
}

.pagination-wrap {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border-subtle);
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 16px;
}

:deep(.el-form-item__label) {
  padding-bottom: 4px;
}

/* ---- Changelog ---- */
.changelog-section {
  margin-top: 12px;
  padding-top: 16px;
  border-top: 1px dashed var(--border-default);
}

.changelog-header {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 10px;
}

.changelog-list {
  max-height: 200px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.changelog-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: var(--el-fill-color-lighter);
  border-radius: var(--el-border-radius-base);
  font-size: 12px;
}

.changelog-field {
  font-weight: 600;
  color: var(--text-primary);
  min-width: 56px;
}

.changelog-values {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--text-secondary);
}

.old-val {
  text-decoration: line-through;
  color: var(--text-tertiary);
}

.arrow {
  color: var(--text-tertiary);
}

.new-val {
  color: var(--brand-emerald);
  font-weight: 500;
}

.changelog-time {
  color: var(--text-tertiary);
  font-size: 11px;
  white-space: nowrap;
}
.stats-bar {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.stat-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  background: var(--el-fill-color-lighter);
  border-radius: 16px;
  font-size: 13px;
}

.stat-chip.warning {
  background: rgba(245, 158, 11, 0.1);
}

.stat-label {
  color: var(--text-secondary);
}

.stat-value {
  color: var(--text-primary);
  font-weight: 600;
}

.empty-invoice {
  display: flex;
  justify-content: center;
  padding: 32px 0;
  color: var(--text-tertiary);
  font-size: 13px;
}

/* v1.8 Export Section */
.export-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.export-form-card h3, .export-history h3 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
  color: var(--text-primary);
}

/* v1.8 Reconciliation Section */
.reconciliation-section {
  padding: 0;
}

.period-selector {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.period-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-secondary);
}

.reconciliation-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.balance-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.balance-card {
  padding: 16px;
  background: var(--el-fill-color-lighter);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.card-label {
  font-size: 12px;
  color: var(--text-tertiary);
}

.card-value {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
}

.card-value.highlight {
  color: var(--el-color-warning);
}

.card-value.primary {
  color: var(--el-color-primary);
}

.card-detail {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: var(--text-secondary);
}

.breakdown-section h4, .unreconciled-section h4 {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--text-primary);
}

.empty-hint {
  color: #999;
  text-align: center;
  padding: 24px;
}

.mono {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
}

/* v1.9 数据核查 */
.consistency-section { padding: 0; }
.consistency-toolbar { margin-bottom: 16px; }
.consistency-ok {
  display: flex; justify-content: center; align-items: center;
  padding: 32px 0; color: var(--el-color-success); font-size: 15px; font-weight: 500;
}

/* v1.9 固定成本 */
.fixed-costs-section { padding: 0; }
.fc-toolbar { display: flex; gap: 10px; margin-bottom: 16px; align-items: center; }
.fc-summary {
  margin-top: 20px; padding: 16px; background: var(--el-fill-color-lighter);
  border-radius: 8px; border: 1px solid var(--border-subtle);
}
.fc-summary-hint { font-size: 12px; color: var(--text-tertiary); margin-bottom: 12px; }
.fc-summary-grid { display: flex; flex-wrap: wrap; gap: 16px; }
.fc-summary-item { display: flex; flex-direction: column; gap: 4px; }
.fc-summary-cat { font-size: 12px; color: var(--text-secondary); }
.fc-summary-val { font-size: 16px; font-weight: 600; color: var(--text-primary); }
.fc-summary-total { margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border-subtle); font-weight: 600; }

/* v1.9 进项发票 */
.input-invoices-section { padding: 0; }
.ii-toolbar { margin-bottom: 16px; }
</style>
