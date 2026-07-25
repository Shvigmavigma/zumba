from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Enum as SQLEnum

from app.db import Base


DEFAULT_SR = 5.0
MIN_SR = 0.0
MAX_SR = 30.0
RACE_GAMES = ("ACC", "AC", "iRacing")
DEFAULT_USER_GAMES = list(RACE_GAMES)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def enum_column(enum_type: type[StrEnum], length: int = 30):
    return mapped_column(
        SQLEnum(
            enum_type,
            values_callable=lambda enum: [item.value for item in enum],
            native_enum=False,
            length=length,
        )
    )


class Role(StrEnum):
    admin = "admin"
    moder = "moder"
    marshall = "marshall"
    smm = "smm"
    pilot = "pilot"


class UserStatus(StrEnum):
    active = "active"
    banned = "banned"
    timeout = "timeout"
    unapproved = "unapproved"


class RaceStatus(StrEnum):
    registration_open = "registration_open"
    ongoing = "ongoing"
    finished = "finished"


class PenaltyType(StrEnum):
    time = "time"
    sr = "sr"


class PenaltyStatus(StrEnum):
    active = "active"
    appealed = "appealed"
    canceled = "canceled"


class AppealStatus(StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class TeamApplicationStatus(StrEnum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class BannerPosition(StrEnum):
    top = "top"
    bottom = "bottom"
    left = "left"
    right = "right"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint(f"sr >= {MIN_SR} AND sr <= {MAX_SR}", name="ck_users_sr_range"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    login: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    first_name: Mapped[str] = mapped_column(String(50))
    last_name: Mapped[str] = mapped_column(String(50))
    nickname: Mapped[str] = mapped_column(String(80), index=True)
    pilot_number: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    country: Mapped[str | None] = mapped_column(String(50), index=True)
    sr: Mapped[float] = mapped_column(Numeric(3, 1), default=DEFAULT_SR, server_default=str(DEFAULT_SR))
    discord: Mapped[str | None] = mapped_column(String(100))
    steam_id: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    role: Mapped[Role] = enum_column(Role)
    status: Mapped[UserStatus] = enum_column(UserStatus)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    ban_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    timeout_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    timeout_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    avatar_color: Mapped[str] = mapped_column(String(7), default="#2563eb")
    games: Mapped[list[str]] = mapped_column(JSONB, default=lambda: list(DEFAULT_USER_GAMES), server_default=text("""'["ACC", "AC", "iRacing"]'::jsonb"""))
    team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL", use_alter=True, name="fk_users_team_id"),
        index=True,
    )
    pending_profile_changes: Mapped[dict | None] = mapped_column(JSONB)

    created_races: Mapped[list["Race"]] = relationship(back_populates="creator", foreign_keys="Race.creator_id")
    team: Mapped["Team | None"] = relationship(back_populates="members", foreign_keys=[team_id])
    owned_teams: Mapped[list["Team"]] = relationship(back_populates="owner", foreign_keys="Team.owner_id")


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    avatar_color: Mapped[str] = mapped_column(String(7), default="#dc2626")
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL", use_alter=True, name="fk_teams_owner_id"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    owner: Mapped[User | None] = relationship(back_populates="owned_teams", foreign_keys=[owner_id])
    members: Mapped[list[User]] = relationship(back_populates="team", foreign_keys="User.team_id")
    applications: Mapped[list["TeamApplication"]] = relationship(back_populates="team", cascade="all, delete-orphan")


class TeamCreationRequest(Base):
    __tablename__ = "team_creation_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    description: Mapped[str] = mapped_column(Text, default="")
    avatar_color: Mapped[str] = mapped_column(String(7), default="#dc2626")
    status: Mapped[TeamApplicationStatus] = enum_column(TeamApplicationStatus)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id", ondelete="SET NULL"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)

    requester: Mapped[User] = relationship(foreign_keys=[requester_id])
    resolver: Mapped[User | None] = relationship(foreign_keys=[resolved_by])
    team: Mapped[Team | None] = relationship()


class TeamApplication(Base):
    __tablename__ = "team_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[TeamApplicationStatus] = enum_column(TeamApplicationStatus)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)

    team: Mapped[Team] = relationship(back_populates="applications")
    user: Mapped[User] = relationship(foreign_keys=[user_id])
    resolver: Mapped[User | None] = relationship(foreign_keys=[resolved_by])


class Race(Base):
    __tablename__ = "races"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    description: Mapped[str] = mapped_column(Text)
    server_link: Mapped[str] = mapped_column(String(255))
    datetime_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    datetime_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    max_pilots: Mapped[int] = mapped_column(Integer)
    car_class: Mapped[str] = mapped_column("class", String(50), index=True)
    track: Mapped[str] = mapped_column(String(100), index=True)
    mods_pack: Mapped[list[str]] = mapped_column(JSONB, default=list)
    allowed_cars: Mapped[list[str]] = mapped_column(JSONB, default=list)
    status: Mapped[RaceStatus] = enum_column(RaceStatus)
    is_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    results: Mapped[dict | list | None] = mapped_column(JSONB)
    game: Mapped[str] = mapped_column(String(20), default="ACC", server_default="ACC")
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    is_official: Mapped[bool] = mapped_column(Boolean, default=False)
    registered_pilots: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    creator: Mapped[User] = relationship(back_populates="created_races", foreign_keys=[creator_id])
    registrations: Mapped[list["RaceRegistration"]] = relationship(back_populates="race", cascade="all, delete-orphan")
    penalties: Mapped[list["Penalty"]] = relationship(back_populates="race", cascade="all, delete-orphan")
    appeals: Mapped[list["Appeal"]] = relationship(back_populates="race", cascade="all, delete-orphan")


class RaceRegistration(Base):
    __tablename__ = "race_registrations"
    __table_args__ = (UniqueConstraint("race_id", "user_id", name="uq_race_registration_race_user"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("races.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    car_model: Mapped[str] = mapped_column(String(80))
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    race: Mapped[Race] = relationship(back_populates="registrations")
    user: Mapped[User] = relationship()


class Penalty(Base):
    __tablename__ = "penalties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    race_id: Mapped[int] = mapped_column(ForeignKey("races.id", ondelete="CASCADE"), index=True)
    issuer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    penalty_type: Mapped[PenaltyType] = enum_column(PenaltyType, length=10)
    penalty_value: Mapped[float] = mapped_column(Numeric)
    status: Mapped[PenaltyStatus] = enum_column(PenaltyStatus)
    description: Mapped[str] = mapped_column(Text)
    is_applied: Mapped[bool] = mapped_column(Boolean, default=False)
    sr_applied_value: Mapped[float] = mapped_column(Numeric, default=0, server_default="0")

    race: Mapped[Race] = relationship(back_populates="penalties")
    issuer: Mapped[User] = relationship(foreign_keys=[issuer_id])
    target: Mapped[User] = relationship(foreign_keys=[target_id])
    appeals: Mapped[list["Appeal"]] = relationship(back_populates="penalty")


class Appeal(Base):
    __tablename__ = "appeals"
    __table_args__ = (UniqueConstraint("user_id", "penalty_id", name="uq_appeal_user_penalty"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    race_id: Mapped[int] = mapped_column(ForeignKey("races.id", ondelete="CASCADE"), index=True)
    penalty_id: Mapped[int] = mapped_column(ForeignKey("penalties.id", ondelete="CASCADE"), index=True)
    proof_link: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    status: Mapped[AppealStatus] = enum_column(AppealStatus)
    moderator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)

    user: Mapped[User] = relationship(foreign_keys=[user_id])
    moderator: Mapped[User | None] = relationship(foreign_keys=[moderator_id])
    race: Mapped[Race] = relationship(back_populates="appeals")
    penalty: Mapped[Penalty] = relationship(back_populates="appeals")


class Setup(Base):
    __tablename__ = "setups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    race_id: Mapped[int | None] = mapped_column(ForeignKey("races.id", ondelete="SET NULL"), index=True)
    car_model: Mapped[str] = mapped_column(String(50), index=True)
    setup_data: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    user: Mapped[User] = relationship()
    race: Mapped[Race | None] = relationship()


class Banner(Base):
    __tablename__ = "banners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    position: Mapped[BannerPosition] = enum_column(BannerPosition, length=20)
    image_url: Mapped[str] = mapped_column(String(255))
    link_url: Mapped[str] = mapped_column(String(255), default="#")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)

    editor: Mapped[User | None] = relationship()


class NewsItem(Base):
    __tablename__ = "news_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str] = mapped_column(String(255))
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)

    author: Mapped[User | None] = relationship()


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict] = mapped_column(JSONB, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


Index("ix_users_role_status", User.role, User.status)
Index("ix_users_games_gin", User.games, postgresql_using="gin")
Index("ix_users_team_status", User.team_id, User.status)
Index("ix_teams_owner_created", Team.owner_id, Team.created_at)
Index("ix_team_creation_requests_status_created", TeamCreationRequest.status, TeamCreationRequest.created_at)
Index("ix_team_creation_requests_requester_status", TeamCreationRequest.requester_id, TeamCreationRequest.status)
Index(
    "uq_team_creation_request_pending_user",
    TeamCreationRequest.requester_id,
    unique=True,
    postgresql_where=text("status = 'pending'"),
)
Index(
    "uq_team_creation_request_pending_name",
    TeamCreationRequest.name,
    unique=True,
    postgresql_where=text("status = 'pending'"),
)
Index("ix_team_applications_team_status_created", TeamApplication.team_id, TeamApplication.status, TeamApplication.created_at)
Index("ix_team_applications_user_status", TeamApplication.user_id, TeamApplication.status)
Index(
    "uq_team_application_pending_team_user",
    TeamApplication.team_id,
    TeamApplication.user_id,
    unique=True,
    postgresql_where=text("status = 'pending'"),
)
Index("ix_races_status_dates", Race.status, Race.datetime_start, Race.datetime_end)
Index("ix_races_game_status_dates", Race.game, Race.status, Race.datetime_start)
Index("ix_races_registered_pilots_gin", Race.registered_pilots, postgresql_using="gin")
Index("ix_races_mods_pack_gin", Race.mods_pack, postgresql_using="gin")
Index("ix_race_registrations_race_registered_at", RaceRegistration.race_id, RaceRegistration.registered_at)
Index("ix_race_registrations_user_registered_at", RaceRegistration.user_id, RaceRegistration.registered_at)
Index("ix_penalties_race_target_status", Penalty.race_id, Penalty.target_id, Penalty.status)
Index("ix_appeals_status_created", Appeal.status, Appeal.created_at)
Index("uq_banners_position", Banner.position, unique=True)
Index("ix_news_items_published_created", NewsItem.is_published, NewsItem.created_at)
