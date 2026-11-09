from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.db.session import get_db
from app.main import app

client = TestClient(app)


class _HealthySession:
    def execute(self, _statement):
        return None


class _BrokenSession:
    def execute(self, _statement):
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_db_ok_when_database_reachable():
    app.dependency_overrides[get_db] = lambda: _HealthySession()
    try:
        response = client.get("/health/db")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "reachable"}


def test_health_db_503_when_database_down():
    app.dependency_overrides[get_db] = lambda: _BrokenSession()
    try:
        response = client.get("/health/db")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503
    assert response.json() == {"detail": "database unreachable"}

def test_root_points_to_docs():
    assert client.get("/").json()["docs"] == "/docs"


def test_database_url_accepts_hosted_formats():
    from app.core.config import Settings

    for url in ("postgres://u:p@host/db", "postgresql://u:p@host/db?sslmode=require"):
        assert Settings(database_url=url).database_url.startswith("postgresql+psycopg://u:p@host/db")


def test_production_refuses_the_dev_jwt_secret():
    import pytest
    from pydantic import ValidationError

    from app.core.config import Settings

    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        Settings(environment="production")
    assert Settings(environment="production", jwt_secret_key="x" * 48).environment == "production"
