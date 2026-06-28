from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import time

from .config import settings

from sqlmodel import SQLModel, Session, create_engine, select
from .models import URLMapping  # Import model so SQLModel registers it

# ------------------------------
# Database setup
# ------------------------------
engine = create_engine(settings.database_url, echo=False)


def get_db():
    with Session(engine) as session:
        yield session


def init_db():
    """Create tables on startup."""
    SQLModel.metadata.create_all(engine)


# ------------------------------
# Import routers (they rely on `get_session` and `BASE_URL`)
# ------------------------------
from .routers.shortener import shortener_router
from .routers.analytics import analytics_router

# ------------------------------
# FastAPI application
# ------------------------------
app = FastAPI(title="Lean URL Shortener with Analytics")

# Simple in-memory rate limiter for backend safety
RATE_LIMIT_LIMIT = 5 # requests
RATE_LIMIT_WINDOW = 60 # seconds
ip_requests = {}

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Only rate limit url shortening creations for security
    if request.url.path == "/shorten" and request.method == "POST":
        client_ip = request.client.host if request.client else "127.0.0.1"
        now = time.time()
        # Filter request timestamps older than window
        ip_requests[client_ip] = [t for t in ip_requests.get(client_ip, []) if now - t < RATE_LIMIT_WINDOW]
        
        if len(ip_requests[client_ip]) >= RATE_LIMIT_LIMIT:
            return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Try again in a minute."})
            
        ip_requests[client_ip].append(now)
        
    return await call_next(request)


@app.on_event("startup")
async def on_startup():
    init_db()


# Register routers
app.include_router(shortener_router)
app.include_router(analytics_router)