from app.models import AuditLog
from tests.conftest import register_and_login


def _actions(db):
    return [a.action for a in db.query(AuditLog).order_by(AuditLog.created_at, AuditLog.action).all()]


def test_register_and_login_are_audited(client, db):
    register_and_login(client)
    assert sorted(_actions(db)) == ["auth.login", "auth.register"]
    login = db.query(AuditLog).filter_by(action="auth.login").one()
    assert login.user_id is not None and login.ip_address  # TestClient reports "testclient"


def test_failed_logins_are_audited_even_for_unknown_emails(client, db):
    register_and_login(client)
    client.post("/auth/login", data={"username": "rahul@example.com", "password": "wrong-pass"})
    client.post("/auth/login", data={"username": "ghost@example.com", "password": "whatever1"})
    failed = db.query(AuditLog).filter_by(action="auth.login_failed").order_by(AuditLog.created_at).all()
    assert [f.details["email"] for f in failed] == ["rahul@example.com", "ghost@example.com"]
    assert failed[0].user_id is not None and failed[1].user_id is None


def test_job_and_schema_changes_are_audited(client, db, public_dns):
    auth = register_and_login(client)
    schema_id = client.post(
        "/schemas", json={"name": "p", "fields": {"title": {"type": "string"}}}, headers=auth
    ).json()["id"]
    job_id = client.post("/jobs", json={"url": "https://shop.example/", "schema_id": schema_id}, headers=auth).json()["id"]
    client.delete(f"/jobs/{job_id}", headers=auth)
    client.delete(f"/schemas/{schema_id}", headers=auth)
    actions = [a for a in _actions(db) if not a.startswith("auth.")]
    assert sorted(actions) == ["job.create", "job.delete", "schema.create", "schema.delete"]
    deleted = db.query(AuditLog).filter_by(action="job.delete").one()
    assert str(deleted.target_id) == job_id  # the trail outlives the job


def test_blocked_urls_are_audited(client, db):
    auth = register_and_login(client)
    client.post("/jobs", json={"url": "http://169.254.169.254/", "fields": {"x": {"type": "string"}}}, headers=auth)
    blocked = db.query(AuditLog).filter_by(action="job.blocked_url").one()
    assert blocked.details["url"] == "http://169.254.169.254/"


def test_audit_trail_survives_account_deletion(client, db):
    from app.models import User

    register_and_login(client)
    db.delete(db.query(User).one())
    db.commit()
    rows = db.query(AuditLog).all()
    assert len(rows) == 2 and all(r.user_id is None for r in rows)
