import asyncio
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Race, RaceStatus, Role, Team, TeamRaceRegistration, User, UserStatus
from app.routers.races import build_acc_team_results_payload, build_team_driver_payloads, get_team_registration_rows
from app.services import recalculate_race_results


def acc_line(registration: TeamRaceRegistration, driver: dict, position: int, race_index: int) -> dict:
    driver_data = {
        "firstName": driver.get("first_name"),
        "lastName": driver.get("last_name"),
        "shortName": driver.get("short_name"),
        "playerId": driver.get("steam_id"),
    }
    finish_ms = 3_600_000 + position * 18_500 + race_index * 7_000
    return {
        "currentDriver": driver_data,
        "car": {
            "raceNumber": registration.race_number,
            "carModel": registration.car_model,
            "drivers": [driver_data],
        },
        "timing": {
            "totalTime": finish_ms,
            "lapCount": 24,
            "bestLap": 91_000 + position * 230,
        },
        "driverTotalTimes": [finish_ms],
    }


async def eligible_teams(session, limit: int = 4) -> list[tuple[Team, list[User]]]:
    selected: list[tuple[Team, list[User]]] = []
    teams = list((await session.scalars(select(Team).order_by(Team.id))).all())
    for team in teams:
        members = list(
            (
                await session.scalars(
                    select(User)
                    .where(User.team_id == team.id, User.status == UserStatus.active)
                    .order_by(User.id)
                    .limit(2)
                )
            ).all()
        )
        if len(members) >= 2:
            selected.append((team, members))
        if len(selected) == limit:
            return selected
    raise RuntimeError(f"Need at least {limit} teams with two active drivers")


async def main() -> None:
    async with SessionLocal() as session:
        creator = await session.scalar(select(User).where(User.role == Role.admin).order_by(User.id))
        if creator is None:
            raise RuntimeError("Admin user is required to create simulated races")
        teams = await eligible_teams(session)
        now = datetime.now(timezone.utc)
        run_label = now.strftime("%Y-%m-%d %H:%M:%S UTC")
        summaries: list[dict] = []

        for race_index in range(1, 3):
            has_qualification = race_index == 1
            start = now - timedelta(hours=5 - race_index * 2)
            race = Race(
                name=f"Симуляция командной гонки #{race_index} — {run_label}",
                description="Автоматическая проверка командных регистраций, результатов и счётчиков.",
                server_link="https://example.invalid/team-race-simulation",
                datetime_start=start,
                datetime_end=start + timedelta(hours=1, minutes=30),
                max_pilots=8,
                car_class="GT3",
                track="Spa-Francorchamps" if race_index == 1 else "Monza",
                mods_pack=[],
                allowed_cars=["12"],
                status=RaceStatus.ongoing,
                is_passed=False,
                results=None,
                game="ACC",
                has_qualification=has_qualification,
                is_team_event=True,
                is_official=False,
                creator_id=creator.id,
            )
            session.add(race)
            await session.flush()

            for position, (team, members) in enumerate(teams, start=1):
                drivers = await build_team_driver_payloads(session, team, [member.id for member in members])
                session.add(
                    TeamRaceRegistration(
                        race_id=race.id,
                        team_id=team.id,
                        car_model="12",
                        race_number=race_index * 100 + position,
                        drivers=drivers,
                        registered_by=team.owner_id,
                        registered_at=start - timedelta(days=1, minutes=position),
                    )
                )
            await session.flush()

            registration_rows = await get_team_registration_rows(session, race.id)
            race_lines = [
                acc_line(registration, registration.drivers[0], position, race_index)
                for position, (registration, _) in enumerate(registration_rows, start=1)
            ]
            qualification = (
                {
                    "sessionType": "Q",
                    "trackName": race.track,
                    "sessionResult": {"leaderBoardLines": list(reversed(race_lines))},
                }
                if has_qualification
                else None
            )
            race_payload = {
                "sessionType": "R",
                "trackName": race.track,
                "sessionResult": {"leaderBoardLines": race_lines},
            }
            race.results = build_acc_team_results_payload(race, qualification, race_payload, registration_rows)
            await recalculate_race_results(session, race)
            race.status = RaceStatus.finished
            race.is_passed = True
            summaries.append(
                {
                    "race_id": race.id,
                    "name": race.name,
                    "registered_teams": len(registration_rows),
                    "result_rows": len(race.results.get("rows", [])),
                    "winner": race.results["rows"][0].get("team_name"),
                    "has_qualification": has_qualification,
                }
            )

        await session.commit()
        print(json.dumps({"simulated_races": summaries}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
