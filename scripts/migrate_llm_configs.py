#!/usr/bin/env python3
"""
LLM配置数据迁移脚本

从复杂的三级结构迁移到简化的二级结构：
- 旧: 厂家管理(llm_providers) → 模型目录(model_catalogs) → LLM配置(llm_configs)
- 新: 厂家+模型二级结构(simplified_llm_configs)

功能：
1. 备份现有数据
2. 转换数据到新结构
3. 验证转换结果
4. 支持回滚
"""

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from bson import ObjectId

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 必须在导入其他模块前初始化环境变量
os.environ.setdefault('MONGODB_CONNECTION_STRING', 'mongodb://admin:tradingagents123@mongodb:27017/tradingagents?authSource=admin')
os.environ.setdefault('MONGODB_DATABASE_NAME', 'tradingagents')

from motor.motor_asyncio import AsyncIOMotorClient
from app.models.config import SimplifiedLLMConfig


class LLMMigrator:
    """LLM配置迁移器"""

    def __init__(self):
        self.db = None
        self.client = None

    async def _get_db(self):
        """获取数据库连接"""
        if self.db is None:
            # 直接创建MongoDB客户端
            connection_string = os.getenv('MONGODB_CONNECTION_STRING',
                                        'mongodb://admin:tradingagents123@mongodb:27017/tradingagents?authSource=admin')
            db_name = os.getenv('MONGODB_DATABASE_NAME', 'tradingagents')

            self.client = AsyncIOMotorClient(connection_string)
            self.db = self.client[db_name]

            # 测试连接
            await self.db.list_collection_names()

        return self.db

    async def close(self):
        """关闭数据库连接"""
        if self.client:
            self.client.close()

    async def backup_existing_data(self) -> Dict[str, int]:
        """备份现有数据到 *_backup 集合"""
        db = await self._get_db()
        backup_stats = {}

        print("📦 开始备份现有数据...")

        # 备份 llm_providers
        providers_count = await db.llm_providers.count_documents({})
        if providers_count > 0:
            providers = await db.llm_providers.find({}).to_list(length=None)
            await db.llm_providers_backup.delete_many({})
            await db.llm_providers_backup.insert_many(providers)
            backup_stats['llm_providers'] = providers_count
            print(f"  ✅ 备份 llm_providers: {providers_count} 条")
        else:
            print("  ⏭️  llm_providers 为空，跳过")

        # 备份 llm_configs
        configs_count = await db.llm_configs.count_documents({})
        if configs_count > 0:
            configs = await db.llm_configs.find({}).to_list(length=None)
            await db.llm_configs_backup.delete_many({})
            await db.llm_configs_backup.insert_many(configs)
            backup_stats['llm_configs'] = configs_count
            print(f"  ✅ 备份 llm_configs: {configs_count} 条")
        else:
            print("  ⏭️  llm_configs 为空，跳过")

        # 备份 model_catalogs
        catalogs_count = await db.model_catalogs.count_documents({})
        if catalogs_count > 0:
            catalogs = await db.model_catalogs.find({}).to_list(length=None)
            await db.model_catalogs_backup.delete_many({})
            await db.model_catalogs_backup.insert_many(catalogs)
            backup_stats['model_catalogs'] = catalogs_count
            print(f"  ✅ 备份 model_catalogs: {catalogs_count} 条")
        else:
            print("  ⏭️  model_catalogs 为空，跳过")

        print(f"📦 备份完成！总计: {sum(backup_stats.values())} 条\n")
        return backup_stats

    async def migrate_to_simplified(self) -> List[Dict[str, Any]]:
        """迁移数据到简化结构"""
        db = await self._get_db()

        print("🔄 开始迁移到简化结构...")

        # 读取现有数据
        providers = await db.llm_providers.find({}).to_list(length=None)
        configs = await db.llm_configs.find({}).to_list(length=None)
        model_catalogs = await db.model_catalogs.find({}).to_list(length=None)

        print(f"  📊 读取数据: {len(providers)} 个厂家, {len(configs)} 个配置, {len(model_catalogs)} 个模型目录")

        # 创建厂家和模型目录映射
        providers_map = {p['name']: p for p in providers}
        catalogs_map = {}  # {provider: {model_name: model_info}}

        for catalog in model_catalogs:
            provider = catalog['provider']
            catalogs_map[provider] = {}
            for model_info in catalog.get('models', []):
                catalogs_map[provider][model_info['name']] = model_info

        # 合并转换
        simplified_configs = []
        for config in configs:
            provider_name = config.get('provider', '')
            provider = providers_map.get(provider_name, {})
            model_name = config.get('model_name', '')
            catalog_info = catalogs_map.get(provider_name, {}).get(model_name, {})

            # 构建简化配置
            simplified_config = {
                '_id': ObjectId(),
                'provider': provider_name,
                'provider_name': provider.get('display_name', provider_name),
                'model_name': model_name,
                'model_display_name': config.get('model_display_name') or catalog_info.get('display_name') or model_name,
                'api_key': provider.get('api_key') or config.get('api_key'),
                'api_base': config.get('api_base') or provider.get('default_base_url'),
                'max_tokens': config.get('max_tokens', 4000),
                'temperature': config.get('temperature', 0.7),
                'timeout': config.get('timeout', 180),
                'enabled': config.get('enabled', True),
                'is_default': False,  # 稍后设置默认
                'input_price': catalog_info.get('input_price_per_1k'),
                'output_price': catalog_info.get('output_price_per_1k'),
                'currency': catalog_info.get('currency', 'CNY'),
                'capabilities': catalog_info.get('capabilities', []),
                'suitable_for': config.get('suitable_roles', []),
                'description': config.get('description'),
                'created_at': config.get('created_at', datetime.utcnow()),
                'updated_at': datetime.utcnow()
            }

            simplified_configs.append(simplified_config)

        # 设置第一个启用的配置为默认
        enabled_configs = [c for c in simplified_configs if c['enabled']]
        if enabled_configs:
            enabled_configs[0]['is_default'] = True

        print(f"  ✅ 转换完成: {len(simplified_configs)} 个简化配置")

        # 写入新集合
        await db.simplified_llm_configs.delete_many({})
        if simplified_configs:
            await db.simplified_llm_configs.insert_many(simplified_configs)
            print(f"  ✅ 写入 simplified_llm_configs: {len(simplified_configs)} 条\n")
        else:
            print("  ⚠️  没有数据需要迁移\n")

        return simplified_configs

    async def validate_migration(self) -> bool:
        """验证迁移结果"""
        db = await self._get_db()

        print("🔍 验证迁移结果...")

        # 检查新集合
        simplified_count = await db.simplified_llm_configs.count_documents({})
        print(f"  📊 simplified_llm_configs: {simplified_count} 条")

        # 检查备份数据
        backup_count = await db.llm_providers_backup.count_documents({})
        backup_count += await db.llm_configs_backup.count_documents({})
        backup_count += await db.model_catalogs_backup.count_documents({})
        print(f"  📦 备份数据: {backup_count} 条")

        # 验证数据完整性
        if simplified_count > 0:
            sample = await db.simplified_llm_configs.find_one({})
            required_fields = ['provider', 'provider_name', 'model_name', 'model_display_name']
            missing_fields = [f for f in required_fields if f not in sample]

            if missing_fields:
                print(f"  ❌ 缺少必需字段: {missing_fields}")
                return False
            else:
                print("  ✅ 数据结构验证通过")
                return True
        else:
            print("  ⚠️  simplified_llm_configs 为空")
            return True

    async def rollback_migration(self) -> bool:
        """回滚迁移"""
        db = await self._get_db()

        print("🔄 开始回滚迁移...")

        try:
            # 删除新集合
            await db.simplified_llm_configs.delete_many({})
            print("  ✅ 删除 simplified_llm_configs")

            # 从备份恢复数据
            for collection_name in ['llm_providers', 'llm_configs', 'model_catalogs']:
                backup_collection_name = f"{collection_name}_backup"
                backup_count = await db[backup_collection_name].count_documents({})

                if backup_count > 0:
                    # 从备份恢复
                    backups = await db[backup_collection_name].find({}).to_list(length=None)
                    await db[collection_name].delete_many({})
                    await db[collection_name].insert_many(backs)
                    print(f"  ✅ 恢复 {collection_name}: {backup_count} 条")
                else:
                    print(f"  ⏭️  {collection_name} 备份为空，跳过")

            print("🔄 回滚完成！\n")
            return True

        except Exception as e:
            print(f"  ❌ 回滚失败: {e}\n")
            return False

    async def run_migration(self, force: bool = False) -> bool:
        """执行完整的迁移流程"""
        try:
            print("=" * 60)
            print("🚀 开始LLM配置迁移")
            print("=" * 60)
            print()

            # 1. 备份现有数据
            await self.backup_existing_data()

            # 2. 检查是否已有简化配置
            db = await self._get_db()
            existing_count = await db.simplified_llm_configs.count_documents({})

            if existing_count > 0 and not force:
                print(f"⚠️  simplified_llm_configs 已有 {existing_count} 条数据")
                print("如需重新迁移，请使用 --force 参数")
                return False

            # 3. 迁移数据
            await self.migrate_to_simplified()

            # 4. 验证迁移
            success = await self.validate_migration()

            if success:
                print("=" * 60)
                print("✅ 迁移成功完成！")
                print("=" * 60)
                return True
            else:
                print("=" * 60)
                print("❌ 迁移验证失败，请检查日志")
                print("=" * 60)
                return False

        except Exception as e:
            print(f"❌ 迁移失败: {e}")
            import traceback
            traceback.print_exc()
            return False


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='LLM配置迁移工具')
    parser.add_argument('--force', action='store_true', help='强制重新迁移（覆盖现有简化配置）')
    parser.add_argument('--rollback', action='store_true', help='回滚到迁移前的状态')
    parser.add_argument('--validate-only', action='store_true', help='仅验证现有数据，不执行迁移')

    args = parser.parse_args()

    migrator = LLMMigrator()
    success = False

    try:
        if args.rollback:
            # 回滚模式
            print("🔄 执行回滚操作...\n")
            success = await migrator.rollback_migration()

        elif args.validate_only:
            # 验证模式
            print("🔍 验证现有数据...\n")
            success = await migrator.validate_migration()

        else:
            # 迁移模式
            success = await migrator.run_migration(force=args.force)
    finally:
        # 关闭数据库连接
        await migrator.close()

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    asyncio.run(main())
