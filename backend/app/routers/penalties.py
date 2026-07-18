from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import MARSHALL_PLUS, get_current_user, require_marshall_plus
from app.models import Penalty, PenaltyStatus, Race, User
from app.rate_limit import limiter
from app.schemas import PenaltyCreate, PenaltyRead
from app.services import recalculate_race_results, restore_sr_penalty


router = APIRouter()


@router.get("", response_model=list[PenaltyRead])
@limiter.limit("3/minute")
async def list_penalties(
    request: Request,
    race_id: int | None = None,
    target_id: int | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Penalty).order_by(Penalty.created_at.desc())
    if user.role not in MARSHALL_PLUS:
        target_id = user.id
    if race_id is not None:
        stmt = stmt.where(Penalty.race_id == race_id)
    if target_id is not None:
        stmt = stmt.where(Penalty.target_id == target_id)
    return (await session.scalars(stmt.limit(200))).all()


@router.post("", response_model=PenaltyRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def create_penalty(
    request: Request,
    payload: PenaltyCreate,
    issuer: User = Depends(require_marshall_plus),
    session: AsyncSession = Depends(get_session),
):
    race = await session.get(Race, payload.race_id)
    target = await session.get(User, payload.target_id)
    if race is None or target is None:
        raise HTTPException(status_code=404, detail="Race or target user not found")
    penalty = Penalty(**payload.model_dump(), issuer_id=issuer.id, status=PenaltyStatus.active, is_applied=False)
    session.add(penalty)
    await session.flush()
    await recalculate_race_results(session, race)
    await session.commit()
    await session.refresh(penalty)
    return penalty


@router.delete("/{penalty_id}", response_model=PenaltyRead)
@limiter.limit("3/minute")
async def cancel_penalty(
    penalty_id: int,
    request: Request,
    _: User = Depends(require_marshall_plus),
    session: AsyncSession = Depends(get_session),
):
    penalty = await session.get(Penalty, penalty_id)
    if penalty is None:
        raise HTTPException(status_code=404, detail="Penalty not found")
    penalty.status = PenaltyStatus.canceled
    await restore_sr_penalty(session, penalty)
    race = await session.get(Race, penalty.race_id)
    if race is not None:
        await recalculate_race_results(session, race)
    await session.commit()
    await session.refresh(penalty)
    return penalty
