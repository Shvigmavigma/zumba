from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AppSetting, DEFAULT_RATING, DEFAULT_SR, MAX_RATING, MAX_SR, MIN_RATING, MIN_SR, RACE_GAMES, Penalty, PenaltyStatus, PenaltyType, Race, RaceStatus, User, default_game_ratings


APPLIED_PENALTY_STATUSES = {PenaltyStatus.active, PenaltyStatus.appealed}
RATING_K_NEWCOMER = 64
RATING_K_DEFAULT = 32
RATING_K_VETERAN = 16
RATING_DELTA_SCALE = 1.5
SYSTEM_SETTINGS_KEY = "system_settings"
RATING_ROW_KEYS = ("rating_old", "rating_new", "rating_delta", "rating_expected", "rating_score", "rating_k")
SR_FINISH_BONUS = 0.3
SR_BONUS_META_KEY = "sr_bonus"


def penalty_time_ms(penalty: Penalty) -> float:
    value = float(penalty.time_penalty_ms or 0)
    if value <= 0 and penalty.penalty_type == PenaltyType.time:
        return float(penalty.penalty_value or 0)
    return value


def penalty_sr_value(penalty: Penalty) -> float:
    value = float(penalty.sr_penalty_value or 0)
    if value <= 0 and penalty.penalty_type == PenaltyType.sr:
        return float(penalty.penalty_value or 0)
    return value


def clamp_rating(value: float) -> int:
    return int(round(min(MAX_RATING, max(MIN_RATING, value))))


def rating_game(game: str | None) -> str:
    return game if game in RACE_GAMES else RACE_GAMES[0]


def user_game_rating_state(user: User, game: str) -> tuple[int, int]:
    ratings = user.game_ratings if isinstance(user.game_ratings, dict) else {}
    item = ratings.get(game) if isinstance(ratings.get(game), dict) else {}
    rating = item.get("rating", user.rating if user.rating is not None else DEFAULT_RATING)
    race_count = item.get("race_count", user.rating_race_count if user.rating_race_count is not None else 0)
    return clamp_rating(float(rating or DEFAULT_RATING)), max(0, int(race_count or 0))


def set_user_game_rating(user: User, game: str, rating: float, race_count: int) -> None:
    ratings = default_game_ratings()
    existing = user.game_ratings if isinstance(user.game_ratings, dict) else {}
    for item_game in RACE_GAMES:
        existing_item = existing.get(item_game)
        if isinstance(existing_item, dict):
            current_rating, current_count = user_game_rating_state(user, item_game)
            ratings[item_game] = {"rating": current_rating, "race_count": current_count}
    normalized_rating = clamp_rating(float(rating))
    normalized_count = max(0, int(race_count))
    ratings[game] = {"rating": normalized_rating, "race_count": normalized_count}
    user.game_ratings = ratings
    if game == RACE_GAMES[0]:
        user.rating = normalized_rating
        user.rating_race_count = normalized_count


def clamp_sr(value: float) -> float:
    return round(min(MAX_SR, max(MIN_SR, value)), 1)


def rating_k_factor(race_count: int) -> int:
    if race_count < 10:
        return RATING_K_NEWCOMER
    if race_count > 50:
        return RATING_K_VETERAN
    return RATING_K_DEFAULT


def result_sort_key(row: dict, fallback_index: int) -> tuple:
    adjusted = row.get("adjusted_finish_ms", row.get("finish_ms"))
    lap_count = row.get("lap_count", 0) or 0
    has_time = isinstance(adjusted, (int, float))
    return (
        0 if has_time else 1,
        -int(lap_count) if isinstance(lap_count, (int, float)) else 0,
        float(adjusted) if has_time else float("inf"),
        fallback_index,
    )


def recalculate_positions(rows: list[dict]) -> list[dict]:
    indexed_rows = [(index, row) for index, row in enumerate(rows)]
    sorted_rows = sorted(indexed_rows, key=lambda item: result_sort_key(item[1], item[0]))
    leader_adjusted: float | None = None
    leader_laps: int | None = None
    recalculated: list[dict] = []

    for position, (_, row) in enumerate(sorted_rows, start=1):
        updated = dict(row)
        adjusted = updated.get("adjusted_finish_ms", updated.get("finish_ms"))
        lap_count = updated.get("lap_count", 0) or 0
        updated["position"] = position
        if isinstance(adjusted, (int, float)):
            if leader_adjusted is None:
                leader_adjusted = float(adjusted)
                leader_laps = int(lap_count) if isinstance(lap_count, (int, float)) else 0
                updated["gap_ms"] = 0
            elif leader_laps is not None and int(lap_count or 0) == leader_laps:
                updated["gap_ms"] = max(0, float(adjusted) - leader_adjusted)
            else:
                updated["gap_ms"] = None
        recalculated.append(updated)
    return recalculated


def result_rows(results: dict | list | None) -> list[dict]:
    if isinstance(results, list):
        return [row for row in results if isinstance(row, dict)]
    if isinstance(results, dict) and isinstance(results.get("rows"), list):
        return [row for row in results["rows"] if isinstance(row, dict)]
    return []


def update_result_rows(results: dict | list | None, rows: list[dict]) -> dict | list | None:
    if isinstance(results, list):
        return rows
    if isinstance(results, dict) and isinstance(results.get("rows"), list):
        updated = dict(results)
        updated["rows"] = rows
        return updated
    return results


def set_sr_bonus_meta(results: dict | list | None, meta: dict | None) -> dict | list | None:
    if isinstance(results, dict):
        updated = dict(results)
    elif isinstance(results, list):
        updated = {"format": "legacy", "rows": results}
    else:
        return results
    if meta is None:
        updated.pop(SR_BONUS_META_KEY, None)
    else:
        updated[SR_BONUS_META_KEY] = meta
    return updated


def sr_bonus_meta(results: dict | list | None) -> dict | None:
    if not isinstance(results, dict):
        return None
    meta = results.get(SR_BONUS_META_KEY)
    return meta if isinstance(meta, dict) else None


def sr_bonus_user_ids(results: dict | list | None) -> list[int]:
    user_ids: list[int] = []
    seen: set[int] = set()
    for row in result_rows(results):
        user_id = row.get("user_id")
        if user_id is None or row.get("status") == "missing":
            continue
        lap_count = row.get("lap_count")
        has_activity = (
            isinstance(row.get("finish_ms"), (int, float))
            or isinstance(row.get("best_lap_ms"), (int, float))
            or (isinstance(lap_count, (int, float)) and lap_count > 0)
        )
        if not has_activity:
            continue
        normalized_user_id = int(user_id)
        if normalized_user_id in seen:
            continue
        seen.add(normalized_user_id)
        user_ids.append(normalized_user_id)
    return user_ids


def rating_time_ms(row: dict) -> float | None:
    adjusted = row.get("adjusted_finish_ms", row.get("finish_ms"))
    if isinstance(adjusted, (int, float)):
        return float(adjusted)
    best_lap = row.get("best_lap_ms")
    if isinstance(best_lap, (int, float)):
        return float(best_lap)
    return None


def rating_source_rows(results: dict | list | None) -> list[dict]:
    best_by_user: dict[int, tuple[int, dict, float]] = {}
    for index, row in enumerate(result_rows(results)):
        user_id = row.get("user_id")
        if user_id is None:
            continue
        time_ms = rating_time_ms(row)
        if time_ms is None:
            continue
        user_id = int(user_id)
        current = best_by_user.get(user_id)
        candidate = (index, row, time_ms)
        if current is None or result_sort_key({**row, "adjusted_finish_ms": time_ms}, index) < result_sort_key({**current[1], "adjusted_finish_ms": current[2]}, current[0]):
            best_by_user[user_id] = candidate
    return [item[1] for item in sorted(best_by_user.values(), key=lambda item: result_sort_key({**item[1], "adjusted_finish_ms": item[2]}, item[0]))]


def rating_positions(rows: list[dict]) -> dict[int, float]:
    explicit_positions: dict[int, float] = {}
    for row in rows:
        user_id = row.get("user_id")
        position = row.get("position")
        if user_id is None or not isinstance(position, (int, float)) or float(position) <= 0:
            explicit_positions = {}
            break
        explicit_positions[int(user_id)] = float(position)
    if len(explicit_positions) == len(rows):
        return explicit_positions

    sorted_rows = sorted(rows, key=lambda row: (rating_time_ms(row) or float("inf"), int(row.get("user_id") or 0)))
    positions: dict[int, float] = {}
    start = 0
    while start < len(sorted_rows):
        time_ms = rating_time_ms(sorted_rows[start])
        end = start + 1
        while end < len(sorted_rows) and rating_time_ms(sorted_rows[end]) == time_ms:
            end += 1
        average_position = (start + 1 + end) / 2
        for row in sorted_rows[start:end]:
            positions[int(row["user_id"])] = average_position
        start = end
    return positions


def build_rating_changes(
    race_rows: list[dict],
    users: dict[int, User],
    game: str,
    rating_change_coefficient: float = RATING_DELTA_SCALE,
) -> tuple[list[dict], float]:
    eligible_rows = [row for row in race_rows if int(row.get("user_id") or 0) in users and rating_time_ms(row) is not None]
    participant_count = len(eligible_rows)
    if participant_count < 2:
        return [], 0

    positions = rating_positions(eligible_rows)
    sof = sum(user_game_rating_state(users[int(row["user_id"])], game)[0] for row in eligible_rows) / participant_count
    changes: list[dict] = []
    for row in eligible_rows:
        user_id = int(row["user_id"])
        user = users[user_id]
        old_rating, race_count_before = user_game_rating_state(user, game)
        expected = 0.0
        for opponent_row in eligible_rows:
            opponent_id = int(opponent_row["user_id"])
            if opponent_id == user_id:
                continue
            opponent_rating = user_game_rating_state(users[opponent_id], game)[0]
            expected += 1 / (1 + 10 ** ((opponent_rating - old_rating) / 400))
        score = participant_count - positions[user_id]
        k_factor = rating_k_factor(race_count_before)
        delta = k_factor * (score - expected) / max(0.01, float(rating_change_coefficient))
        new_rating = clamp_rating(old_rating + delta)
        changes.append(
            {
                "user_id": user_id,
                "old_rating": old_rating,
                "new_rating": new_rating,
                "delta": new_rating - old_rating,
                "position": positions[user_id],
                "score": round(score, 4),
                "expected": round(expected, 4),
                "k": k_factor,
                "time_ms": rating_time_ms(row),
                "race_count_before": race_count_before,
                "race_count_after": race_count_before + 1,
            }
        )
    return changes, sof


def annotate_rating_rows(results: dict | list | None, changes: list[dict], sof: float, game: str) -> dict | list | None:
    rows = result_rows(results)
    if not rows:
        return results
    changes_by_user = {int(change["user_id"]): change for change in changes}
    annotated_rows: list[dict] = []
    for row in rows:
        updated = dict(row)
        user_id = updated.get("user_id")
        change = changes_by_user.get(int(user_id)) if user_id is not None else None
        if change:
            updated["rating_old"] = change["old_rating"]
            updated["rating_new"] = change["new_rating"]
            updated["rating_delta"] = change["delta"]
            updated["rating_expected"] = change["expected"]
            updated["rating_score"] = change["score"]
            updated["rating_k"] = change["k"]
        else:
            for key in RATING_ROW_KEYS:
                updated.pop(key, None)
        annotated_rows.append(updated)
    updated_results = update_result_rows(results, annotated_rows)
    if isinstance(updated_results, dict):
        updated_results["rating"] = {
            "system": "RER",
            "game": game,
            "sof": int(round(sof)),
            "participants": len(changes),
            "changes": changes,
        }
    return updated_results


def clear_rating_annotations(results: dict | list | None) -> dict | list | None:
    rows = result_rows(results)
    if rows:
        clean_rows: list[dict] = []
        for row in rows:
            updated = dict(row)
            for key in RATING_ROW_KEYS:
                updated.pop(key, None)
            clean_rows.append(updated)
        updated_results = update_result_rows(results, clean_rows)
    elif isinstance(results, dict):
        updated_results = dict(results)
    else:
        updated_results = results
    if isinstance(updated_results, dict):
        updated_results.pop("rating", None)
    return updated_results


async def restore_race_rating(session: AsyncSession, race: Race) -> None:
    if not race.rating_applied or not isinstance(race.results, dict):
        return
    rating_meta = race.results.get("rating", {})
    game = rating_game(rating_meta.get("game") if isinstance(rating_meta, dict) else race.game)
    changes = rating_meta.get("changes", []) if isinstance(rating_meta, dict) else []
    if not isinstance(changes, list) or not changes:
        race.rating_applied = False
        return
    user_ids = [int(change["user_id"]) for change in changes if change.get("user_id") is not None]
    users = {user.id: user for user in (await session.scalars(select(User).where(User.id.in_(user_ids)))).all()} if user_ids else {}
    for change in changes:
        user = users.get(int(change.get("user_id") or 0))
        if user is None:
            continue
        set_user_game_rating(user, game, float(change.get("old_rating", DEFAULT_RATING)), int(change.get("race_count_before", 0)))
    race.results = clear_rating_annotations(race.results)
    race.rating_applied = False


async def get_rating_change_coefficient(session: AsyncSession) -> float:
    setting = await session.get(AppSetting, SYSTEM_SETTINGS_KEY)
    value = setting.value if setting is not None and isinstance(setting.value, dict) else {}
    try:
        return max(
            0.01,
            min(
                10.0,
                float(value.get("rating_change_coefficient", value.get("sr_change_coefficient", RATING_DELTA_SCALE))),
            ),
        )
    except (TypeError, ValueError):
        return RATING_DELTA_SCALE


async def apply_race_rating(
    session: AsyncSession,
    race: Race,
    rating_change_coefficient: float | None = None,
) -> None:
    await restore_race_rating(session, race)
    if not race.is_official:
        return
    game = rating_game(race.game)
    rows = rating_source_rows(race.results)
    user_ids = [int(row["user_id"]) for row in rows if row.get("user_id") is not None]
    if len(user_ids) < 2:
        return
    users = {user.id: user for user in (await session.scalars(select(User).where(User.id.in_(user_ids)))).all()}
    coefficient = rating_change_coefficient if rating_change_coefficient is not None else await get_rating_change_coefficient(session)
    changes, sof = build_rating_changes(rows, users, game, coefficient)
    if not changes:
        return
    for change in changes:
        user = users.get(int(change["user_id"]))
        if user is None:
            continue
        set_user_game_rating(user, game, change["new_rating"], int(change["race_count_after"]))
    race.results = annotate_rating_rows(race.results, changes, sof, game)
    race.rating_applied = True


async def recalculate_all_ratings(session: AsyncSession) -> None:
    await recalculate_all_sr(session)
    users = list((await session.scalars(select(User))).all())
    for user in users:
        user.rating = DEFAULT_RATING
        user.rating_race_count = 0
        user.game_ratings = default_game_ratings()

    races = list(
        (
            await session.scalars(
                select(Race)
                .where(Race.status == RaceStatus.finished, Race.results.is_not(None))
                .order_by(Race.datetime_start.asc(), Race.id.asc())
            )
        ).all()
    )
    rating_change_coefficient = await get_rating_change_coefficient(session)
    for race in races:
        race.results = clear_rating_annotations(race.results)
        race.rating_applied = False
        await recalculate_race_results(session, race)
        await apply_race_rating(session, race, rating_change_coefficient)


def recalculate_results(results: dict | list | None, penalties: list[Penalty]) -> dict | list | None:
    if results is None:
        return None

    active_time_penalties: dict[int, float] = {}
    active_sr_penalties: dict[int, float] = {}
    for penalty in penalties:
        if penalty.status not in APPLIED_PENALTY_STATUSES:
            continue
        target_id = penalty.target_id
        time_value = penalty_time_ms(penalty)
        sr_value = penalty_sr_value(penalty)
        if time_value > 0:
            active_time_penalties[target_id] = active_time_penalties.get(target_id, 0) + time_value
        if sr_value > 0:
            active_sr_penalties[target_id] = active_sr_penalties.get(target_id, 0) + sr_value

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
        rows = [apply_to_row(item) if isinstance(item, dict) else item for item in results]
        return recalculate_positions(rows) if all(isinstance(item, dict) for item in rows) else rows
    if isinstance(results, dict) and isinstance(results.get("rows"), list):
        updated = dict(results)
        rows = [apply_to_row(item) if isinstance(item, dict) else item for item in results["rows"]]
        updated["rows"] = recalculate_positions(rows) if all(isinstance(item, dict) for item in rows) else rows
        return updated
    return results


async def recalculate_race_results(session: AsyncSession, race: Race) -> None:
    penalties = list((await session.scalars(select(Penalty).where(Penalty.race_id == race.id))).all())
    race.results = recalculate_results(race.results, penalties)


async def get_sr_per_race(session: AsyncSession) -> float:
    setting = await session.get(AppSetting, SYSTEM_SETTINGS_KEY)
    value = setting.value if setting is not None and isinstance(setting.value, dict) else {}
    try:
        return max(0.0, min(100.0, float(value.get("sr_per_race", value.get("sr_finish_bonus", SR_FINISH_BONUS)))))
    except (TypeError, ValueError):
        return SR_FINISH_BONUS


async def recalculate_all_sr(session: AsyncSession) -> None:
    """Rebuild SR from the configured per-race amount and finished results."""
    users = list((await session.scalars(select(User))).all())
    for user in users:
        user.sr = DEFAULT_SR

    penalties = list((await session.scalars(select(Penalty))).all())
    for penalty in penalties:
        penalty.is_applied = False
        penalty.sr_applied_value = 0

    races = list(
        (
            await session.scalars(
                select(Race)
                .where(Race.status == RaceStatus.finished, Race.results.is_not(None))
                .order_by(Race.datetime_start.asc(), Race.id.asc())
            )
        ).all()
    )
    for race in races:
        race.results = set_sr_bonus_meta(race.results, None)
        await recalculate_race_results(session, race)
        await apply_sr_penalties(session, race)


async def restore_race_sr_bonus(session: AsyncSession, race: Race) -> None:
    meta = sr_bonus_meta(race.results)
    changes = meta.get("changes", []) if meta else []
    if not isinstance(changes, list) or not changes:
        race.results = set_sr_bonus_meta(race.results, None)
        return
    user_ids = [int(change["user_id"]) for change in changes if change.get("user_id") is not None]
    users = {user.id: user for user in (await session.scalars(select(User).where(User.id.in_(user_ids)))).all()} if user_ids else {}
    for change in changes:
        user = users.get(int(change.get("user_id") or 0))
        if user is None:
            continue
        applied_value = float(change.get("applied_value") or 0)
        user.sr = clamp_sr(float(user.sr or 0) - applied_value)
    race.results = set_sr_bonus_meta(race.results, None)


async def award_race_sr_bonus(session: AsyncSession, race: Race) -> None:
    if race.status != RaceStatus.finished or race.results is None:
        return
    user_ids = sr_bonus_user_ids(race.results)
    if not user_ids:
        race.results = set_sr_bonus_meta(race.results, None)
        return
    users = {user.id: user for user in (await session.scalars(select(User).where(User.id.in_(user_ids)))).all()}
    bonus_value = await get_sr_per_race(session)
    changes: list[dict] = []
    for user_id in user_ids:
        user = users.get(user_id)
        if user is None:
            continue
        old_sr = clamp_sr(float(user.sr or 0))
        applied_value = min(bonus_value, max(0, MAX_SR - old_sr))
        new_sr = clamp_sr(old_sr + applied_value)
        user.sr = new_sr
        changes.append(
            {
                "user_id": user_id,
                "old_sr": old_sr,
                "new_sr": new_sr,
                "bonus_value": round(bonus_value, 3),
                "applied_value": round(applied_value, 3),
            }
        )
    race.results = set_sr_bonus_meta(
        race.results,
        {
            "system": "SR",
            "bonus_value": round(bonus_value, 3),
            "participants": len(changes),
            "changes": changes,
        },
    )


async def apply_race_sr_bonus(session: AsyncSession, race: Race) -> None:
    await restore_race_sr_bonus(session, race)
    await award_race_sr_bonus(session, race)


async def apply_sr_penalty(session: AsyncSession, penalty: Penalty) -> None:
    if penalty.status not in APPLIED_PENALTY_STATUSES or penalty.is_applied:
        return
    penalty_value = penalty_sr_value(penalty)
    if penalty_value <= 0:
        return
    target = await session.get(User, penalty.target_id)
    if target is None:
        return
    current_sr = float(target.sr)
    applied_value = min(penalty_value, max(0, current_sr - MIN_SR))
    target.sr = clamp_sr(current_sr - applied_value)
    penalty.sr_applied_value = applied_value
    penalty.is_applied = True


async def apply_sr_penalties(session: AsyncSession, race: Race) -> None:
    await restore_race_sr_bonus(session, race)
    penalties = (
        await session.scalars(
            select(Penalty).where(
                Penalty.race_id == race.id,
                Penalty.sr_penalty_value > 0,
                Penalty.status.in_(APPLIED_PENALTY_STATUSES),
                Penalty.is_applied.is_(False),
            )
        )
    ).all()
    for penalty in penalties:
        await apply_sr_penalty(session, penalty)
    await award_race_sr_bonus(session, race)


async def restore_sr_penalty(session: AsyncSession, penalty: Penalty) -> None:
    if not penalty.is_applied:
        return
    target = await session.get(User, penalty.target_id)
    if target is not None:
        applied_value = float(penalty.sr_applied_value or 0)
        target.sr = clamp_sr(float(target.sr) + applied_value)
    penalty.sr_applied_value = 0
    penalty.is_applied = False
