"""Shared test setup.

Database tests use a separate database, `<your database>_test`, created automatically
on the same Postgres server, so running tests never touches your real data.
If Postgres isn't running, those tests are skipped.
"""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.session import get_db
from app.main import app
from app.models import Base


def _test_database_url():
    url = make_url(get_settings().database_url)
    return url.set(database=f"{url.database}_test")


@pytest.fixture(scope="session")
def db_engine():
    test_url = _test_database_url()
    admin = create_engine(test_url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            exists = conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": test_url.database})
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{test_url.database}"'))
    except OperationalError:
        pytest.skip("Postgres is not running; skipping database tests")
    finally:
        admin.dispose()
    engine = create_engine(test_url)
    # Start from an empty schema every run, so tables or types left over from an
    # older version of the models can never get in the way.
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(db_engine):
    factory = sessionmaker(bind=db_engine, autoflush=False, expire_on_commit=False)
    yield factory
    with db_engine.begin() as conn:
        tables = ", ".join(t.name for t in Base.metadata.sorted_tables)
        conn.execute(text(f"TRUNCATE {tables} CASCADE"))


@pytest.fixture
def db(session_factory) -> Iterator[Session]:
    with session_factory() as session:
        yield session


@pytest.fixture
def client(session_factory) -> Iterator[TestClient]:
    def _get_test_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _get_test_db
    try:
        yield TestClient(app)  # no `with`: the background worker is not started in tests
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def public_dns(monkeypatch):
    """Pretend every hostname resolves to a public IP, so tests never need the internet."""
    monkeypatch.setattr("app.scraper.url_guard.resolve_host", lambda host: ["93.184.215.14"])


def register_and_login(client: TestClient, email: str = "rahul@example.com", password: str = "s3cret-pass") -> dict[str, str]:
    response = client.post("/auth/register", json={"email": email, "password": password})
    assert response.status_code == 201, response.text
    token = client.post("/auth/login", data={"username": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}