from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.deps import get_optional_user, require_admin, require_moder_plus, require_pilot_plus
from app.models import AppSetting, Role, Team, TeamApplication, TeamApplicationStatus, TeamCreationRequest, User
from app.rate_limit import limiter
from app.schemas import (
    TeamApplicationRead,
    TeamConfigRead,
    TeamConfigUpdate,
    TeamCreate,
    TeamCreationRequestRead,
    TeamDetailRead,
    TeamMemberRead,
    TeamOwnerTransfer,
    TeamRead,
    TeamUpdate,
)


router = APIRouter()

TEAM_MEMBER_LIMIT_KEY = "team_member_limit"
DEFAULT_TEAM_MEMBER_LIMIT = 5
MAX_TEAM_MEMBER_LIMIT = 100
TEAM_MANAGER_ROLES = {Role.admin, Role.moder}


def clamp_team_limit(value: int) -> int:
    return max(1, min(MAX_TEAM_MEMBER_LIMIT, value))


async def get_team_member_limit(session: AsyncSession) -> int:
    setting = await session.get(AppSetting, TEAM_MEMBER_LIMIT_KEY)
    raw_value = setting.value if setting is not None else {}
    if not isinstance(raw_value, dict):
        return DEFAULT_TEAM_MEMBER_LIMIT
    try:
        return clamp_team_limit(int(raw_value.get("limit", DEFAULT_TEAM_MEMBER_LIMIT)))
    except (TypeError, ValueError):
        return DEFAULT_TEAM_MEMBER_LIMIT


async def save_team_member_limit(session: AsyncSession, limit: int) -> int:
    normalized_limit = clamp_team_limit(limit)
    setting = await session.get(AppSetting, TEAM_MEMBER_LIMIT_KEY)
    if setting is None:
        setting = AppSetting(key=TEAM_MEMBER_LIMIT_KEY, value={"limit": normalized_limit})
        session.add(setting)
    else:
        setting.value = {"limit": normalized_limit}
    await session.commit()
    return normalized_limit


async def load_member_counts(session: AsyncSession, team_ids: list[int]) -> dict[int, int]:
    if not team_ids:
        return {}
    rows = await session.execute(
        select(User.team_id, func.count())
        .where(User.team_id.in_(team_ids))
        .group_by(User.team_id)
    )
    return {int(team_id): int(count) for team_id, count in rows if team_id is not None}


async def load_owners(session: AsyncSession, teams: list[Team]) -> dict[int, User]:
    owner_ids = sorted({team.owner_id for team in teams if team.owner_id is not None})
    if not owner_ids:
        return {}
    owners = (await session.scalars(select(User).where(User.id.in_(owner_ids)))).all()
    return {owner.id: owner for owner in owners}


async def load_current_user_applications(session: AsyncSession, team_ids: list[int], current_user: User | None) -> dict[int, TeamApplicationStatus]:
    if current_user is None or not team_ids:
        return {}
    applications = (
        await session.scalars(
            select(TeamApplication)
            .where(TeamApplication.team_id.in_(team_ids), TeamApplication.user_id == current_user.id)
            .order_by(TeamApplication.created_at.desc(), TeamApplication.id.desc())
        )
    ).all()
    statuses: dict[int, TeamApplicationStatus] = {}
    for application in applications:
        statuses.setdefault(application.team_id, application.status)
    return statuses


def can_manage_team(user: User | None, team: Team) -> bool:
    if user is None:
        return False
    return team.owner_id == user.id or user.role in TEAM_MANAGER_ROLES


async def load_pending_application_counts(session: AsyncSession, team_ids: list[int], current_user: User | None) -> dict[int, int]:
    if current_user is None or not team_ids:
        return {}
    conditions = [
        TeamApplication.team_id.in_(team_ids),
        TeamApplication.status == TeamApplicationStatus.pending,
    ]
    if current_user.role not in TEAM_MANAGER_ROLES:
        conditions.append(Team.owner_id == current_user.id)
    rows = await session.execute(
        select(TeamApplication.team_id, func.count())
        .join(Team, Team.id == TeamApplication.team_id)
        .where(*conditions)
        .group_by(TeamApplication.team_id)
    )
    return {int(team_id): int(count) for team_id, count in rows}


async def load_pending_creation_request_count(session: AsyncSession, current_user: User | None) -> int:
    if current_user is None or current_user.role not in TEAM_MANAGER_ROLES:
        return 0
    return int(
        await session.scalar(
            select(func.count())
            .select_from(TeamCreationRequest)
            .where(TeamCreationRequest.status == TeamApplicationStatus.pending)
        )
        or 0
    )


async def load_current_user_creation_request_status(session: AsyncSession, current_user: User | None) -> TeamApplicationStatus | None:
    if current_user is None:
        return None
    request = await session.scalar(
        select(TeamCreationRequest)
        .where(
            TeamCreationRequest.requester_id == current_user.id,
            TeamCreationRequest.status == TeamApplicationStatus.pending,
        )
        .order_by(TeamCreationRequest.created_at.desc(), TeamCreationRequest.id.desc())
    )
    return request.status if request is not None else None


def team_payload(
    team: Team,
    member_count: int,
    member_limit: int,
    current_user: User | None,
    owner: User | None,
    my_application_status: TeamApplicationStatus | None = None,
    pending_application_count: int = 0,
) -> dict:
    is_member = current_user is not None and current_user.team_id == team.id
    is_owner = current_user is not None and team.owner_id == current_user.id
    can_manage = can_manage_team(current_user, team)
    has_pending_application = my_application_status == TeamApplicationStatus.pending
    return {
        "id": team.id,
        "name": team.name,
        "description": team.description or "",
        "avatar_color": team.avatar_color,
        "owner_id": team.owner_id,
        "owner_login": owner.login if owner else None,
        "owner_nickname": owner.nickname if owner else None,
        "member_count": member_count,
        "member_limit": member_limit,
        "can_join": current_user is not None and current_user.team_id is None and member_count < member_limit and not has_pending_application,
        "is_member": is_member,
        "is_owner": is_owner,
        "can_manage": can_manage,
        "my_application_status": my_application_status,
        "pending_application_count": pending_application_count if can_manage else 0,
        "created_at": team.created_at,
        "updated_at": team.updated_at,
    }


def application_payload(application: TeamApplication, applicant: User) -> TeamApplicationRead:
    return TeamApplicationRead(
        id=application.id,
        team_id=application.team_id,
        user_id=application.user_id,
        status=application.status,
        created_at=application.created_at,
        updated_at=application.updated_at,
        resolved_at=application.resolved_at,
        resolved_by=application.resolved_by,
        user=TeamMemberRead.model_validate(applicant),
    )


async def load_pending_applications(session: AsyncSession, team: Team) -> list[TeamApplicationRead]:
    rows = await session.execute(
        select(TeamApplication, User)
        .join(User, TeamApplication.user_id == User.id)
        .where(TeamApplication.team_id == team.id, TeamApplication.status == TeamApplicationStatus.pending)
        .order_by(TeamApplication.created_at.asc(), TeamApplication.id.asc())
    )
    return [application_payload(application, applicant) for application, applicant in rows]


def creation_request_payload(request: TeamCreationRequest, requester: User) -> TeamCreationRequestRead:
    return TeamCreationRequestRead(
        id=request.id,
        requester_id=request.requester_id,
        name=request.name,
        description=request.description or "",
        avatar_color=request.avatar_color,
        status=request.status,
        team_id=request.team_id,
        created_at=request.created_at,
        updated_at=request.updated_at,
        resolved_at=request.resolved_at,
        resolved_by=request.resolved_by,
        requester=TeamMemberRead.model_validate(requester),
    )


async def load_pending_creation_requests(session: AsyncSession) -> list[TeamCreationRequestRead]:
    rows = await session.execute(
        select(TeamCreationRequest, User)
        .join(User, TeamCreationRequest.requester_id == User.id)
        .where(TeamCreationRequest.status == TeamApplicationStatus.pending)
        .order_by(TeamCreationRequest.created_at.asc(), TeamCreationRequest.id.asc())
    )
    return [creation_request_payload(request, requester) for request, requester in rows]


async def build_team_detail(
    session: AsyncSession,
    team: Team,
    current_user: User | None,
    member_limit: int | None = None,
) -> TeamDetailRead:
    resolved_limit = member_limit if member_limit is not None else await get_team_member_limit(session)
    member_count = int(
        await session.scalar(select(func.count()).select_from(User).where(User.team_id == team.id))
        or 0
    )
    owner = await session.get(User, team.owner_id) if team.owner_id is not None else None
    members = (
        await session.scalars(
            select(User)
            .where(User.team_id == team.id)
            .order_by(User.created_at.asc(), User.id.asc())
        )
    ).all()
    my_applications = await load_current_user_applications(session, [team.id], current_user)
    pending_applications = await load_pending_applications(session, team) if can_manage_team(current_user, team) else []
    payload = team_payload(
        team,
        member_count,
        resolved_limit,
        current_user,
        owner,
        my_applications.get(team.id),
        len(pending_applications),
    )
    payload["members"] = [TeamMemberRead.model_validate(member) for member in members]
    payload["applications"] = pending_applications
    return TeamDetailRead(**payload)


async def get_team_or_404(session: AsyncSession, team_id: int, for_update: bool = False) -> Team:
    stmt = select(Team).where(Team.id == team_id)
    if for_update:
        stmt = stmt.with_for_update()
    team = await session.scalar(stmt)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


async def get_application_or_404(session: AsyncSession, team_id: int, application_id: int, for_update: bool = False) -> TeamApplication:
    stmt = select(TeamApplication).where(TeamApplication.id == application_id, TeamApplication.team_id == team_id)
    if for_update:
        stmt = stmt.with_for_update()
    application = await session.scalar(stmt)
    if application is None:
        raise HTTPException(status_code=404, detail="Team application not found")
    return application


async def get_creation_request_or_404(session: AsyncSession, request_id: int, for_update: bool = False) -> TeamCreationRequest:
    stmt = select(TeamCreationRequest).where(TeamCreationRequest.id == request_id)
    if for_update:
        stmt = stmt.with_for_update()
    creation_request = await session.scalar(stmt)
    if creation_request is None:
        raise HTTPException(status_code=404, detail="Team creation request not found")
    return creation_request


@router.get("/config", response_model=TeamConfigRead)
@limiter.limit("600/minute")
async def get_team_config(
    request: Request,
    current_user: User | None = Depends(get_optional_user),
    session: AsyncSession = Depends(get_session),
):
    return TeamConfigRead(
        member_limit=await get_team_member_limit(session),
        my_create_request_status=await load_current_user_creation_request_status(session, current_user),
        pending_creation_request_count=await load_pending_creation_request_count(session, current_user),
    )


@router.patch("/config", response_model=TeamConfigRead)
@limiter.limit("10/minute")
async def update_team_config(
    payload: TeamConfigUpdate,
    request: Request,
    _: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
):
    limit = await save_team_member_limit(session, payload.member_limit)
    return TeamConfigRead(member_limit=limit)


@router.get("", response_model=list[TeamRead])
@limiter.limit("600/minute")
async def list_teams(
    request: Request,
    search: str | None = None,
    current_user: User | None = Depends(get_optional_user),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(Team)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(or_(Team.name.ilike(like), Team.description.ilike(like)))
    teams = (await session.scalars(stmt.order_by(Team.created_at.desc(), Team.id.desc()))).all()
    member_limit = await get_team_member_limit(session)
    counts = await load_member_counts(session, [team.id for team in teams])
    owners = await load_owners(session, teams)
    applications = await load_current_user_applications(session, [team.id for team in teams], current_user)
    application_counts = await load_pending_application_counts(session, [team.id for team in teams], current_user)
    return [
        TeamRead(
            **team_payload(
                team,
                counts.get(team.id, 0),
                member_limit,
                current_user,
                owners.get(team.owner_id),
                applications.get(team.id),
                application_counts.get(team.id, 0),
            )
        )
        for team in teams
    ]


@router.get("/create-requests", response_model=list[TeamCreationRequestRead])
@limiter.limit("600/minute")
async def list_team_creation_requests(
    request: Request,
    _: User = Depends(require_moder_plus),
    session: AsyncSession = Depends(get_session),
):
    return await load_pending_creation_requests(session)


@router.post("/create-requests/{request_id}/approve", response_model=TeamCreationRequestRead)
@limiter.limit("60/minute")
async def approve_team_creation_request(
    request_id: int,
    request: Request,
    user: User = Depends(require_moder_plus),
    session: AsyncSession = Depends(get_session),
):
    creation_request = await get_creation_request_or_404(session, request_id, for_update=True)
    if creation_request.status != TeamApplicationStatus.pending:
        raise HTTPException(status_code=400, detail="Team creation request is already resolved")

    requester = await session.get(User, creation_request.requester_id)
    if requester is None:
        creation_request.status = TeamApplicationStatus.rejected
        creation_request.resolved_at = datetime.now(timezone.utc)
        creation_request.resolved_by = user.id
        await session.commit()
        raise HTTPException(status_code=404, detail="Requester not found")
    if requester.team_id is not None:
        raise HTTPException(status_code=400, detail="Requester is already in a team")

    duplicate = await session.scalar(select(Team).where(Team.name == creation_request.name))
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="Team name already exists")

    team = Team(
        name=creation_request.name,
        description=creation_request.description or "",
        avatar_color=creation_request.avatar_color,
        owner_id=requester.id,
    )
    session.add(team)
    now = datetime.now(timezone.utc)
    try:
        await session.flush()
        requester.team_id = team.id
        creation_request.status = TeamApplicationStatus.approved
        creation_request.team_id = team.id
        creation_request.resolved_at = now
        creation_request.resolved_by = user.id
        await session.execute(
            update(TeamApplication)
            .where(TeamApplication.user_id == requester.id, TeamApplication.status == TeamApplicationStatus.pending)
            .values(status=TeamApplicationStatus.rejected, resolved_at=now, resolved_by=user.id)
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Team name already exists") from exc

    await session.refresh(creation_request)
    await session.refresh(requester)
    return creation_request_payload(creation_request, requester)


@router.post("/create-requests/{request_id}/reject", response_model=TeamCreationRequestRead)
@limiter.limit("60/minute")
async def reject_team_creation_request(
    request_id: int,
    request: Request,
    user: User = Depends(require_moder_plus),
    session: AsyncSession = Depends(get_session),
):
    creation_request = await get_creation_request_or_404(session, request_id, for_update=True)
    if creation_request.status != TeamApplicationStatus.pending:
        raise HTTPException(status_code=400, detail="Team creation request is already resolved")
    requester = await session.get(User, creation_request.requester_id)
    if requester is None:
        raise HTTPException(status_code=404, detail="Requester not found")
    creation_request.status = TeamApplicationStatus.rejected
    creation_request.resolved_at = datetime.now(timezone.utc)
    creation_request.resolved_by = user.id
    await session.commit()
    await session.refresh(creation_request)
    return creation_request_payload(creation_request, requester)


@router.post("", response_model=TeamCreationRequestRead, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_team_request(
    payload: TeamCreate,
    request: Request,
    user: User = Depends(require_pilot_plus),
    session: AsyncSession = Depends(get_session),
):
    if user.team_id is not None:
        raise HTTPException(status_code=400, detail="Leave your current team before requesting a new one")
    duplicate_team = await session.scalar(select(Team).where(Team.name == payload.name))
    if duplicate_team is not None:
        raise HTTPException(status_code=409, detail="Team name already exists")
    existing_pending = await session.scalar(
        select(TeamCreationRequest).where(
            TeamCreationRequest.requester_id == user.id,
            TeamCreationRequest.status == TeamApplicationStatus.pending,
        )
    )
    if existing_pending is not None:
        raise HTTPException(status_code=409, detail="Team creation request already exists")
    duplicate_pending_name = await session.scalar(
        select(TeamCreationRequest).where(
            TeamCreationRequest.name == payload.name,
            TeamCreationRequest.status == TeamApplicationStatus.pending,
        )
    )
    if duplicate_pending_name is not None:
        raise HTTPException(status_code=409, detail="Team creation request with this name already exists")

    creation_request = TeamCreationRequest(
        requester_id=user.id,
        name=payload.name,
        description=payload.description or "",
        avatar_color=payload.avatar_color,
        status=TeamApplicationStatus.pending,
    )
    session.add(creation_request)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Team creation request already exists") from exc
    await session.refresh(creation_request)
    return creation_request_payload(creation_request, user)


@router.get("/{team_id}", response_model=TeamDetailRead)
@limiter.limit("600/minute")
async def get_team(
    team_id: int,
    request: Request,
    current_user: User | None = Depends(get_optional_user),
    session: AsyncSession = Depends(get_session),
):
    team = await get_team_or_404(session, team_id)
    return await build_team_detail(session, team, current_user)


@router.patch("/{team_id}", response_model=TeamDetailRead)
@limiter.limit("20/minute")
async def update_team(
    team_id: int,
    payload: TeamUpdate,
    request: Request,
    user: User = Depends(require_pilot_plus),
    session: AsyncSession = Depends(get_session),
):
    team = await get_team_or_404(session, team_id)
    if not can_manage_team(user, team):
        raise HTTPException(status_code=403, detail="Only the team owner or moderators can edit this team")
    for field, value in payload.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(team, field, value)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Team name already exists") from exc
    await session.refresh(team)
    return await build_team_detail(session, team, user)


@router.patch("/{team_id}/owner", response_model=TeamDetailRead)
@limiter.limit("20/minute")
async def transfer_team_ownership(
    team_id: int,
    payload: TeamOwnerTransfer,
    request: Request,
    user: User = Depends(require_pilot_plus),
    session: AsyncSession = Depends(get_session),
):
    team = await get_team_or_404(session, team_id, for_update=True)
    if not can_manage_team(user, team):
        raise HTTPException(status_code=403, detail="Only the team owner or moderators can transfer ownership")
    if payload.new_owner_id == team.owner_id:
        raise HTTPException(status_code=400, detail="Choose another team member as the new owner")

    new_owner = await session.get(User, payload.new_owner_id)
    if new_owner is None or new_owner.team_id != team.id:
        raise HTTPException(status_code=400, detail="New owner must be a member of this team")

    team.owner_id = new_owner.id
    await session.commit()
    await session.refresh(team)
    return await build_team_detail(session, team, user)


@router.post("/{team_id}/join", response_model=TeamDetailRead)
@limiter.limit("60/minute")
async def request_team_join(
    team_id: int,
    request: Request,
    user: User = Depends(require_pilot_plus),
    session: AsyncSession = Depends(get_session),
):
    if user.team_id is not None:
        raise HTTPException(status_code=400, detail="Leave your current team before requesting another one")
    team = await get_team_or_404(session, team_id, for_update=True)
    member_limit = await get_team_member_limit(session)
    member_count = int(
        await session.scalar(select(func.count()).select_from(User).where(User.team_id == team.id))
        or 0
    )
    if member_count >= member_limit:
        raise HTTPException(status_code=409, detail="Team member limit reached")
    existing_pending = await session.scalar(
        select(TeamApplication).where(
            TeamApplication.team_id == team.id,
            TeamApplication.user_id == user.id,
            TeamApplication.status == TeamApplicationStatus.pending,
        )
    )
    if existing_pending is not None:
        raise HTTPException(status_code=409, detail="Team application already exists")
    session.add(TeamApplication(team_id=team.id, user_id=user.id, status=TeamApplicationStatus.pending))
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Team application already exists") from exc
    await session.refresh(team)
    return await build_team_detail(session, team, user, member_limit)


@router.post("/{team_id}/applications/{application_id}/approve", response_model=TeamDetailRead)
@limiter.limit("60/minute")
async def approve_team_application(
    team_id: int,
    application_id: int,
    request: Request,
    user: User = Depends(require_pilot_plus),
    session: AsyncSession = Depends(get_session),
):
    team = await get_team_or_404(session, team_id, for_update=True)
    if not can_manage_team(user, team):
        raise HTTPException(status_code=403, detail="Only the team owner or moderators can approve applications")
    application = await get_application_or_404(session, team.id, application_id, for_update=True)
    if application.status != TeamApplicationStatus.pending:
        raise HTTPException(status_code=400, detail="Team application is already resolved")
    applicant = await session.get(User, application.user_id)
    if applicant is None:
        application.status = TeamApplicationStatus.rejected
        application.resolved_at = datetime.now(timezone.utc)
        application.resolved_by = user.id
        await session.commit()
        raise HTTPException(status_code=404, detail="Applicant not found")
    if applicant.team_id is not None:
        raise HTTPException(status_code=400, detail="Applicant is already in a team")
    member_limit = await get_team_member_limit(session)
    member_count = int(
        await session.scalar(select(func.count()).select_from(User).where(User.team_id == team.id))
        or 0
    )
    if member_count >= member_limit:
        raise HTTPException(status_code=409, detail="Team member limit reached")

    now = datetime.now(timezone.utc)
    applicant.team_id = team.id
    application.status = TeamApplicationStatus.approved
    application.resolved_at = now
    application.resolved_by = user.id
    await session.execute(
        update(TeamApplication)
        .where(
            TeamApplication.user_id == applicant.id,
            TeamApplication.id != application.id,
            TeamApplication.status == TeamApplicationStatus.pending,
        )
        .values(status=TeamApplicationStatus.rejected, resolved_at=now, resolved_by=user.id)
    )
    await session.commit()
    await session.refresh(team)
    return await build_team_detail(session, team, user, member_limit)


@router.post("/{team_id}/applications/{application_id}/reject", response_model=TeamDetailRead)
@limiter.limit("60/minute")
async def reject_team_application(
    team_id: int,
    application_id: int,
    request: Request,
    user: User = Depends(require_pilot_plus),
    session: AsyncSession = Depends(get_session),
):
    team = await get_team_or_404(session, team_id)
    if not can_manage_team(user, team):
        raise HTTPException(status_code=403, detail="Only the team owner or moderators can reject applications")
    application = await get_application_or_404(session, team.id, application_id, for_update=True)
    if application.status != TeamApplicationStatus.pending:
        raise HTTPException(status_code=400, detail="Team application is already resolved")
    application.status = TeamApplicationStatus.rejected
    application.resolved_at = datetime.now(timezone.utc)
    application.resolved_by = user.id
    await session.commit()
    await session.refresh(team)
    return await build_team_detail(session, team, user)


@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("20/minute")
async def delete_team(
    team_id: int,
    request: Request,
    user: User = Depends(require_pilot_plus),
    session: AsyncSession = Depends(get_session),
):
    team = await get_team_or_404(session, team_id, for_update=True)
    if not can_manage_team(user, team):
        raise HTTPException(status_code=403, detail="Only the team owner or moderators can delete this team")
    await session.execute(update(User).where(User.team_id == team.id).values(team_id=None))
    await session.delete(team)
    await session.commit()


@router.delete("/{team_id}/members/{user_id}", response_model=TeamDetailRead)
@limiter.limit("60/minute")
async def remove_team_member(
    team_id: int,
    user_id: int,
    request: Request,
    user: User = Depends(require_pilot_plus),
    session: AsyncSession = Depends(get_session),
):
    team = await get_team_or_404(session, team_id, for_update=True)
    if not can_manage_team(user, team):
        raise HTTPException(status_code=403, detail="Only the team owner or moderators can remove members")
    if user_id == team.owner_id:
        raise HTTPException(status_code=400, detail="Transfer ownership before removing the owner")
    member = await session.get(User, user_id)
    if member is None or member.team_id != team.id:
        raise HTTPException(status_code=404, detail="Team member not found")
    member.team_id = None
    await session.commit()
    await session.refresh(team)
    return await build_team_detail(session, team, user)


@router.delete("/{team_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("60/minute")
async def leave_team(
    team_id: int,
    request: Request,
    user: User = Depends(require_pilot_plus),
    session: AsyncSession = Depends(get_session),
):
    team = await get_team_or_404(session, team_id, for_update=True)
    if user.team_id != team.id:
        raise HTTPException(status_code=400, detail="You are not a member of this team")
    if team.owner_id == user.id:
        raise HTTPException(status_code=400, detail="Transfer ownership or delete the team before leaving")
    user.team_id = None
    await session.commit()
