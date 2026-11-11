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


def test_create_job_with_saved_schema(client, auth, public_dns):
    schema_id = client.post("/schemas", json=PRODUCT, headers=auth).json()["id"]
    response = client.post("/jobs", json={"url": "https://shop.example/p/1", "schema_id": schema_id}, headers=auth)
    assert response.status_code == 202, response.text
    job = response.json()
    assert job["status"] == "queued"
    assert set(job["fields"]) == {"title", "price"}  # snapshot of the schema
    assert job["result"] is None

    page = client.get("/jobs", headers=auth).json()
    assert page["total"] == 1 and page["items"][0]["id"] == job["id"]


def test_create_job_with_inline_fields(client, auth, public_dns):
    body = {"url": "https://shop.example/p/2", "fields": {"title": {"type": "string"}}}
    assert client.post("/jobs", json=body, headers=auth).status_code == 202


def test_job_needs_exactly_one_of_schema_or_fields(client, auth, public_dns):
    assert client.post("/jobs", json={"url": "https://shop.example/"}, headers=auth).status_code == 422


def test_ssrf_urls_are_rejected_at_submit(client, auth):
    response = client.post(
        "/jobs", json={"url": "http://169.254.169.254/latest/", "fields": {"x": {"type": "string"}}}, headers=auth
    )
    assert response.status_code == 422
    assert "private" in response.json()["detail"]


def test_active_job_limit(client, auth, public_dns):
    body = {"url": "https://shop.example/", "fields": {"title": {"type": "string"}}}
    codes = [client.post("/jobs", json=body, headers=auth).status_code for _ in range(6)]
    assert codes == [202] * 5 + [429]


def test_jobs_require_login(client):
    assert client.get("/jobs").status_code == 401
