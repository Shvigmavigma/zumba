from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import MARSHALL_PLUS, require_marshall_plus, require_pilot_plus
from app.models import Appeal, AppealStatus, Penalty, PenaltyStatus, Race, RaceStatus, User
from app.rate_limit import limiter
from app.schemas import AppealCreate, AppealModerationRequest, AppealRead
from app.services import apply_sr_penalty, recalculate_all_ratings, recalculate_race_results, restore_sr_penalty


router = APIRouter()


@router.get("", response_model=list[AppealRead])
@limiter.limit("3/minute")
async def list_appeals(
    request: Request,
    status_filter: AppealStatus | None = None,
    user: User = Depends(require_pilot_plus),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Appeal).order_by(Appeal.created_at.desc())
    if user.role not in MARSHALL_PLUS:
        stmt = stmt.where(Appeal.user_id == user.id)
    if status_filter is not None:
        stmt = stmt.where(Appeal.status == status_filter)
    return (await session.scalars(stmt.limit(200))).all()


@router.post("", response_model=AppealRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def create_appeal(
    request: Request,
    payload: AppealCreate,
    user: User = Depends(require_pilot_plus),
    session: AsyncSession = Depends(get_session),
):
    penalty = await session.get(Penalty, payload.penalty_id)
    if penalty is None or penalty.race_id != payload.race_id:
        raise HTTPException(status_code=404, detail="Penalty not found for this race")
    if penalty.target_id != user.id:
        raise HTTPException(status_code=403, detail="Only penalty target can appeal")
    if penalty.status != PenaltyStatus.active:
        raise HTTPException(status_code=400, detail="Penalty is not active")
    appeal = Appeal(
        user_id=user.id,
        race_id=payload.race_id,
        penalty_id=payload.penalty_id,
        proof_link=str(payload.proof_link),
        description=payload.description,
        status=AppealStatus.pending,
    )
    penalty.status = PenaltyStatus.appealed
    session.add(appeal)
    race = await session.get(Race, payload.race_id)
    if race is not None:
        await recalculate_race_results(session, race)
        if race.status == RaceStatus.finished:
            await recalculate_all_ratings(session)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Appeal already exists") from exc
    await session.refresh(appeal)
    return appeal


@router.patch("/{appeal_id}/moderate", response_model=AppealRead)
@limiter.limit("3/minute")
async def moderate_appeal(
    appeal_id: int,
    request: Request,
    payload: AppealModerationRequest,
    moderator: User = Depends(require_marshall_plus),
    session: AsyncSession = Depends(get_session),
):
    if payload.status == AppealStatus.pending:
        raise HTTPException(status_code=400, detail="Use approved or rejected")
    appeal = await session.get(Appeal, appeal_id)
    if appeal is None:
        raise HTTPException(status_code=404, detail="Appeal not found")
    if appeal.status != AppealStatus.pending:
        raise HTTPException(status_code=400, detail="Appeal is already resolved")
    penalty = await session.get(Penalty, appeal.penalty_id)
    race = await session.get(Race, appeal.race_id)
    if penalty is None:
        raise HTTPException(status_code=404, detail="Penalty not found")

    appeal.status = payload.status
    appeal.moderator_id = moderator.id
    if payload.status == AppealStatus.approved:
        appeal.rejection_reason = None
        penalty.status = PenaltyStatus.canceled
        await restore_sr_penalty(session, penalty)
    else:
        appeal.rejection_reason = payload.rejection_reason or "Rejected by marshall"
        penalty.status = PenaltyStatus.active
        if race is not None and race.status == RaceStatus.finished:
            await apply_sr_penalty(session, penalty)

    if race is not None:
        await recalculate_race_results(session, race)
        if race.status == RaceStatus.finished:
            await recalculate_all_ratings(session)
    await session.commit()
    await session.refresh(appeal)
    return appeal
