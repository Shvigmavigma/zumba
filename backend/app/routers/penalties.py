from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.deps import MARSHALL_PLUS, get_current_user, require_admin, require_marshall_plus
from app.models import Appeal, Penalty, PenaltyStatus, Race, RaceStatus, User
from app.rate_limit import limiter
from app.schemas import PenaltyCreate, PenaltyDetailRead, PenaltyRead
from app.services import apply_sr_penalties, recalculate_all_ratings, recalculate_race_results, restore_sr_penalty


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
    if user.role not in MARSHALL_PLUS and race_id is None:
        target_id = user.id
    if race_id is not None:
        stmt = stmt.where(Penalty.race_id == race_id)
    if target_id is not None:
        stmt = stmt.where(Penalty.target_id == target_id)
    return (await session.scalars(stmt.limit(200))).all()


@router.get("/{penalty_id}", response_model=PenaltyDetailRead)
@limiter.limit("600/minute")
async def get_penalty(
    penalty_id: int,
    request: Request,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    penalty = await session.scalar(
        select(Penalty)
        .options(
            selectinload(Penalty.race),
            selectinload(Penalty.target).selectinload(User.team),
            selectinload(Penalty.issuer).selectinload(User.team),
        )
        .where(Penalty.id == penalty_id)
    )
    if penalty is None:
        raise HTTPException(status_code=404, detail="Penalty not found")
    if user.role not in MARSHALL_PLUS and penalty.target_id != user.id:
        raise HTTPException(status_code=403, detail="Only penalty target can view this penalty")

    data = PenaltyRead.model_validate(penalty).model_dump()
    data.update(
        {
            "race_name": penalty.race.name if penalty.race else None,
            "target_login": penalty.target.login if penalty.target else None,
            "target_nickname": penalty.target.nickname if penalty.target else None,
            "target_pilot_number": penalty.target.pilot_number if penalty.target else None,
            "target_avatar_color": penalty.target.avatar_color if penalty.target else None,
            "target_avatar_url": penalty.target.avatar_url if penalty.target else None,
            "target_rating": int(round(float(penalty.target.rating))) if penalty.target else None,
            "target_team_name": penalty.target.team.name if penalty.target and penalty.target.team else None,
            "target_team_abbreviation": penalty.target.team.abbreviation if penalty.target and penalty.target.team else None,
            "issuer_login": penalty.issuer.login if penalty.issuer else None,
            "issuer_nickname": penalty.issuer.nickname if penalty.issuer else None,
            "issuer_rating": int(round(float(penalty.issuer.rating))) if penalty.issuer else None,
            "issuer_team_name": penalty.issuer.team.name if penalty.issuer and penalty.issuer.team else None,
            "issuer_team_abbreviation": penalty.issuer.team.abbreviation if penalty.issuer and penalty.issuer.team else None,
        }
    )
    return data


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
    if race.status == RaceStatus.finished:
        await apply_sr_penalties(session, race)
    await recalculate_race_results(session, race)
    if race.status == RaceStatus.finished:
        await recalculate_all_ratings(session)
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
        if race.status == RaceStatus.finished:
            await recalculate_all_ratings(session)
    await session.commit()
    await session.refresh(penalty)
    return penalty


@router.delete("/{penalty_id}/permanent", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("3/minute")
async def delete_penalty_permanently(
    penalty_id: int,
    request: Request,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    penalty = await session.get(Penalty, penalty_id)
    if penalty is None:
        raise HTTPException(status_code=404, detail="Penalty not found")
    race = await session.get(Race, penalty.race_id)
    await restore_sr_penalty(session, penalty)
    await session.execute(delete(Appeal).where(Appeal.penalty_id == penalty.id))
    await session.delete(penalty)
    await session.flush()
    if race is not None:
        await recalculate_race_results(session, race)
        if race.status == RaceStatus.finished:
            await recalculate_all_ratings(session)
    await session.commit()
