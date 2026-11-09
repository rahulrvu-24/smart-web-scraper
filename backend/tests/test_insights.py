import asyncio

from app.core.config import Settings
from app.models import LLMUsageLog, ScrapeJob
from app.worker import queue, runner
from tests.conftest import register_and_login
from tests.test_worker import _fake_extract, _fake_fetch


def test_usage_summary_counts_calls_tokens_and_fallbacks(client, db, monkeypatch, session_factory, public_dns):
    monkeypatch.setattr(runner, "SessionLocal", session_factory)
    monkeypatch.setattr(runner, "fetch_page", _fake_fetch())
    monkeypatch.setattr(runner, "extract", _fake_extract)
    auth = register_and_login(client)
    client.post("/jobs", json={"url": "https://shop.example/", "fields": {"title": {"type": "string"}}}, headers=auth)
    with session_factory() as s:
        claimed = queue.claim_next_job(s)
    asyncio.run(runner.process_job(claimed, Settings(groq_api_key="k")))

    summary = client.get("/usage", headers=auth).json()
    assert summary["jobs_by_status"] == {"succeeded": 1}
    assert summary["llm_calls"] == 2 and summary["failed_llm_calls"] == 1
    assert summary["fallback_used"] == 1
    assert summary["input_tokens"] == 10
    assert {m["model"] for m in summary["by_model"]} == {"strict-model", "test-model"}


def test_usage_is_per_user(client, db):
    auth = register_and_login(client)
    other = register_and_login(client, email="other@example.com")
    assert client.get("/usage", headers=other).json()["llm_calls"] == 0
    assert client.get("/usage", headers=auth).json()["jobs_by_status"] == {}


def test_activity_lists_own_events_newest_first(client):
    auth = register_and_login(client)
    register_and_login(client, email="other@example.com")
    events = client.get("/activity", headers=auth).json()
    assert [e["action"] for e in events] == ["auth.login", "auth.register"]
