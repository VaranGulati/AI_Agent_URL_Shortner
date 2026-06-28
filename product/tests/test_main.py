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

def test_ssrf_validation(client):
    # Try shortening localhost and local private IPs (SSRF protection)
    response = client.post("/shorten", json={"original_url": "http://127.0.0.1"})
    assert response.status_code == 400
    assert "unsafe local space" in response.json()["detail"]

    response = client.post("/shorten", json={"original_url": "http://localhost"})
    assert response.status_code == 400

def test_update_url(client, session):
    # Setup mapping directly in DB
    mapping = URLMapping(original_url="https://www.google.com", short_code="g")
    session.add(mapping)
    session.commit()

    # Dynamically update redirection URL
    response = client.patch("/g", json={"new_url": "https://www.wikipedia.org"})
    assert response.status_code == 200
    assert response.json()["target_url"] == "https://www.wikipedia.org/"

    # Verify that requesting g now redirects to wikipedia
    response2 = client.get("/g", follow_redirects=False)
    assert response2.status_code == 307
    assert response2.headers["location"] == "https://www.wikipedia.org/"

def test_rate_limiter(client):
    # Clean up rate limits history
    from app.main import ip_requests
    ip_requests.clear()

    # Send 5 requests (Limit is 5)
    for _ in range(5):
        response = client.post("/shorten", json={"original_url": "https://www.google.com"})
        assert response.status_code == 200

    # 6th request must trigger rate limiter
    response = client.post("/shorten", json={"original_url": "https://www.google.com"})
    assert response.status_code == 429
    assert "Rate limit exceeded" in response.json()["detail"]