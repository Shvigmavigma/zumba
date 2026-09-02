import copy
import json
import secrets
from pathlib import Path
from threading import Lock
from time import time
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import Response
from redis import Redis
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.deps import MODER_PLUS, require_roles
from app.models import MediaCompetition, User
from app.rate_limit import limiter


router = APIRouter()
settings = get_settings()
UPLOAD_DIR = Path(settings.upload_dir) / "competitions"
ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}
MAX_IMAGE_BYTES = 12 * 1024 * 1024
CAPTCHA_TTL_SECONDS = 10 * 60
_captcha_store: dict[str, tuple[int, float]] = {}
_captcha_lock = Lock()
_captcha_redis: Redis | None = None


def empty_data() -> dict:
    return {
        "participants": [],
        "votes": {},
        "voters": {},
        "matches": [],
        "results": [],
        "settings": {"variant": "direct", "group_count": 2, "advancing_places": [1]},
    }


def participant_by_id(data: dict, participant_id: str) -> dict | None:
    return next((item for item in data.get("participants", []) if item.get("id") == participant_id), None)


def public_path(item: MediaCompetition) -> str:
    return f"/competitions/view/{item.public_token}"


def bracket_path(item: MediaCompetition) -> str:
    return f"/competitions/bracket/{item.public_token}"


def participant_public(item: dict) -> dict:
    return {
        "id": item.get("id"),
        "name": item.get("name", "Без названия"),
        "images": list(item.get("images") or [])[:4],
        "votes": int(item.get("votes", 0)),
    }


def persist_data(item: MediaCompetition, data: dict) -> None:
    # JSONB has no mutable tracking by default; assigning a deep copy ensures
    # nested participant/bracket edits are written in the same transaction.
    item.data = copy.deepcopy(data)


def staff_payload(item: MediaCompetition) -> dict:
    data = copy.deepcopy(item.data or empty_data())
    participants = [participant_public(participant) for participant in data.get("participants", [])]
    matches = []
    for match in data.get("matches", []):
        participant_a = participant_by_id(data, match.get("a"))
        participant_b = participant_by_id(data, match.get("b"))
        matches.append({
            **match,
            "a_name": participant_a.get("name") if participant_a else None,
            "b_name": participant_b.get("name") if participant_b else None,
            "public_path": f"{public_path(item)}?match={match.get('id')}" if match.get("id") else public_path(item),
        })
    return {
        "id": item.id,
        "name": item.name,
        "kind": item.kind,
        "status": item.status,
        "public_token": item.public_token,
        "public_path": public_path(item),
        "public_bracket_path": bracket_path(item) if item.kind == "tournament" else None,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "settings": data.get("settings", {}),
        "participants": participants,
        "matches": matches,
        "results": data.get("results", []),
    }


def captcha_payload() -> dict:
    first, second = secrets.randbelow(8) + 2, secrets.randbelow(8) + 2
    # Keep the expected answer on the server.  Encoding the operands into a
    # client-visible HMAC token would let a bot decode the answer directly.
    token = secrets.token_urlsafe(32)
    expected = first + second
    store = _captcha_redis_client()
    if store is not None:
        try:
            store.setex(f"bmrl:captcha:{token}", CAPTCHA_TTL_SECONDS, expected)
        except Exception:
            store = None
    if store is None:
        now = time()
        with _captcha_lock:
            expired = [key for key, (_, expires_at) in _captcha_store.items() if expires_at <= now]
            for key in expired:
                _captcha_store.pop(key, None)
            _captcha_store[token] = (expected, now + CAPTCHA_TTL_SECONDS)
    return {"question": f"Сколько будет {first} + {second}?", "token": token}


def check_captcha(token: str, answer: int) -> bool:
    token = str(token or "").strip()
    if not token or len(token) > 128:
        return False
    store = _captcha_redis_client()
    if store is not None:
        try:
            expected = store.get(f"bmrl:captcha:{token}")
            return expected is not None and int(expected) == int(answer)
        except (TypeError, ValueError):
            return False
        except Exception:
            pass
    now = time()
    with _captcha_lock:
        entry = _captcha_store.get(token)
        if entry is None:
            return False
        expected, expires_at = entry
        if expires_at <= now:
            _captcha_store.pop(token, None)
            return False
    try:
        return expected == int(answer)
    except (TypeError, ValueError):
        return False


def _captcha_redis_client() -> Redis | None:
    global _captcha_redis
    if _captcha_redis is not None:
        return _captcha_redis
    uri = settings.rate_limit_storage_uri or ""
    if not uri.startswith(("redis://", "rediss://")):
        return None
    try:
        _captcha_redis = Redis.from_url(uri, decode_responses=True, socket_connect_timeout=0.2, socket_timeout=0.2)
    except Exception:
        return None
    return _captcha_redis


def playoff_matches(participants: list[str], stage: str = "playoff") -> list[dict]:
    matches = []
    for index in range(0, len(participants) - 1, 2):
        matches.append({
            "id": uuid4().hex,
            "round": 1,
            "stage": stage,
            "a": participants[index],
            "b": participants[index + 1],
            "winner": None,
            "votes_a": 0,
            "votes_b": 0,
            "status": "open",
        })
    if len(participants) % 2:
        matches.append({
            "id": uuid4().hex,
            "round": 1,
            "stage": stage,
            "a": participants[-1],
            "b": None,
            "winner": participants[-1],
            "votes_a": 0,
            "votes_b": 0,
            "status": "bye",
        })
    return matches


def bracket_match(participant_a: str | None, participant_b: str | None, *, stage: str, round_number: int = 1, bracket: str | None = None) -> dict:
    match = {
        "id": uuid4().hex,
        "round": round_number,
        "stage": stage,
        "a": participant_a,
        "b": participant_b,
        "winner": participant_a if participant_b is None else None,
        "votes_a": 0,
        "votes_b": 0,
        "status": "bye" if participant_b is None else "open",
    }
    if bracket:
        match["bracket"] = bracket
    return match


def match_loser(match: dict) -> str | None:
    winner = match.get("winner")
    if winner == match.get("a"):
        return match.get("b")
    if winner == match.get("b"):
        return match.get("a")
    return None


def _round_number(match: dict) -> int:
    try:
        return int(match.get("round", 1))
    except (TypeError, ValueError):
        return 1


def tournament_final_match(data: dict) -> dict | None:
    """Return the final progression match for any tournament variant."""
    matches = data.get("matches", [])
    if data.get("settings", {}).get("variant") == "double_elimination":
        return next(
            (
                match
                for match in matches
                if match.get("stage") == "playoff" and match.get("bracket") == "final"
            ),
            None,
        )
    progression = [
        match
        for match in matches
        if match.get("stage") not in {"group", "third_place"}
    ]
    return max(progression, key=_round_number, default=None)


def tournament_results_ready(data: dict) -> bool:
    """Only expose final standings after every required match is resolved."""
    final = tournament_final_match(data)
    if final is None or final.get("status") == "open" or not final.get("winner"):
        return False
    third_place = next(
        (match for match in data.get("matches", []) if match.get("stage") == "third_place"),
        None,
    )
    return third_place is None or (
        third_place.get("status") != "open" and bool(third_place.get("winner"))
    )


def build_tournament_results(data: dict) -> list[dict]:
    """Build deterministic standings shared by close and match-finalization."""
    final = tournament_final_match(data)
    third_place = next(
        (match for match in data.get("matches", []) if match.get("stage") == "third_place"),
        None,
    )
    ordered_ids: list[str] = []
    for match in (final, third_place):
        if not match:
            continue
        for participant_id in (match.get("winner"), match_loser(match)):
            if participant_id and participant_id not in ordered_ids:
                ordered_ids.append(participant_id)
    ordered_ids.extend(
        entry.get("id")
        for entry in data.get("participants", [])
        if entry.get("id") not in ordered_ids
    )
    vote_totals: dict[str, int] = {}
    for match in data.get("matches", []):
        if match.get("a"):
            vote_totals[match["a"]] = vote_totals.get(match["a"], 0) + int(match.get("votes_a", 0))
        if match.get("b"):
            vote_totals[match["b"]] = vote_totals.get(match["b"], 0) + int(match.get("votes_b", 0))
    return [
        {
            "place": index + 1,
            "participant_id": participant_id,
            "votes": vote_totals.get(participant_id, 0),
        }
        for index, participant_id in enumerate(ordered_ids)
    ]


def normalize_advancing_places(value) -> list[int]:
    if not isinstance(value, (list, tuple, set)):
        return [1]
    places = set()
    for entry in value:
        try:
            place = int(entry)
        except (TypeError, ValueError):
            continue
        if place >= 1:
            places.add(place)
    return sorted(places) or [1]


def build_matches(data: dict) -> None:
    participants = [item["id"] for item in data.get("participants", [])]
    if len(participants) < 2:
        raise HTTPException(status_code=400, detail="Добавьте минимум двух участников")
    data["matches"] = []
    data["results"] = []
    settings_data = data.setdefault("settings", {})
    variant = settings_data.get("variant", "direct")
    if variant == "double_elimination":
        if len(participants) != 8:
            raise HTTPException(status_code=400, detail="Верхняя и нижняя сетка требуют ровно 8 участников")
        settings_data["phase"] = "double_upper"
        data["matches"] = [
            bracket_match(participants[index], participants[index + 1], stage="upper", round_number=1, bracket="upper")
            for index in range(0, 8, 2)
        ]
        return
    if variant == "groups":
        group_count = max(2, min(int(settings_data.get("group_count", 2) or 2), len(participants)))
        settings_data["advancing_places"] = normalize_advancing_places(settings_data.get("advancing_places"))
        groups = [[] for _ in range(group_count)]
        for index, participant_id in enumerate(participants):
            groups[index % group_count].append(participant_id)
        data["groups"] = groups
        settings_data["phase"] = "groups"
        for group_index, group in enumerate(groups, 1):
            for index, participant_a in enumerate(group):
                for participant_b in group[index + 1:]:
                    data["matches"].append({
                        "id": uuid4().hex,
                        "round": 1,
                        "stage": "group",
                        "group": group_index,
                        "a": participant_a,
                        "b": participant_b,
                        "winner": None,
                        "votes_a": 0,
                        "votes_b": 0,
                        "status": "open",
                    })
        if not data["matches"]:
            raise HTTPException(status_code=400, detail="В каждой группе должно быть минимум два участника")
        return
    data.setdefault("settings", {})["phase"] = "playoff"
    data["matches"] = playoff_matches(participants, "qualifying" if variant == "qualifying" else "playoff")


def advance_double_elimination(data: dict) -> None:
    """Advance the fixed 8-participant upper/lower qualification bracket.

    The opening round is shared. Its winners continue through the upper
    bracket and its losers through the lower bracket. Each route then gets its
    own semifinal (upper-vs-upper and lower-vs-lower), after which those two
    semifinal winners meet in the final and the losers play for third place.
    """
    matches = data.setdefault("matches", [])
    settings_data = data.setdefault("settings", {})

    upper_round_one = [match for match in matches if match.get("bracket") == "upper" and int(match.get("round", 1)) == 1]
    lower_round_one = [match for match in matches if match.get("bracket") == "lower" and int(match.get("round", 1)) == 1]
    upper_round_two = [match for match in matches if match.get("bracket") == "upper" and int(match.get("round", 1)) == 2]
    semifinals = [match for match in matches if match.get("stage") == "semifinal"]
    final = [match for match in matches if match.get("stage") == "playoff" and match.get("bracket") == "final"]

    if len(upper_round_one) == 4 and not lower_round_one and not upper_round_two and all(match.get("status") != "open" for match in upper_round_one):
        upper_winners = [match.get("winner") for match in upper_round_one if match.get("winner")]
        upper_losers = [match_loser(match) for match in upper_round_one]
        if len(upper_winners) == 4 and len(upper_losers) == 4:
            matches.extend([
                bracket_match(upper_winners[0], upper_winners[1], stage="upper", round_number=2, bracket="upper"),
                bracket_match(upper_winners[2], upper_winners[3], stage="upper", round_number=2, bracket="upper"),
                bracket_match(upper_losers[0], upper_losers[1], stage="lower", round_number=1, bracket="lower"),
                bracket_match(upper_losers[2], upper_losers[3], stage="lower", round_number=1, bracket="lower"),
            ])
            settings_data["phase"] = "double_brackets"
        return

    if len(upper_round_two) == 2 and len(lower_round_one) == 2 and not semifinals and all(
        match.get("status") != "open" for match in [*upper_round_two, *lower_round_one]
    ):
        upper_winners = [match.get("winner") for match in upper_round_two if match.get("winner")]
        lower_winners = [match.get("winner") for match in lower_round_one if match.get("winner")]
        if len(upper_winners) == 2 and len(lower_winners) == 2:
            matches.extend([
                bracket_match(upper_winners[0], upper_winners[1], stage="semifinal", round_number=1, bracket="upper"),
                bracket_match(lower_winners[0], lower_winners[1], stage="semifinal", round_number=1, bracket="lower"),
            ])
            settings_data["phase"] = "semifinal"
        return

    if len(semifinals) == 2 and not final and all(match.get("status") != "open" for match in semifinals):
        semifinal_winners = [match.get("winner") for match in semifinals if match.get("winner")]
        semifinal_losers = [match_loser(match) for match in semifinals]
        if len(semifinal_winners) == 2 and len(semifinal_losers) == 2:
            matches.extend([
                bracket_match(semifinal_winners[0], semifinal_winners[1], stage="playoff", round_number=2, bracket="final"),
                bracket_match(semifinal_losers[0], semifinal_losers[1], stage="third_place", round_number=2, bracket="third_place"),
            ])
            settings_data["phase"] = "final"


def advance_bracket(data: dict) -> None:
    if data.get("settings", {}).get("variant") == "double_elimination":
        advance_double_elimination(data)
        return
    while True:
        progression_matches = [item for item in data.get("matches", []) if item.get("stage") not in {"group", "third_place"}]
        rounds = sorted({int(item.get("round", 1)) for item in progression_matches})
        advanced = False
        for round_number in rounds:
            matches = [item for item in progression_matches if int(item.get("round", 1)) == round_number]
            if not matches or any(item.get("status") == "open" for item in matches):
                continue
            winners = [item["winner"] for item in matches if item.get("winner")]
            if len(winners) <= 1:
                data["results"] = [{"place": 1, "participant_id": winners[0]}] if winners else []
                return
            next_round = round_number + 1
            if any(int(item.get("round", 1)) == next_round for item in data["matches"]):
                continue
            if len(winners) == 2 and len(matches) == 2:
                losers = [match_loser(match) for match in matches]
                if all(losers):
                    data["matches"].append(bracket_match(losers[0], losers[1], stage="third_place", round_number=next_round, bracket="third_place"))
            for index in range(0, len(winners) - 1, 2):
                data["matches"].append(bracket_match(winners[index], winners[index + 1], stage="playoff", round_number=next_round))
            if len(winners) % 2:
                bye = winners[-1]
                data["matches"].append(bracket_match(bye, None, stage="playoff", round_number=next_round))
            advanced = True
            break
        if not advanced:
            return


async def get_competition(competition_id: int, session: AsyncSession) -> MediaCompetition:
    item = await session.get(MediaCompetition, competition_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Соревнование не найдено")
    return item


async def get_public_competition(token: str, session: AsyncSession) -> MediaCompetition:
    item = await session.scalar(select(MediaCompetition).where(MediaCompetition.public_token == token))
    if item is None:
        raise HTTPException(status_code=404, detail="Ссылка на соревнование недействительна")
    return item


@router.get("", response_model=None)
@limiter.limit("120/minute")
async def list_competitions(request: Request, _: User = Depends(require_roles(MODER_PLUS)), session: AsyncSession = Depends(get_session)):
    items = (await session.scalars(select(MediaCompetition).order_by(desc(MediaCompetition.updated_at)).limit(10))).all()
    return [staff_payload(item) for item in items]


@router.post("", status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_competition(request: Request, payload: dict, user: User = Depends(require_roles(MODER_PLUS)), session: AsyncSession = Depends(get_session)):
    existing = (await session.scalars(select(MediaCompetition).limit(11))).all()
    if len(existing) >= 10:
        raise HTTPException(status_code=400, detail="Можно создать не более 10 соревнований")
    name = str(payload.get("name") or "").strip()
    kind = str(payload.get("kind") or "vote").strip().lower()
    if not name or len(name) > 160:
        raise HTTPException(status_code=422, detail="Укажите название соревнования")
    if kind not in {"vote", "tournament"}:
        raise HTTPException(status_code=422, detail="Неизвестный тип соревнования")
    item = MediaCompetition(name=name, kind=kind, public_token=secrets.token_urlsafe(24), data=empty_data(), created_by=user.id)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return staff_payload(item)


@router.get("/{competition_id}")
@limiter.limit("240/minute")
async def get_competition_for_staff(competition_id: int, request: Request, _: User = Depends(require_roles(MODER_PLUS)), session: AsyncSession = Depends(get_session)):
    return staff_payload(await get_competition(competition_id, session))


@router.patch("/{competition_id}")
@limiter.limit("60/minute")
async def update_competition(competition_id: int, request: Request, payload: dict, _: User = Depends(require_roles(MODER_PLUS)), session: AsyncSession = Depends(get_session)):
    item = await get_competition(competition_id, session)
    if item.status == "complete":
        raise HTTPException(status_code=400, detail="Завершённое соревнование нельзя изменять")
    if "name" in payload:
        name = str(payload.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=422, detail="Название не может быть пустым")
        item.name = name[:160]
    data = copy.deepcopy(item.data or empty_data())
    settings_data = data.setdefault("settings", {})
    settings_data.update({key: payload[key] for key in ("variant", "group_count") if key in payload})
    if "advancing_places" in payload:
        settings_data["advancing_places"] = normalize_advancing_places(payload.get("advancing_places"))
    persist_data(item, data)
    await session.commit()
    await session.refresh(item)
    return staff_payload(item)


@router.delete("/{competition_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_competition(competition_id: int, request: Request, _: User = Depends(require_roles(MODER_PLUS)), session: AsyncSession = Depends(get_session)):
    item = await get_competition(competition_id, session)
    for participant in (item.data or {}).get("participants", []):
        for image_url in participant.get("images", []):
            path = UPLOAD_DIR / Path(str(image_url).removeprefix("/api/uploads/competitions/")).name
            if path.exists():
                path.unlink()
    await session.delete(item)
    await session.commit()


@router.post("/{competition_id}/participants")
@limiter.limit("120/minute")
async def add_participant(competition_id: int, request: Request, payload: dict, _: User = Depends(require_roles(MODER_PLUS)), session: AsyncSession = Depends(get_session)):
    item = await get_competition(competition_id, session)
    if item.status != "draft":
        raise HTTPException(status_code=400, detail="Участников можно добавлять только в черновик")
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="Укажите имя участника")
    data = copy.deepcopy(item.data or empty_data())
    participant = {"id": uuid4().hex, "name": name[:120], "images": [], "votes": 0}
    data.setdefault("participants", []).append(participant)
    persist_data(item, data)
    await session.commit()
    return participant_public(participant)


@router.patch("/{competition_id}/participants/{participant_id}")
@limiter.limit("120/minute")
async def update_participant(competition_id: int, participant_id: str, request: Request, payload: dict, _: User = Depends(require_roles(MODER_PLUS)), session: AsyncSession = Depends(get_session)):
    item = await get_competition(competition_id, session)
    if item.status != "draft":
        raise HTTPException(status_code=400, detail="Завершённое соревнование нельзя изменять")
    data = copy.deepcopy(item.data or empty_data())
    participant = participant_by_id(data, participant_id)
    if participant is None:
        raise HTTPException(status_code=404, detail="Участник не найден")
    name = str(payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="Имя не может быть пустым")
    participant["name"] = name[:120]
    persist_data(item, data)
    await session.commit()
    return participant_public(participant)


@router.delete("/{competition_id}/participants/{participant_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("120/minute")
async def delete_participant(competition_id: int, participant_id: str, request: Request, _: User = Depends(require_roles(MODER_PLUS)), session: AsyncSession = Depends(get_session)):
    item = await get_competition(competition_id, session)
    if item.status != "draft":
        raise HTTPException(status_code=400, detail="Завершённое соревнование нельзя изменять")
    data = copy.deepcopy(item.data or empty_data())
    participant = participant_by_id(data, participant_id)
    if participant is None:
        raise HTTPException(status_code=404, detail="Участник не найден")
    data["participants"] = [entry for entry in data.get("participants", []) if entry.get("id") != participant_id]
    persist_data(item, data)
    await session.commit()


@router.post("/{competition_id}/participants/{participant_id}/media")
@limiter.limit("60/minute")
async def upload_participant_media(competition_id: int, participant_id: str, request: Request, file: list[UploadFile] = File(...), _: User = Depends(require_roles(MODER_PLUS)), session: AsyncSession = Depends(get_session)):
    item = await get_competition(competition_id, session)
    if item.status != "draft":
        raise HTTPException(status_code=400, detail="Медиа можно загружать только в черновик")
    # Copy before touching nested participant data. JSONB values are mutable
    # Python objects; mutating item.data first makes SQLAlchemy's old/new
    # comparison see the same object and skip the UPDATE entirely.
    competition_data = copy.deepcopy(item.data or empty_data())
    participant = participant_by_id(competition_data, participant_id)
    if participant is None:
        raise HTTPException(status_code=404, detail="Участник не найден")
    files = list(file or [])
    if not files:
        raise HTTPException(status_code=422, detail="Выберите хотя бы одно изображение")
    free_slots = max(0, 4 - len(participant.get("images", [])))
    if not free_slots:
        raise HTTPException(status_code=400, detail="Можно загрузить не более 4 изображений")

    # Read and validate every selected file before changing the participant. This
    # keeps a multi-file upload all-or-nothing and avoids half-filled cards when
    # one of the selected files is invalid.
    prepared: list[tuple[bytes, str]] = []
    for upload in files[:free_slots]:
        extension = ALLOWED_IMAGE_TYPES.get(upload.content_type or "")
        if not extension:
            raise HTTPException(status_code=415, detail="Поддерживаются PNG, JPG, WEBP и GIF")
        file_data = await upload.read()
        if not file_data or len(file_data) > MAX_IMAGE_BYTES:
            raise HTTPException(status_code=413, detail="Изображение пустое или больше 12 МБ")
        prepared.append((file_data, extension))

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    written_paths: list[Path] = []
    try:
        new_images: list[str] = []
        for file_data, extension in prepared:
            path = UPLOAD_DIR / f"{competition_id}-{uuid4().hex}{extension}"
            path.write_bytes(file_data)
            written_paths.append(path)
            new_images.append(f"/api/uploads/competitions/{path.name}")
        participant.setdefault("images", []).extend(new_images)
        persist_data(item, competition_data)
        await session.commit()
    except Exception:
        for path in written_paths:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass
        raise
    return participant_public(participant)


@router.delete("/{competition_id}/participants/{participant_id}/media/{media_index}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("120/minute")
async def delete_participant_media(competition_id: int, participant_id: str, media_index: int, request: Request, _: User = Depends(require_roles(MODER_PLUS)), session: AsyncSession = Depends(get_session)):
    item = await get_competition(competition_id, session)
    data = copy.deepcopy(item.data or empty_data())
    participant = participant_by_id(data, participant_id)
    if participant is None or media_index < 0 or media_index >= len(participant.get("images", [])):
        raise HTTPException(status_code=404, detail="Изображение не найдено")
    image_url = participant["images"].pop(media_index)
    path = UPLOAD_DIR / Path(str(image_url).removeprefix("/api/uploads/competitions/")).name
    if path.exists():
        path.unlink()
    persist_data(item, data)
    await session.commit()


@router.post("/{competition_id}/start")
@limiter.limit("30/minute")
async def start_competition(competition_id: int, request: Request, _: User = Depends(require_roles(MODER_PLUS)), session: AsyncSession = Depends(get_session)):
    item = await get_competition(competition_id, session)
    if item.status != "draft":
        raise HTTPException(status_code=400, detail="Соревнование уже запущено")
    data = copy.deepcopy(item.data or empty_data())
    if item.kind == "tournament":
        build_matches(data)
    elif len(data.get("participants", [])) < 2:
        raise HTTPException(status_code=400, detail="Добавьте минимум двух участников")
    persist_data(item, data)
    item.status = "in-progress"
    await session.commit()
    return staff_payload(item)


@router.post("/{competition_id}/close")
@limiter.limit("30/minute")
async def close_competition(competition_id: int, request: Request, _: User = Depends(require_roles(MODER_PLUS)), session: AsyncSession = Depends(get_session)):
    item = await get_competition(competition_id, session)
    if item.status != "in-progress":
        raise HTTPException(status_code=400, detail="Соревнование не запущено")
    data = copy.deepcopy(item.data or empty_data())
    if item.kind == "tournament":
        settings_data = data.setdefault("settings", {})
        if settings_data.get("variant") == "groups" and settings_data.get("phase") == "groups":
            group_matches = [match for match in data.get("matches", []) if match.get("stage") == "group"]
            if any(match.get("status") == "open" for match in group_matches):
                raise HTTPException(status_code=400, detail="Сначала завершите все групповые пары")
            advancing_places = normalize_advancing_places(settings_data.get("advancing_places"))
            advancers = []
            for group_index, group in enumerate(data.get("groups", []), 1):
                points = {participant_id: 0 for participant_id in group}
                for match in group_matches:
                    if match.get("group") != group_index or not match.get("winner"):
                        continue
                    points[match["winner"]] = points.get(match["winner"], 0) + 3
                standings = sorted(group, key=lambda participant_id: (-points.get(participant_id, 0), group.index(participant_id)))
                advancers.extend(standings[place - 1] for place in advancing_places if place <= len(standings))
            settings_data["phase"] = "playoff"
            # Keep completed group matches in the public payload so viewers can
            # switch between the group stage and the playoff bracket.
            data["matches"] = group_matches + playoff_matches(advancers)
            persist_data(item, data)
            await session.commit()
            await session.refresh(item)
            return staff_payload(item)
        advance_bracket(data)
        if any(match.get("status") == "open" and not match.get("winner") for match in data.get("matches", [])):
            raise HTTPException(status_code=400, detail="Сначала завершите все пары")
    if item.kind == "tournament":
        data["results"] = build_tournament_results(data)
    else:
        participants = sorted(data.get("participants", []), key=lambda entry: (-int(entry.get("votes", 0)), str(entry.get("name", "")).lower()))
        data["results"] = [{"place": index + 1, "participant_id": entry.get("id"), "votes": int(entry.get("votes", 0))} for index, entry in enumerate(participants)]
    persist_data(item, data)
    item.status = "complete"
    await session.commit()
    return staff_payload(item)


@router.post("/{competition_id}/matches/{match_id}/close")
@limiter.limit("120/minute")
async def close_match(competition_id: int, match_id: str, request: Request, _: User = Depends(require_roles(MODER_PLUS)), session: AsyncSession = Depends(get_session)):
    item = await get_competition(competition_id, session)
    if item.kind != "tournament" or item.status != "in-progress":
        raise HTTPException(status_code=400, detail="Пара недоступна")
    data = copy.deepcopy(item.data or empty_data())
    match = next((entry for entry in data.get("matches", []) if entry.get("id") == match_id), None)
    if match is None or match.get("status") != "open":
        raise HTTPException(status_code=404, detail="Пара не найдена")
    votes_a, votes_b = int(match.get("votes_a", 0)), int(match.get("votes_b", 0))
    if votes_a == votes_b:
        raise HTTPException(status_code=400, detail="Для завершения пары нужен явный победитель")
    match["winner"] = match.get("a") if votes_a > votes_b else match.get("b")
    match["status"] = "closed"
    if match.get("stage") != "group":
        advance_bracket(data)
    if tournament_results_ready(data):
        data["results"] = build_tournament_results(data)
    elif item.kind == "tournament":
        # ``advance_bracket`` may produce a temporary winner as soon as the
        # final closes. Keep standings empty until the required third-place
        # match (when present) is also fixed, so public results never look
        # complete too early.
        data["results"] = []
    persist_data(item, data)
    await session.commit()
    return staff_payload(item)


@router.get("/{competition_id}/export")
@limiter.limit("60/minute")
async def export_competition(competition_id: int, request: Request, _: User = Depends(require_roles(MODER_PLUS)), session: AsyncSession = Depends(get_session)):
    item = await get_competition(competition_id, session)
    payload = staff_payload(item)
    content = json.dumps(payload, ensure_ascii=False, default=str, indent=2).encode("utf-8")
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="competition-{item.id}.json"'},
    )


@router.get("/public/{token}")
@limiter.limit("600/minute")
async def public_competition(token: str, request: Request, voter_token: str = "", session: AsyncSession = Depends(get_session)):
    item = await get_public_competition(token, session)
    data = copy.deepcopy(item.data or empty_data())
    # The token is only used to show the viewer's current choice.  Keeping the
    # choice in the response makes a refresh (or opening the link again) clear
    # and lets the UI offer an explicit "Переголосовать" action.
    voter_token = str(voter_token or "").strip()
    voter_prefix = f"{voter_token}:" if len(voter_token) >= 16 else ""
    raw_voters = data.get("voters", {})
    voters = raw_voters if isinstance(raw_voters, dict) and voter_prefix else {}
    current_general_vote = voters.get(f"{voter_token}:vote") if voter_prefix else None
    matches = []
    for match in data.get("matches", []):
        if match.get("status") not in {"open", "bye", "closed"}:
            continue
        a = participant_by_id(data, match.get("a"))
        b = participant_by_id(data, match.get("b"))
        match_voter_key = f"{voter_token}:{match.get('id')}" if voter_prefix and match.get("id") else None
        matches.append({
            "id": match.get("id"),
            "public_path": f"{public_path(item)}?match={match.get('id')}" if match.get("id") else public_path(item),
            "round": match.get("round", 1),
            "stage": match.get("stage", "playoff"),
            "bracket": match.get("bracket"),
            "group": match.get("group"),
            "a": participant_public(a) if a else None,
            "b": participant_public(b) if b else None,
            "winner": match.get("winner"),
            "winner_name": participant_by_id(data, match.get("winner")).get("name") if participant_by_id(data, match.get("winner")) else None,
            "votes_a": int(match.get("votes_a", 0)),
            "votes_b": int(match.get("votes_b", 0)),
            "status": match.get("status"),
            "my_vote": voters.get(match_voter_key) if match_voter_key else None,
        })
    return {
        "id": item.id,
        "name": item.name,
        "kind": item.kind,
        "status": item.status,
        "public_path": public_path(item),
        "participants": [participant_public(entry) for entry in data.get("participants", [])],
        "my_vote": current_general_vote,
        "matches": matches,
        "results": data.get("results", []),
        "settings": data.get("settings", {}),
        "captcha": captcha_payload(),
    }


async def public_vote(token: str, request: Request, payload: dict, match_id: str | None, session: AsyncSession):
    item = await session.scalar(select(MediaCompetition).where(MediaCompetition.public_token == token).with_for_update())
    if item is None:
        raise HTTPException(status_code=404, detail="Ссылка на соревнование недействительна")
    if item.status != "in-progress":
        raise HTTPException(status_code=400, detail="Голосование закрыто")
    try:
        captcha_answer = int(payload.get("captcha_answer", -1))
    except (TypeError, ValueError):
        captcha_answer = -1
    if not check_captcha(str(payload.get("captcha_token") or ""), captcha_answer):
        raise HTTPException(status_code=400, detail="Неверная проверка на бота")
    voter_token = str(payload.get("voter_token") or "").strip()
    if len(voter_token) < 16:
        raise HTTPException(status_code=400, detail="Не удалось определить голосующего")
    data = copy.deepcopy(item.data or empty_data())
    voters = data.get("voters")
    if not isinstance(voters, dict):
        voters = {}
        data["voters"] = voters
    voter_key = f"{voter_token}:{match_id or 'vote'}"
    previous_target_id = voters.get(voter_key)
    if match_id:
        match = next((entry for entry in data.get("matches", []) if entry.get("id") == match_id), None)
        if match is None or match.get("status") != "open":
            raise HTTPException(status_code=404, detail="Пара недоступна")
        target_id = str(payload.get("participant_id") or "")
        if target_id not in {match.get("a"), match.get("b")}:
            raise HTTPException(status_code=400, detail="Выберите участника пары")
        previous_side = "votes_a" if previous_target_id == match.get("a") else "votes_b" if previous_target_id == match.get("b") else None
        target_side = "votes_a" if target_id == match.get("a") else "votes_b"
        # A voter has one ballot per pair.  Switching the candidate moves the
        # existing ballot instead of adding a second one.
        if previous_side and previous_side != target_side:
            match[previous_side] = max(0, int(match.get(previous_side, 0)) - 1)
        if previous_target_id != target_id:
            match[target_side] = int(match.get(target_side, 0)) + 1
        voters[voter_key] = target_id
        persist_data(item, data)
        await session.commit()
        return {"ok": True, "votes_a": match.get("votes_a", 0), "votes_b": match.get("votes_b", 0)}
    target_id = str(payload.get("participant_id") or "")
    participant = participant_by_id(data, target_id)
    if participant is None:
        raise HTTPException(status_code=400, detail="Выберите карточку")
    if previous_target_id and previous_target_id != target_id:
        previous_participant = participant_by_id(data, previous_target_id)
        if previous_participant is not None:
            previous_participant["votes"] = max(0, int(previous_participant.get("votes", 0)) - 1)
    if previous_target_id != target_id:
        participant["votes"] = int(participant.get("votes", 0)) + 1
    voters[voter_key] = target_id
    persist_data(item, data)
    await session.commit()
    return {"ok": True, "votes": participant["votes"]}


@router.post("/public/{token}/vote")
@limiter.limit("30/minute")
async def vote(token: str, request: Request, payload: dict, session: AsyncSession = Depends(get_session)):
    return await public_vote(token, request, payload, None, session)


@router.post("/public/{token}/match/{match_id}/vote")
@limiter.limit("30/minute")
async def match_vote(token: str, match_id: str, request: Request, payload: dict, session: AsyncSession = Depends(get_session)):
    return await public_vote(token, request, payload, match_id, session)
