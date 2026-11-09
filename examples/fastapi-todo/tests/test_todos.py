import os

os.environ["API_KEYS"] = "test-key"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.deps import get_db
from app.main import app

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine)
Base.metadata.create_all(engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)
HEADERS = {"X-API-Key": "test-key"}


def test_create_and_list():
    created = client.post("/todos", json={"title": "write tests"}, headers=HEADERS)
    assert created.status_code == 201
    listed = client.get("/todos", headers=HEADERS)
    assert [t["title"] for t in listed.json()] == ["write tests"]


def test_rejects_bad_key():
    assert client.get("/todos", headers={"X-API-Key": "nope"}).status_code == 401
