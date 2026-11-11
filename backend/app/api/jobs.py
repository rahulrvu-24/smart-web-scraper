import asyncio
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.core import audit
from app.core.config import get_settings
from app.models import ExtractionSchema, JobStatus, ScrapeJob
from app.schemas.job import JobCreate, JobPage, JobRead
from app.scraper.url_guard import UnsafeURLError, check_url

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _get_owned(db: DbSession, user: CurrentUser, job_id: uuid.UUID) -> ScrapeJob:
    job = db.scalar(
        select(ScrapeJob).options(selectinload(ScrapeJob.result)).where(ScrapeJob.id == job_id)
    )
    if job is None or job.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


def _enforce_limits(db: DbSession, user: CurrentUser) -> None:
    settings = get_settings()
    hour_ago = datetime.now(UTC) - timedelta(hours=1)
    recent = db.scalar(
        select(func.count()).select_from(ScrapeJob).where(ScrapeJob.user_id == user.id, ScrapeJob.created_at >= hour_ago)
    )
    if recent >= settings.jobs_per_hour:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Limit of {settings.jobs_per_hour} jobs per hour reached. Try again later.",
        )
    active = db.scalar(
        select(func.count())
        .select_from(ScrapeJob)
        .where(ScrapeJob.user_id == user.id, ScrapeJob.status.in_([JobStatus.QUEUED, JobStatus.RUNNING]))
    )
    if active >= settings.max_active_jobs_per_user:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"You already have {active} jobs waiting. Wait for some to finish.",
        )


@router.post("", response_model=JobRead, status_code=status.HTTP_202_ACCEPTED)
async def create_job(body: JobCreate, db: DbSession, user: CurrentUser, request: Request) -> ScrapeJob:
    try:
        url = await asyncio.to_thread(check_url, body.url)  # DNS lookup: keep it off the event loop
    except UnsafeURLError as exc:
        # Blocked URLs are worth recording: repeated ones suggest someone probing for SSRF.
        audit.record(db, request, "job.blocked_url", user.id, details={"url": body.url[:500], "reason": str(exc)})
        db.commit()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    _enforce_limits(db, user)

    if body.schema_id is not None:
        schema = db.get(ExtractionSchema, body.schema_id)
        if schema is None or schema.user_id != user.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Schema not found")
        fields = dict(schema.fields)
    else:
        fields = {k: v.model_dump() for k, v in (body.fields or {}).items()}

    job = ScrapeJob(user_id=user.id, schema_id=body.schema_id, url=url, fields=fields, render_js=body.render_js)
    db.add(job)
    db.flush()
    audit.record(
        db, request, "job.create", user.id, "scrape_job", job.id, {"url": url[:500], "render_js": body.render_js}
    )
    db.commit()
    return _get_owned(db, user, job.id)


@router.get("", response_model=JobPage)
def list_jobs(
    db: DbSession,
    user: CurrentUser,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status_filter: JobStatus | None = Query(default=None, alias="status"),
) -> JobPage:
    query = select(ScrapeJob).where(ScrapeJob.user_id == user.id)
    if status_filter is not None:
        query = query.where(ScrapeJob.status == status_filter)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(query.order_by(ScrapeJob.created_at.desc()).limit(limit).offset(offset)).all()
    return JobPage(items=items, total=total)


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: uuid.UUID, db: DbSession, user: CurrentUser) -> ScrapeJob:
    return _get_owned(db, user, job_id)


@router.post("/{job_id}/retry", response_model=JobRead, status_code=status.HTTP_202_ACCEPTED)
def retry_job(job_id: uuid.UUID, db: DbSession, user: CurrentUser, request: Request) -> ScrapeJob:
    job = _get_owned(db, user, job_id)
    if job.status != JobStatus.FAILED:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Only failed jobs can be retried")
    _enforce_limits(db, user)
    job.status = JobStatus.QUEUED
    job.attempts = 0
    job.error_message = None
    job.run_after = None
    job.started_at = None
    job.finished_at = None
    audit.record(db, request, "job.retry", user.id, "scrape_job", job.id)
    db.commit()
    return _get_owned(db, user, job.id)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: uuid.UUID, db: DbSession, user: CurrentUser, request: Request) -> Response:
    job = _get_owned(db, user, job_id)
    audit.record(db, request, "job.delete", user.id, "scrape_job", job.id, {"url": job.url[:500]})
    db.delete(job)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
