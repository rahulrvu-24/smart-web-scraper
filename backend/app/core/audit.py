"""Write audit_logs rows: who did what, to which record, from which IP address."""

import uuid
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AuditLog


def record(
    db: Session,
    request: Request,
    action: str,
    user_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: uuid.UUID | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    """Add an audit row to the session. It's saved by the same commit as the change it
    describes, so a change and its audit entry are saved together or not at all."""
    db.add(
        AuditLog(
            user_id=user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            # Behind Render's proxy, uvicorn --proxy-headers puts the real client IP here.
            ip_address=request.client.host if request.client else None,
            details=details,
        )
    )
