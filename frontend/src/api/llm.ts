/**
 * Simplified LLM Configuration API
 *
 * For 1-2 provider use case. Direct MongoDB operations, no config bridge.
 *
 * Endpoints:
 * - GET  /api/llm          - Get all LLM configs
 * - POST /api/llm          - Create/update LLM config
 * - DELETE /api/llm/{id}   - Delete LLM config
 * - POST /api/llm/test     - Test LLM config
 */

import { ApiClient } from './request'

// ===== Types =====

export interface LLMConfig {
  id: string
  name: string           // Provider name (e.g., deepseek, openai, google)
  display_name: string   // Display name
  model: string          // Model name (e.g., deepseek-chat, gpt-4o)
  api_key?: string       // API key (truncated in response)
  base_url?: string
  temperature: number
  max_tokens: number
  timeout: number
  enabled: boolean
  created_at: string
  updated_at: string
}

export interface LLMConfigRequest {
  id?: string            // Omit for new config
  name: string           // Provider name
  display_name: string   // Display name
  model: string          // Model name
  api_key?: string       // API key (omit to keep existing when updating)
  base_url?: string
  temperature?: number
  max_tokens?: number
  timeout?: number
  enabled?: boolean
}

export interface LLMTestRequest {
  config_id: string
}

export interface LLMTestResponse {
  success: boolean
  message: string
  response_preview?: string
}

// ===== API =====

export const llmApi = {
  /**
   * Get all LLM configurations
   */
  async getAll(): Promise<LLMConfig[]> {
    return ApiClient.get('/api/llm')
  },

  /**
   * Get a single LLM configuration by ID
   */
  async getOne(id: string): Promise<LLMConfig> {
    const configs = await this.getAll()
    const config = configs.find(c => c.id === id)
    if (!config) {
      throw new Error(`LLM config with id ${id} not found`)
    }
    return config
  },

  /**
   * Create or update LLM configuration
   */
  async save(config: LLMConfigRequest): Promise<LLMConfig> {
    return ApiClient.post('/api/llm', config)
  },

  /**
   * Delete LLM configuration
   */
  async delete(id: string): Promise<{ success: boolean; message: string }> {
    return ApiClient.delete(`/api/llm/${id}`)
  },

  /**
   * Test LLM configuration
   */
  async test(request: LLMTestRequest): Promise<LLMTestResponse> {
    return ApiClient.post('/api/llm/test', request)
  }
}

// ===== Constants =====

/**
 * Predefined provider templates
 */
export const PROVIDER_TEMPLATES: Record<string, Partial<LLMConfigRequest>> = {
  deepseek: {
    name: 'deepseek',
    display_name: 'DeepSeek',
    model: 'deepseek-chat',
    base_url: 'https://api.deepseek.com',
    temperature: 0.7,
    max_tokens: 4000,
    timeout: 180,
    enabled: true
  },
  openai: {
    name: 'openai',
    display_name: 'OpenAI',
    model: 'gpt-4o',
    base_url: 'https://api.openai.com/v1',
    temperature: 0.7,
    max_tokens: 4000,
    timeout: 180,
    enabled: true
  },
  google: {
    name: 'google',
    display_name: 'Google Gemini',
    model: 'gemini-2.0-flash',
    base_url: 'https://generativelanguage.googleapis.com/v1beta',
    temperature: 0.7,
    max_tokens: 4000,
    timeout: 180,
    enabled: true
  },
  dashscope: {
    name: 'dashscope',
    display_name: 'DashScope (Qwen)',
    model: 'qwen-plus',
    base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    temperature: 0.7,
    max_tokens: 4000,
    timeout: 180,
    enabled: true
  }
}

/**
 * Get template for a provider
 */
export function getProviderTemplate(provider: string): Partial<LLMConfigRequest> {
  return PROVIDER_TEMPLATES[provider] || PROVIDER_TEMPLATES.deepseek
}

/**
 * Get list of available providers
 */
export function getAvailableProviders(): Array<{ key: string; name: string }> {
  return Object.entries(PROVIDER_TEMPLATES).map(([key, template]) => ({
    key,
    name: template.display_name || key
  }))
}
