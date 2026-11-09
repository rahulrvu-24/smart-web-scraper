"""A job queue that lives in Postgres.

Workers claim the oldest queued job with SELECT ... FOR UPDATE SKIP LOCKED: the row is
locked for this worker, and any other worker skips it instead of waiting. So several
workers (or several API instances) can run at once without ever taking the same job.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import JobStatus, ScrapeJob, ScrapeResult

BACKOFF_SECONDS = 30


@dataclass
class ClaimedJob:
    id: uuid.UUID
    url: str
    fields: dict[str, Any]
    attempts: int


def claim_next_job(db: Session) -> ClaimedJob | None:
    now = datetime.now(UTC)
    job = db.scalar(
        select(ScrapeJob)
        .where(ScrapeJob.status == JobStatus.QUEUED)
        .where(or_(ScrapeJob.run_after.is_(None), ScrapeJob.run_after <= now))
        .order_by(ScrapeJob.created_at)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    if job is None:
        db.rollback()
        return None
    job.status = JobStatus.RUNNING
    job.started_at = now
    job.finished_at = None
    job.attempts += 1
    db.commit()
    return ClaimedJob(id=job.id, url=job.url, fields=dict(job.fields), attempts=job.attempts)


def recover_stale_jobs(db: Session, settings: Settings) -> int:
    """Jobs left 'running' by a worker that crashed or was restarted go back in the queue."""
    cutoff = datetime.now(UTC) - timedelta(seconds=settings.job_stale_after_seconds)
    stale = select(ScrapeJob.id).where(ScrapeJob.status == JobStatus.RUNNING, ScrapeJob.started_at < cutoff)
    requeued = db.execute(
        update(ScrapeJob)
        .where(ScrapeJob.id.in_(stale), ScrapeJob.attempts < settings.job_max_attempts)
        .values(status=JobStatus.QUEUED, run_after=None)
    ).rowcount
    db.execute(
        update(ScrapeJob)
        .where(ScrapeJob.id.in_(stale))
        .values(status=JobStatus.FAILED, finished_at=datetime.now(UTC), error_message="The worker stopped while processing this job")
    )
    db.commit()
    return requeued


def mark_succeeded(db: Session, job_id: uuid.UUID, result: ScrapeResult) -> None:
    job = db.get(ScrapeJob, job_id)
    if job is None:  # deleted by its owner while we were working on it
        return
    if job.result is not None:
        db.delete(job.result)
        db.flush()
    result.job_id = job_id
    db.add(result)
    job.status = JobStatus.SUCCEEDED
    job.error_message = None
    job.finished_at = datetime.now(UTC)
    db.commit()


def mark_failed(db: Session, job_id: uuid.UUID, message: str, retryable: bool, settings: Settings) -> None:
    job = db.get(ScrapeJob, job_id)
    if job is None:
        return
    job.error_message = message[:2000]
    if retryable and job.attempts < settings.job_max_attempts:
        job.status = JobStatus.QUEUED
        job.run_after = datetime.now(UTC) + timedelta(seconds=BACKOFF_SECONDS * 2 ** (job.attempts - 1))
    else:
        job.status = JobStatus.FAILED
        job.finished_at = datetime.now(UTC)
    db.commit()


def count_queued(db: Session) -> int:
    return len(db.scalars(select(ScrapeJob.id).where(ScrapeJob.status == JobStatus.QUEUED)).all())
