<template>
  <div class="simplified-llm-config">
    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="filter-section">
        <el-select
          v-model="selectedProvider"
          placeholder="选择厂家"
          clearable
          @change="handleProviderFilter"
          style="width: 200px"
        >
          <el-option
            v-for="provider in providers"
            :key="provider.value"
            :label="provider.label"
            :value="provider.value"
          />
        </el-select>
      </div>
      <el-button type="primary" @click="showAddDialog">
        <el-icon><Plus /></el-icon>
        添加配置
      </el-button>
    </div>

    <!-- 配置列表 -->
    <el-table
      v-loading="loading"
      :data="filteredConfigs"
      style="width: 100%"
      stripe
    >
      <el-table-column label="厂家" width="150">
        <template #default="{ row }">
          <div class="provider-cell">
            <el-tag :type="getProviderTagType(row.provider)" size="small">
              {{ row.provider_name }}
            </el-tag>
            <el-icon v-if="row.is_default" color="#f56c6c" class="default-icon">
              <StarFilled />
            </el-icon>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="模型" width="200">
        <template #default="{ row }">
          <div class="model-cell">
            <div class="model-name">{{ row.model_display_name }}</div>
            <div class="model-id">{{ row.model_name }}</div>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="API配置" width="250">
        <template #default="{ row }">
          <div class="api-config">
            <div v-if="row.api_base" class="api-base">
              <el-text size="small" type="info">{{ row.api_base }}</el-text>
            </div>
            <div class="api-key-status">
              <el-tag :type="row.api_key ? 'success' : 'warning'" size="small">
                {{ row.api_key ? '已配置密钥' : '使用环境变量' }}
              </el-tag>
            </div>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="参数" width="200">
        <template #default="{ row }">
          <div class="params">
            <div class="param-item">
              <span class="label">Tokens:</span>
              <span>{{ row.max_tokens }}</span>
            </div>
            <div class="param-item">
              <span class="label">Temp:</span>
              <span>{{ row.temperature }}</span>
            </div>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="定价" width="150">
        <template #default="{ row }">
          <div v-if="row.input_price || row.output_price" class="pricing">
            <div class="price-item">
              <span class="label">输入:</span>
              <span class="price">{{ row.input_price }}</span>
              <span class="currency">{{ row.currency }}/1K</span>
            </div>
            <div class="price-item">
              <span class="label">输出:</span>
              <span class="price">{{ row.output_price }}</span>
              <span class="currency">{{ row.currency }}/1K</span>
            </div>
          </div>
          <el-text v-else type="info" size="small">未定价</el-text>
        </template>
      </el-table-column>

      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.enabled ? 'success' : 'info'" size="small">
            {{ row.enabled ? '启用' : '禁用' }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="适用场景" width="200">
        <template #default="{ row }">
          <el-tag
            v-for="scenario in row.suitable_for"
            :key="scenario"
            size="small"
            class="scenario-tag"
          >
            {{ getScenarioLabel(scenario) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button-group>
            <el-button size="small" @click="handleEdit(row)">
              <el-icon><Edit /></el-icon>
              编辑
            </el-button>
            <el-button
              v-if="!row.is_default"
              size="small"
              type="warning"
              @click="handleSetDefault(row)"
            >
              <el-icon><Star /></el-icon>
              设为默认
            </el-button>
            <el-button size="small" type="info" @click="handleTest(row)">
              <el-icon><Connection /></el-icon>
              测试
            </el-button>
            <el-button
              size="small"
              type="danger"
              @click="handleDelete(row)"
            >
              <el-icon><Delete /></el-icon>
            </el-button>
          </el-button-group>
        </template>
      </el-table-column>
    </el-table>

    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑LLM配置' : '添加LLM配置'"
      width="800px"
      @close="handleDialogClose"
    >
      <el-form
        ref="formRef"
        :model="formData"
        :rules="formRules"
        label-width="140px"
      >
        <el-divider content-position="left">厂家和模型</el-divider>

        <el-form-item label="厂家" prop="provider">
          <el-select
            v-model="formData.provider"
            placeholder="选择厂家"
            @change="handleProviderChange"
          >
            <el-option
              v-for="provider in providerOptions"
              :key="provider.value"
              :label="provider.label"
              :value="provider.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="厂家名称" prop="provider_name">
          <el-input v-model="formData.provider_name" placeholder="例如: OpenAI" />
        </el-form-item>

        <el-form-item label="模型名称" prop="model_name">
          <el-input v-model="formData.model_name" placeholder="例如: gpt-4" />
        </el-form-item>

        <el-form-item label="模型显示名称" prop="model_display_name">
          <el-input v-model="formData.model_display_name" placeholder="例如: GPT-4 Turbo" />
        </el-form-item>

        <el-divider content-position="left">API配置</el-divider>

        <el-form-item label="API密钥" prop="api_key">
          <el-input
            v-model="formData.api_key"
            type="password"
            placeholder="可选，留空则使用环境变量"
            show-password
          />
        </el-form-item>

        <el-form-item label="API地址" prop="api_base">
          <el-input
            v-model="formData.api_base"
            placeholder="例如: https://api.openai.com/v1"
          />
        </el-form-item>

        <el-divider content-position="left">模型参数</el-divider>

        <el-form-item label="最大Token数" prop="max_tokens">
          <el-input-number
            v-model="formData.max_tokens"
            :min="1"
            :max="128000"
            :step="1000"
          />
        </el-form-item>

        <el-form-item label="温度" prop="temperature">
          <el-input-number
            v-model="formData.temperature"
            :min="0"
            :max="2"
            :step="0.1"
            :precision="1"
          />
        </el-form-item>

        <el-form-item label="超时时间(秒)" prop="timeout">
          <el-input-number
            v-model="formData.timeout"
            :min="10"
            :max="600"
            :step="10"
          />
        </el-form-item>

        <el-divider content-position="left">定价信息（可选）</el-divider>

        <el-form-item label="输入价格">
          <el-input-number
            v-model="formData.input_price"
            :min="0"
            :precision="6"
            :step="0.001"
            controls-position="right"
          />
          <span class="unit-label">{{ formData.currency || 'CNY' }}/1K tokens</span>
        </el-form-item>

        <el-form-item label="输出价格">
          <el-input-number
            v-model="formData.output_price"
            :min="0"
            :precision="6"
            :step="0.001"
            controls-position="right"
          />
          <span class="unit-label">{{ formData.currency || 'CNY' }}/1K tokens</span>
        </el-form-item>

        <el-form-item label="货币">
          <el-select v-model="formData.currency">
            <el-option label="CNY (人民币)" value="CNY" />
            <el-option label="USD (美元)" value="USD" />
            <el-option label="EUR (欧元)" value="EUR" />
          </el-select>
        </el-form-item>

        <el-divider content-position="left">其他配置</el-divider>

        <el-form-item label="适用场景" prop="suitable_for">
          <el-checkbox-group v-model="formData.suitable_for">
            <el-checkbox label="quick_analysis">快速分析</el-checkbox>
            <el-checkbox label="deep_analysis">深度分析</el-checkbox>
            <el-checkbox label="report_generation">报告生成</el-checkbox>
            <el-checkbox label="data_analysis">数据分析</el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <el-form-item label="能力标签" prop="capabilities">
          <el-checkbox-group v-model="formData.capabilities">
            <el-checkbox label="vision">视觉</el-checkbox>
            <el-checkbox label="function_calling">函数调用</el-checkbox>
            <el-checkbox label="long_context">长上下文</el-checkbox>
            <el-checkbox label="reasoning">推理</el-checkbox>
            <el-checkbox label="fast_response">快速响应</el-checkbox>
            <el-checkbox label="cost_effective">成本效益</el-checkbox>
          </el-checkbox-group>
        </el-form-item>

        <el-form-item label="描述">
          <el-input
            v-model="formData.description"
            type="textarea"
            :rows="3"
            placeholder="模型描述（可选）"
          />
        </el-form-item>

        <el-form-item label="状态">
          <el-switch v-model="formData.enabled" active-text="启用" inactive-text="禁用" />
        </el-form-item>

        <el-form-item label="设为默认">
          <el-switch v-model="formData.is_default" />
          <el-text type="info" size="small" style="margin-left: 10px">
            每个厂家的第一个配置会自动设为默认
          </el-text>
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
  Star,
  StarFilled,
  Connection
} from '@element-plus/icons-vue'
import { configApi, type SimplifiedLLMConfig, type SimplifiedLLMConfigRequest } from '@/api/config'

// 数据
const configs = ref<SimplifiedLLMConfig[]>([])
const loading = ref(false)
const selectedProvider = ref('')

// 厂家选项
const providers = [
  { label: 'OpenAI', value: 'openai' },
  { label: 'DeepSeek', value: 'deepseek' },
  { label: '通义千问', value: 'qwen' },
  { label: '智谱AI', value: 'zhipu' },
  { label: 'Anthropic', value: 'anthropic' },
  { label: 'Google', value: 'google' },
  { label: '硅基流动', value: 'siliconflow' },
  { label: '其他', value: 'other' }
]

const providerOptions = providers

// 过滤后的配置
const filteredConfigs = computed(() => {
  if (!selectedProvider.value) {
    return configs.value
  }
  return configs.value.filter(c => c.provider === selectedProvider.value)
})

// 对话框
const dialogVisible = ref(false)
const isEdit = ref(false)
const submitLoading = ref(false)
const formRef = ref<FormInstance>()
const currentEditId = ref<string>()

// 表单数据
const formData = reactive<SimplifiedLLMConfigRequest>({
  provider: 'openai',
  provider_name: '',
  model_name: '',
  model_display_name: '',
  api_key: '',
  api_base: '',
  max_tokens: 4000,
  temperature: 0.7,
  timeout: 180,
  enabled: true,
  is_default: false,
  input_price: undefined,
  output_price: undefined,
  currency: 'CNY',
  capabilities: [],
  suitable_for: [],
  description: ''
})

// 表单验证规则
const formRules: FormRules = {
  provider: [{ required: true, message: '请选择厂家', trigger: 'change' }],
  provider_name: [{ required: true, message: '请输入厂家名称', trigger: 'blur' }],
  model_name: [{ required: true, message: '请输入模型名称', trigger: 'blur' }],
  model_display_name: [{ required: true, message: '请输入模型显示名称', trigger: 'blur' }]
}

// 方法
const loadConfigs = async () => {
  loading.value = true
  try {
    configs.value = await configApi.getSimplifiedLLMConfigs()
  } catch (error: any) {
    ElMessage.error('加载配置失败: ' + (error.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

const handleProviderFilter = () => {
  // 自动触发，因为使用了computed
}

const showAddDialog = () => {
  isEdit.value = false
  currentEditId.value = undefined
  Object.assign(formData, {
    provider: 'openai',
    provider_name: '',
    model_name: '',
    model_display_name: '',
    api_key: '',
    api_base: '',
    max_tokens: 4000,
    temperature: 0.7,
    timeout: 180,
    enabled: true,
    is_default: false,
    input_price: undefined,
    output_price: undefined,
    currency: 'CNY',
    capabilities: [],
    suitable_for: [],
    description: ''
  })
  dialogVisible.value = true
}

const handleEdit = (row: SimplifiedLLMConfig) => {
  isEdit.value = true
  currentEditId.value = row.id
  Object.assign(formData, {
    provider: row.provider,
    provider_name: row.provider_name,
    model_name: row.model_name,
    model_display_name: row.model_display_name,
    api_key: row.api_key || '',
    api_base: row.api_base || '',
    max_tokens: row.max_tokens,
    temperature: row.temperature,
    timeout: row.timeout,
    enabled: row.enabled,
    is_default: row.is_default,
    input_price: row.input_price,
    output_price: row.output_price,
    currency: row.currency,
    capabilities: [...(row.capabilities || [])],
    suitable_for: [...(row.suitable_for || [])],
    description: row.description || ''
  })
  dialogVisible.value = true
}

const handleProviderChange = (value: string) => {
  const provider = providers.find(p => p.value === value)
  if (provider) {
    formData.provider_name = provider.label
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    submitLoading.value = true
    try {
      if (isEdit.value && currentEditId.value) {
        await configApi.updateSimplifiedLLMConfig(currentEditId.value, formData)
        ElMessage.success('配置更新成功')
      } else {
        await configApi.addSimplifiedLLMConfig(formData)
        ElMessage.success('配置添加成功')
      }
      dialogVisible.value = false
      await loadConfigs()
    } catch (error: any) {
      ElMessage.error('操作失败: ' + (error.message || '未知错误'))
    } finally {
      submitLoading.value = false
    }
  })
}

const handleDelete = async (row: SimplifiedLLMConfig) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除配置 "${row.provider_name} - ${row.model_display_name}" 吗？`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )

    await configApi.deleteSimplifiedLLMConfig(row.id)
    ElMessage.success('删除成功')
    await loadConfigs()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败: ' + (error.message || '未知错误'))
    }
  }
}

const handleSetDefault = async (row: SimplifiedLLMConfig) => {
  try {
    await configApi.setDefaultSimplifiedLLM(row.id)
    ElMessage.success('已设为默认配置')
    await loadConfigs()
  } catch (error: any) {
    ElMessage.error('设置失败: ' + (error.message || '未知错误'))
  }
}

const handleTest = async (row: SimplifiedLLMConfig) => {
  const loading = ElMessage({
    message: '正在测试连接...',
    type: 'info',
    duration: 0
  })

  try {
    const result = await configApi.testSimplifiedLLMConfig(row.id)
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

const handleDialogClose = () => {
  formRef.value?.resetFields()
}

const getProviderTagType = (provider: string) => {
  const typeMap: Record<string, string> = {
    openai: 'success',
    deepseek: 'primary',
    qwen: 'warning',
    zhipu: 'danger',
    anthropic: 'info',
    google: 'success',
    siliconflow: 'primary'
  }
  return typeMap[provider] || ''
}

const getScenarioLabel = (scenario: string) => {
  const labelMap: Record<string, string> = {
    quick_analysis: '快速分析',
    deep_analysis: '深度分析',
    report_generation: '报告生成',
    data_analysis: '数据分析'
  }
  return labelMap[scenario] || scenario
}

// 生命周期
onMounted(() => {
  loadConfigs()
})
</script>

<style scoped>
.simplified-llm-config {
  padding: 20px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding: 16px;
  background: #fff;
  border-radius: 4px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.provider-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.default-icon {
  font-size: 18px;
}

.model-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.model-name {
  font-weight: 500;
}

.model-id {
  font-size: 12px;
  color: #909399;
}

.api-config {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.api-base {
  font-size: 12px;
}

.params {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.param-item {
  display: flex;
  gap: 4px;
  font-size: 12px;
}

.param-item .label {
  color: #909399;
}

.pricing {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
}

.price-item {
  display: flex;
  gap: 4px;
}

.price-item .label {
  color: #909399;
}

.price-item .price {
  color: #67c23a;
  font-weight: 500;
}

.scenario-tag {
  margin-right: 4px;
  margin-bottom: 4px;
}

.unit-label {
  margin-left: 8px;
  color: #909399;
  font-size: 12px;
}

:deep(.el-divider__text) {
  font-weight: 500;
  color: #409eff;
}
</style>
