from collections import defaultdict
from time import monotonic

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Race, RaceStatus, Team, User
from app.rate_limit import limiter
from app.schemas import HallOfFamePilotRead, HallOfFameRead, HallOfFameTeamRead
from app.services import result_rows


router = APIRouter()

HALL_OF_FAME_CACHE_TTL_SECONDS = 30
PODIUM_POINTS = {1: 3, 2: 2, 3: 1}
MEDAL_FIELDS = {1: "gold", 2: "silver", 3: "bronze"}

_hall_of_fame_cache: tuple[float, HallOfFameRead] | None = None


def empty_stats() -> dict[str, int]:
    return {"points": 0, "gold": 0, "silver": 0, "bronze": 0, "podiums": 0}


def podium_position(row: dict) -> int | None:
    raw_position = row.get("position")
    try:
        position = float(raw_position)
    except (TypeError, ValueError):
        return None
    if not position.is_integer():
        return None
    normalized = int(position)
    return normalized if normalized in PODIUM_POINTS else None


def pilot_payload(user: User, team_name: str | None, stats: dict[str, int]) -> HallOfFamePilotRead:
    return HallOfFamePilotRead(
        id=user.id,
        login=user.login,
        first_name=user.first_name,
        last_name=user.last_name,
        nickname=user.nickname,
        pilot_number=user.pilot_number,
        country=user.country,
        sr=float(user.sr),
        rating=int(round(float(user.rating))),
        rating_race_count=user.rating_race_count,
        avatar_color=user.avatar_color,
        avatar_url=user.avatar_url,
        team_id=user.team_id,
        team_name=team_name,
        points=stats["points"],
        gold=stats["gold"],
        silver=stats["silver"],
        bronze=stats["bronze"],
        podiums=stats["podiums"],
    )


def podium_sort_key(item: HallOfFamePilotRead | HallOfFameTeamRead) -> tuple:
    name = getattr(item, "nickname", None) or getattr(item, "name", None) or ""
    rating = getattr(item, "rating", None)
    if rating is None:
        rating = getattr(item, "average_rating", 0)
    return (-item.points, -item.gold, -item.silver, -item.bronze, -rating, name.lower(), item.id)


@router.get("", response_model=HallOfFameRead)
@limiter.limit("1200/minute")
async def hall_of_fame(request: Request, session: AsyncSession = Depends(get_session)):
    global _hall_of_fame_cache
    now = monotonic()
    if _hall_of_fame_cache is not None and now < _hall_of_fame_cache[0]:
        return _hall_of_fame_cache[1]

    races = (
        await session.scalars(
            select(Race)
            .where(Race.status == RaceStatus.finished, Race.results.is_not(None))
            .order_by(Race.datetime_start.asc(), Race.id.asc())
        )
    ).all()

    pilot_stats: dict[int, dict[str, int]] = defaultdict(empty_stats)
    for race in races:
        race_podiums: dict[int, int] = {}
        for row in result_rows(race.results):
            user_id = row.get("user_id")
            position = podium_position(row)
            if user_id is None or position is None:
                continue
            try:
                normalized_user_id = int(user_id)
            except (TypeError, ValueError):
                continue
            current_position = race_podiums.get(normalized_user_id)
            if current_position is None or position < current_position:
                race_podiums[normalized_user_id] = position

        for user_id, position in race_podiums.items():
            stats = pilot_stats[user_id]
            stats["points"] += PODIUM_POINTS[position]
            stats[MEDAL_FIELDS[position]] += 1
            stats["podiums"] += 1

    if not pilot_stats:
        payload = HallOfFameRead(pilots=[], teams=[])
        _hall_of_fame_cache = (now + HALL_OF_FAME_CACHE_TTL_SECONDS, payload)
        return payload

    user_rows = (
        await session.execute(
            select(User, Team.name)
            .outerjoin(Team, Team.id == User.team_id)
            .where(User.id.in_(pilot_stats.keys()))
        )
    ).all()
    users_by_id = {user.id: (user, team_name) for user, team_name in user_rows}

    pilots = [
        pilot_payload(user, team_name, pilot_stats[user.id])
        for user, team_name in users_by_id.values()
        if pilot_stats[user.id]["points"] > 0
    ]
    pilots.sort(key=podium_sort_key)

    team_stats: dict[int, dict[str, int]] = defaultdict(empty_stats)
    team_pilots: dict[int, list[HallOfFamePilotRead]] = defaultdict(list)
    for pilot in pilots:
        if pilot.team_id is None:
            continue
        stats = team_stats[pilot.team_id]
        stats["points"] += pilot.points
        stats["gold"] += pilot.gold
        stats["silver"] += pilot.silver
        stats["bronze"] += pilot.bronze
        stats["podiums"] += pilot.podiums
        team_pilots[pilot.team_id].append(pilot)

    teams: list[HallOfFameTeamRead] = []
    if team_stats:
        team_ids = list(team_stats.keys())
        loaded_teams = (await session.scalars(select(Team).where(Team.id.in_(team_ids)))).all()
        member_count_rows = await session.execute(
            select(User.team_id, func.count())
            .where(User.team_id.in_(team_ids))
            .group_by(User.team_id)
        )
        average_rating_rows = await session.execute(
            select(User.team_id, func.avg(User.rating))
            .where(User.team_id.in_(team_ids))
            .group_by(User.team_id)
        )
        member_counts = {int(team_id): int(count) for team_id, count in member_count_rows if team_id is not None}
        average_ratings = {int(team_id): int(round(float(average or 0))) for team_id, average in average_rating_rows if team_id is not None}

        for team in loaded_teams:
            stats = team_stats[team.id]
            best_pilot = sorted(team_pilots.get(team.id, []), key=podium_sort_key)[0] if team_pilots.get(team.id) else None
            teams.append(
                HallOfFameTeamRead(
                    id=team.id,
                    name=team.name,
                    description=team.description or "",
                    avatar_color=team.avatar_color,
                    avatar_url=team.avatar_url,
                    owner_id=team.owner_id,
                    member_count=member_counts.get(team.id, 0),
                    average_rating=average_ratings.get(team.id, 0),
                    points=stats["points"],
                    gold=stats["gold"],
                    silver=stats["silver"],
                    bronze=stats["bronze"],
                    podiums=stats["podiums"],
                    best_pilot=best_pilot,
                )
            )
    teams.sort(key=podium_sort_key)

    payload = HallOfFameRead(pilots=pilots, teams=teams)
    _hall_of_fame_cache = (now + HALL_OF_FAME_CACHE_TTL_SECONDS, payload)
    return payload
