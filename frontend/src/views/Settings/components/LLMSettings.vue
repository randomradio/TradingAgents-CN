<template>
  <div class="llm-settings">
    <!-- Header -->
    <div class="header">
      <div class="title-section">
        <h3>LLM 配置</h3>
        <p class="subtitle">配置 1-2 个 LLM 提供商即可</p>
      </div>
      <el-button type="primary" @click="showAddDialog">
        <el-icon><Plus /></el-icon>
        添加配置
      </el-button>
    </div>

    <!-- Configs List -->
    <el-card v-loading="loading" class="configs-card">
      <el-empty v-if="!loading && configs.length === 0" description="暂无 LLM 配置">
        <el-button type="primary" @click="showAddDialog">添加配置</el-button>
      </el-empty>

      <div v-else class="configs-list">
        <div
          v-for="config in configs"
          :key="config.id"
          class="config-item"
          :class="{ disabled: !config.enabled }"
        >
          <div class="config-info">
            <div class="config-header">
              <el-tag :type="getProviderTagType(config.name)" size="large">
                {{ config.display_name }}
              </el-tag>
              <el-tag v-if="config.enabled" type="success" size="small">启用</el-tag>
              <el-tag v-else type="info" size="small">禁用</el-tag>
            </div>
            <div class="config-model">{{ config.model }}</div>
            <div v-if="config.base_url" class="config-url">{{ config.base_url }}</div>
            <div class="config-params">
              <span>tokens: {{ config.max_tokens }}</span>
              <span>temp: {{ config.temperature }}</span>
              <span>timeout: {{ config.timeout }}s</span>
            </div>
          </div>

          <div class="config-actions">
            <el-button-group>
              <el-button size="small" @click="handleEdit(config)">
                <el-icon><Edit /></el-icon>
              </el-button>
              <el-button size="small" @click="handleTest(config)">
                <el-icon><Connection /></el-icon>
              </el-button>
              <el-button
                size="small"
                :type="config.enabled ? 'warning' : 'success'"
                @click="handleToggle(config)"
              >
                {{ config.enabled ? '禁用' : '启用' }}
              </el-button>
              <el-button size="small" type="danger" @click="handleDelete(config)">
                <el-icon><Delete /></el-icon>
              </el-button>
            </el-button-group>
          </div>
        </div>
      </div>
    </el-card>

    <!-- Add/Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑配置' : '添加配置'"
      width="500px"
      @close="handleDialogClose"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="100px"
      >
        <!-- Quick Select -->
        <el-form-item label="快速选择">
          <el-select
            v-model="selectedProvider"
            placeholder="选择提供商模板"
            @change="handleProviderSelect"
            style="width: 100%"
          >
            <el-option
              v-for="provider in providerOptions"
              :key="provider.key"
              :label="provider.name"
              :value="provider.key"
            />
          </el-select>
        </el-form-item>

        <el-divider />

        <el-form-item label="提供商" prop="name">
          <el-input v-model="formData.name" placeholder="deepseek, openai, google, dashscope" />
        </el-form-item>

        <el-form-item label="显示名称" prop="display_name">
          <el-input v-model="formData.display_name" placeholder="DeepSeek" />
        </el-form-item>

        <el-form-item label="模型" prop="model">
          <el-input v-model="formData.model" placeholder="deepseek-chat, gpt-4o, gemini-2.0-flash" />
        </el-form-item>

        <el-form-item label="API Key">
          <el-input
            v-model="formData.api_key"
            type="password"
            placeholder="sk-xxx (可选，留空使用环境变量)"
            show-password
          />
        </el-form-item>

        <el-form-item label="Base URL">
          <el-input v-model="formData.base_url" placeholder="https://api.deepseek.com" />
        </el-form-item>

        <el-divider />

        <el-form-item label="最大 Tokens">
          <el-input-number v-model="formData.max_tokens" :min="1" :max="128000" :step="1000" />
        </el-form-item>

        <el-form-item label="温度">
          <el-input-number v-model="formData.temperature" :min="0" :max="2" :step="0.1" :precision="1" />
        </el-form-item>

        <el-form-item label="超时 (秒)">
          <el-input-number v-model="formData.timeout" :min="10" :max="600" :step="10" />
        </el-form-item>

        <el-form-item label="启用">
          <el-switch v-model="formData.enabled" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitLoading">
          {{ isEdit ? '保存' : '添加' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import {
  Plus,
  Edit,
  Delete,
  Connection
} from '@element-plus/icons-vue'
import { llmApi, getAvailableProviders, getProviderTemplate, type LLMConfig, type LLMConfigRequest } from '@/api/llm'

// Data
const configs = ref<LLMConfig[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitLoading = ref(false)
const formRef = ref<FormInstance>()
const currentEditId = ref<string>()
const selectedProvider = ref('')

// Provider options
const providerOptions = getAvailableProviders()

// Form data
const formData = reactive<LLMConfigRequest>({
  name: 'deepseek',
  display_name: 'DeepSeek',
  model: 'deepseek-chat',
  api_key: '',
  base_url: 'https://api.deepseek.com',
  temperature: 0.7,
  max_tokens: 4000,
  timeout: 180,
  enabled: true
})

// Form rules
const formRules: FormRules = {
  name: [{ required: true, message: '请输入提供商名称', trigger: 'blur' }],
  display_name: [{ required: true, message: '请输入显示名称', trigger: 'blur' }],
  model: [{ required: true, message: '请输入模型名称', trigger: 'blur' }]
}

// Methods
const loadConfigs = async () => {
  loading.value = true
  try {
    configs.value = await llmApi.getAll()
  } catch (error: any) {
    ElMessage.error('加载配置失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

const showAddDialog = () => {
  isEdit.value = false
  currentEditId.value = undefined
  selectedProvider.value = ''
  resetForm()
  dialogVisible.value = true
}

const resetForm = () => {
  Object.assign(formData, {
    name: 'deepseek',
    display_name: 'DeepSeek',
    model: 'deepseek-chat',
    api_key: '',
    base_url: 'https://api.deepseek.com',
    temperature: 0.7,
    max_tokens: 4000,
    timeout: 180,
    enabled: true
  })
}

const handleProviderSelect = (provider: string) => {
  const template = getProviderTemplate(provider)
  Object.assign(formData, {
    ...template,
    api_key: '' // Don't pre-fill API key
  })
}

const handleEdit = (config: LLMConfig) => {
  isEdit.value = true
  currentEditId.value = config.id
  selectedProvider.value = ''
  Object.assign(formData, {
    name: config.name,
    display_name: config.display_name,
    model: config.model,
    api_key: '', // Don't show existing API key
    base_url: config.base_url || '',
    temperature: config.temperature,
    max_tokens: config.max_tokens,
    timeout: config.timeout,
    enabled: config.enabled
  })
  dialogVisible.value = true
}

const handleSubmit = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    submitLoading.value = true
    try {
      if (isEdit.value && currentEditId.value) {
        formData.id = currentEditId.value
      }
      await llmApi.save(formData)
      ElMessage.success(isEdit.value ? '保存成功' : '添加成功')
      dialogVisible.value = false
      await loadConfigs()
    } catch (error: any) {
      ElMessage.error('操作失败: ' + (error.message || '未知错误'))
    } finally {
      submitLoading.value = false
    }
  })
}

const handleDelete = async (config: LLMConfig) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除 "${config.display_name}" 配置吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await llmApi.delete(config.id)
    ElMessage.success('删除成功')
    await loadConfigs()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败: ' + (error.message || '未知错误'))
    }
  }
}

const handleTest = async (config: LLMConfig) => {
  const loading = ElMessage({
    message: '正在测试连接...',
    type: 'info',
    duration: 0
  })

  try {
    const result = await llmApi.test({ config_id: config.id })
    loading.close()

    if (result.success) {
      ElMessage.success(result.message || '测试成功')
    } else {
      ElMessage.error(result.message || '测试失败')
    }
  } catch (error: any) {
    loading.close()
    ElMessage.error('测试失败: ' + (error.message || '未知错误'))
  }
}

const handleToggle = async (config: LLMConfig) => {
  const newEnabled = !config.enabled
  try {
    await llmApi.save({
      ...config,
      enabled: newEnabled,
      api_key: '' // Don't change API key
    })
    ElMessage.success(newEnabled ? '已启用' : '已禁用')
    await loadConfigs()
  } catch (error: any) {
    ElMessage.error('操作失败: ' + (error.message || '未知错误'))
  }
}

const handleDialogClose = () => {
  formRef.value?.resetFields()
}

const getProviderTagType = (provider: string) => {
  const typeMap: Record<string, any> = {
    openai: '',
    deepseek: 'primary',
    google: 'success',
    dashscope: 'warning',
    anthropic: 'info'
  }
  return typeMap[provider.toLowerCase()] || ''
}

// Lifecycle
onMounted(() => {
  loadConfigs()
})
</script>

<style scoped>
.llm-settings {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.title-section h3 {
  margin: 0;
  font-size: 18px;
}

.subtitle {
  margin: 4px 0 0 0;
  font-size: 13px;
  color: #909399;
}

.configs-card {
  min-height: 200px;
}

.configs-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.config-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  transition: all 0.3s;
}

.config-item:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.1);
}

.config-item.disabled {
  opacity: 0.6;
}

.config-info {
  flex: 1;
}

.config-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.config-model {
  font-weight: 500;
  color: #303133;
  margin-bottom: 4px;
}

.config-url {
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.config-params {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #909399;
}

:deep(.el-divider) {
  margin: 16px 0;
}
</style>
