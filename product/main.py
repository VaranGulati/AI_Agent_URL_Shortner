from fastapi import FastAPI

# Import the API router defined elsewhere in the project
from router import router  # adjust the import path if your router is in a different module

# Import the SQLAlchemy Base and engine to handle DB table creation
from database import Base, engine

app = FastAPI()

# Register the router with the FastAPI application
app.include_router(router)


@app.on_event("startup")
def on_startup() -> None:
    """
    FastAPI startup event handler.
    Creates all database tables defined in the SQLAlchemy models if they do not exist.
    """
    Base.metadata.create_all(bind=engine)