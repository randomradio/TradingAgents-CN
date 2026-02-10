"""
Simplified LLM Configuration

Direct read from MongoDB, no config bridge, no environment variable syncing.
Designed for 1-2 providers use case.

Usage:
    from tradingagents.config.llm_config import get_llm_config, get_active_llm_config

    # Get all configs
    configs = get_llm_config()

    # Get first active config for quick analysis
    config = get_active_llm_config()
    if config:
        llm = create_llm_from_config(config)
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError

logger = logging.getLogger(__name__)


@dataclass
class LLMConfig:
    """Simple LLM configuration"""
    provider: str  # e.g., "openai", "deepseek", "google", "dashscope"
    model: str  # e.g., "gpt-4o", "deepseek-chat", "gemini-2.0-flash"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 4000
    timeout: int = 180
    enabled: bool = True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LLMConfig":
        """Create from MongoDB document or dict"""
        # Handle different field names from various sources
        provider = data.get("provider", data.get("name", "openai"))
        model = data.get("model", data.get("model_name", data.get("model_name", "gpt-4o")))
        api_key = data.get("api_key")
        base_url = data.get("base_url", data.get("api_base", data.get("default_base_url")))
        temperature = float(data.get("temperature", 0.7))
        max_tokens = int(data.get("max_tokens", 4000))
        timeout = int(data.get("timeout", 180))
        enabled = bool(data.get("enabled", data.get("is_active", True)))

        return cls(
            provider=provider,
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            enabled=enabled
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for create_llm_by_provider"""
        return {
            "provider": self.provider,
            "model": self.model,
            "api_key": self.api_key,
            "base_url": self.base_url,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout,
        }


# Global cache for configs (simple in-memory cache)
_config_cache: Optional[List[LLMConfig]] = None
_db_connection_params: Optional[Dict[str, str]] = None


def _get_mongodb_connection_params() -> Dict[str, str]:
    """Get MongoDB connection parameters from environment"""
    global _db_connection_params

    if _db_connection_params is not None:
        return _db_connection_params

    # Try standard env vars
    conn_str = os.getenv("MONGODB_CONNECTION_STRING") or os.getenv("MONGO_URI")
    if not conn_str:
        # Build from components
        host = os.getenv("MONGODB_HOST", "localhost")
        port = os.getenv("MONGODB_PORT", "27017")
        username = os.getenv("MONGODB_USERNAME", "")
        password = os.getenv("MONGODB_PASSWORD", "")
        auth_source = os.getenv("MONGODB_AUTH_SOURCE", "admin")
        database = os.getenv("MONGODB_DATABASE", os.getenv("MONGODB_DATABASE_NAME", "tradingagents"))

        if username and password:
            conn_str = f"mongodb://{username}:{password}@{host}:{port}/{database}?authSource={auth_source}"
        else:
            conn_str = f"mongodb://{host}:{port}/{database}"

    _db_connection_params = {
        "connection_string": conn_str,
        "database": os.getenv("MONGODB_DATABASE", os.getenv("MONGODB_DATABASE_NAME", "tradingagents"))
    }

    return _db_connection_params


def _load_configs_from_db() -> List[LLMConfig]:
    """Load LLM configs directly from MongoDB"""
    try:
        params = _get_mongodb_connection_params()
        client = MongoClient(params["connection_string"], serverSelectionTimeoutMS=5000)
        db = client[params["database"]]

        configs = []

        # Try llm_providers collection first (new format)
        try:
            providers = list(db.llm_providers.find({"is_active": True}))
            if providers:
                for p in providers:
                    # Get model - first from direct "model" field, then from extra_config
                    model = p.get("model")
                    if not model:
                        model = p.get("extra_config", {}).get("default_model")
                    if not model:
                        # Try to get from system_settings
                        system_config = db.system_configs.find_one({"is_active": True})
                        if system_config:
                            settings = system_config.get("system_settings", {})
                            model = settings.get("deep_analysis_model", settings.get("quick_analysis_model"))

                    if not model:
                        # Fallback to known models per provider
                        model = _get_default_model_for_provider(p.get("name", ""))

                    # Get base_url - first from direct "base_url" field, then from "default_base_url"
                    base_url = p.get("base_url") or p.get("default_base_url")

                    configs.append(LLMConfig(
                        provider=p.get("name", ""),
                        model=model,
                        api_key=p.get("api_key"),
                        base_url=base_url,
                        enabled=p.get("is_active", True)
                    ))
                    logger.debug(f"Loaded LLM config from llm_providers: {p.get('name')} -> {model}")
        except Exception as e:
            logger.debug(f"llm_providers collection not found or error: {e}")

        # Fallback to system_configs.llm_configs (old format)
        if not configs:
            try:
                system_config = db.system_configs.find_one({"is_active": True})
                if system_config:
                    llm_configs = system_config.get("llm_configs", [])
                    for cfg in llm_configs:
                        if cfg.get("enabled", True):
                            configs.append(LLMConfig.from_dict(cfg))
                            logger.debug(f"Loaded LLM config from system_configs: {cfg.get('provider')} -> {cfg.get('model_name')}")
            except Exception as e:
                logger.debug(f"system_configs collection error: {e}")

        client.close()
        return configs

    except ConnectionFailure:
        logger.warning("Could not connect to MongoDB for LLM config")
        return []
    except PyMongoError as e:
        logger.warning(f"MongoDB error reading LLM config: {e}")
        return []
    except Exception as e:
        logger.warning(f"Error loading LLM config from MongoDB: {e}")
        return []


def _get_default_model_for_provider(provider: str) -> str:
    """Get a sensible default model for each provider"""
    defaults = {
        "openai": "gpt-4o",
        "deepseek": "deepseek-chat",
        "google": "gemini-2.0-flash",
        "dashscope": "qwen-plus",
        "anthropic": "claude-3-5-sonnet-20241022",
        "gemini": "gemini-2.0-flash",
        "zhipu": "glm-4",
        "qwen": "qwen-plus",
        "302ai": "gpt-4o",  # Aggregator default
        "openrouter": "openai/gpt-4o",
    }
    return defaults.get(provider.lower(), "gpt-4o")


def get_llm_config(use_cache: bool = True) -> List[LLMConfig]:
    """
    Get all LLM configurations from MongoDB.

    Args:
        use_cache: Use in-memory cache (default: True). Set False to force reload.

    Returns:
        List of LLMConfig objects. Empty list if no configs found.
    """
    global _config_cache

    if use_cache and _config_cache is not None:
        return _config_cache

    _config_cache = _load_configs_from_db()

    # If no configs from DB, try environment variables as fallback
    if not _config_cache:
        _config_cache = _load_configs_from_env()

    return _config_cache or []


def _load_configs_from_env() -> List[LLMConfig]:
    """Load LLM configs from environment variables as fallback"""
    configs = []

    # Common provider env var patterns
    provider_mappings = [
        ("openai", "OPENAI_API_KEY", "https://api.openai.com/v1", "gpt-4o"),
        ("deepseek", "DEEPSEEK_API_KEY", "https://api.deepseek.com", "deepseek-chat"),
        ("google", "GOOGLE_API_KEY", "https://generativelanguage.googleapis.com/v1beta", "gemini-2.0-flash"),
        ("dashscope", "DASHSCOPE_API_KEY", "https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-plus"),
        ("anthropic", "ANTHROPIC_API_KEY", "https://api.anthropic.com", "claude-3-5-sonnet-20241022"),
    ]

    for provider, api_key_var, default_base_url, default_model in provider_mappings:
        api_key = os.getenv(api_key_var)
        if api_key and not api_key.startswith("your_"):
            # Check for custom base URL
            base_url_var = f"{provider.upper()}_BASE_URL"
            base_url = os.getenv(base_url_var) or default_base_url

            # Check for custom model
            model_var = f"{provider.upper()}_MODEL"
            model = os.getenv(model_var) or default_model

            configs.append(LLMConfig(
                provider=provider,
                model=model,
                api_key=api_key,
                base_url=base_url,
                enabled=True
            ))
            logger.info(f"Loaded LLM config from env: {provider}")

    return configs


def get_active_llm_config() -> Optional[LLMConfig]:
    """
    Get the first active LLM configuration.

    For simple use case with 1-2 providers, just return the first enabled one.

    Returns:
        First active LLMConfig or None
    """
    configs = get_llm_config()
    for cfg in configs:
        if cfg.enabled:
            return cfg
    return None


def get_llm_config_by_provider(provider: str) -> Optional[LLMConfig]:
    """
    Get LLM config for specific provider.

    Args:
        provider: Provider name (e.g., "openai", "deepseek")

    Returns:
        LLMConfig or None
    """
    configs = get_llm_config()
    for cfg in configs:
        if cfg.provider.lower() == provider.lower() and cfg.enabled:
            return cfg
    return None


def invalidate_cache() -> None:
    """Clear the in-memory config cache. Call after updating configs."""
    global _config_cache
    _config_cache = None
    logger.debug("LLM config cache invalidated")


def reload_config() -> List[LLMConfig]:
    """Force reload configs from MongoDB."""
    invalidate_cache()
    return get_llm_config(use_cache=False)


def get_config_for_graph() -> Dict[str, Any]:
    """
    Get a config dict suitable for TradingAgentsGraph.

    This is the simplest way to use LLM configs from MongoDB:

        from tradingagents.config.llm_config import get_config_for_graph
        from tradingagents.graph.trading_graph import TradingAgentsGraph

        config = get_config_for_graph()
        ta = TradingAgentsGraph(config=config)

    Returns:
        Config dict with keys: llm_provider, deep_think_llm, quick_think_llm,
        backend_url, quick_provider, deep_provider, quick_api_key, deep_api_key
    """
    import os
    from tradingagents.default_config import DEFAULT_CONFIG

    # Start with defaults
    config = dict(DEFAULT_CONFIG)

    # Try to load active LLM config from MongoDB
    active_config = get_active_llm_config()

    if active_config:
        # Use MongoDB config
        config.update({
            "llm_provider": active_config.provider,
            "deep_think_llm": active_config.model,
            "quick_think_llm": active_config.model,
            "backend_url": active_config.base_url or "",
            "quick_provider": active_config.provider,
            "deep_provider": active_config.provider,
            "quick_api_key": active_config.api_key,
            "deep_api_key": active_config.api_key,
        })
        logger.info(f"Using LLM config from MongoDB: {active_config.provider}/{active_config.model}")
    else:
        # Fallback to environment variables
        logger.info("No active LLM config in MongoDB, using environment variables")

    return config


__all__ = [
    "LLMConfig",
    "get_llm_config",
    "get_active_llm_config",
    "get_llm_config_by_provider",
    "invalidate_cache",
    "reload_config",
    "get_config_for_graph",
]
