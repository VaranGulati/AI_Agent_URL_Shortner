from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl, ValidationError
from sqlmodel import Session
from typing import Dict

# Local imports (adjust the import paths according to your project structure)
from ..dependencies import get_session
from ..services import create_short_url, resolve_short_code
from ..config import settings

shortener_router = APIRouter()


class ShortenRequest(BaseModel):
    original_url: HttpUrl


class ShortenResponse(BaseModel):
    short_code: str
    short_url: str


@shortener_router.post("/shorten", response_model=ShortenResponse)
def shorten(
    payload: ShortenRequest,
    session: Session = Depends(get_session),
) -> ShortenResponse:
    """
    Create a new short URL.

    - **payload**: JSON body containing ``original_url`` (must be a valid URL).
    - **returns**: Fully qualified short URL (e.g., ``http://localhost:8000/abc123``).
    """
    try:
        original = payload.original_url
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    mapping = create_short_url(str(original), session)
    short_url = f"{settings.base_url.rstrip('/')}/{mapping.short_code}"
    return ShortenResponse(short_code=mapping.short_code, short_url=short_url)


@shortener_router.get("/{code}")
def redirect(
    code: str,
    session: Session = Depends(get_session),
) -> RedirectResponse:
    """
    Resolve a short code and redirect to the original URL.

    - **code**: The short code part of the URL.
    - **returns**: 307 Temporary Redirect to the original URL if found,
      otherwise a 404 error.
    """
    mapping = resolve_short_code(code, session)
    if not mapping:
        raise HTTPException(status_code=404, detail="Short URL not found")
    return RedirectResponse(url=mapping.original_url, status_code=307)