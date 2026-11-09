from collections.abc import Iterator

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from .config import API_KEYS
from .database import SessionLocal


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_api_key(x_api_key: str = Header(...)) -> str:
    if x_api_key not in API_KEYS:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid API key")
    return x_api_key


DbSession = Depends(get_db)
ApiKey = Depends(get_api_key)
