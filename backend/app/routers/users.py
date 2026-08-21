from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import Numeric, String, cast, delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.avatar_uploads import ensure_avatar_upload_allowed, mark_avatar_uploaded, remove_avatar_file, save_avatar_file
from app.config import get_settings
from app.db import get_session
from app.deps import as_utc, clear_expired_timeout, require_admin, require_moder_plus, require_pilot_plus
from app.models import RACE_GAMES, Appeal, Banner, Championship, Penalty, Race, RaceRegistration, Role, Setup, Team, TeamApplication, TeamCreationRequest, User, UserStatus
from app.race_videos import remove_race_video_file
from app.rate_limit import limiter
from app.schemas import AdminDangerDeleteRequest, RoleUpdate, TimeoutRequest, UserAdminUpdate, UserPrivate, UserPublic, UserUpdate
from app.security import verify_password


router = APIRouter()
settings = get_settings()


def user_response(user: User, team_name: str | None = None, team_abbreviation: str | None = None, private: bool = False) -> dict:
    schema = UserPrivate if private else UserPublic
    data = schema.model_validate(user).model_dump()
    data["team_name"] = team_name
    data["team_abbreviation"] = team_abbreviation
    return data


async def user_team_info(session: AsyncSession, user: User) -> tuple[str | None, str | None]:
    if user.team_id is None:
        return None, None
    team = await session.get(Team, user.team_id)
    return (team.name, team.abbreviation) if team else (None, None)


async def set_user_avatar(session: AsyncSession, user: User, file: UploadFile) -> dict:
    ensure_avatar_upload_allowed(user)
    previous_avatar_url = user.avatar_url
    new_avatar_url = await save_avatar_file(file, "users", user.id, settings.max_user_avatar_upload_mb)
    user.avatar_url = new_avatar_url
    mark_avatar_uploaded(user)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        remove_avatar_file(new_avatar_url)
        raise
    await session.refresh(user)
    remove_avatar_file(previous_avatar_url)
    team_name, team_abbreviation = await user_team_info(session, user)
    return user_response(user, team_name, team_abbreviation, private=True)


def ensure_danger_request(payload: AdminDangerDeleteRequest, admin: User, expected_confirmation: str) -> None:
    if payload.confirmation.strip() != expected_confirmation or payload.confirmation_repeat.strip() != expected_confirmation:
        raise HTTPException(status_code=400, detail="Confirmation phrase is invalid")
    if not verify_password(payload.password, admin.password_hash):
        raise HTTPException(status_code=403, detail="Admin password is invalid")


async def reassign_restricted_user_references(
    session: AsyncSession,
    user_ids: list[int],
    admin_id: int,
) -> None:
    await session.execute(update(Championship).where(Championship.creator_id.in_(user_ids)).values(creator_id=admin_id))
    await session.execute(update(Race).where(Race.creator_id.in_(user_ids)).values(creator_id=admin_id))
    await session.execute(update(Penalty).where(Penalty.issuer_id.in_(user_ids)).values(issuer_id=admin_id))


PROFILE_REQUIRED_FIELDS = {"email", "first_name", "last_name", "nickname", "avatar_color", "games"}
ADMIN_UNIQUE_FIELDS = {"email", "login"}


async def ensure_unique_user_fields(session: AsyncSession, data: dict, user_id: int) -> None:
    for field in ADMIN_UNIQUE_FIELDS & data.keys():
        value = str(data[field]) if field == "email" else data[field]
        existing = await session.scalar(select(User).where(getattr(User, field) == value, User.id != user_id))
        if existing is not None:
            raise HTTPException(status_code=409, detail=f"{field.replace('_', ' ').title()} already exists")


def rating_sort_expr(rating_game: str):
    game = rating_game if rating_game in RACE_GAMES else RACE_GAMES[0]
    return func.coalesce(cast(User.game_ratings[game]["rating"].astext, Numeric(8, 2)), User.rating)


def user_sort_columns(sort: str, rating_game: str = RACE_GAMES[0]) -> tuple:
    rating_expr = rating_sort_expr(rating_game)
    if sort == "alpha_desc":
        return (func.lower(User.nickname).desc(), func.lower(User.login).desc(), User.id.desc())
    if sort == "alpha_asc":
        return (func.lower(User.nickname).asc(), func.lower(User.login).asc(), User.id.asc())
    if sort == "rating_asc":
        return (rating_expr.asc(), User.sr.desc(), func.lower(User.nickname).asc(), User.id.asc())
    if sort == "sr_desc":
        return (User.sr.desc(), rating_expr.desc(), func.lower(User.nickname).asc(), User.id.asc())
    if sort == "sr_asc":
        return (User.sr.asc(), rating_expr.desc(), func.lower(User.nickname).asc(), User.id.asc())
    return (rating_expr.desc(), User.sr.desc(), func.lower(User.nickname).asc(), User.id.asc())


@router.get("/pilots", response_model=list[UserPublic])
@limiter.limit("1200/minute")
async def list_pilots(
    request: Request,
    search: str | None = None,
    country: str | None = None,
    sort: str = "rating_desc",
    rating_game: str = RACE_GAMES[0],
    offset: int = 0,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
):
    limit = min(limit, 100)
    stmt = select(User, Team.name, Team.abbreviation).outerjoin(Team, Team.id == User.team_id).where(User.status == UserStatus.active)
    if country:
        stmt = stmt.where(User.country == country)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            or_(
                User.login.ilike(like),
                User.nickname.ilike(like),
                User.first_name.ilike(like),
                User.last_name.ilike(like),
                cast(User.pilot_number, String).ilike(like),
                Team.name.ilike(like),
                Team.abbreviation.ilike(like),
            )
        )
    rows = (await session.execute(stmt.order_by(*user_sort_columns(sort, rating_game)).offset(offset).limit(limit))).all()
    return [user_response(user, team_name, team_abbreviation) for user, team_name, team_abbreviation in rows]


@router.get("/moderation/pending", response_model=list[UserPrivate])
@limiter.limit("3/minute")
async def pending_users(request: Request, _: User = Depends(require_moder_plus), session: AsyncSession = Depends(get_session)):
    rows = (
        await session.execute(
            select(User, Team.name, Team.abbreviation)
            .outerjoin(Team, Team.id == User.team_id)
            .where(or_(User.status == UserStatus.unapproved, User.pending_profile_changes.is_not(None)))
            .order_by(User.created_at)
        )
    ).all()
    return [user_response(user, team_name, team_abbreviation, private=True) for user, team_name, team_abbreviation in rows]


@router.get("/admin", response_model=list[UserPrivate])
@limiter.limit("600/minute")
async def admin_user_list(
    request: Request,
    _: User = Depends(require_admin),
    search: str | None = None,
    sort: str = "rating_desc",
    rating_game: str = RACE_GAMES[0],
    offset: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
):
    stmt = select(User, Team.name, Team.abbreviation).outerjoin(Team, Team.id == User.team_id)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            or_(
                User.login.ilike(like),
                User.email.ilike(like),
                User.nickname.ilike(like),
                User.first_name.ilike(like),
                User.last_name.ilike(like),
                cast(User.pilot_number, String).ilike(like),
                Team.name.ilike(like),
                Team.abbreviation.ilike(like),
            )
        )
    rows = (
        await session.execute(
            stmt
            .order_by(*user_sort_columns(sort, rating_game))
            .offset(offset)
            .limit(min(limit, 200))
        )
    ).all()
    users = [user for user, _, _ in rows]
    now = datetime.now(timezone.utc)
    has_expired_timeouts = False
    for user in users:
        has_expired_timeouts = clear_expired_timeout(user, now) or has_expired_timeouts
    if has_expired_timeouts:
        await session.commit()
        for user in users:
            await session.refresh(user)
    return [user_response(user, team_name, team_abbreviation, private=True) for user, team_name, team_abbreviation in rows]


@router.post("/admin/delete-pilots")
@limiter.limit("3/minute")
async def delete_all_pilots(
    request: Request,
    payload: AdminDangerDeleteRequest,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    ensure_danger_request(payload, admin, "DELETE PILOTS")
    pilot_ids = list((await session.scalars(select(User.id).where(User.role == Role.pilot))).all())
    if not pilot_ids:
        return {"deleted": 0}
    pilot_avatar_urls = list((await session.scalars(select(User.avatar_url).where(User.id.in_(pilot_ids), User.avatar_url.is_not(None)))).all())

    pilot_id_set = set(pilot_ids)
    races = (await session.scalars(select(Race))).all()
    for race in races:
        if not isinstance(race.registered_pilots, list):
            continue
        filtered_pilots = []
        for item in race.registered_pilots:
            if not isinstance(item, dict):
                filtered_pilots.append(item)
                continue
            try:
                user_id = int(item.get("user_id") or 0)
            except (TypeError, ValueError):
                user_id = 0
            if user_id not in pilot_id_set:
                filtered_pilots.append(item)
        race.registered_pilots = filtered_pilots

    target_penalty_ids = list(
        (
            await session.scalars(
                select(Penalty.id).where(or_(Penalty.target_id.in_(pilot_ids), Penalty.issuer_id.in_(pilot_ids)))
            )
        ).all()
    )
    if target_penalty_ids:
        await session.execute(delete(Appeal).where(Appeal.penalty_id.in_(target_penalty_ids)))
        await session.execute(delete(Penalty).where(Penalty.id.in_(target_penalty_ids)))

    await session.execute(delete(Appeal).where(Appeal.user_id.in_(pilot_ids)))
    await session.execute(update(Appeal).where(Appeal.moderator_id.in_(pilot_ids)).values(moderator_id=None))
    await session.execute(delete(RaceRegistration).where(RaceRegistration.user_id.in_(pilot_ids)))
    await session.execute(delete(Setup).where(Setup.user_id.in_(pilot_ids)))
    await session.execute(delete(TeamApplication).where(TeamApplication.user_id.in_(pilot_ids)))
    await session.execute(update(TeamApplication).where(TeamApplication.resolved_by.in_(pilot_ids)).values(resolved_by=None))
    await session.execute(delete(TeamCreationRequest).where(TeamCreationRequest.requester_id.in_(pilot_ids)))
    await session.execute(update(TeamCreationRequest).where(TeamCreationRequest.resolved_by.in_(pilot_ids)).values(resolved_by=None))
    await session.execute(update(Banner).where(Banner.updated_by.in_(pilot_ids)).values(updated_by=None))
    await session.execute(update(Team).where(Team.owner_id.in_(pilot_ids)).values(owner_id=None))
    await reassign_restricted_user_references(session, pilot_ids, admin.id)

    result = await session.execute(delete(User).where(User.id.in_(pilot_ids)))
    await session.commit()
    for avatar_url in pilot_avatar_urls:
        remove_avatar_file(avatar_url)
    return {"deleted": result.rowcount or len(pilot_ids)}


@router.post("/admin/delete-races")
@limiter.limit("3/minute")
async def delete_all_races(
    request: Request,
    payload: AdminDangerDeleteRequest,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    ensure_danger_request(payload, admin, "DELETE RACES")
    race_count = await session.scalar(select(func.count()).select_from(Race))
    race_video_urls = list((await session.scalars(select(Race.video_url).where(Race.video_url.is_not(None)))).all())
    await session.execute(delete(Appeal))
    await session.execute(delete(Penalty))
    await session.execute(delete(RaceRegistration))
    await session.execute(update(Setup).values(race_id=None))
    await session.execute(delete(Race))
    await session.commit()
    for video_url in race_video_urls:
        remove_race_video_file(video_url)
    return {"deleted": int(race_count or 0)}


@router.get("/{user_id}", response_model=UserPublic)
@limiter.limit("600/minute")
async def get_user(user_id: int, request: Request, session: AsyncSession = Depends(get_session)):
    row = await session.execute(select(User, Team.name, Team.abbreviation).outerjoin(Team, Team.id == User.team_id).where(User.id == user_id))
    result = row.first()
    if result is None:
        raise HTTPException(status_code=404, detail="User not found")
    user, team_name, team_abbreviation = result
    return user_response(user, team_name, team_abbreviation)


@router.patch("/me", response_model=UserPrivate)
@limiter.limit("3/minute")
async def update_me(
    request: Request,
    payload: UserUpdate,
    user: User = Depends(require_pilot_plus),
    session: AsyncSession = Depends(get_session),
):
    data = payload.model_dump(exclude_unset=True)
    if any(field in data and data[field] is None for field in PROFILE_REQUIRED_FIELDS):
        raise HTTPException(status_code=400, detail="Required profile fields cannot be null")
    await ensure_unique_user_fields(session, data, user.id)
    if user.role == Role.admin:
        for field, value in data.items():
            setattr(user, field, value)
    elif data:
        user.pending_profile_changes = data
    await session.commit()
    await session.refresh(user)
    team_name, team_abbreviation = await user_team_info(session, user)
    return user_response(user, team_name, team_abbreviation, private=True)


@router.post("/me/avatar", response_model=UserPrivate)
@limiter.limit("20/minute")
async def upload_my_avatar(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(require_pilot_plus),
    session: AsyncSession = Depends(get_session),
):
    return await set_user_avatar(session, user, file)


@router.patch("/{user_id}", response_model=UserPrivate)
@limiter.limit("60/minute")
async def update_user_profile(
    user_id: int,
    request: Request,
    payload: UserAdminUpdate,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    data = payload.model_dump(exclude_unset=True)
    required_fields = PROFILE_REQUIRED_FIELDS | {"login", "pilot_number"}
    if any(field in data and data[field] is None for field in required_fields):
        raise HTTPException(status_code=400, detail="Required profile fields cannot be null")
    await ensure_unique_user_fields(session, data, user.id)

    for field, value in data.items():
        setattr(user, field, value)
    user.pending_profile_changes = None
    await session.commit()
    await session.refresh(user)
    team_name, team_abbreviation = await user_team_info(session, user)
    return user_response(user, team_name, team_abbreviation, private=True)


@router.post("/{user_id}/avatar", response_model=UserPrivate)
@limiter.limit("20/minute")
async def upload_user_avatar(
    user_id: int,
    request: Request,
    file: UploadFile = File(...),
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return await set_user_avatar(session, user, file)


@router.post("/{user_id}/approve", response_model=UserPrivate)
@limiter.limit("3/minute")
async def approve_user(user_id: int, request: Request, _: User = Depends(require_moder_plus), session: AsyncSession = Depends(get_session)):
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.pending_profile_changes:
        if "email" in user.pending_profile_changes:
            existing_email = await session.scalar(
                select(User).where(User.email == str(user.pending_profile_changes["email"]), User.id != user.id)
            )
            if existing_email is not None:
                raise HTTPException(status_code=409, detail="Email already exists")
        for field, value in user.pending_profile_changes.items():
            setattr(user, field, value)
        user.pending_profile_changes = None
    if user.status == UserStatus.unapproved:
        user.status = UserStatus.active
    await session.commit()
    await session.refresh(user)
    return user


@router.delete("/{user_id}/reject", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("3/minute")
async def reject_user(user_id: int, request: Request, _: User = Depends(require_moder_plus), session: AsyncSession = Depends(get_session)):
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    avatar_url = user.avatar_url
    if user.status == UserStatus.unapproved:
        await session.delete(user)
    elif user.pending_profile_changes:
        user.pending_profile_changes = None
    else:
        raise HTTPException(status_code=400, detail="No registration or profile change to reject")
    await session.commit()
    if user.status == UserStatus.unapproved:
        remove_avatar_file(avatar_url)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_user_account(
    user_id: int,
    request: Request,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")
    if user.role == Role.admin:
        admin_count = await session.scalar(select(func.count()).select_from(User).where(User.role == Role.admin))
        if (admin_count or 0) <= 1:
            raise HTTPException(status_code=400, detail="The last admin account cannot be deleted")

    user_avatar_url = user.avatar_url
    deleted_team_avatar_urls: list[str] = []
    owned_team_ids = list((await session.scalars(select(Team.id).where(Team.owner_id == user.id))).all())
    for team_id in owned_team_ids:
        next_owner = await session.scalar(
            select(User)
            .where(User.team_id == team_id, User.id != user.id)
            .order_by(User.created_at.asc(), User.id.asc())
            .limit(1)
        )
        if next_owner is None:
            team_avatar_url = await session.scalar(select(Team.avatar_url).where(Team.id == team_id))
            if team_avatar_url:
                deleted_team_avatar_urls.append(team_avatar_url)
            await session.execute(delete(Team).where(Team.id == team_id))
        else:
            await session.execute(update(Team).where(Team.id == team_id).values(owner_id=next_owner.id))

    target_penalty_ids = list((await session.scalars(select(Penalty.id).where(Penalty.target_id == user.id))).all())
    if target_penalty_ids:
        await session.execute(delete(Appeal).where(Appeal.penalty_id.in_(target_penalty_ids)))
        await session.execute(delete(Penalty).where(Penalty.id.in_(target_penalty_ids)))

    await session.execute(delete(Appeal).where(Appeal.user_id == user.id))
    await session.execute(update(Appeal).where(Appeal.moderator_id == user.id).values(moderator_id=None))
    await session.execute(delete(RaceRegistration).where(RaceRegistration.user_id == user.id))
    await session.execute(delete(Setup).where(Setup.user_id == user.id))
    await session.execute(delete(TeamApplication).where(TeamApplication.user_id == user.id))
    await session.execute(update(TeamApplication).where(TeamApplication.resolved_by == user.id).values(resolved_by=None))
    await session.execute(delete(TeamCreationRequest).where(TeamCreationRequest.requester_id == user.id))
    await session.execute(update(TeamCreationRequest).where(TeamCreationRequest.resolved_by == user.id).values(resolved_by=None))
    await session.execute(update(Banner).where(Banner.updated_by == user.id).values(updated_by=None))
    await reassign_restricted_user_references(session, [user.id], admin.id)

    await session.delete(user)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="User cannot be deleted because linked records still exist") from exc
    remove_avatar_file(user_avatar_url)
    for avatar_url in deleted_team_avatar_urls:
        remove_avatar_file(avatar_url)


@router.patch("/{user_id}/role", response_model=UserPrivate)
@limiter.limit("3/minute")
async def update_role(
    user_id: int,
    request: Request,
    payload: RoleUpdate,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = payload.role
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/{user_id}/ban", response_model=UserPrivate)
@limiter.limit("3/minute")
async def ban_user(user_id: int, request: Request, _: User = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == Role.admin:
        raise HTTPException(status_code=403, detail="Admins cannot be banned")
    user.status = UserStatus.banned
    user.ban_end = None
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/{user_id}/unban", response_model=UserPrivate)
@limiter.limit("3/minute")
async def unban_user(user_id: int, request: Request, _: User = Depends(require_admin), session: AsyncSession = Depends(get_session)):
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.status = UserStatus.active
    user.ban_end = None
    user.timeout_start = None
    user.timeout_end = None
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/{user_id}/timeout", response_model=UserPrivate)
@limiter.limit("3/minute")
async def timeout_user(
    user_id: int,
    request: Request,
    payload: TimeoutRequest,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    timeout_end = as_utc(payload.timeout_end)
    if timeout_end <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Timeout end must be in the future")
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == Role.admin:
        raise HTTPException(status_code=403, detail="Admins cannot be timed out")
    user.status = UserStatus.timeout
    user.timeout_start = datetime.now(timezone.utc)
    user.timeout_end = timeout_end
    user.ban_end = None
    await session.commit()
    await session.refresh(user)
    return user


@router.delete("/{user_id}/timeout", response_model=UserPrivate)
@limiter.limit("10/minute")
async def end_timeout_user(
    user_id: int,
    request: Request,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.status == UserStatus.timeout:
        user.status = UserStatus.active
    user.timeout_start = None
    user.timeout_end = None
    await session.commit()
    await session.refresh(user)
    return user
