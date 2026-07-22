from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator

from app.models import MAX_SR, MIN_SR, AppealStatus, BannerPosition, PenaltyStatus, PenaltyType, RaceStatus, Role, UserStatus

GameCode = Literal["ACC", "AC", "iRacing"]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserPrivate"


class LoginRequest(BaseModel):
    login: str
    password: str


class UserRegister(BaseModel):
    login: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    password_confirm: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    nickname: str = Field(min_length=1, max_length=80)
    pilot_number: int = Field(ge=1, le=9999)
    steam_auth_token: str = Field(min_length=1)
    country: str | None = Field(default=None, max_length=50)
    discord: str | None = Field(default=None, max_length=100)
    avatar_color: str = Field(default="#2563eb", pattern=r"^#[0-9A-Fa-f]{6}$")
    games: list[GameCode] = Field(default_factory=lambda: ["ACC"], min_length=1, max_length=3)

    @field_validator("password_confirm")
    @classmethod
    def passwords_match(cls, value: str, info):
        if info.data.get("password") != value:
            raise ValueError("passwords do not match")
        return value


class UserPublic(BaseModel):
    id: int
    login: str
    first_name: str
    last_name: str
    nickname: str
    pilot_number: int
    country: str | None
    sr: float = Field(ge=MIN_SR, le=MAX_SR)
    discord: str | None
    steam_id: str
    role: Role
    status: UserStatus
    avatar_color: str
    games: list[str] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}


class UserPrivate(UserPublic):
    email: EmailStr
    updated_at: datetime
    ban_end: datetime | None
    timeout_start: datetime | None
    timeout_end: datetime | None
    pending_profile_changes: dict | None = None


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    first_name: str | None = Field(default=None, max_length=50)
    last_name: str | None = Field(default=None, max_length=50)
    nickname: str | None = Field(default=None, max_length=80)
    country: str | None = Field(default=None, max_length=50)
    discord: str | None = Field(default=None, max_length=100)
    avatar_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    games: list[GameCode] | None = Field(default=None, min_length=1, max_length=3)


class RoleUpdate(BaseModel):
    role: Role


class TimeoutRequest(BaseModel):
    timeout_end: datetime


class RegisteredPilot(BaseModel):
    user_id: int
    car_model: str
    registered_at: datetime


class RaceBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str
    server_link: str = Field(max_length=255)
    datetime_start: datetime
    datetime_end: datetime
    max_pilots: int = Field(ge=1, le=500)
    car_class: str = Field(min_length=1, max_length=50)
    track: str = Field(min_length=1, max_length=100)
    mods_pack: list[str] = Field(default_factory=list)
    allowed_cars: list[str] = Field(default_factory=list)
    game: GameCode = "ACC"
    is_official: bool = False


class RaceCreate(RaceBase):
    pass


class RaceUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    description: str | None = None
    server_link: str | None = Field(default=None, max_length=255)
    datetime_start: datetime | None = None
    datetime_end: datetime | None = None
    max_pilots: int | None = Field(default=None, ge=1, le=500)
    car_class: str | None = Field(default=None, max_length=50)
    track: str | None = Field(default=None, max_length=100)
    mods_pack: list[str] | None = None
    allowed_cars: list[str] | None = None
    status: RaceStatus | None = None
    results: dict | list | None = None
    game: GameCode | None = None
    is_official: bool | None = None


class RaceRead(RaceBase):
    id: int
    status: RaceStatus
    is_passed: bool
    results: dict | list | None
    creator_id: int
    registered_pilots: list[dict]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RaceManageRead(BaseModel):
    id: int
    name: str
    description: str
    status: RaceStatus
    datetime_start: datetime
    datetime_end: datetime
    max_pilots: int
    registered_count: int
    car_class: str
    track: str
    game: str
    creator_id: int
    is_official: bool
    created_at: datetime
    updated_at: datetime


class RaceRegisterRequest(BaseModel):
    car_model: str = Field(min_length=1, max_length=80)


class ResultsUpload(BaseModel):
    results: dict | list


class PenaltyCreate(BaseModel):
    race_id: int
    target_id: int
    penalty_type: PenaltyType
    penalty_value: float = Field(gt=0)
    description: str = Field(min_length=1)


class PenaltyRead(PenaltyCreate):
    id: int
    issuer_id: int
    created_at: datetime
    status: PenaltyStatus
    is_applied: bool
    sr_applied_value: float = 0.0

    model_config = {"from_attributes": True}


class PenaltyDetailRead(PenaltyRead):
    race_name: str | None = None
    target_login: str | None = None
    target_nickname: str | None = None
    target_pilot_number: int | None = None
    target_avatar_color: str | None = None
    issuer_login: str | None = None
    issuer_nickname: str | None = None


class AppealCreate(BaseModel):
    race_id: int
    penalty_id: int
    proof_link: HttpUrl
    description: str = Field(min_length=1)


class AppealModerationRequest(BaseModel):
    status: AppealStatus
    rejection_reason: str | None = None


class AppealRead(BaseModel):
    id: int
    created_at: datetime
    user_id: int
    race_id: int
    penalty_id: int
    proof_link: str
    description: str
    rejection_reason: str | None
    status: AppealStatus
    moderator_id: int | None

    model_config = {"from_attributes": True}


class SetupCreate(BaseModel):
    race_id: int | None = None
    car_model: str = Field(min_length=1, max_length=50)
    setup_data: str = Field(min_length=1, max_length=255)
    description: str | None = None


class SetupRead(SetupCreate):
    id: int
    user_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class BannerUpdate(BaseModel):
    image_url: str = Field(default="", max_length=255)
    link_url: str = Field(default="#", max_length=255)


class BannerRead(BannerUpdate):
    id: int
    position: BannerPosition
    updated_at: datetime
    updated_by: int | None

    model_config = {"from_attributes": True}


class BannerFileRead(BaseModel):
    name: str
    url: str
    size: int
    updated_at: datetime


class NewsItemRead(BaseModel):
    id: int
    title: str
    body: str
    image_url: str
    is_published: bool
    created_at: datetime
    updated_at: datetime
    created_by: int | None

    model_config = {"from_attributes": True}


class NewsItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    body: str | None = Field(default=None, min_length=1, max_length=1000)
    is_published: bool | None = None


class DashboardStats(BaseModel):
    pilots: int
    completed_races: int
    open_races: int
    staff: int
