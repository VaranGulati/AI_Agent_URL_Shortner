import string
import random
import datetime
from typing import Optional

from sqlmodel import Session, select

from .models import URLMapping
from .config import settings


def _generate_code(length: Optional[int] = None) -> str:
    """
    Generate a random alphanumeric code.
    If length is not provided, use the configured ``settings.code_length``.
    """
    if length is None:
        length = settings.code_length
    chars = string.ascii_letters + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def create_short_url(original_url: str, session: Session) -> URLMapping:
    """
    Create a new ``URLMapping`` with a unique short code.
    The function retries code generation until a non‑existent code is found.
    """
    while True:
        code = _generate_code()
        existing = session.exec(
            select(URLMapping).where(URLMapping.short_code == code)
        ).first()
        if not existing:
            break

    mapping = URLMapping(original_url=original_url, short_code=code)
    session.add(mapping)
    session.commit()
    session.refresh(mapping)
    return mapping


def resolve_short_code(code: str, session: Session) -> Optional[URLMapping]:
    """
    Retrieve a ``URLMapping`` by its short code, update access statistics,
    and return the mapping. Returns ``None`` if the code does not exist.
    """
    mapping = session.exec(
        select(URLMapping).where(URLMapping.short_code == code)
    ).first()
    if mapping:
        mapping.access_count += 1
        mapping.last_accessed = datetime.datetime.utcnow()
        session.add(mapping)
        session.commit()
        session.refresh(mapping)
    return mapping