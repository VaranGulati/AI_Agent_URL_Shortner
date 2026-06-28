import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from app.main import app
from app.database import get_session
from app.models import URLMapping

import os

# Setup file-based SQLite database for testing to avoid in-memory SQLite connection persistence issues
DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

@pytest.fixture(name="session")
def session_fixture():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)
    # Clean up test database file
    if os.path.exists("./test.db"):
        try:
            os.remove("./test.db")
        except PermissionError:
            pass

@pytest.fixture(name="client")
def client_fixture(session):
    def get_session_override():
        return session
    
    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

def test_shorten_url(client):
    response = client.post("/shorten", json={"original_url": "https://www.google.com"})
    assert response.status_code == 200
    data = response.json()
    assert "short_code" in data
    assert "short_url" in data
    assert "/analytics/" not in data["short_url"]

def test_redirect(client, session):
    # Setup mapping directly in DB
    mapping = URLMapping(original_url="https://www.github.com", short_code="git")
    session.add(mapping)
    session.commit()
    
    # Trigger redirect (disable auto redirects to check status code)
    response = client.get("/git", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "https://www.github.com"
    
    # Check that clicks incremented
    session.refresh(mapping)
    assert mapping.access_count == 1

def test_analytics(client, session):
    # Setup mapping directly in DB
    mapping = URLMapping(original_url="https://www.wikipedia.org", short_code="wiki", access_count=5)
    session.add(mapping)
    session.commit()
    
    # Request stats
    response = client.get("/analytics/wiki")
    assert response.status_code == 200
    data = response.json()
    assert data["original_url"] == "https://www.wikipedia.org"
    assert data["access_count"] == 5
    assert data["short_code"] == "wiki"

def test_analytics_not_found(client):
    response = client.get("/analytics/missing")
    assert response.status_code == 404