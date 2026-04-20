<template>
  <div class="page-container">
    <div class="page-header">
      <span class="page-title">公司设置</span>
      <PageHelpDrawer pageKey="company_settings" />
      <el-button type="primary" :loading="saving" @click="handleSave">
        <el-icon><Check /></el-icon>
        保存
      </el-button>
    </div>

    <el-card v-loading="loading">
      <el-form
        ref="formRef"
        :model="form"
        label-width="120px"
        label-position="right"
        class="company-form"
      >
        <el-divider content-position="left">基本信息</el-divider>

        <el-form-item label="公司全称">
          <el-input v-model="form.company_name" placeholder="如：东莞市天问智算科技有限责任公司" />
        </el-form-item>

        <el-form-item label="统一社会信用代码">
          <el-input v-model="form.company_tax_id" placeholder="如：91441900MA5XXXXX" />
        </el-form-item>

        <el-form-item label="注册地址">
          <el-input v-model="form.company_address" placeholder="如：东莞市南城街道XX路XX号" />
        </el-form-item>

        <el-form-item label="法定代表人">
          <el-input v-model="form.company_legal_rep" placeholder="如：张三" />
        </el-form-item>

        <el-divider content-position="left">联系方式</el-divider>

        <el-form-item label="联系人">
          <el-input v-model="form.company_contact" placeholder="如：李四" />
        </el-form-item>

        <el-form-item label="联系电话">
          <el-input v-model="form.company_phone" placeholder="如：0769-12345678" />
        </el-form-item>

        <el-form-item label="邮箱">
          <el-input v-model="form.company_email" placeholder="如：contact@tianwen.com" />
        </el-form-item>

        <el-divider content-position="left">银行信息</el-divider>

        <el-form-item label="开户行">
          <el-input v-model="form.company_bank_name" placeholder="如：中国工商银行东莞分行" />
        </el-form-item>

        <el-form-item label="银行账号">
          <el-input v-model="form.company_bank_account" placeholder="如：6222XXXXXXXXXXXX" />
        </el-form-item>

        <el-divider content-position="left">税务配置</el-divider>
        <el-alert type="info" :closable="false" style="margin-bottom: 16px">
          <template #title>增值税计算模式配置</template>
          根据纳税人类型自动切换算法。小规模纳税人按销售额判断免税/减征；一般纳税人按销项-进项差额法。
        </el-alert>

        <el-form-item label="纳税人类型">
          <el-select v-model="taxForm.payer_type" style="width: 100%">
            <el-option label="小规模纳税人" value="small_scale" />
            <el-option label="一般纳税人" value="general" />
          </el-select>
        </el-form-item>

        <template v-if="taxForm.payer_type === 'small_scale'">
          <el-form-item label="征收率 (%)">
            <el-input-number v-model="taxForm.small_scale_rate" :min="0.01" :max="0.05" :step="0.005" :precision="3" :controls="false" style="width: 100%" />
            <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 4px">2023-2027 年小规模减按 1% 征收（默认 3%）</div>
          </el-form-item>
          <el-form-item label="季度免税额 (元)">
            <el-input-number v-model="taxForm.small_scale_exempt_threshold" :min="0" :step="10000" :controls="false" style="width: 100%" />
            <div style="font-size: 11px; color: var(--text-tertiary); margin-top: 4px">季度销售额 ≤ 此金额免征增值税（月≤10万即季≤30万）</div>
          </el-form-item>
        </template>

        <template v-if="taxForm.payer_type === 'general'">
          <el-form-item label="标准税率 (%)">
            <el-input-number v-model="taxForm.general_standard_rate" :min="0.01" :max="0.17" :step="0.01" :precision="2" :controls="false" style="width: 100%" />
          </el-form-item>
          <el-form-item label="进项抵扣范围">
            <el-radio-group v-model="taxForm.general_include_ordinary_input">
              <el-radio :value="false">仅专用发票</el-radio>
              <el-radio :value="true">含普通发票</el-radio>
            </el-radio-group>
          </el-form-item>
        </template>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Check } from '@element-plus/icons-vue'
import { getCompanySettings, updateCompanySettings, getTaxConfig, updateTaxConfig } from '../api/company'
import PageHelpDrawer from '../components/PageHelpDrawer.vue'

const loading = ref(false)
const saving = ref(false)
const formRef = ref(null)

const form = ref({
  company_name: '',
  company_tax_id: '',
  company_address: '',
  company_legal_rep: '',
  company_contact: '',
  company_phone: '',
  company_email: '',
  company_bank_name: '',
  company_bank_account: '',
})

const taxForm = ref({
  payer_type: 'small_scale',
  small_scale_rate: 0.01,
  small_scale_exempt_threshold: 300000,
  general_standard_rate: 0.13,
  general_include_ordinary_input: false,
})

async function loadSettings() {
  loading.value = true
  try {
    const [res, taxRes] = await Promise.all([getCompanySettings(), getTaxConfig()])
    if (res.data?.data) Object.assign(form.value, res.data.data)
    if (taxRes.data?.data) Object.assign(taxForm.value, taxRes.data.data)
  } catch (e) {
    ElMessage.error('加载公司设置失败')
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    await Promise.all([updateCompanySettings(form.value), updateTaxConfig(taxForm.value)])
    ElMessage.success('设置已更新')
  } catch (e) {
    ElMessage.error('保存失败，请稍后重试')
  } finally {
    saving.value = false
  }
}

onMounted(loadSettings)
</script>

<style scoped>
.page-container {
  max-width: 800px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.page-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary);
}
.company-form {
  max-width: 600px;
}
</style>
