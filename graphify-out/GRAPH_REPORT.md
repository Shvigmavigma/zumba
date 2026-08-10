# Graph Report - C:\Users\PC\Desktop\proga\zumba  (2026-08-10)

## Corpus Check
- 82 files · ~69,373 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1544 nodes · 4732 edges · 77 communities (58 shown, 19 thin omitted)
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 727 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Race Backend
- Database Models
- Teams Backend
- Championship Backend
- Race Details UI
- Championship List UI
- Frontend API Utilities
- Admin Users UI
- Rating Profile UI
- Main Menu UI
- Team List UI
- Avatar Upload Backend
- Banner Editor UI
- Admin API Actions
- Shared UI Components
- Fuel Calculator
- Country Selector
- Calendar UI
- Backend Dependencies
- Twitch Backend
- Race Editor UI
- App Shell
- Penalty Modal UI
- Frontend Package
- Backend Config
- Race Admin UI
- News Backend
- Auth Backend
- Pagination Component
- Banner Backend
- News Manager UI
- Project Docs
- Seed Demo Data
- Backend App Startup
- Championship Creation UI
- Setups Backend
- Hall Of Fame Backend
- Championship Registration UI
- News Carousel UI
- Results Upload UI
- Team Editing UI
- Docker Services
- Optional Auth Deps
- Race Video Backend
- User Moderation UI
- Twitch Widget UI
- Race Actions UI
- Result Pilot Display
- Team Account Sync
- Dashboard Stats Backend
- Redesign Mockup
- Race Asset Admin
- Timeout Admin UI
- Championship Edit UI
- Championship Class Select
- Result Timing UI
- Team Creation Requests
- Team Member Admin
- Vite Config
- Backend Package Init
- Default Race Assets
- Championship Car Assets
- Championship Loading
- Championship Pilot Labels
- Championship Stage Count
- Twitch Embed Helpers
- Main Race Metrics
- Main Race Loading
- Twitch Viewer UI
- Main Stage Count
- Race Date Formatting
- Fan Vote Candidates
- Race Registration UI
- Team Creation UI
- PNPM Workspace
- Avatar Asset
- Team Avatar Asset

## God Nodes (most connected - your core abstractions)
1. `User` - 160 edges
2. `api()` - 110 edges
3. `Role` - 88 edges
4. `RaceStatus` - 88 edges
5. `UserStatus` - 85 edges
6. `TeamApplicationStatus` - 85 edges
7. `PenaltyStatus` - 82 edges
8. `BannerPosition` - 82 edges
9. `AppealStatus` - 81 edges
10. `PenaltyType` - 80 edges

## Surprising Connections (you probably didn't know these)
- `PostgreSQL Async SQLAlchemy` --implements--> `Base`  [INFERRED]
  README.md → backend/app/db.py
- `Docker Compose Startup` --semantically_similar_to--> `Docker Compose Stack`  [INFERRED] [semantically similar]
  DEPLOY.md → README.md
- `Appeal` --uses--> `Base`  [INFERRED]
  backend/app/models.py → backend/app/db.py
- `AppSetting` --uses--> `Base`  [INFERRED]
  backend/app/models.py → backend/app/db.py
- `Banner` --uses--> `Base`  [INFERRED]
  backend/app/models.py → backend/app/db.py

## Import Cycles
- 1-file cycle: `backend/app/avatar_uploads.py -> backend/app/avatar_uploads.py`
- 1-file cycle: `backend/app/config.py -> backend/app/config.py`
- 1-file cycle: `backend/app/db.py -> backend/app/db.py`
- 1-file cycle: `backend/app/main.py -> backend/app/main.py`
- 1-file cycle: `backend/app/rate_limit.py -> backend/app/rate_limit.py`
- 1-file cycle: `backend/app/routers/auth.py -> backend/app/routers/auth.py`
- 1-file cycle: `backend/app/routers/banners.py -> backend/app/routers/banners.py`
- 1-file cycle: `backend/app/routers/twitch.py -> backend/app/routers/twitch.py`
- 1-file cycle: `backend/app/security.py -> backend/app/security.py`
- 1-file cycle: `backend/app/deps.py -> backend/app/deps.py`
- 1-file cycle: `backend/app/models.py -> backend/app/models.py`
- 1-file cycle: `backend/app/routers/appeals.py -> backend/app/routers/appeals.py`
- 1-file cycle: `backend/app/routers/championships.py -> backend/app/routers/championships.py`
- 1-file cycle: `backend/app/routers/hall_of_fame.py -> backend/app/routers/hall_of_fame.py`
- 1-file cycle: `backend/app/schemas.py -> backend/app/schemas.py`
- 1-file cycle: `frontend/src/App.vue -> frontend/src/App.vue`
- 1-file cycle: `frontend/src/main.js -> frontend/src/main.js`
- 1-file cycle: `frontend/src/pages/Login.vue -> frontend/src/pages/Login.vue`
- 1-file cycle: `frontend/vite.config.js -> frontend/vite.config.js`
- 2-file cycle: `frontend/src/App.vue -> frontend/src/store.js -> frontend/src/App.vue`

## Hyperedges (group relationships)
- **BMRL Application Stack** — readme_fastapi_rest_api, readme_postgresql_async_sqlalchemy, readme_redis_slowapi_rate_limiting, readme_vue3_spa, docker_compose_backend_service, docker_compose_web_service [INFERRED 0.85]
- **Race Management Workflow** — backend_app_routers_races, frontend_src_pages_racedetails, design_mockups_bmrl_redesign_race_detail_screen, readme_row_lock_registration_rationale [INFERRED 0.75]
- **BMRL Visual Branding Assets** — design_mockups_bmrl_redesign_visual_system, frontend_public_assets_bmrl_logo_nav, frontend_public_assets_banner_top, frontend_public_assets_banner_side, frontend_public_assets_banner_bottom [INFERRED 0.75]

## Communities (77 total, 19 thin omitted)

### Community 0 - "Race Backend"
Cohesion: 0.06
Nodes (118): Penalty, Race, RaceFanVote, RaceRegistration, remove_race_video_file(), create_appeal(), list_appeals(), moderate_appeal() (+110 more)

### Community 1 - "Database Models"
Cohesion: 0.17
Nodes (89): Base, AppealStatus, BannerPosition, ChampionshipScoringSystem, PenaltyStatus, PenaltyType, RaceStatus, Role (+81 more)

### Community 2 - "Teams Backend"
Cohesion: 0.11
Nodes (72): asyncio, Appeal, Team, TeamApplication, TeamCreationRequest, User, application_payload(), approve_team_application() (+64 more)

### Community 3 - "Championship Backend"
Cohesion: 0.12
Nodes (64): AppSetting, Championship, ChampionshipRegistration, assets_for_game(), find_asset_class(), get_race_assets(), normalize_race_assets(), normalize_race_create_assets() (+56 more)

### Community 4 - "Race Details UI"
Cohesion: 0.03
Nodes (45): accQualificationFile, accRaceFile, actionPending, activeResultRows, appeals, canIssuePenalty, canManageRace, canShowRegistrationPanel (+37 more)

### Community 5 - "Championship List UI"
Cohesion: 0.03
Nodes (46): addPilotCar, addPilotId, addPilotNumber, applyCar, applyPilotNumber, approvedRegistrations, assetGames, canChangeMyCar (+38 more)

### Community 6 - "Frontend API Utilities"
Cohesion: 0.06
Nodes (39): API_BASE, apiErrorMessage(), COUNTRY_CODES, countryOptions(), countryOptionsWithCurrent(), displayNames(), i18n, messages (+31 more)

### Community 7 - "Admin Users UI"
Cohesion: 0.04
Nodes (42): activeDangerAction, activeRaceAssetsDraft, busyUsers, dangerActions, dangerDialog, dangerForm, dangerFormValid, dangerResult (+34 more)

### Community 8 - "Rating Profile UI"
Cohesion: 0.06
Nodes (42): userMeta(), openEditDialog(), pilotLine(), registrationPilotLine(), activeTab, data, error, load() (+34 more)

### Community 9 - "Main Menu UI"
Cohesion: 0.04
Nodes (40): Bottom Banner Asset, Side Banner Asset, Top Banner Asset, activeNewsIndex, banners, canEmbedTwitch, canFilterMyGames, currentNews (+32 more)

### Community 10 - "Team List UI"
Cohesion: 0.04
Nodes (38): busyApplications, busyCreateRequests, busyMembers, busyTeams, canCreateTeam, canModerateTeams, config, createForm (+30 more)

### Community 11 - "Avatar Upload Backend"
Cohesion: 0.17
Nodes (43): avatar_extension(), current_upload_day(), ensure_avatar_upload_allowed(), mark_avatar_uploaded(), datetime, UploadFile, remove_avatar_file(), same_utc_day() (+35 more)

### Community 12 - "Banner Editor UI"
Cohesion: 0.07
Nodes (40): applyCrop(), banners, canvasBlob(), clamp(), clampCropOffset(), clearBanner(), clearing, closeBannerImage() (+32 more)

### Community 13 - "Admin API Actions"
Cohesion: 0.06
Nodes (38): api(), chooseRole(), deleteAccount(), saveFanVoteConfig(), saveTeamLimit(), saveTwitchConfig(), saveUserProfile(), updateUserInList() (+30 more)

### Community 14 - "Shared UI Components"
Cohesion: 0.07
Nodes (32): { t }, emit, options, props, { t }, toggle(), countryLabel(), GAME_VALUES (+24 more)

### Community 15 - "Fuel Calculator"
Cohesion: 0.06
Nodes (35): applyPreset(), car, carOptions, cars, copy, currentFuel, expectedLaps, formationLap (+27 more)

### Community 16 - "Country Selector"
Cohesion: 0.09
Nodes (33): activeIndex, addListeners(), choose(), clearCountry(), clearLabelText, closeDropdown(), emit, emptyLabelText (+25 more)

### Community 17 - "Calendar UI"
Cohesion: 0.07
Nodes (30): calendarSources, canFilterMyGames, championships, cursor, dateKey(), dayGameCounts(), dayRaces(), days (+22 more)

### Community 18 - "Backend Dependencies"
Cohesion: 0.18
Nodes (20): get_session(), AsyncSession, get_current_user(), require_active(), require_roles(), enum_column(), datetime, utc_now() (+12 more)

### Community 19 - "Twitch Backend"
Cohesion: 0.19
Nodes (28): AsyncClient, clear_status_cache(), config_from_value(), fallback_status(), fallback_video_status(), get_app_access_token(), get_twitch_config(), get_twitch_config_value() (+20 more)

### Community 20 - "Race Editor UI"
Cohesion: 0.08
Nodes (26): allClassCarsSelected, applyAssetDefaults(), assetGames, carsText, classChoices, currentRaceAssets, error, form (+18 more)

### Community 21 - "App Shell"
Cohesion: 0.08
Nodes (24): HTML Entrypoint, src/main.js Module, Vue App Mount, BMRL Navigation Logo, canEditBanners, canManageNews, canManageRaces, closeMoreMenu() (+16 more)

### Community 22 - "Penalty Modal UI"
Cohesion: 0.13
Nodes (25): appealDraft(), appealDrafts, appealForPenalty(), canAppealPenalty(), emit, isOwnPenalty(), participantById(), participantName() (+17 more)

### Community 23 - "Frontend Package"
Cohesion: 0.09
Nodes (22): dependencies, lucide-vue-next, vite, @vitejs/plugin-vue, vue, vue-i18n, vue-router, devDependencies (+14 more)

### Community 24 - "Backend Config"
Cohesion: 0.12
Nodes (19): Any, get_settings(), Settings, cached_token_limit_key(), ip_limit_key(), is_admin_request(), Request, request_limit_key() (+11 more)

### Community 25 - "Race Admin UI"
Cohesion: 0.10
Nodes (19): isExternalRace(), raceOpenHref(), applyFilters(), busyRace, closeRace(), deleteRace(), error, exportRegistrations() (+11 more)

### Community 26 - "News Backend"
Cohesion: 0.22
Nodes (20): NewsItem, create_news(), delete_news(), delete_news_file(), ensure_news_upload_dir(), invalidate_news_cache(), list_news(), list_news_for_manage() (+12 more)

### Community 27 - "Auth Backend"
Cohesion: 0.28
Nodes (20): finish_steam_callback(), is_loopback_url(), login(), login_redirect(), me(), private_user_response(), AsyncSession, get (+12 more)

### Community 28 - "Pagination Component"
Cohesion: 0.13
Nodes (16): canGoBack, canGoNext, emit, pageLabel, props, setPage(), shouldShow, { t } (+8 more)

### Community 29 - "Banner Backend"
Cohesion: 0.19
Nodes (19): banner_file_url(), clear_banner(), ensure_banner_upload_dir(), file_read(), invalidate_banner_cache(), list_banner_files(), list_banners(), AsyncSession (+11 more)

### Community 30 - "News Manager UI"
Cohesion: 0.13
Nodes (14): busyItems, createNews(), deleteNews(), error, fileInput, form, items, load() (+6 more)

### Community 31 - "Project Docs"
Cohesion: 0.13
Nodes (15): PostgreSQL Backup And Restore, Docker Compose Startup, Environment Configuration, HTTPS Proxying, Steam Public Base URL Requirement, Transfer And Launch Guide, BMRL Race Control, Docker Compose Stack (+7 more)

### Community 32 - "Seed Demo Data"
Cohesion: 0.31
Nodes (13): Banner, hash_password(), demo_car_for_position(), demo_results(), migrate_json_race_registrations(), normalize_user_sr_values(), parse_registered_at(), AsyncSession (+5 more)

### Community 33 - "Backend App Startup"
Cohesion: 0.18
Nodes (11): db_initialization_lock(), init_db(), health(), lifespan(), get, contextlib, fastapi middleware cors, fastapi responses (+3 more)

### Community 34 - "Championship Creation UI"
Cohesion: 0.20
Nodes (12): addStage(), addStageToSelected(), createChampionship(), defaultForm(), defaultStage(), deleteStage(), resetForm(), resetStageEditForm() (+4 more)

### Community 35 - "Setups Backend"
Cohesion: 0.33
Nodes (10): Setup, create_setup(), delete_setup(), list_setups(), AsyncSession, delete, get, limit (+2 more)

### Community 36 - "Hall Of Fame Backend"
Cohesion: 0.29
Nodes (9): empty_stats(), hall_of_fame(), pilot_payload(), podium_position(), AsyncSession, get, limit, Request (+1 more)

### Community 37 - "Championship Registration UI"
Cohesion: 0.33
Nodes (10): addParticipant(), applyToChampionship(), moderateRegistration(), parseCar(), parsePilotNumber(), pilotNumberDraft(), removeParticipant(), replaceChampionship() (+2 more)

### Community 38 - "News Carousel UI"
Cohesion: 0.22
Nodes (9): clampNewsIndex(), closeNewsViewer(), closeTwitchViewer(), goToNews(), handleNewsKeydown(), moveNewsFromViewer(), openNews(), scrollNews() (+1 more)

### Community 39 - "Results Upload UI"
Cohesion: 0.25
Nodes (9): closeRace(), fillManualRows(), parseDuration(), participantName(), readJsonFile(), refreshFanVote(), resultPilotName(), uploadAccResults() (+1 more)

### Community 40 - "Team Editing UI"
Cohesion: 0.42
Nodes (9): approveApplication(), fillEditForm(), load(), rejectApplication(), requestJoin(), saveTeam(), setApplicationBusy(), transferOwnership() (+1 more)

### Community 41 - "Docker Services"
Cohesion: 0.32
Nodes (8): Backend Service, Backend Uploads Volume, Postgres Data Volume, Postgres Service, Redis Service, Docker Compose Stack, Published Port 80, Web Service

### Community 42 - "Optional Auth Deps"
Cohesion: 0.43
Nodes (7): as_utc(), clear_expired_timeout(), get_optional_user(), AsyncSession, datetime, resolve_user_from_token(), HTTPAuthorizationCredentials

### Community 43 - "Race Video Backend"
Cohesion: 0.38
Nodes (6): UploadFile, remove_uploaded_file(), save_race_video_file(), video_extension(), pathlib, uuid

### Community 44 - "User Moderation UI"
Cohesion: 0.29
Nodes (7): ban(), endTimeout(), issueTimeout(), load(), resetUserPageAndLoad(), runDangerAction(), unban()

### Community 45 - "Twitch Widget UI"
Cohesion: 0.38
Nodes (7): clampTwitchWidgetPosition(), dragTwitchWidget(), getTwitchWidgetSize(), handleTwitchResize(), placeTwitchWidget(), startTwitchDrag(), stopTwitchDrag()

### Community 46 - "Race Actions UI"
Cohesion: 0.29
Nodes (7): castFanVote(), createAppeal(), createPenalty(), load(), pilotNumberDraft(), setupFanVote(), syncFanVoteSelection()

### Community 47 - "Result Pilot Display"
Cohesion: 0.29
Nodes (7): participantById(), participantSubtitle(), resultPilotAvatar(), resultPilotColor(), resultPilotRating(), resultPilotSubtitle(), resultPilotTeam()

### Community 48 - "Team Account Sync"
Cohesion: 0.40
Nodes (6): deleteTeam(), leaveTeam(), openTeam(), setBusy(), syncCurrentUser(), updateStoredUser()

### Community 49 - "Dashboard Stats Backend"
Cohesion: 0.40
Nodes (5): AsyncSession, get, limit, Request, stats()

### Community 50 - "Redesign Mockup"
Cohesion: 0.40
Nodes (5): Admin Screen Design, BMRL Redesign Concept, Race Detail Design, Race List Design, Racing Visual System

### Community 51 - "Race Asset Admin"
Cohesion: 0.50
Nodes (4): configFromDraft(), draftFromConfig(), normalizeRaceAssetsDraft(), saveRaceAssets()

### Community 52 - "Timeout Admin UI"
Cohesion: 0.67
Nodes (4): datetimeLocalValue(), defaultTimeoutUntil(), openTimeoutDialog(), timeoutMin()

### Community 53 - "Championship Edit UI"
Cohesion: 0.67
Nodes (3): startEditChampionship(), startEditStage(), toLocalInput()

### Community 54 - "Championship Class Select"
Cohesion: 0.67
Nodes (3): toggleClass(), toggleClassIn(), toggleEditClass()

### Community 55 - "Result Timing UI"
Cohesion: 0.67
Nodes (3): formatDuration(), resultGap(), resultPenalty()

### Community 56 - "Team Creation Requests"
Cohesion: 0.67
Nodes (3): approveCreateRequest(), rejectCreateRequest(), setCreateRequestBusy()

### Community 57 - "Team Member Admin"
Cohesion: 0.67
Nodes (3): memberTitle(), removeMember(), setMemberBusy()

## Knowledge Gaps
- **496 isolated node(s):** `name`, `version`, `private`, `type`, `dev` (+491 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **19 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Vue 3 SPA` connect `Project Docs` to `App Shell`, `Frontend API Utilities`?**
  _High betweenness centrality (0.464) - this node is a cross-community bridge._
- **Why does `Base` connect `Database Models` to `Seed Demo Data`, `Race Backend`, `Teams Backend`, `Championship Backend`, `Setups Backend`, `Backend Dependencies`, `News Backend`, `Project Docs`?**
  _High betweenness centrality (0.169) - this node is a cross-community bridge._
- **Are the 74 inferred relationships involving `Role` (e.g. with `Base` and `AccResultsUpload`) actually correct?**
  _`Role` has 74 INFERRED edges - model-reasoned connections that need verification._
- **Are the 74 inferred relationships involving `RaceStatus` (e.g. with `Base` and `AccResultsUpload`) actually correct?**
  _`RaceStatus` has 74 INFERRED edges - model-reasoned connections that need verification._
- **Are the 74 inferred relationships involving `UserStatus` (e.g. with `Base` and `AccResultsUpload`) actually correct?**
  _`UserStatus` has 74 INFERRED edges - model-reasoned connections that need verification._
- **What connects `name`, `version`, `private` to the rest of the system?**
  _496 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Race Backend` be split into smaller, more focused modules?**
  _Cohesion score 0.062324929971988796 - nodes in this community are weakly interconnected._