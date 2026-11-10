from app.models import User
from tests.conftest import register_and_login


def _register(client, email="rahul@example.com", password="s3cret-pass"):
    return client.post("/auth/register", json={"email": email, "password": password})


def test_register_returns_the_user_without_the_password(client):
    response = _register(client, email="Rahul@Example.com")
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "rahul@example.com"  # stored lowercase
    assert "password" not in body and "hashed_password" not in body


def test_duplicate_email_is_rejected(client):
    _register(client)
    assert _register(client, email="RAHUL@example.com").status_code == 409


def test_short_password_and_bad_email(client):
    assert _register(client, email="a@b.co", password="short").status_code == 422
    assert _register(client, email="not-an-email").status_code == 422


def test_password_is_hashed(client, db):
    _register(client)
    user = db.query(User).one()
    assert user.hashed_password != "s3cret-pass"
    assert user.hashed_password.startswith("$argon2")


def test_login_returns_a_bearer_token(client):
    _register(client)
    response = client.post("/auth/login", data={"username": "rahul@example.com", "password": "s3cret-pass"})
    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"].count(".") == 2  # header.payload.signature


def test_wrong_password_or_unknown_email(client):
    _register(client)
    wrong = client.post("/auth/login", data={"username": "rahul@example.com", "password": "wrong-pass"})
    unknown = client.post("/auth/login", data={"username": "nobody@example.com", "password": "s3cret-pass"})
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()  # same message: don't reveal which emails exist

def test_me_returns_the_logged_in_user(client):
    headers = register_and_login(client)
    me = client.get("/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "rahul@example.com"


def test_me_requires_a_valid_token(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401