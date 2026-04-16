<template>
  <div class="page-container">
    <div class="page-header">
      <span class="page-title">公司设置</span>
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
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Check } from '@element-plus/icons-vue'
import { getCompanySettings, updateCompanySettings } from '../api/company'

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

async function loadSettings() {
  loading.value = true
  try {
    const res = await getCompanySettings()
    if (res.data?.data) {
      Object.assign(form.value, res.data.data)
    }
  } catch (e) {
    ElMessage.error('加载公司设置失败')
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    await updateCompanySettings(form.value)
    ElMessage.success('公司设置已更新')
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
