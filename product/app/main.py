from fastapi import FastAPI
from pydantic import BaseModel

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


@app.on_event("startup")
async def on_startup():
    init_db()


# Register routers
app.include_router(shortener_router)
app.include_router(analytics_router)