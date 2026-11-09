from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _preflight(origin: str):
    return client.options(
        "/health",
        headers={"Origin": origin, "Access-Control-Request-Method": "GET"},
    )


def test_frontend_origin_is_allowed():
    response = _preflight("http://localhost:3000")
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_unknown_origin_is_rejected():
    response = _preflight("https://evil.example")
    assert "access-control-allow-origin" not in response.headers