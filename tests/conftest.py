import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["SECRET_KEY"] = "test-secret"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c


def signup(client, email="a@example.com", password="password123"):
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def auth(client):
    return signup(client)
