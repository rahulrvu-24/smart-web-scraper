from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.worker.queue import count_queued

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health() -> dict[str, str]:
    """Liveness check: the API process is up and answering requests."""
    return {"status": "ok"}


@router.get("/db")
def health_db(db: Session = Depends(get_db)) -> dict[str, str]:
    """Readiness check: the API can reach Postgres and run a query."""
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unreachable",
        )
    return {"status": "ok", "database": "reachable"}

@router.get("/worker")
def health_worker(request: Request, db: Session = Depends(get_db)) -> dict[str, str | int]:
    """Is the background worker running, and how many jobs are waiting?"""
    task = getattr(request.app.state, "worker_task", None)
    if task is None:
        state = "disabled"
    elif task.done():
        state = "stopped"
    else:
        state = "running"
    try:
        queued = count_queued(db)
    except SQLAlchemyError:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="database unreachable")
    if state == "stopped":
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="worker stopped")
    return {"status": "ok", "worker": state, "queued": queued}
