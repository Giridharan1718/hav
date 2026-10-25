"""Audit trail of privileged and security-relevant actions.

Never writes personal data, OTPs, tokens or passwords into the event metadata.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.logging import request_id_ctx
from app.core.security import hash_identifier
from app.models import AuditEvent, User


def record(
    db: Session,
    *,
    actor: User | None,
    action: str,
    resource_type: str,
    resource_id: str | uuid.UUID | None = None,
    outcome: str = "success",
    ip: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditEvent(
            actor_user_id=actor.id if actor else None,
            actor_role=actor.role if actor else None,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            outcome=outcome,
            request_id=request_id_ctx.get() if request_id_ctx.get() != "-" else None,
            ip_hash=hash_identifier(ip) if ip else None,
            event_metadata=metadata or {},
        )
    )
