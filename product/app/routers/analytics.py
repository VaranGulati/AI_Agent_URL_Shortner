from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from pydantic import BaseModel
from datetime import datetime

# Assuming the shared components are importable from their respective modules
# Adjust the import paths according to your project layout
from ..models import URLMapping
from ..dependencies import get_session


analytics_router = APIRouter(prefix="/analytics", tags=["analytics"])


class AnalyticsResponse(BaseModel):
    original_url: str
    short_code: str
    created_at: datetime
    access_count: int
    last_accessed: datetime | None = None

    class Config:
        orm_mode = True


@analytics_router.get("/{code}", response_model=AnalyticsResponse)
def get_stats(
    code: str,
    session: Session = Depends(get_session)
) -> AnalyticsResponse:
    """
    Retrieve analytics for a given short code.

    - **original_url**: The original long URL.
    - **short_code**: The short identifier.
    - **created_at**: When the short URL was created.
    - **access_count**: Total number of redirects performed.
    - **last_accessed**: Timestamp of the most recent redirect (or null).
    """
    mapping = session.exec(
        select(URLMapping).where(URLMapping.short_code == code)
    ).first()

    if not mapping:
        raise HTTPException(status_code=404, detail="Short URL not found")

    return AnalyticsResponse(
        original_url=mapping.original_url,
        short_code=mapping.short_code,
        created_at=mapping.created_at,
        access_count=mapping.access_count,
        last_accessed=mapping.last_accessed,
    )