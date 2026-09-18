from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserConsent


PRIVACY_POLICY_VERSION = "2026-09-18"
TERMS_VERSION = "2026-09-18"
MODERATION_HISTORY_RETENTION_DAYS = 180

CONSENT_KIND_DATA_PROCESSING = "data_processing"
CONSENT_KIND_TERMS = "terms"


def record_consent(
    session: AsyncSession,
    *,
    user_id: int,
    kind: str,
    document_version: str,
    consented_at: datetime,
) -> None:
    session.add(
        UserConsent(
            user_id=user_id,
            kind=kind,
            document_version=document_version,
            consented_at=consented_at,
        )
    )
