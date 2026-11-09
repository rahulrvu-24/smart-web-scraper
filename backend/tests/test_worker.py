import asyncio
import uuid

import pytest

from app.core.config import Settings
from app.extraction.llm import Extraction, LLMError
from app.models import JobStatus, ScrapeJob, User
from app.scraper.fetcher import FetchedPage, FetchError
from app.worker import queue, runner

SETTINGS = Settings(groq_api_key="test-key", job_max_attempts=3)
FIELDS = {"title": {"type": "string", "description": ""}, "price": {"type": "number", "description": ""}}


@pytest.fixture
def make_job(db):
    user = User(email="w@example.com", hashed_password="x")
    db.add(user)
    db.commit()

    def _make(url="https://shop.example/p/1") -> uuid.UUID:
        job = ScrapeJob(user_id=user.id, url=url, fields=FIELDS)
        db.add(job)
        db.commit()
        return job.id

    return _make


@pytest.fixture
def worker_db(monkeypatch, session_factory):
    monkeypatch.setattr(runner, "SessionLocal", session_factory)


def _fake_fetch(html="<html><title>Shop</title><body><h1>Pro</h1><p>$42.99</p></body></html>"):
    async def fetch(url, settings):
        return FetchedPage(url=url, status_code=200, html=html, method="http")

    return fetch


async def _fake_extract(fields, page, url, settings):
    return Extraction(data={"title": "Pro", "price": 42.99}, is_valid=True, errors=[], model="test-model", input_tokens=10, output_tokens=5, latency_ms=7)


def test_claim_skips_jobs_locked_by_another_worker(session_factory, make_job):
    first, second = make_job(), make_job()
    with session_factory() as a, session_factory() as b:
        # Worker A locks a row in an open transaction...
        locked = a.execute(
            queue.select(ScrapeJob).where(ScrapeJob.id == first).with_for_update()
        ).scalar_one()
        # ...so worker B skips it and takes the next one instead of waiting.
        claimed = queue.claim_next_job(b)
        assert locked.id == first and claimed.id == second
        a.rollback()


def test_successful_job_stores_result(monkeypatch, worker_db, session_factory, make_job):
    job_id = make_job()
    monkeypatch.setattr(runner, "fetch_page", _fake_fetch())
    monkeypatch.setattr(runner, "extract", _fake_extract)
    with session_factory() as s:
        claimed = queue.claim_next_job(s)
    asyncio.run(runner.process_job(claimed, SETTINGS))
    with session_factory() as s:
        job = s.get(ScrapeJob, job_id)
        assert job.status == JobStatus.SUCCEEDED and job.finished_at is not None
        assert job.result.data == {"title": "Pro", "price": 42.99}
        assert job.result.page_title == "Shop" and job.result.fetch_method == "http"
        assert job.result.llm_model == "test-model"


def test_temporary_failure_is_retried_with_backoff(monkeypatch, worker_db, session_factory, make_job):
    job_id = make_job()

    async def flaky(url, settings):
        raise FetchError("Site returned HTTP 503", retryable=True)

    monkeypatch.setattr(runner, "fetch_page", flaky)
    with session_factory() as s:
        claimed = queue.claim_next_job(s)
    asyncio.run(runner.process_job(claimed, SETTINGS))
    with session_factory() as s:
        job = s.get(ScrapeJob, job_id)
        assert job.status == JobStatus.QUEUED
        assert job.run_after is not None and "503" in job.error_message
        assert queue.claim_next_job(s) is None  # not before its backoff time


def test_permanent_failure_stops_immediately(monkeypatch, worker_db, session_factory, make_job):
    job_id = make_job()
    monkeypatch.setattr(runner, "fetch_page", _fake_fetch())

    async def bad_key(*args):
        raise LLMError("The Groq API key was rejected (check GROQ_API_KEY)")

    monkeypatch.setattr(runner, "extract", bad_key)
    with session_factory() as s:
        claimed = queue.claim_next_job(s)
    asyncio.run(runner.process_job(claimed, SETTINGS))
    with session_factory() as s:
        job = s.get(ScrapeJob, job_id)
        assert job.status == JobStatus.FAILED and "API key" in job.error_message


def test_gives_up_after_max_attempts(monkeypatch, worker_db, session_factory, make_job):
    job_id = make_job()
    with session_factory() as s:
        s.get(ScrapeJob, job_id).attempts = 2
        s.commit()
        claimed = queue.claim_next_job(s)  # attempt 3 of 3
    assert claimed.attempts == 3

    async def flaky(url, settings):
        raise FetchError("timeout", retryable=True)

    monkeypatch.setattr(runner, "fetch_page", flaky)
    asyncio.run(runner.process_job(claimed, SETTINGS))
    with session_factory() as s:
        assert s.get(ScrapeJob, job_id).status == JobStatus.FAILED


def test_stale_running_jobs_are_requeued(session_factory, make_job):
    job_id = make_job()
    with session_factory() as s:
        queue.claim_next_job(s)
        s.execute(queue.update(ScrapeJob).values(started_at=queue.datetime(2020, 1, 1, tzinfo=queue.UTC)))
        s.commit()
        assert queue.recover_stale_jobs(s, SETTINGS) == 1
        assert s.get(ScrapeJob, job_id).status == JobStatus.QUEUED


def test_end_to_end_through_the_api(client, monkeypatch, worker_db, session_factory, public_dns):
    from tests.conftest import register_and_login

    auth = register_and_login(client)
    body = {"url": "https://shop.example/p/1", "fields": {"title": {"type": "string"}, "price": {"type": "number"}}}
    job_id = client.post("/jobs", json=body, headers=auth).json()["id"]
    monkeypatch.setattr(runner, "fetch_page", _fake_fetch())
    monkeypatch.setattr(runner, "extract", _fake_extract)
    with session_factory() as s:
        claimed = queue.claim_next_job(s)
    asyncio.run(runner.process_job(claimed, SETTINGS))
    job = client.get(f"/jobs/{job_id}", headers=auth).json()
    assert job["status"] == "succeeded"
    assert job["result"]["data"] == {"title": "Pro", "price": 42.99}
    assert job["result"]["is_valid"] is True
