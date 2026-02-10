"""
Simplified LLM Configuration Router

For 1-2 provider use case. Direct MongoDB operations, no config bridge.

Endpoints:
- GET  /api/llm          - Get all LLM configs
- POST /api/llm          - Create/update LLM config
- DELETE /api/llm/{id}   - Delete LLM config
- POST /api/llm/test     - Test LLM config
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from bson import ObjectId

from app.routers.auth_db import get_current_user
from app.core.database import get_mongo_db
from app.utils.timezone import now_tz

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/llm", tags=["LLM Configuration"])


# ===== Request/Response Models =====

class LLMConfigRequest(BaseModel):
    """LLM configuration request"""
    id: Optional[str] = Field(None, description="Config ID (omit for new config)")
    name: str = Field(..., description="Provider name (e.g., deepseek, openai, google)")
    display_name: str = Field(..., description="Display name")
    model: str = Field(..., description="Model name (e.g., deepseek-chat, gpt-4o)")
    api_key: Optional[str] = Field(None, description="API key (omit to keep existing)")
    base_url: Optional[str] = Field(None, description="API base URL")
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=4000, ge=1)
    timeout: int = Field(default=180, ge=1)
    enabled: bool = Field(default=True, description="Is this config active?")


class LLMConfigResponse(BaseModel):
    """LLM configuration response"""
    id: str
    name: str
    display_name: str
    model: str
    api_key: Optional[str] = None  # Truncated in response
    base_url: Optional[str] = None
    temperature: float
    max_tokens: int
    timeout: int
    enabled: bool
    created_at: str
    updated_at: str


class LLMTestRequest(BaseModel):
    """Test LLM configuration by ID"""
    config_id: str = Field(..., description="Config ID to test (will retrieve full API key from DB)")


# ===== Helper Functions =====

def _truncate_api_key(api_key: Optional[str]) -> Optional[str]:
    """Truncate API key for display"""
    if not api_key or len(api_key) < 8:
        return api_key
    return api_key[:4] + "..." + api_key[-4:]


def _doc_to_response(doc: dict) -> LLMConfigResponse:
    """Convert MongoDB doc to response"""
    # Convert datetime objects to ISO strings
    created_at = doc.get("created_at")
    if created_at and hasattr(created_at, "isoformat"):
        created_at = created_at.isoformat()
    elif not created_at:
        created_at = now_tz().isoformat()

    updated_at = doc.get("updated_at")
    if updated_at and hasattr(updated_at, "isoformat"):
        updated_at = updated_at.isoformat()
    elif not updated_at:
        updated_at = now_tz().isoformat()

    return LLMConfigResponse(
        id=str(doc.get("_id")),
        name=doc.get("name", ""),
        display_name=doc.get("display_name", ""),
        model=doc.get("model", ""),
        api_key=_truncate_api_key(doc.get("api_key")),
        base_url=doc.get("base_url"),
        temperature=doc.get("temperature", 0.7),
        max_tokens=doc.get("max_tokens", 4000),
        timeout=doc.get("timeout", 180),
        enabled=doc.get("enabled", True),
        created_at=created_at,
        updated_at=updated_at
    )


# ===== Endpoints =====

@router.get("", response_model=List[LLMConfigResponse])
async def get_llm_configs(current_user: dict = Depends(get_current_user)):
    """Get all LLM configurations"""
    db = get_mongo_db()
    configs = []
    async for doc in db.llm_providers.find().sort("name", 1):
        configs.append(_doc_to_response(doc))
    return configs


@router.post("", response_model=LLMConfigResponse)
async def upsert_llm_config(
    config: LLMConfigRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create or update LLM configuration"""
    db = get_mongo_db()
    now = now_tz()

    if config.id:
        # Update existing
        oid = ObjectId(config.id)
        existing = await db.llm_providers.find_one({"_id": oid})
        if not existing:
            raise HTTPException(status_code=404, detail="Config not found")

        update_doc = {
            "name": config.name,
            "display_name": config.display_name,
            "model": config.model,
            "base_url": config.base_url,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "timeout": config.timeout,
            "enabled": config.enabled,
            "updated_at": now.isoformat()
        }

        # Only update API key if provided (non-empty)
        if config.api_key and config.api_key.strip():
            update_doc["api_key"] = config.api_key.strip()

        await db.llm_providers.update_one({"_id": oid}, {"$set": update_doc})
        doc = await db.llm_providers.find_one({"_id": oid})
    else:
        # Create new
        doc = {
            "name": config.name,
            "display_name": config.display_name,
            "model": config.model,
            "api_key": config.api_key or None,
            "base_url": config.base_url,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "timeout": config.timeout,
            "enabled": config.enabled,
            "is_active": config.enabled,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        result = await db.llm_providers.insert_one(doc)
        doc["_id"] = result.inserted_id

    # Invalidate cache in core framework
    try:
        from tradingagents.config.llm_config import invalidate_cache
        invalidate_cache()
        logger.info("LLM config cache invalidated after update")
    except Exception as e:
        logger.warning(f"Failed to invalidate cache: {e}")

    return _doc_to_response(doc)


@router.delete("/{config_id}", response_model=dict)
async def delete_llm_config(
    config_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete LLM configuration"""
    db = get_mongo_db()
    oid = ObjectId(config_id)
    result = await db.llm_providers.delete_one({"_id": oid})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Config not found")

    # Invalidate cache
    try:
        from tradingagents.config.llm_config import invalidate_cache
        invalidate_cache()
    except Exception:
        pass

    return {"success": True, "message": "Config deleted"}


@router.post("/test", response_model=dict)
async def test_llm_config(
    config: LLMTestRequest,
    current_user: dict = Depends(get_current_user)
):
    """Test LLM configuration using stored API key from MongoDB"""
    db = get_mongo_db()

    try:
        # Retrieve config from MongoDB
        oid = ObjectId(config.config_id)
        doc = await db.llm_providers.find_one({"_id": oid})

        if not doc:
            return {
                "success": False,
                "message": "Configuration not found"
            }

        # Get the full API key from database
        api_key = doc.get("api_key")
        if not api_key:
            return {
                "success": False,
                "message": "No API key configured. Please add an API key first."
            }

        # Import here to avoid circular dependencies
        from tradingagents.graph.trading_graph import create_llm_by_provider

        # Get config values
        provider = doc.get("name", "")
        model = doc.get("model", "")
        base_url = doc.get("base_url", doc.get("default_base_url", ""))

        # Create LLM instance with full API key from database
        llm = create_llm_by_provider(
            provider=provider,
            model=model,
            backend_url=base_url or "",
            temperature=0.7,
            max_tokens=100,
            timeout=30,
            api_key=api_key
        )

        # Test with a simple invoke
        response = await llm.ainvoke("Hi")
        result = {
            "success": True,
            "message": "LLM connection successful",
            "response_preview": str(response.content)[:100]
        }
        return result

    except Exception as e:
        logger.error(f"LLM test failed: {e}")
        return {
            "success": False,
            "message": str(e)
        }
