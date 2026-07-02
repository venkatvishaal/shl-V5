"""FastAPI endpoint services with catalog-backed readiness."""

import logging

from src.api.schemas import ChatRequest, ChatResponse, HealthResponse, RecommendationItem
from src.agent.conversation_manager import ConversationManager
from src.config import settings
from src.retrieval.catalog import CatalogManager

logger = logging.getLogger(__name__)

_catalog_manager: CatalogManager | None = None
_conversation_manager: ConversationManager | None = None


def get_catalog_manager() -> CatalogManager:
    global _catalog_manager
    if _catalog_manager is None:
        _catalog_manager = CatalogManager(settings.catalog_path)
    return _catalog_manager


def get_conversation_manager() -> ConversationManager:
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager(get_catalog_manager())
    return _conversation_manager


async def health_check() -> HealthResponse:
    """Return ok only when the catalog can safely serve recommendations."""
    catalog = get_catalog_manager()
    report = catalog.validate_catalog()
    if not catalog.catalog or not report["validation_passed"]:
        raise RuntimeError("Catalog is not ready")
    return HealthResponse(status="ok")


async def chat_endpoint(request: ChatRequest) -> ChatResponse:
    reply, recommendations, done = await get_conversation_manager().process(
        request.messages
    )
    items = [
        RecommendationItem(
            name=item["name"],
            url=item["url"],
            test_type=item["test_type"],
        )
        for item in recommendations[:10]
    ]
    return ChatResponse(
        reply=reply,
        recommendations=items,
        end_of_conversation=done,
    )
