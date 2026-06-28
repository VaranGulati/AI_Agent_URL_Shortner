# dependencies.py
"""Convenient re-exports for FastAPI dependencies."""

from .database import get_session, init_db, engine

__all__ = ["get_session", "init_db", "engine"]