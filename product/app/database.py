from sqlmodel import SQLModel, create_engine, Session
from .config import settings

# Create the engine using the database URL from the Settings instance
engine = create_engine(
    settings.database_url,
    echo=False,
    connect_args={"check_same_thread": False},  # Required for SQLite with multiple threads
)


def get_session():
    """
    FastAPI dependency that provides a SQLModel Session per request.
    It uses a context manager to ensure the session is properly closed.
    """
    with Session(engine) as session:
        yield session


def init_db() -> None:
    """
    Helper that creates all tables defined by SQLModel models.
    Typically called during application startup.
    """
    SQLModel.metadata.create_all(engine)