from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, HttpUrl, ValidationError
from sqlmodel import Session, select
from typing import Dict
from urllib.parse import urlparse
import socket

# Local imports (adjust the import paths according to your project structure)
from ..dependencies import get_session
from ..services import create_short_url, resolve_short_code
from ..config import settings
from ..models import URLMapping

shortener_router = APIRouter()


class ShortenRequest(BaseModel):
    original_url: HttpUrl


class ShortenResponse(BaseModel):
    short_code: str
    short_url: str


class UpdateRequest(BaseModel):
    new_url: HttpUrl


def is_safe_url(url: str) -> bool:
    """SSRF & Open-Redirect safety check: Enforces valid HTTP/S schemas and blocks private ranges."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
            
        hostname = parsed.hostname
        if not hostname:
            return False
            
        # SSRF Protection: Resolve hostname and block private/loopback IP address spaces
        ip = socket.gethostbyname(hostname)
        if ip.startswith("127.") or ip.startswith("10.") or ip.startswith("192.168."):
            return False
        if ip.startswith("172."):
            parts = ip.split('.')
            if len(parts) >= 2 and 16 <= int(parts[1]) <= 31:
                return False
        return True
    except Exception:
        return False


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

    if not is_safe_url(str(original)):
        raise HTTPException(status_code=400, detail="URL points to unsafe local space or is invalid.")

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


@shortener_router.patch("/{code}")
def update_url(
    code: str,
    payload: UpdateRequest,
    session: Session = Depends(get_session)
):
    """
    Dynamically update the redirection destination URL for a short code.
    """
    mapping = session.exec(
        select(URLMapping).where(URLMapping.short_code == code)
    ).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="Short URL not found")
        
    if not is_safe_url(str(payload.new_url)):
        raise HTTPException(status_code=400, detail="New URL points to unsafe space.")
        
    mapping.original_url = str(payload.new_url)
    session.add(mapping)
    session.commit()
    session.refresh(mapping)
    
    return {"message": "URL dynamically updated", "short_code": code, "target_url": mapping.original_url}