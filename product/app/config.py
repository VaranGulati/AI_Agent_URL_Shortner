import os

class Settings:
    """Centralised configuration for the URL shortener service."""
    def __init__(self):
        self.base_url = os.environ.get("BASE_URL", "http://localhost:8000/")
        self.code_length = int(os.environ.get("CODE_LENGTH", "6"))
        self.database_url = os.environ.get("DATABASE_URL", "sqlite:///./shortener.db")

# Module‑level singleton used throughout the application
settings = Settings()