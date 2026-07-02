"""
SHL Assessment Recommender — FastAPI application entry point.

Endpoints
---------
GET  /         Root info (service name, version, available routes)
GET  /health   Liveness/readiness probe → {"status": "ok"}
POST /chat     Multi-turn conversation endpoint
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.config import settings
from src.api.schemas import ChatRequest, ChatResponse, HealthResponse
from src.api.endpoints import health_check, chat_endpoint
from src.utils.logger import setup_logger

# ── Logging ───────────────────────────────────────────────────────────────────

setup_logger(settings.log_level)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run code on startup / shutdown."""
    logger.info("SHL Recommender starting up")
    # Warm up catalog + conversation manager so the first request isn't slow
    from src.api.endpoints import get_conversation_manager
    try:
        get_conversation_manager()
        logger.info("Catalog and conversation manager initialised")
    except Exception as e:
        logger.error(f"Warm-up failed (will retry on first request): {e}")
    yield
    logger.info("SHL Recommender shutting down")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="SHL Assessment Recommender",
    description=(
        "Conversational AI agent that recommends SHL assessments "
        "through multi-turn dialogue."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# Allow all origins for the demo deployment (tighten for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global exception handler ──────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/", summary="Service information")
async def root():
    """Return basic service metadata."""
    return {
        "service": "SHL Assessment Recommender",
        "version": "1.0.0",
        "endpoints": ["/health", "/chat"],
    }


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health / readiness check",
)
async def health():
    """Liveness probe — returns 200 {"status": "ok"} when the service is ready."""
    return await health_check()


@app.post(
    "/chat",
    response_model=ChatResponse,
    summary="Multi-turn assessment recommendation chat",
)
async def chat(request: ChatRequest):
    """
    Accept a conversation history and return the agent's next reply,
    an optional list of 1-10 SHL assessment recommendations, and a flag
    indicating whether the conversation is complete.
    """
    try:
        return await chat_endpoint(request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unhandled error in /chat: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ── Dev runner ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=settings.service_env == "development",
        log_level=settings.log_level.lower(),
    )