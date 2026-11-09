import pytest

from tests.conftest import register_and_login

PRODUCT = {
    "name": "product",
    "description": "Basic product page",
    "fields": {"title": {"type": "string", "description": "Product name"}, "price": {"type": "number"}},
}


@pytest.fixture
def auth(client):
    return register_and_login(client)


def test_schema_crud(client, auth):
    created = client.post("/schemas", json=PRODUCT, headers=auth)
    assert created.status_code == 201, created.text
    schema_id = created.json()["id"]
    assert created.json()["version"] == 1

    assert client.post("/schemas", json=PRODUCT, headers=auth).status_code == 409
    assert [s["name"] for s in client.get("/schemas", headers=auth).json()] == ["product"]

    updated = client.put(f"/schemas/{schema_id}", json={**PRODUCT, "fields": {"title": {"type": "string"}}}, headers=auth)
    assert updated.json()["version"] == 2
    assert list(updated.json()["fields"]) == ["title"]

    assert client.delete(f"/schemas/{schema_id}", headers=auth).status_code == 204
    assert client.get(f"/schemas/{schema_id}", headers=auth).status_code == 404


def test_schema_validation(client, auth):
    bad = {**PRODUCT, "fields": {"Bad Name": {"type": "string"}}}
    assert client.post("/schemas", json=bad, headers=auth).status_code == 422
    assert client.post("/schemas", json={**PRODUCT, "fields": {}}, headers=auth).status_code == 422


def test_users_cannot_see_each_others_data(client, auth):
    schema_id = client.post("/schemas", json=PRODUCT, headers=auth).json()["id"]
    other = register_and_login(client, email="other@example.com")
    assert client.get(f"/schemas/{schema_id}", headers=other).status_code == 404
    assert client.get("/schemas", headers=other).json() == []

