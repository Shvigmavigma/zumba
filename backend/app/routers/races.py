from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import require_moder_plus, require_pilot_plus
from app.models import Race, RaceStatus, Role, User
from app.rate_limit import limiter
from app.schemas import RaceCreate, RaceRead, RaceRegisterRequest, RaceUpdate, ResultsUpload
from app.services import apply_sr_penalties, recalculate_race_results


router = APIRouter()


def update_time_based_status(race: Race) -> None:
    now = datetime.now(timezone.utc)
    if race.status == RaceStatus.registration_open and race.datetime_end <= now:
        race.status = RaceStatus.ongoing


async def ensure_race(session: AsyncSession, race_id: int) -> Race:
    race = await session.get(Race, race_id)
    if race is None:
        raise HTTPException(status_code=404, detail="Race not found")
    update_time_based_status(race)
    return race


@router.get("", response_model=list[RaceRead])
@limiter.limit("3/minute")
async def list_races(
    request: Request,
    status_filter: str = "all",
    offset: int = 0,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
):
    limit = min(limit, 100)
    stmt = select(Race)
    if status_filter == "upcoming":
        stmt = stmt.where(Race.status == RaceStatus.registration_open)
    elif status_filter == "past":
        stmt = stmt.where(Race.status == RaceStatus.finished)
    elif status_filter in RaceStatus._value2member_map_:
        stmt = stmt.where(Race.status == RaceStatus(status_filter))
    stmt = stmt.order_by(Race.datetime_start.desc()).offset(offset).limit(limit)
    races = list((await session.scalars(stmt)).all())
    changed = False
    for race in races:
        before = race.status
        update_time_based_status(race)
        changed = changed or before != race.status
    if changed:
        await session.commit()
    return races


@router.post("", response_model=RaceRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def create_race(payload: RaceCreate, request: Request, user: User = Depends(require_moder_plus), session: AsyncSession = Depends(get_session)):
    if payload.datetime_end <= payload.datetime_start:
        raise HTTPException(status_code=400, detail="Registration end must be after start")
    race = Race(
        **payload.model_dump(),
        creator_id=user.id,
        status=RaceStatus.registration_open,
        is_passed=False,
        registered_pilots=[],
    )
    session.add(race)
    await session.commit()
    await session.refresh(race)
    return race


@router.get("/{race_id}", response_model=RaceRead)
@limiter.limit("3/minute")
async def get_race(
    race_id: int,
    request: Request,
    _: User = Depends(require_pilot_plus),
    session: AsyncSession = Depends(get_session),
):
    race = await ensure_race(session, race_id)
    await session.commit()
    await session.refresh(race)
    return race


@router.patch("/{race_id}", response_model=RaceRead)
@limiter.limit("3/minute")
async def update_race(
    race_id: int,
    request: Request,
    payload: RaceUpdate,
    user: User = Depends(require_moder_plus),
    session: AsyncSession = Depends(get_session),
):
    race = await ensure_race(session, race_id)
    if user.role != Role.admin and race.creator_id != user.id and user.role != Role.moder:
        raise HTTPException(status_code=403, detail="Only creator, moder or admin can edit this race")
    data = payload.model_dump(exclude_unset=True)
    if "datetime_end" in data or "datetime_start" in data:
        start = data.get("datetime_start", race.datetime_start)
        end = data.get("datetime_end", race.datetime_end)
        if end <= start:
            raise HTTPException(status_code=400, detail="Registration end must be after start")
    for field, value in data.items():
        setattr(race, field, value)
    if race.status == RaceStatus.finished:
        race.is_passed = True
        await apply_sr_penalties(session, race)
    await recalculate_race_results(session, race)
    await session.commit()
    await session.refresh(race)
    return race


@router.post("/{race_id}/register", response_model=RaceRead)
@limiter.limit("3/minute")
async def register_for_race(
    race_id: int,
    request: Request,
    payload: RaceRegisterRequest,
    user: User = Depends(require_pilot_plus),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Race).where(Race.id == race_id).with_for_update())
    race = result.scalar_one_or_none()
    if race is None:
        raise HTTPException(status_code=404, detail="Race not found")
    update_time_based_status(race)
    if race.status != RaceStatus.registration_open:
        raise HTTPException(status_code=400, detail="Registration is not open")
    if race.allowed_cars and payload.car_model not in race.allowed_cars:
        raise HTTPException(status_code=400, detail="Car is not allowed")

    pilots = list(race.registered_pilots or [])
    if any(item.get("user_id") == user.id for item in pilots):
        raise HTTPException(status_code=409, detail="Already registered")
    if len(pilots) >= race.max_pilots:
        raise HTTPException(status_code=409, detail="Race is full")

    pilots.append({"user_id": user.id, "car_model": payload.car_model, "registered_at": datetime.now(timezone.utc).isoformat()})
    race.registered_pilots = pilots
    await session.commit()
    await session.refresh(race)
    return race


@router.delete("/{race_id}/register", response_model=RaceRead)
@limiter.limit("3/minute")
async def unregister_from_race(
    race_id: int,
    request: Request,
    user: User = Depends(require_pilot_plus),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(Race).where(Race.id == race_id).with_for_update())
    race = result.scalar_one_or_none()
    if race is None:
        raise HTTPException(status_code=404, detail="Race not found")
    update_time_based_status(race)
    if race.status != RaceStatus.registration_open:
        raise HTTPException(status_code=400, detail="Registration is not open")
    race.registered_pilots = [item for item in list(race.registered_pilots or []) if item.get("user_id") != user.id]
    await session.commit()
    await session.refresh(race)
    return race


@router.get("/{race_id}/registered-pilots")
@limiter.limit("3/minute")
async def export_registered_pilots(
    race_id: int,
    request: Request,
    user: User = Depends(require_moder_plus),
    session: AsyncSession = Depends(get_session),
):
    race = await ensure_race(session, race_id)
    if user.role != Role.admin and race.creator_id != user.id and user.role != Role.moder:
        raise HTTPException(status_code=403, detail="Only creator, moder or admin can export pilots")
    return {"race_id": race.id, "registered_pilots": race.registered_pilots}


@router.post("/{race_id}/results", response_model=RaceRead)
@limiter.limit("3/minute")
async def upload_results(
    race_id: int,
    request: Request,
    payload: ResultsUpload,
    user: User = Depends(require_moder_plus),
    session: AsyncSession = Depends(get_session),
):
    race = await ensure_race(session, race_id)
    if user.role != Role.admin and race.creator_id != user.id and user.role != Role.moder:
        raise HTTPException(status_code=403, detail="Only creator, moder or admin can upload results")
    race.results = payload.results
    race.status = RaceStatus.finished
    race.is_passed = True
    await recalculate_race_results(session, race)
    await apply_sr_penalties(session, race)
    await session.commit()
    await session.refresh(race)
    return race
