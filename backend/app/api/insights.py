"""Read-only views over llm_usage_logs and audit_logs for the logged-in user."""

from fastapi import APIRouter, Query
from sqlalchemy import case, func, select

from app.api.deps import CurrentUser, DbSession
from app.models import AuditLog, LLMUsageLog, ScrapeJob
from app.schemas.insights import ActivityItem, ModelUsage, UsageSummary

router = APIRouter(tags=["insights"])


@router.get("/usage", response_model=UsageSummary)
def usage(db: DbSession, user: CurrentUser) -> UsageSummary:
    jobs = dict(
        db.execute(
            select(ScrapeJob.status, func.count()).where(ScrapeJob.user_id == user.id).group_by(ScrapeJob.status)
        ).all()
    )
    failed = func.sum(case((LLMUsageLog.succeeded.is_(False), 1), else_=0))
    rows = db.execute(
        select(
            LLMUsageLog.model,
            func.count(),
            failed,
            func.coalesce(func.sum(LLMUsageLog.input_tokens), 0),
            func.coalesce(func.sum(LLMUsageLog.output_tokens), 0),
            func.coalesce(func.avg(LLMUsageLog.latency_ms), 0),
        )
        .where(LLMUsageLog.user_id == user.id)
        .group_by(LLMUsageLog.model)
        .order_by(func.count().desc())
    ).all()
    by_model = [
        ModelUsage(
            model=m, calls=c, failed_calls=int(f or 0), input_tokens=int(i), output_tokens=int(o), avg_latency_ms=int(lat)
        )
        for m, c, f, i, o, lat in rows
    ]
    fallback_used = db.scalar(
        select(func.count())
        .select_from(LLMUsageLog)
        .where(LLMUsageLog.user_id == user.id, LLMUsageLog.mode == "json_object", LLMUsageLog.succeeded.is_(True))
    )
    return UsageSummary(
        jobs_by_status={status.value: count for status, count in jobs.items()},
        llm_calls=sum(m.calls for m in by_model),
        failed_llm_calls=sum(m.failed_calls for m in by_model),
        input_tokens=sum(m.input_tokens for m in by_model),
        output_tokens=sum(m.output_tokens for m in by_model),
        fallback_used=fallback_used or 0,
        by_model=by_model,
    )


@router.get("/activity", response_model=list[ActivityItem])
def activity(db: DbSession, user: CurrentUser, limit: int = Query(default=50, ge=1, le=200)) -> list[AuditLog]:
    return list(
        db.scalars(
            select(AuditLog).where(AuditLog.user_id == user.id).order_by(AuditLog.created_at.desc()).limit(limit)
        )
    )
