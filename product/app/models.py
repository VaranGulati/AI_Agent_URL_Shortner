from typing import Optional
import datetime

from sqlmodel import SQLModel, Field


class URLMapping(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    original_url: str = Field(index=True, nullable=False)
    short_code: str = Field(index=True, unique=True, nullable=False, max_length=10)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow, nullable=False)
    access_count: int = Field(default=0, nullable=False)
    last_accessed: Optional[datetime.datetime] = Field(default=None, nullable=True)