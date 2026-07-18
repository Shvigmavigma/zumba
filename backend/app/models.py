from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Enum as SQLEnum

from app.db import Base


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


class BannerPosition(StrEnum):
    top = "top"
    bottom = "bottom"
    left = "left"
    right = "right"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    login: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    first_name: Mapped[str] = mapped_column(String(50))
    last_name: Mapped[str] = mapped_column(String(50))
    nickname: Mapped[str] = mapped_column(String(80), index=True)
    pilot_number: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    country: Mapped[str | None] = mapped_column(String(50), index=True)
    sr: Mapped[float] = mapped_column(Numeric(3, 1), default=5.0)
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
    pending_profile_changes: Mapped[dict | None] = mapped_column(JSONB)

    created_races: Mapped[list["Race"]] = relationship(back_populates="creator", foreign_keys="Race.creator_id")


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
    game: Mapped[str] = mapped_column(String(50), default="Assetto Corsa")
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    is_official: Mapped[bool] = mapped_column(Boolean, default=False)
    registered_pilots: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    creator: Mapped[User] = relationship(back_populates="created_races", foreign_keys=[creator_id])
    penalties: Mapped[list["Penalty"]] = relationship(back_populates="race", cascade="all, delete-orphan")
    appeals: Mapped[list["Appeal"]] = relationship(back_populates="race", cascade="all, delete-orphan")


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


Index("ix_users_role_status", User.role, User.status)
Index("ix_races_status_dates", Race.status, Race.datetime_start, Race.datetime_end)
Index("ix_races_registered_pilots_gin", Race.registered_pilots, postgresql_using="gin")
Index("ix_races_mods_pack_gin", Race.mods_pack, postgresql_using="gin")
Index("ix_penalties_race_target_status", Penalty.race_id, Penalty.target_id, Penalty.status)
Index("ix_appeals_status_created", Appeal.status, Appeal.created_at)
Index("uq_banners_position", Banner.position, unique=True)
