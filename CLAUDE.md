# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TradingAgents-CN is a Chinese-enhanced multi-agent stock analysis framework. The project uses a hybrid licensing model:
- **Open-source (Apache 2.0)**: `tradingagents/` core framework, agents, LLM adapters, data providers
- **Proprietary**: `app/` (FastAPI backend), `frontend/` (Vue 3 frontend) - require commercial license

The system orchestrates multiple AI agents to analyze stocks through structured debate, supporting A-shares, Hong Kong, and US markets.

## Development Commands

### Environment Setup
```bash
# Create virtual environment (Python 3.10+)
python3.10 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .

# Copy environment template and configure
cp .env.example .env
# Edit .env with your API keys and database settings
```

### Running Tests
```bash
# Run all tests (excludes integration tests by default)
pytest

# Run specific test file
pytest tests/test_analysis.py

# Run with verbose output
pytest -v

# Include integration tests
pytest -m integration
```

### Docker Development
```bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Running the Analysis (CLI)
```bash
# Direct Python execution
python main.py

# Using the CLI
python -m cli.main analyze NVDA
```

## Architecture Overview

### Multi-Agent System

The core framework uses a hierarchical agent architecture:

1. **Analysts** (Information Gatherers)
   - `FundamentalsAnalyst`: Financial statements, valuation metrics (PE, PB, ROE)
   - `MarketAnalyst`: Technical analysis, price trends, indicators
   - `NewsAnalyst`: News sentiment and event impact
   - `ChinaMarketAnalyst`: A-share specific analysis
   - `SocialMediaAnalyst`: Reddit sentiment

2. **Researchers** (Debate Opponents)
   - `BullResearcher`: Generates bullish thesis
   - `BearResearcher`: Generates bearish thesis

3. **Risk Managers** (Debate Moderators)
   - `AggressiveDebator`, `ConservativeDebator`, `NeutralDebator`: Provide balanced perspectives

4. **Managers** (Decision Makers)
   - `ResearchManager`: Synthesizes all analyses and debates
   - `RiskManager`: Evaluates risk profiles

5. **Trader** (Action Executor)
   - `Trader`: Generates trading recommendations

### Analysis Flow

```
Stock Request → Data Collection → Analysts → Researchers → Debate → Risk Managers → Research Manager → Decision → Memory Learning
```

The workflow is orchestrated through `TradingAgentsGraph` in `tradingagents/graph/trading_graph.py` using LangGraph for conditional logic and state management.

### Data Provider Architecture

The system uses an **adapter pattern** with **priority-based fallback**:

**Data Sources** (in `tradingagents/dataflows/providers/`):
- **China**: Tushare (primary), AKShare (alternative), BaoStock (backup)
- **US**: yFinance (free), Alpha Vantage (fundamentals), FinnHub (news)
- **HK**: Specialized HK stock providers

**Key Classes**:
- `DataSourceManager` (`data_source_manager.py`): Manages source selection and priority
- `BaseStockDataProvider` (`providers/base_provider.py`): Abstract interface for all providers
- All providers implement `get_stock_basic_info()`, `get_stock_quotes()`, `get_historical_data()`, etc.

The system automatically falls back to alternative sources if the primary fails, with priority stored in MongoDB.

### LLM Integration

LLM adapters (`tradingagents/llm_adapters/`) support multiple providers through a unified OpenAI-compatible interface:
- **Google**: `ChatGoogleOpenAI` - Gemini models with custom base URL support
- **DashScope**: `ChatDashScopeOpenAI` - Alibaba Qwen models
- **DeepSeek**: `ChatDeepSeek` - Native DeepSeek API integration
- **Generic OpenAI-compatible**: `create_openai_compatible_llm()` - For any OpenAI-compatible endpoint

Configuration flow: Environment variables → Database settings → Runtime override

### Caching System

Multi-layer caching in `tradingagents/dataflows/cache/`:
- **Integrated cache**: Auto-selects MongoDB → Redis → File
- **MongoDB adapter**: `mongodb_cache_adapter.py`
- **File cache**: `file_cache.py`
- **App adapter**: `app_adapter.py` for FastAPI backend integration

Enable with `TA_USE_APP_CACHE=true` or `TA_CACHE_STRATEGY=integrated`.

### Configuration System

- **Environment**: `.env` file (see `.env.example`)
- **Database**: MongoDB-stored LLM provider configs, data source priorities
- **Runtime**: `tradingagents/config/runtime_settings.py`

Key configuration functions:
- `get_llm_config()`: Retrieves LLM settings from DB with environment fallback
- `get_data_source_priority()`: Gets data source priority order from DB

### News Analysis

The unified news tool (`tradingagents/tools/unified_news_tool.py`):
- Auto-detects market (A-share/US/HK) based on stock symbol
- Aggregates from multiple sources (Google News, Chinese Finance sites, Reddit)
- Supports sentiment analysis and event impact assessment
- Integrated through `enhanced_news_retriever.py` and `enhanced_news_filter.py`

## Important Implementation Notes

### Event Loop Handling
The project uses `asyncio` extensively. When calling async code from sync contexts:
- Use `asyncio.run()` for one-off calls
- Use dedicated event loop in background threads
- The `concurrent-log-handler` package is used for Windows-friendly logging

### Data Source Priority
Default priority is stored in MongoDB `system_config` collection. Modify via:
- Web UI: Settings → Data Source Management
- Direct DB update to `system_config` collection
- Environment: `DEFAULT_CHINA_DATA_SOURCE=akshare`

### Adding New Agents
1. Create agent class in `tradingagents/agents/` appropriate subdirectory
2. Define agent's system prompt and tools in `__init__`
3. Add to agent graph in `tradingagents/graph/setup.py`
4. Update state transitions in `tradingagents/graph/conditional_logic.py`

### Adding New Data Providers
1. Create provider class inheriting from `BaseStockDataProvider`
2. Implement all abstract methods
3. Register in `ChinaDataSource` or `USDataSource` enum
4. Add provider initialization in data source manager

### Test Organization
- `tests/conftest.py`: Adds project root to `sys.path`
- `tests/pytest.ini`: Configures pytest to skip integration tests by default
- Integration tests should be marked with `@pytest.mark.integration`

## Key Files to Understand

| File | Purpose |
|------|---------|
| `tradingagents/graph/trading_graph.py` | Main graph orchestration and LLM creation |
| `tradingagents/dataflows/data_source_manager.py` | Data source selection and fallback logic |
| `tradingagents/config/runtime_settings.py` | Runtime configuration retrieval |
| `tradingagents/agents/utils/agent_states.py` | State definitions for LangGraph |
| `tradingagents/default_config.py` | Default analysis configuration |
| `.env.example` | All available environment variables |
