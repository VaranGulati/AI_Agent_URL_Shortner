# app/__init__.py

# (empty file)


# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///./shortener.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()


# app/models.py
from sqlalchemy import Column, Integer, String
from .database import Base


class URLMap(Base):
    __tablename__ = "url_maps"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, index=True, nullable=False)
    target = Column(String, nullable=False)


# app/schemas.py
from pydantic import BaseModel, HttpUrl


class CreateRequest(BaseModel):
    url: HttpUrl


class CreateResponse(BaseModel):
    short_code: str
    short_url: str


# app/main.py
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
import string
import random

from .database import SessionLocal, engine, Base
from .schemas import CreateRequest, CreateResponse

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="FastAPI URL Shortener")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def generate_code(length: int = 6) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


@app.post("/shorten", response_model=CreateResponse)
def create_short_url(payload: CreateRequest, db: Session = Depends(get_db)):
    # Ensure the generated code is unique
    for _ in range(10):
        code = generate_code()
        exists = db.execute(select(URLMap).where(URLMap.code == code)).first()
        if not exists:
            break
    else:
        raise HTTPException(status_code=500, detail="Could not generate a unique short code")

    mapping = URLMap(code=code, target=str(payload.url))
    db.add(mapping)
    db.commit()
    db.refresh(mapping)

    short_path = app.url_path_for("redirect", code=mapping.code)
    return CreateResponse(short_code=mapping.code, short_url=short_path)


@app.get("/{code}", name="redirect")
def redirect(code: str, db: Session = Depends(get_db)):
    result = db.execute(select(URLMap).where(URLMap.code == code)).scalar_one_or_none()
    if not result:
        raise HTTPException(status_code=404, detail="Short URL not found")
    return RedirectResponse(url=result.target)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)