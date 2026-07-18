from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Penalty, PenaltyStatus, PenaltyType, Race, User


def recalculate_results(results: dict | list | None, penalties: list[Penalty]) -> dict | list | None:
    if results is None:
        return None

    active_time_penalties: dict[int, float] = {}
    active_sr_penalties: dict[int, float] = {}
    for penalty in penalties:
        if penalty.status != PenaltyStatus.active:
            continue
        target_id = penalty.target_id
        if penalty.penalty_type == PenaltyType.time:
            active_time_penalties[target_id] = active_time_penalties.get(target_id, 0) + float(penalty.penalty_value)
        if penalty.penalty_type == PenaltyType.sr:
            active_sr_penalties[target_id] = active_sr_penalties.get(target_id, 0) + float(penalty.penalty_value)

    def apply_to_row(row: dict) -> dict:
        user_id = row.get("user_id")
        if user_id is None:
            return row
        updated = dict(row)
        base_ms = updated.get("finish_ms")
        time_penalty = active_time_penalties.get(int(user_id), 0)
        sr_penalty = active_sr_penalties.get(int(user_id), 0)
        updated["time_penalty_ms"] = time_penalty
        updated["sr_penalty"] = sr_penalty
        if isinstance(base_ms, (int, float)):
            updated["adjusted_finish_ms"] = base_ms + time_penalty
        return updated

    if isinstance(results, list):
        return [apply_to_row(item) if isinstance(item, dict) else item for item in results]
    if isinstance(results, dict) and isinstance(results.get("rows"), list):
        updated = dict(results)
        updated["rows"] = [apply_to_row(item) if isinstance(item, dict) else item for item in results["rows"]]
        return updated
    return results


async def recalculate_race_results(session: AsyncSession, race: Race) -> None:
    penalties = list((await session.scalars(select(Penalty).where(Penalty.race_id == race.id))).all())
    race.results = recalculate_results(race.results, penalties)


async def apply_sr_penalties(session: AsyncSession, race: Race) -> None:
    penalties = (
        await session.scalars(
            select(Penalty).where(
                Penalty.race_id == race.id,
                Penalty.penalty_type == PenaltyType.sr,
                Penalty.status == PenaltyStatus.active,
                Penalty.is_applied.is_(False),
            )
        )
    ).all()
    for penalty in penalties:
        target = await session.get(User, penalty.target_id)
        if target is not None:
            target.sr = max(5.0, float(target.sr) - float(penalty.penalty_value))
            penalty.is_applied = True


async def restore_sr_penalty(session: AsyncSession, penalty: Penalty) -> None:
    if penalty.penalty_type != PenaltyType.sr or not penalty.is_applied:
        return
    target = await session.get(User, penalty.target_id)
    if target is not None:
        target.sr = min(30.0, float(target.sr) + float(penalty.penalty_value))
    penalty.is_applied = False

