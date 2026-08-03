from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator, model_validator

from app.models import MAX_RATING, MAX_SR, MIN_RATING, MIN_SR, AppealStatus, BannerPosition, PenaltyStatus, PenaltyType, RaceStatus, Role, TeamApplicationStatus, UserStatus

GameCode = Literal["ACC", "AC", "iRacing", "LMU"]


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
    games: list[GameCode] = Field(default_factory=lambda: ["ACC"], min_length=1, max_length=4)

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
    rating: int = Field(ge=int(MIN_RATING), le=int(MAX_RATING))
    rating_race_count: int = Field(ge=0)
    discord: str | None
    steam_id: str
    role: Role
    status: UserStatus
    avatar_color: str
    avatar_url: str | None = None
    games: list[str] = Field(default_factory=list)
    team_id: int | None = None
    team_name: str | None = None
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
    games: list[GameCode] | None = Field(default=None, min_length=1, max_length=4)


class UserAdminUpdate(UserUpdate):
    login: str | None = Field(default=None, min_length=3, max_length=50)
    pilot_number: int | None = Field(default=None, ge=1, le=9999)


class TeamBase(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=1000)
    avatar_color: str = Field(default="#dc2626", pattern=r"^#[0-9A-Fa-f]{6}$")


class TeamCreate(TeamBase):
    pass


class TeamUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = Field(default=None, max_length=1000)
    avatar_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")


class TeamOwnerTransfer(BaseModel):
    new_owner_id: int = Field(ge=1)


class TeamMemberRead(BaseModel):
    id: int
    login: str
    nickname: str
    pilot_number: int
    country: str | None
    sr: float = Field(ge=MIN_SR, le=MAX_SR)
    rating: int = Field(ge=int(MIN_RATING), le=int(MAX_RATING))
    rating_race_count: int = Field(ge=0)
    team_id: int | None = None
    team_name: str | None = None
    avatar_color: str
    avatar_url: str | None = None
    games: list[str] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}


class TeamApplicationRead(BaseModel):
    id: int
    team_id: int
    user_id: int
    status: TeamApplicationStatus
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    resolved_by: int | None
    user: TeamMemberRead


class TeamCreationRequestRead(BaseModel):
    id: int
    requester_id: int
    name: str
    description: str
    avatar_color: str
    avatar_url: str | None = None
    status: TeamApplicationStatus
    team_id: int | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    resolved_by: int | None
    requester: TeamMemberRead


class TeamRead(BaseModel):
    id: int
    name: str
    description: str
    avatar_color: str
    avatar_url: str | None = None
    owner_id: int | None
    owner_login: str | None = None
    owner_nickname: str | None = None
    member_count: int
    member_limit: int
    average_rating: int = Field(ge=0)
    can_join: bool
    is_member: bool
    is_owner: bool
    can_manage: bool
    my_application_status: TeamApplicationStatus | None = None
    pending_application_count: int = 0
    created_at: datetime
    updated_at: datetime


class TeamDetailRead(TeamRead):
    members: list[TeamMemberRead]
    applications: list[TeamApplicationRead] = Field(default_factory=list)


class TeamConfigRead(BaseModel):
    member_limit: int
    my_create_request_status: TeamApplicationStatus | None = None
    pending_creation_request_count: int = 0


class TeamConfigUpdate(BaseModel):
    member_limit: int = Field(ge=1, le=100)


class RoleUpdate(BaseModel):
    role: Role


class TimeoutRequest(BaseModel):
    timeout_end: datetime


class AdminDangerDeleteRequest(BaseModel):
    confirmation: str = Field(min_length=1, max_length=60)
    confirmation_repeat: str = Field(min_length=1, max_length=60)
    password: str = Field(min_length=1, max_length=128)


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
    has_qualification: bool = True
    is_official: bool = False


class RaceCreate(RaceBase):
    pass


class RaceAssetClass(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    cars: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize_items(self):
        self.name = self.name.strip()
        seen: set[str] = set()
        self.cars = [car for car in (item.strip() for item in self.cars) if car and not (car.lower() in seen or seen.add(car.lower()))]
        return self


class RaceAssetsConfig(BaseModel):
    tracks: list[str] = Field(default_factory=list)
    classes: list[RaceAssetClass] = Field(default_factory=list)

    @model_validator(mode="after")
    def normalize_items(self):
        seen_tracks: set[str] = set()
        self.tracks = [
            track
            for track in (item.strip() for item in self.tracks)
            if track and not (track.lower() in seen_tracks or seen_tracks.add(track.lower()))
        ]
        seen_classes: set[str] = set()
        self.classes = [item for item in self.classes if not (item.name.lower() in seen_classes or seen_classes.add(item.name.lower()))]
        return self


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
    has_qualification: bool | None = None
    is_official: bool | None = None


class RaceRead(RaceBase):
    id: int
    status: RaceStatus
    is_passed: bool
    results: dict | list | None
    rating_applied: bool
    video_url: str | None = None
    video_filename: str | None = None
    video_uploaded_at: datetime | None = None
    creator_id: int
    registered_pilots: list[dict]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RaceManageRead(BaseModel):
    id: int
    name: str
    description: str
    server_link: str
    status: RaceStatus
    datetime_start: datetime
    datetime_end: datetime
    max_pilots: int
    registered_count: int
    car_class: str
    track: str
    game: str
    has_qualification: bool
    rating_applied: bool
    creator_id: int
    is_official: bool
    created_at: datetime
    updated_at: datetime


class FanVoteConfigRead(BaseModel):
    duration_hours: int = Field(ge=1, le=168)


class FanVoteConfigUpdate(BaseModel):
    duration_hours: int = Field(ge=1, le=168)


class FanVoteOptionRead(BaseModel):
    user_id: int
    login: str
    nickname: str
    first_name: str
    last_name: str
    pilot_number: int
    team_name: str | None = None
    avatar_color: str
    avatar_url: str | None = None
    rating: int
    sr: float
    votes: int = 0
    percentage: float = 0


class FanVoteRead(BaseModel):
    enabled: bool
    is_open: bool
    show_results: bool
    duration_hours: int
    started_at: datetime | None = None
    ends_at: datetime | None = None
    total_votes: int = 0
    my_vote_user_id: int | None = None
    options: list[FanVoteOptionRead] = Field(default_factory=list)


class FanVoteSetup(BaseModel):
    option_user_ids: list[int] = Field(min_length=3, max_length=3)

    @field_validator("option_user_ids")
    @classmethod
    def unique_options(cls, value: list[int]):
        if len(set(value)) != len(value):
            raise ValueError("Choose three different pilots")
        return value


class FanVoteCast(BaseModel):
    target_user_id: int = Field(ge=1)


class RaceRegisterRequest(BaseModel):
    car_model: str = Field(min_length=1, max_length=80)


class ResultsUpload(BaseModel):
    results: dict | list


class AccResultsUpload(BaseModel):
    qualification_results: dict | None = None
    race_results: dict


class ManualResultRow(BaseModel):
    user_id: int
    finish_ms: int = Field(ge=0)
    lap_count: int = Field(default=0, ge=0)
    best_lap_ms: int | None = Field(default=None, ge=0)


class ManualResultsUpload(BaseModel):
    rows: list[ManualResultRow] = Field(min_length=1)


class PenaltyCreate(BaseModel):
    race_id: int
    target_id: int
    penalty_type: PenaltyType
    penalty_value: float = Field(gt=0)
    time_penalty_ms: float | None = Field(default=None, ge=0)
    sr_penalty_value: float | None = Field(default=None, ge=0)
    description: str = Field(min_length=1)

    @model_validator(mode="after")
    def normalize_penalty_impacts(self):
        if self.time_penalty_ms is None:
            self.time_penalty_ms = self.penalty_value if self.penalty_type == PenaltyType.time else 0
        if self.sr_penalty_value is None:
            self.sr_penalty_value = self.penalty_value if self.penalty_type == PenaltyType.sr else 0
        if self.time_penalty_ms <= 0 or self.sr_penalty_value <= 0:
            raise ValueError("time_penalty_ms and sr_penalty_value must both be greater than zero")
        self.penalty_type = PenaltyType.combined
        self.penalty_value = self.time_penalty_ms
        return self


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
    target_avatar_url: str | None = None
    target_rating: int | None = None
    target_team_name: str | None = None
    issuer_login: str | None = None
    issuer_nickname: str | None = None
    issuer_rating: int | None = None
    issuer_team_name: str | None = None


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


class TwitchStatus(BaseModel):
    channel_login: str
    channel_url: str
    is_configured: bool
    is_live: bool
    status: Literal["live", "vod", "channel"]
    embed_type: Literal["channel", "video"]
    embed_value: str
    external_url: str
    title: str | None = None
    game_name: str | None = None
    thumbnail_url: str | None = None
    viewer_count: int | None = None
    started_at: datetime | None = None
    published_at: datetime | None = None


class TwitchConfigRead(BaseModel):
    fallback_video_url: str = ""
    fallback_video_id: str = ""
    fallback_video_title: str = ""
    fallback_video_thumbnail_url: str = ""


class TwitchConfigUpdate(BaseModel):
    fallback_video_url: str = Field(default="", max_length=300)
    fallback_video_title: str = Field(default="", max_length=120)


class HallOfFamePilotRead(BaseModel):
    id: int
    login: str
    first_name: str
    last_name: str
    nickname: str
    pilot_number: int
    country: str | None
    sr: float = Field(ge=MIN_SR, le=MAX_SR)
    rating: int = Field(ge=int(MIN_RATING), le=int(MAX_RATING))
    rating_race_count: int = Field(ge=0)
    avatar_color: str
    avatar_url: str | None = None
    team_id: int | None = None
    team_name: str | None = None
    points: int = Field(ge=0)
    gold: int = Field(ge=0)
    silver: int = Field(ge=0)
    bronze: int = Field(ge=0)
    podiums: int = Field(ge=0)


class HallOfFameTeamRead(BaseModel):
    id: int
    name: str
    description: str
    avatar_color: str
    avatar_url: str | None = None
    owner_id: int | None
    member_count: int = Field(ge=0)
    average_rating: int = Field(ge=0)
    points: int = Field(ge=0)
    gold: int = Field(ge=0)
    silver: int = Field(ge=0)
    bronze: int = Field(ge=0)
    podiums: int = Field(ge=0)
    best_pilot: HallOfFamePilotRead | None = None


class HallOfFameRead(BaseModel):
    pilots: list[HallOfFamePilotRead]
    teams: list[HallOfFameTeamRead]


class DashboardStats(BaseModel):
    pilots: int
    completed_races: int
    open_races: int
    staff: int
