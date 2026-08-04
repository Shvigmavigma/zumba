from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AppSetting, Race
from app.schemas import RaceAssetGameConfig, RaceAssetsConfig


RACE_ASSETS_KEY = "race_assets"
RACE_ASSET_GAMES = {"ACC", "AC", "iRacing"}

DEFAULT_RACE_ASSETS = {
    "tracks": [
        "Autodromo Internazionale Enzo e Dino Ferrari (2020 GT World Challenge Pack)",
        "Barcelona",
        "Brands Hatch",
        "Circuit of the Americas (American Track Pack)",
        "Donington Park (British GT Pack)",
        "Hungaroring",
        "Indianapolis (American Track Pack)",
        "Kyalami (Intercontinental GT Pack)",
        "Laguna Seca (Intercontinental GT Pack)",
        "Misano",
        "Monza",
        "Mount Panorama (Intercontinental GT Pack)",
        "Nurburgring",
        "Nurburgring 24h (Nurburgring 24h Pack)",
        "Oulton Park (British GT Pack)",
        "Paul Ricard",
        "Red Bull Ring (GT2 Pack)",
        "Ricardo Tormo Circuit (2023 Pack)",
        "Silverstone",
        "Snetterton (British GT Pack)",
        "Spa-Francorchamps",
        "Suzuka (Intercontinental GT Pack)",
        "Watkins Glen (American Track Pack)",
        "Zandvoort",
        "Zolder",
    ],
    "classes": [
        {
            "name": "GT3",
            "cars": [
                "Aston Martin V12 Vantage GT3 2013",
                "Aston Martin V8 Vantage GT3 2019",
                "Audi R8 LMS GT3 2015",
                "Audi R8 LMS Evo GT3 2019",
                "Audi R8 LMS Evo II GT3 2022",
                "Bentley Continental GT3 2015",
                "Bentley Continental GT3 2018",
                "BMW M6 GT3 2017",
                "BMW M4 GT3 2021",
                "Emil Frey Jaguar GT3 2012",
                "Ferrari 296 GT3 2023",
                "Ferrari 488 GT3 2018",
                "Ferrari 488 EVO GT3 2020",
                "Ford Mustang GT3 2024",
                "Honda NSX GT3 2017",
                "Honda NSX Evo GT3 2019",
                "Lamborghini Huracan EVO2 GT3 2023",
                "Lamborghini Huracan GT3 2015",
                "Lamborghini Huracan Evo GT3 2019",
                "Lexus RC F GT3 2016",
                "McLaren 650S GT3 2015",
                "McLaren 720S GT3 2019",
                "McLaren 720S Evo GT3 2023",
                "Mercedes AMG GT3 2015",
                "Mercedes AMG Evo GT3 2020",
                "Nissan GTR Nismo GT3 2015",
                "Nissan GTR Nismo GT3 2018",
                "Porsche 911 GT3 R 2018",
                "Porsche 911 II GT3R 2019",
                "Porsche 992 GT3R 2023",
                "Reiter Engineering R-EX GT3 2017",
            ],
        },
        {
            "name": "GT2",
            "cars": [
                "Audi R8 LMS GT2",
                "KTM X-Bow GT2",
                "Maserati MC20 GT2",
                "Mercedes-AMG GT2",
                "Porsche 935 (2019)",
                "Porsche 911 GT2 RS CS EVO Kit",
            ],
        },
        {
            "name": "GT4",
            "cars": [
                "Alpine A110 2018",
                "AMR V8 Vantage 2018",
                "Audi R8 LMS 2018",
                "BMW M4 2018",
                "Chevrolet Camaro R 2017",
                "Ginetta G55 2012",
                "KTM X-Bow 2016",
                "Maserati Granturismo MC 2016",
                "McLaren 570S 2016",
                "Mercedes AMG 2016",
                "Porsche 718 Cayman GT4 Clubsport 2019",
            ],
        },
        {"name": "TCX", "cars": ["BMW M2 CS 2020"]},
        {"name": "Ferrari Challenge", "cars": ["Ferrari 488 Challenge Evo 2020"]},
        {
            "name": "Lamborghini Super Trofeo",
            "cars": [
                "Lamborghini Huracan Super Trofeo 2015",
                "Lamborghini Huracan Super Trofeo Evo 2 2021",
            ],
        },
        {
            "name": "Porsche CUP",
            "cars": [
                "Porsche 911 II GT3 Cup 2017",
                "Porsche 911 GT3 Cup (992) 2021",
            ],
        },
    ],
}
DEFAULT_RACE_ASSETS["games"] = {
    "ACC": {"tracks": DEFAULT_RACE_ASSETS["tracks"], "classes": DEFAULT_RACE_ASSETS["classes"]},
    "AC": {"tracks": [], "classes": []},
    "iRacing": {"tracks": [], "classes": []},
}


def normalize_race_assets(value: dict | None) -> RaceAssetsConfig:
    if not isinstance(value, dict):
        value = DEFAULT_RACE_ASSETS
    return RaceAssetsConfig.model_validate(value)


async def get_race_assets(session: AsyncSession) -> RaceAssetsConfig:
    setting = await session.get(AppSetting, RACE_ASSETS_KEY)
    return normalize_race_assets(setting.value if setting is not None else None)


async def save_race_assets(session: AsyncSession, payload: RaceAssetsConfig) -> RaceAssetsConfig:
    normalized = normalize_race_assets(payload.model_dump())
    setting = await session.get(AppSetting, RACE_ASSETS_KEY)
    if setting is None:
        setting = AppSetting(key=RACE_ASSETS_KEY, value=normalized.model_dump())
        session.add(setting)
    else:
        setting.value = normalized.model_dump()
    await session.commit()
    return normalized


def assets_for_game(config: RaceAssetsConfig, game: str) -> RaceAssetGameConfig:
    if game == "ACC":
        return RaceAssetGameConfig(tracks=config.tracks, classes=config.classes)
    return config.games.get(game, RaceAssetGameConfig())


def find_asset_class(config: RaceAssetGameConfig, class_name: str):
    normalized_name = class_name.strip().lower()
    return next((item for item in config.classes if item.name.lower() == normalized_name), None)


def validate_asset_selection(config: RaceAssetsConfig, game: str, track: str, car_class: str, allowed_cars: list[str] | None) -> list[str]:
    game_config = assets_for_game(config, game)
    if track.strip().lower() not in {item.lower() for item in game_config.tracks}:
        raise HTTPException(status_code=400, detail="Track is not in race assets")
    asset_class = find_asset_class(game_config, car_class)
    if asset_class is None:
        raise HTTPException(status_code=400, detail="Class is not in race assets")
    selected_cars = [item.strip() for item in (allowed_cars or asset_class.cars) if item.strip()]
    if not selected_cars:
        raise HTTPException(status_code=400, detail="Choose at least one allowed car")
    class_cars = {item.lower() for item in asset_class.cars}
    invalid_cars = [item for item in selected_cars if item.lower() not in class_cars]
    if invalid_cars:
        raise HTTPException(status_code=400, detail=f"Cars are not in selected class: {', '.join(invalid_cars[:5])}")
    return selected_cars


async def normalize_race_create_assets(session: AsyncSession, data: dict) -> dict:
    game = data.get("game")
    if game not in RACE_ASSET_GAMES:
        return data
    config = await get_race_assets(session)
    data["allowed_cars"] = validate_asset_selection(config, game, data.get("track", ""), data.get("car_class", ""), data.get("allowed_cars"))
    return data


async def normalize_race_update_assets(session: AsyncSession, race: Race, data: dict) -> dict:
    asset_fields = {"game", "track", "car_class", "allowed_cars"}
    if not asset_fields.intersection(data):
        return data
    game = data.get("game", race.game)
    if game not in RACE_ASSET_GAMES:
        return data
    config = await get_race_assets(session)
    data["allowed_cars"] = validate_asset_selection(
        config,
        game,
        data.get("track", race.track),
        data.get("car_class", race.car_class),
        data.get("allowed_cars", race.allowed_cars),
    )
    return data
