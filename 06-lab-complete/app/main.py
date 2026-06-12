"""
Production AI Agent — Kết hợp tất cả Day 12 concepts & Day 6 Triage Logic
"""
import os
import time
import signal
import logging
import json
from datetime import datetime, timezone
from collections import defaultdict, deque
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Security, Depends, Request, Response
from fastapi.security.api_key import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
import redis

from app.config import settings
from app.triage import triage

# ─────────────────────────────────────────────────────────
# Logging — JSON structured
# ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
_is_ready = False
_request_count = 0
_error_count = 0

# Initialize Redis client
redis_client = None
if settings.redis_url:
    try:
        redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        logger.info(json.dumps({"event": "redis_connected", "url": settings.redis_url}))
    except Exception as e:
        logger.error(json.dumps({"event": "redis_connection_failed", "error": str(e)}))

# ─────────────────────────────────────────────────────────
# Rate Limiter (Redis sliding window / In-memory fallback)
# ─────────────────────────────────────────────────────────
_rate_windows: dict[str, deque] = defaultdict(deque)

def check_rate_limit(key: str):
    if not redis_client:
        # Fallback to in-memory deque
        now = time.time()
        window = _rate_windows[key]
        while window and window[0] < now - 60:
            window.popleft()
        if len(window) >= settings.rate_limit_per_minute:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {settings.rate_limit_per_minute} req/min",
                headers={"Retry-After": "60"},
            )
        window.append(now)
        return

    # Redis sliding window
    now = time.time()
    redis_key = f"rate_limit:{key}"
    try:
        pipeline = redis_client.pipeline()
        pipeline.zremrangebyscore(redis_key, 0, now - 60)
        pipeline.zcard(redis_key)
        pipeline.zadd(redis_key, {str(now): now})
        pipeline.expire(redis_key, 60)
        _, card, _, _ = pipeline.execute()
        
        if card > settings.rate_limit_per_minute:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded: {settings.rate_limit_per_minute} req/min",
                headers={"Retry-After": "60"},
            )
    except redis.RedisError as e:
        # Fail open or log error? In production, we log and proceed to not block user on Redis crash
        logger.error(json.dumps({"event": "redis_rate_limit_error", "error": str(e)}))

# ─────────────────────────────────────────────────────────
# Cost Guard (Redis monthly budget / In-memory daily fallback)
# ─────────────────────────────────────────────────────────
_daily_cost = 0.0
_cost_reset_day = time.strftime("%Y-%m-%d")

def check_and_record_cost(user_id: str, estimated_cost: float):
    if not redis_client:
        global _daily_cost, _cost_reset_day
        today = time.strftime("%Y-%m-%d")
        if today != _cost_reset_day:
            _daily_cost = 0.0
            _cost_reset_day = today
        if _daily_cost + estimated_cost > settings.daily_budget_usd:
            raise HTTPException(503, "Daily budget exhausted. Try tomorrow.")
        _daily_cost += estimated_cost
        return

    # Redis monthly budget check ($10/month per user as per CODE_LAB.md)
    month_key = datetime.now(timezone.utc).strftime("%Y-%m")
    key = f"budget:{user_id}:{month_key}"
    try:
        current = float(redis_client.get(key) or 0.0)
        if current + estimated_cost > 10.0:
            raise HTTPException(402, "Monthly budget exhausted.")
        
        redis_client.incrbyfloat(key, estimated_cost)
        redis_client.expire(key, 32 * 24 * 3600)  # 32 days
    except redis.RedisError as e:
        logger.error(json.dumps({"event": "redis_cost_guard_error", "error": str(e)}))

# ─────────────────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────────────────
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    if not api_key or api_key != settings.agent_api_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key. Include header: X-API-Key: <key>",
        )
    return api_key

# ─────────────────────────────────────────────────────────
# Stateless Session History helpers
# ─────────────────────────────────────────────────────────
def get_session_history(session_id: str) -> list[dict]:
    if not redis_client or not session_id:
        return []
    history_key = f"history:{session_id}"
    try:
        raw_history = redis_client.lrange(history_key, 0, -1)
        history = []
        for item in raw_history:
            try:
                history.append(json.loads(item))
            except Exception:
                pass
        return history
    except Exception as e:
        logger.error(json.dumps({"event": "get_history_error", "session_id": session_id, "error": str(e)}))
        return []

def save_session_history(session_id: str, role: str, content: str):
    if not redis_client or not session_id:
        return
    history_key = f"history:{session_id}"
    try:
        redis_client.rpush(history_key, json.dumps({"role": role, "content": content}))
        redis_client.ltrim(history_key, -20, -1)  # Keep last 20 messages
        redis_client.expire(history_key, 24 * 3600)  # Expire in 24 hours
    except Exception as e:
        logger.error(json.dumps({"event": "save_history_error", "session_id": session_id, "error": str(e)}))

# ─────────────────────────────────────────────────────────
# Lifespan
# ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready
    logger.info(json.dumps({
        "event": "startup",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }))
    time.sleep(0.1)  # simulate init
    _is_ready = True
    logger.info(json.dumps({"event": "ready"}))

    yield

    _is_ready = False
    logger.info(json.dumps({"event": "shutdown"}))

# ─────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

@app.middleware("http")
async def request_middleware(request: Request, call_next):
    global _request_count, _error_count
    start = time.time()
    _request_count += 1
    try:
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        if "server" in response.headers:
            del response.headers["server"]
        duration = round((time.time() - start) * 1000, 1)
        logger.info(json.dumps({
            "event": "request",
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "ms": duration,
        }))
        return response
    except Exception as e:
        _error_count += 1
        raise

# ─────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────
class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000,
                          description="Your question for the agent")
    session_id: str | None = Field(default=None, description="Optional session/conversation ID")

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[dict] = Field(default_factory=list)
    session_id: str | None = Field(default=None)

class ReportRequest(BaseModel):
    user_message: str
    bot_reply: str
    route: str = ""
    model: str = ""
    description: str = ""

# ─────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────

@app.get("/", tags=["Info"])
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "endpoints": {
            "ask": "POST /ask (requires X-API-Key)",
            "chat": "POST /chat (requires X-API-Key)",
            "health": "GET /health",
            "ready": "GET /ready",
        },
    }

@app.post("/ask", tags=["Agent"])
async def ask_agent(
    body: AskRequest,
    request: Request,
    _key: str = Depends(verify_api_key),
):
    """
    Send a question to the AI agent.
    """
    # Rate limiting
    check_rate_limit(_key[:8])

    # Cost checking (approximate cost: $0.001 per request)
    check_and_record_cost(_key[:8], 0.001)

    logger.info(json.dumps({
        "event": "ask_call",
        "q_len": len(body.question),
        "client": str(request.client.host) if request.client else "unknown",
    }))

    # Get history from Redis if session_id is provided
    history = get_session_history(body.session_id) if body.session_id else []

    # Run triage orchestrator
    result = await triage(body.question, history)

    # Save to Redis history if session_id is provided
    if body.session_id:
        save_session_history(body.session_id, "user", body.question)
        save_session_history(body.session_id, "assistant", result.get("reply", ""))

    return result

@app.post("/chat", tags=["Agent"])
async def chat_agent(
    body: ChatRequest,
    request: Request,
    _key: str = Depends(verify_api_key),
):
    """
    Day 6 compatible chat endpoint with full production compliance.
    """
    check_rate_limit(_key[:8])
    check_and_record_cost(_key[:8], 0.001)

    logger.info(json.dumps({
        "event": "chat_call",
        "msg_len": len(body.message),
        "client": str(request.client.host) if request.client else "unknown",
    }))

    # History resolution: use passed history or load from redis
    history = body.history
    if not history and body.session_id:
        history = get_session_history(body.session_id)

    # Run triage orchestrator
    result = await triage(body.message, history)

    # Save to Redis history if session_id is provided
    if body.session_id:
        save_session_history(body.session_id, "user", body.message)
        save_session_history(body.session_id, "assistant", result.get("reply", ""))

    return result

@app.post("/report", tags=["Operations"])
async def report(req: ReportRequest):
    """Log user-flagged bot replies in structured JSON logs."""
    logger.info(json.dumps({
        "event": "user_report",
        "route": req.route,
        "model": req.model,
        "user_message": req.user_message[:500],
        "bot_reply": req.bot_reply[:500],
        "description": req.description[:300]
    }))
    return {"status": "ok"}

@app.get("/health", tags=["Operations"])
def health():
    """Liveness probe. Platform restarts container if this fails."""
    status = "ok"
    checks = {
        "llm": "openrouter",
        "redis": "connected" if redis_client else "disconnected"
    }
    return {
        "status": status,
        "version": settings.app_version,
        "environment": settings.environment,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@app.get("/ready", tags=["Operations"])
def ready():
    """Readiness probe. Load balancer stops routing here if not ready."""
    if not _is_ready:
        raise HTTPException(503, "Not ready")
    if redis_client:
        try:
            redis_client.ping()
        except Exception as e:
            raise HTTPException(503, f"Redis connection failed: {str(e)}")
    return {"ready": True}

@app.get("/metrics", tags=["Operations"])
def metrics(_key: str = Depends(verify_api_key)):
    """Basic metrics (protected)."""
    return {
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "error_count": _error_count,
        "redis_connected": redis_client is not None,
    }

# ─────────────────────────────────────────────────────────
# Graceful Shutdown
# ─────────────────────────────────────────────────────────
def _handle_signal(signum, _frame):
    logger.info(json.dumps({"event": "signal", "signum": signum}))

signal.signal(signal.SIGTERM, _handle_signal)

if __name__ == "__main__":
    logger.info(f"Starting {settings.app_name} on {settings.host}:{settings.port}")
    logger.info(f"API Key: {settings.agent_api_key[:4]}****")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_graceful_shutdown=30,
    )
