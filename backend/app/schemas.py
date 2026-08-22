from __future__ import annotations

from datetime import datetime
import re
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, HttpUrl, field_validator, model_validator

from app.models import (
    MAX_RATING,
    MAX_SR,
    MIN_RATING,
    MIN_SR,
    AppealStatus,
    BannerPosition,
    ChampionshipScoringSystem,
    PenaltyStatus,
    PenaltyType,
    RaceStatus,
    Role,
    TeamApplicationStatus,
    UserStatus,
)

GameCode = Literal["ACC", "AC", "iRacing", "LMU"]
AssetGameCode = Literal["ACC", "AC", "iRacing", "LMU"]
TEAM_ABBREVIATION_RE = re.compile(r"^[A-Z]{3}$")
TRACK_ID_RE = re.compile(r"[^a-z0-9_-]+")


class GameRatingRead(BaseModel):
    rating: int = Field(ge=int(MIN_RATING), le=int(MAX_RATING))
    race_count: int = Field(ge=0)


def normalize_team_abbreviation(value: str) -> str:
    abbreviation = str(value or "").strip().upper()
    if not TEAM_ABBREVIATION_RE.fullmatch(abbreviation):
        raise ValueError("Team abbreviation must be exactly 3 latin letters")
    return abbreviation


def normalize_track_asset_id(value: str | None, fallback: str, used: set[str]) -> str:
    candidate = TRACK_ID_RE.sub("-", str(value or "").strip().lower()).strip("-_")
    if not candidate:
        candidate = TRACK_ID_RE.sub("-", fallback.strip().lower()).strip("-_") or "track"
    candidate = candidate[:64]
    base = candidate
    suffix = 2
    while candidate in used:
        candidate = f"{base[:58]}-{suffix}"
        suffix += 1
    used.add(candidate)
    return candidate


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
    pilot_number: int = Field(ge=0, le=999)
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
    game_ratings: dict[str, GameRatingRead] = Field(default_factory=dict)
    discord: str | None
    steam_id: str
    role: Role
    status: UserStatus
    avatar_color: str
    avatar_url: str | None = None
    games: list[str] = Field(default_factory=list)
    team_id: int | None = None
    team_name: str | None = None
    team_abbreviation: str | None = None
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
    pilot_number: int | None = Field(default=None, ge=0, le=999)
    sr: float | None = Field(default=None, ge=MIN_SR, le=MAX_SR)
    rating: int | None = Field(default=None, ge=int(MIN_RATING), le=int(MAX_RATING))
    game_ratings: dict[GameCode, int] | None = None

    @field_validator("game_ratings")
    @classmethod
    def valid_game_ratings(cls, value: dict[GameCode, int] | None):
        if value is None:
            return value
        for rating in value.values():
            if rating < MIN_RATING or rating > MAX_RATING:
                raise ValueError(f"Ratings must be between {int(MIN_RATING)} and {int(MAX_RATING)}")
        return value


class TeamBase(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    abbreviation: str = Field(min_length=3, max_length=3)
    description: str = Field(default="", max_length=1000)
    avatar_color: str = Field(default="#dc2626", pattern=r"^#[0-9A-Fa-f]{6}$")

    @field_validator("abbreviation")
    @classmethod
    def valid_abbreviation(cls, value: str):
        return normalize_team_abbreviation(value)


class TeamCreate(TeamBase):
    pass


class TeamUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    abbreviation: str | None = Field(default=None, min_length=3, max_length=3)
    description: str | None = Field(default=None, max_length=1000)
    avatar_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")

    @field_validator("abbreviation")
    @classmethod
    def valid_abbreviation(cls, value: str | None):
        return normalize_team_abbreviation(value) if value is not None else value


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
    game_ratings: dict[str, GameRatingRead] = Field(default_factory=dict)
    team_id: int | None = None
    team_name: str | None = None
    team_abbreviation: str | None = None
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
    abbreviation: str
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
    abbreviation: str
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
    pilot_number: int
    registered_at: datetime


class RaceBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str
    server_link: str = Field(max_length=255)
    lmu_results_at: datetime | None = None
    datetime_start: datetime
    datetime_end: datetime
    max_pilots: int = Field(ge=1, le=500)
    car_class: str = Field(min_length=1, max_length=50)
    track: str = Field(min_length=1, max_length=100)
    track_id: str | None = Field(default=None, max_length=80)
    mods_pack: list[str] = Field(default_factory=list)
    allowed_cars: list[str] = Field(default_factory=list)
    game: GameCode = "ACC"
    has_qualification: bool = True
    scoring_system: ChampionshipScoringSystem = ChampionshipScoringSystem.fia
    pole_bonus_enabled: bool = False
    is_team_event: bool = False
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


class RaceAssetGameConfig(BaseModel):
    tracks: list[str] = Field(default_factory=list)
    classes: list[RaceAssetClass] = Field(default_factory=list)
    track_images: dict[str, str] = Field(default_factory=dict)
    track_ids: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def normalize_items(self):
        seen_tracks: set[str] = set()
        self.tracks = [
            track
            for track in (item.strip() for item in self.tracks)
            if track and not (track.lower() in seen_tracks or seen_tracks.add(track.lower()))
        ]
        allowed_tracks = {track.lower(): track for track in self.tracks}
        incoming_track_ids = {str(track).strip().lower(): str(track_id).strip() for track, track_id in self.track_ids.items() if str(track_id).strip()}
        used_track_ids: set[str] = set()
        self.track_ids = {
            track: normalize_track_asset_id(incoming_track_ids.get(track.lower()), track, used_track_ids)
            for track in self.tracks
        }
        self.track_images = {
            allowed_tracks[track.strip().lower()]: str(image_url).strip()
            for track, image_url in self.track_images.items()
            if track.strip().lower() in allowed_tracks and str(image_url).strip()
        }
        seen_classes: set[str] = set()
        self.classes = [item for item in self.classes if not (item.name.lower() in seen_classes or seen_classes.add(item.name.lower()))]
        return self


class RaceAssetsConfig(RaceAssetGameConfig):
    games: dict[AssetGameCode, RaceAssetGameConfig] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def accept_legacy_shape(cls, value):
        if isinstance(value, dict) and "games" not in value:
            legacy = {
                "tracks": value.get("tracks", []),
                "classes": value.get("classes", []),
                "track_images": value.get("track_images", {}),
                "track_ids": value.get("track_ids", {}),
            }
            return {
                **legacy,
                "games": {
                    "ACC": legacy,
                    "AC": {"tracks": [], "classes": []},
                    "iRacing": {"tracks": [], "classes": []},
                    "LMU": {"tracks": [], "classes": []},
                },
            }
        return value

    @model_validator(mode="after")
    def sync_legacy_acc_fields(self):
        allowed_games = ("ACC", "AC", "iRacing", "LMU")
        self.games = {game: self.games.get(game, RaceAssetGameConfig()) for game in allowed_games}
        if not self.tracks and not self.classes and not self.track_images:
            acc = self.games["ACC"]
            self.tracks = list(acc.tracks)
            self.classes = list(acc.classes)
            self.track_images = dict(acc.track_images)
            self.track_ids = dict(acc.track_ids)
        self.games["ACC"] = RaceAssetGameConfig(tracks=self.tracks, classes=self.classes, track_images=self.track_images, track_ids=self.track_ids)
        return self


class RaceUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    description: str | None = None
    server_link: str | None = Field(default=None, max_length=255)
    lmu_results_at: datetime | None = None
    datetime_start: datetime | None = None
    datetime_end: datetime | None = None
    max_pilots: int | None = Field(default=None, ge=1, le=500)
    car_class: str | None = Field(default=None, max_length=50)
    track: str | None = Field(default=None, max_length=100)
    track_id: str | None = Field(default=None, max_length=80)
    mods_pack: list[str] | None = None
    allowed_cars: list[str] | None = None
    status: RaceStatus | None = None
    results: dict | list | None = None
    game: GameCode | None = None
    has_qualification: bool | None = None
    scoring_system: ChampionshipScoringSystem | None = None
    pole_bonus_enabled: bool | None = None
    is_team_event: bool | None = None
    is_official: bool | None = None


class TeamRaceRegistrationRead(BaseModel):
    id: int
    race_id: int
    team_id: int
    team_name: str | None = None
    team_abbreviation: str | None = None
    team_avatar_color: str | None = None
    team_avatar_url: str | None = None
    car_model: str
    race_number: int
    drivers: list[dict] = Field(default_factory=list)
    registered_by: int | None = None
    registered_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RaceRead(RaceBase):
    id: int
    status: RaceStatus
    is_passed: bool
    results: dict | list | None
    rating_applied: bool
    video_url: str | None = None
    video_filename: str | None = None
    video_uploaded_at: datetime | None = None
    championship_id: int | None = None
    championship_round: int | None = None
    creator_id: int
    registered_pilots: list[dict]
    team_registrations: list[TeamRaceRegistrationRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RaceManageRead(BaseModel):
    id: int
    name: str
    description: str
    server_link: str
    lmu_results_at: datetime | None = None
    status: RaceStatus
    datetime_start: datetime
    datetime_end: datetime
    max_pilots: int
    registered_count: int
    car_class: str
    track: str
    track_id: str | None = None
    game: str
    has_qualification: bool
    scoring_system: ChampionshipScoringSystem
    pole_bonus_enabled: bool
    is_team_event: bool
    rating_applied: bool
    championship_id: int | None = None
    championship_round: int | None = None
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
    team_abbreviation: str | None = None
    avatar_color: str
    avatar_url: str | None = None
    rating: int
    game_ratings: dict[str, GameRatingRead] = Field(default_factory=dict)
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
    pilot_number: int | None = Field(default=None, ge=0, le=999)


class TeamRaceDriverInput(BaseModel):
    user_id: int = Field(ge=1)


class TeamRaceRegisterRequest(BaseModel):
    car_model: str = Field(min_length=1, max_length=80)
    race_number: int = Field(ge=0, le=999)
    drivers: list[TeamRaceDriverInput] = Field(min_length=1, max_length=6)

    @field_validator("drivers")
    @classmethod
    def unique_drivers(cls, value: list[TeamRaceDriverInput]):
        ids = [item.user_id for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("Choose different team pilots")
        return value


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


class ChampionshipStageCreate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    datetime_start: datetime
    track: str | None = Field(default=None, max_length=100)
    car_class: str | None = Field(default=None, max_length=50)
    server_link: str | None = Field(default="", max_length=255)
    lmu_results_at: datetime | None = None
    has_qualification: bool = True
    scoring_system: ChampionshipScoringSystem = ChampionshipScoringSystem.fia
    pole_bonus_enabled: bool = False
    is_team_event: bool | None = None


class ChampionshipCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=3000)
    classes: list[str] = Field(default_factory=list, min_length=1, max_length=8)
    registration_start: datetime
    registration_end: datetime
    championship_start: datetime
    championship_end: datetime
    video_url: str | None = Field(default=None, max_length=255)
    game: GameCode = "ACC"
    car_change_allowed: bool = False
    scoring_system: ChampionshipScoringSystem = ChampionshipScoringSystem.fia
    pole_bonus_enabled: bool = False
    is_team_event: bool = False
    is_published: bool = False
    stages: list[ChampionshipStageCreate] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def validate_dates_and_classes(self):
        if self.registration_end <= self.registration_start:
            raise ValueError("Registration end must be after registration start")
        if self.championship_end <= self.championship_start:
            raise ValueError("Championship end must be after championship start")
        if self.registration_end > self.championship_end:
            raise ValueError("Registration must end before the championship ends")
        seen: set[str] = set()
        self.classes = [item for item in (value.strip() for value in self.classes) if item and not (item.lower() in seen or seen.add(item.lower()))]
        if not self.classes:
            raise ValueError("Choose at least one class")
        return self


class ChampionshipUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=3000)
    classes: list[str] | None = Field(default=None, min_length=1, max_length=8)
    registration_start: datetime | None = None
    registration_end: datetime | None = None
    championship_start: datetime | None = None
    championship_end: datetime | None = None
    video_url: str | None = Field(default=None, max_length=255)
    game: GameCode | None = None
    car_change_allowed: bool | None = None
    scoring_system: ChampionshipScoringSystem | None = None
    pole_bonus_enabled: bool | None = None
    is_team_event: bool | None = None
    is_published: bool | None = None

    @model_validator(mode="after")
    def normalize_items(self):
        if self.classes is not None:
            seen: set[str] = set()
            self.classes = [item for item in (value.strip() for value in self.classes) if item and not (item.lower() in seen or seen.add(item.lower()))]
            if not self.classes:
                raise ValueError("Choose at least one class")
        return self


class ChampionshipStageAdd(ChampionshipStageCreate):
    pass


class ChampionshipStageUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    datetime_start: datetime | None = None
    track: str | None = Field(default=None, max_length=100)
    car_class: str | None = Field(default=None, max_length=50)
    server_link: str | None = Field(default=None, max_length=255)
    lmu_results_at: datetime | None = None
    has_qualification: bool | None = None
    scoring_system: ChampionshipScoringSystem | None = None
    pole_bonus_enabled: bool | None = None
    is_team_event: bool | None = None


class ChampionshipApplyRequest(BaseModel):
    pilot_number: int = Field(ge=0, le=999)
    car_model: str = Field(min_length=1, max_length=80)


class ChampionshipRegistrationModeration(BaseModel):
    status: TeamApplicationStatus
    car_model: str | None = Field(default=None, max_length=80)
    pilot_number: int | None = Field(default=None, ge=0, le=999)

    @field_validator("status")
    @classmethod
    def valid_status(cls, value: TeamApplicationStatus):
        if value not in {TeamApplicationStatus.approved, TeamApplicationStatus.rejected}:
            raise ValueError("Use approved or rejected")
        return value


class ChampionshipParticipantAdd(BaseModel):
    user_id: int = Field(ge=1)
    car_model: str = Field(min_length=1, max_length=80)
    pilot_number: int = Field(ge=0, le=999)


class ChampionshipCarUpdate(BaseModel):
    car_model: str = Field(min_length=1, max_length=80)


class ChampionshipRegistrationRead(BaseModel):
    id: int
    championship_id: int
    user_id: int
    status: TeamApplicationStatus
    car_model: str | None = None
    pilot_number: int
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None
    resolved_by: int | None = None
    user: TeamMemberRead


class ChampionshipStandingRead(BaseModel):
    user_id: int
    login: str
    first_name: str
    last_name: str
    nickname: str
    pilot_number: int
    team_id: int | None = None
    team_name: str | None = None
    team_abbreviation: str | None = None
    avatar_color: str
    avatar_url: str | None = None
    rating: int
    game_ratings: dict[str, GameRatingRead] = Field(default_factory=dict)
    sr: float
    points: int
    pole_points: int = 0
    starts: int = 0
    best_finish: int | None = None


class ChampionshipRead(BaseModel):
    id: int
    name: str
    description: str
    classes: list[str]
    registration_start: datetime
    registration_end: datetime
    championship_start: datetime
    championship_end: datetime
    video_url: str | None = None
    game: str
    car_change_allowed: bool
    scoring_system: ChampionshipScoringSystem
    pole_bonus_enabled: bool
    is_team_event: bool
    is_published: bool
    creator_id: int
    status: str
    can_apply: bool = False
    my_registration_status: TeamApplicationStatus | None = None
    participant_count: int = 0
    pending_count: int = 0
    stages: list[RaceRead] = Field(default_factory=list)
    registrations: list[ChampionshipRegistrationRead] = Field(default_factory=list)
    standings: list[ChampionshipStandingRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


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
    target_team_abbreviation: str | None = None
    issuer_login: str | None = None
    issuer_nickname: str | None = None
    issuer_rating: int | None = None
    issuer_team_name: str | None = None
    issuer_team_abbreviation: str | None = None


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


class DonationEntry(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    amount: str = Field(min_length=1, max_length=40)
    message: str = Field(default="", max_length=120)


class DonationSettingsRead(BaseModel):
    donation_url: str = ""
    top_donations: list[DonationEntry] = Field(default_factory=list)


class DonationSettingsUpdate(BaseModel):
    donation_url: str = Field(default="", max_length=300)
    top_donations: list[DonationEntry] = Field(default_factory=list, max_length=5)


class BrandingSettingsRead(BaseModel):
    light_logo_url: str
    dark_logo_url: str
    default_avatar_url: str


class SystemSettingsRead(BaseModel):
    requests_per_user_per_minute: int = Field(ge=1, le=10000)
    rating_change_coefficient: float = Field(gt=0, le=10)
    sr_per_race: float = Field(ge=0, le=100)


class SystemSettingsUpdate(BaseModel):
    requests_per_user_per_minute: int = Field(ge=1, le=10000)
    rating_change_coefficient: float = Field(gt=0, le=10)
    sr_per_race: float = Field(ge=0, le=100)


class LicenseTierRead(BaseModel):
    min_rating: int
    max_rating: int
    name: str
    color: str


class LicenseTierUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=30)
    color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")


class LicenseSettingsRead(BaseModel):
    tiers: list[LicenseTierRead]


class LicenseSettingsUpdate(BaseModel):
    tiers: list[LicenseTierUpdate] = Field(min_length=7, max_length=7)


class HallOfFameStatsRead(BaseModel):
    points: int = Field(ge=0)
    gold: int = Field(ge=0)
    silver: int = Field(ge=0)
    bronze: int = Field(ge=0)
    podiums: int = Field(ge=0)


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
    game_ratings: dict[str, GameRatingRead] = Field(default_factory=dict)
    avatar_color: str
    avatar_url: str | None = None
    team_id: int | None = None
    team_name: str | None = None
    team_abbreviation: str | None = None
    points: int = Field(ge=0)
    gold: int = Field(ge=0)
    silver: int = Field(ge=0)
    bronze: int = Field(ge=0)
    podiums: int = Field(ge=0)
    stats_by_game: dict[str, HallOfFameStatsRead] = Field(default_factory=dict)


class HallOfFameTeamRead(BaseModel):
    id: int
    name: str
    abbreviation: str
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
    stats_by_game: dict[str, HallOfFameStatsRead] = Field(default_factory=dict)
    best_pilots_by_game: dict[str, HallOfFamePilotRead] = Field(default_factory=dict)


class HallOfFameRead(BaseModel):
    pilots: list[HallOfFamePilotRead]
    teams: list[HallOfFameTeamRead]


class DashboardStats(BaseModel):
    pilots: int
    completed_races: int
    open_races: int
    staff: int
