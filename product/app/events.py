# main.py
from fastapi import FastAPI

# Import the database utilities
from database import init_db, get_session, engine

# Import routers
from shortener_router import shortener_router
from analytics_router import analytics_router

app = FastAPI(title="Lean URL Shortener with Analytics")

# Wire routers
app.include_router(shortener_router)
app.include_router(analytics_router)

# Startup event – ensure SQLite schema exists before handling any request
@app.on_event("startup")
def on_startup() -> None:
    init_db()