# Simplified LLM configuration - reads directly from MongoDB
# No config bridge, no environment variable syncing needed
from tradingagents.config.llm_config import get_config_for_graph
from tradingagents.graph.trading_graph import TradingAgentsGraph

# 导入日志模块
from tradingagents.utils.logging_manager import get_logger
logger = get_logger('default')

# Get config from MongoDB (falls back to env vars if MongoDB unavailable)
config = get_config_for_graph()

# Optional: Override specific settings
config["max_debate_rounds"] = 1
config["online_tools"] = True

# Initialize with config
ta = TradingAgentsGraph(debug=True, config=config)

# forward propagate
_, decision = ta.propagate("NVDA", "2024-05-10")
print(decision)

# Memorize mistakes and reflect
# ta.reflect_and_remember(1000) # parameter is the position returns
