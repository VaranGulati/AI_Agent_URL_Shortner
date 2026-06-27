# FastAPI URL Shortener

A tiny URL shortener built with FastAPI and SQLite.

## Endpoints
- **POST /shorten** – body `{ "url": "https://example.com" }` → returns `{ "short_code": "a1B2c3", "short_url": "/a1B2c3" }`
- **GET /{code}** – redirects to the original URL.

## Run locally
bash
pip install -r requirements.txt
uvicorn app.main:app --reload


## Docker
bash
docker build -t url-shortener .
docker run -p 8000:8000 url-shortener