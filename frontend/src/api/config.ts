/**
 * 配置管理API
 */

import { ApiClient } from './request'

// 配置相关类型定义

export interface DataSourceConfig {
  name: string
  type: string
  api_key?: string
  api_secret?: string
  endpoint?: string
  timeout: number
  rate_limit: number
  enabled: boolean
  priority: number
  config_params: Record<string, any>
  description?: string
  // 新增字段：支持市场分类
  market_categories?: string[]  // 所属市场分类列表
  display_name?: string         // 显示名称
  provider?: string            // 数据提供商
  created_at?: string
  updated_at?: string
}

export interface DatabaseConfig {
  name: string
  type: string
  host: string
  port: number
  username?: string
  password?: string
  database?: string
  connection_params: Record<string, any>
  pool_size: number
  max_overflow: number
  enabled: boolean
  description?: string
}

export interface SystemConfig {
  config_name: string
  config_type: string
  data_source_configs: DataSourceConfig[]
  default_data_source?: string
  database_configs: DatabaseConfig[]
  system_settings: Record<string, any>
  created_at: string
  updated_at: string
  version: number
  is_active: boolean
}

export interface ConfigTestRequest {
  config_type: 'datasource' | 'database'
  config_data: Record<string, any>
}

export interface ConfigTestResponse {
  success: boolean
  message: string
  details?: Record<string, any>
}

// 系统设置元数据
export interface SettingMeta {
  key: string
  sensitive: boolean
  editable: boolean
  source: 'environment' | 'database' | 'default'
  has_value: boolean
}

// 配置管理API
export const configApi = {
  // 获取系统配置
  getSystemConfig(): Promise<SystemConfig> {
    return ApiClient.get('/api/config/system')
  },

  // ========== 数据源配置管理 ==========

  // 获取所有数据源配置
  getDataSourceConfigs(): Promise<DataSourceConfig[]> {
    return ApiClient.get('/api/config/datasource')
  },

  // 添加数据源配置
  addDataSourceConfig(config: Partial<DataSourceConfig>): Promise<{ message: string; name: string }> {
    return ApiClient.post('/api/config/datasource', config)
  },

  // 设置默认数据源
  setDefaultDataSource(name: string): Promise<{ message: string; default_data_source: string }> {
    return ApiClient.post('/api/config/datasource/set-default', { name })
  },

  // 更新数据源配置
  updateDataSourceConfig(name: string, config: Partial<DataSourceConfig>): Promise<{ message: string }> {
    return ApiClient.put(`/api/config/datasource/${name}`, config)
  },

  // 删除数据源配置
  deleteDataSourceConfig(name: string): Promise<{ message: string }> {
    return ApiClient.delete(`/api/config/datasource/${name}`)
  },

  // 获取系统设置元数据
  getSystemSettingsMeta(): Promise<{ items: SettingMeta[] }> {
    return ApiClient.get('/api/config/settings/meta').then((r: any) => r.data)
  },

  // ========== 数据库配置管理 ==========

  // 获取所有数据库配置
  getDatabaseConfigs(): Promise<DatabaseConfig[]> {
    return ApiClient.get('/api/config/database')
  },

  // 获取指定的数据库配置
  getDatabaseConfig(dbName: string): Promise<DatabaseConfig> {
    return ApiClient.get(`/api/config/database/${encodeURIComponent(dbName)}`)
  },

  // 添加数据库配置
  addDatabaseConfig(config: Partial<DatabaseConfig>): Promise<{ success: boolean; message: string }> {
    return ApiClient.post('/api/config/database', config)
  },

  // 更新数据库配置
  updateDatabaseConfig(dbName: string, config: Partial<DatabaseConfig>): Promise<{ success: boolean; message: string }> {
    return ApiClient.put(`/api/config/database/${encodeURIComponent(dbName)}`, config)
  },

  // 删除数据库配置
  deleteDatabaseConfig(dbName: string): Promise<{ success: boolean; message: string }> {
    return ApiClient.delete(`/api/config/database/${encodeURIComponent(dbName)}`)
  },

  // 测试数据库配置连接
  testDatabaseConfig(dbName: string): Promise<ConfigTestResponse> {
    return ApiClient.post(`/api/config/database/${encodeURIComponent(dbName)}/test`)
  },

  // ========== 系统设置管理 ==========

  // 获取系统设置
  getSystemSettings(): Promise<Record<string, any>> {
    return ApiClient.get('/api/config/settings')
  },

  // 更新系统设置
  updateSystemSettings(settings: Record<string, any>): Promise<{ message: string }> {
    return ApiClient.put('/api/config/settings', settings)
  },

  // ========== 配置测试和导入导出 ==========

  // 测试配置连接
  testConfig(testRequest: ConfigTestRequest): Promise<ConfigTestResponse> {
    return ApiClient.post('/api/config/test', testRequest)
  },

  // 导出配置
  exportConfig(): Promise<{ message: string; data: any; exported_at: string }> {
    return ApiClient.post('/api/config/export')
  },

  // 导入配置
  importConfig(configData: Record<string, any>): Promise<{ message: string }> {
    return ApiClient.post('/api/config/import', configData)
  },

  // 迁移传统配置
  migrateLegacyConfig(): Promise<{ message: string }> {
    return ApiClient.post('/api/config/migrate-legacy')
  },

  // 配置重载
  reloadConfig(): Promise<{ success: boolean; message: string; data?: any }> {
    return ApiClient.post('/api/config/reload')
  }
}

/**
 * 数据源类型常量
 *
 * 注意：这些常量与后端 DataSourceType 枚举保持同步
 * 添加新数据源时，请先在后端 tradingagents/constants/data_sources.py 中注册
 */
export const DATA_SOURCE_TYPES = {
  // 缓存数据源
  MONGODB: 'mongodb',

  // 中国市场数据源
  TUSHARE: 'tushare',
  AKSHARE: 'akshare',
  BAOSTOCK: 'baostock',

  // 美股数据源
  FINNHUB: 'finnhub',
  YAHOO_FINANCE: 'yahoo_finance',
  ALPHA_VANTAGE: 'alpha_vantage',
  IEX_CLOUD: 'iex_cloud',

  // 专业数据源
  WIND: 'wind',
  CHOICE: 'choice',

  // 其他数据源
  QUANDL: 'quandl',
  LOCAL_FILE: 'local_file',
  CUSTOM: 'custom'
} as const

export const DATABASE_TYPES = {
  MONGODB: 'mongodb',
  REDIS: 'redis',
  MYSQL: 'mysql',
  POSTGRESQL: 'postgresql'
} as const

// 默认配置模板
export const DEFAULT_DATA_SOURCE_CONFIG: Partial<DataSourceConfig> = {
  timeout: 30,
  rate_limit: 100,
  enabled: true,
  priority: 0,
  config_params: {},
  market_categories: []
}

export const DEFAULT_DATABASE_CONFIG: Partial<DatabaseConfig> = {
  pool_size: 10,
  max_overflow: 20,
  enabled: true,
  connection_params: {}
}

// 配置验证函数
export const validateDataSourceConfig = (config: Partial<DataSourceConfig>): string[] => {
  const errors: string[] = []

  if (!config.name) errors.push('数据源名称不能为空')
  if (!config.type) errors.push('数据源类型不能为空')
  if (config.timeout && config.timeout <= 0) errors.push('超时时间必须大于0')
  if (config.rate_limit && config.rate_limit <= 0) errors.push('速率限制必须大于0')

  return errors
}

export const validateDatabaseConfig = (config: Partial<DatabaseConfig>): string[] => {
  const errors: string[] = []

  if (!config.name) errors.push('数据库名称不能为空')
  if (!config.type) errors.push('数据库类型不能为空')
  if (!config.host) errors.push('主机地址不能为空')
  if (!config.port || config.port <= 0) errors.push('端口号必须大于0')
  if (config.pool_size && config.pool_size <= 0) errors.push('连接池大小必须大于0')

  return errors
}
