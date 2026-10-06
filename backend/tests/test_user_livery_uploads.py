import asyncio
import io
import json
import zipfile
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.datastructures import UploadFile

from app.db import get_session
from app.deps import get_current_user
from app.main import app
from app.models import Role, UserStatus
from app.user_livery_uploads import create_user_livery_package, prune_user_livery_packages, skin_folder_from_car_json, user_livery_asset_path
from app.routers.users import user_livery_catalog_response


def upload(name: str, data: bytes) -> UploadFile:
    return UploadFile(filename=name, file=io.BytesIO(data))


def create_package(tmp_path, car_json: bytes, folder_file: str):
    return asyncio.run(
        create_user_livery_package(
            42,
            upload("0-car.json", car_json),
            [upload(folder_file, b"livery asset")],
            [],
            max_archive_mb=2,
            max_image_mb=1,
            root=tmp_path,
        )
    )


def test_package_preserves_the_exact_custom_skin_name(tmp_path):
    car_json = json.dumps({"customSkinName": "Super Taikyu TKRI Marin Kitagawa AMG GT3"}).encode("utf-16")
    package_id, skin_name, _, _, _, package_dir = create_package(
        tmp_path,
        car_json,
        "Super Taikyu TKRI Marin Kitagawa AMG GT3/livery.json",
    )

    assert skin_name == "Super Taikyu TKRI Marin Kitagawa AMG GT3"
    with zipfile.ZipFile(package_dir / "cars.zip") as archive:
        assert archive.namelist() == ["0-car.json"]
        assert json.loads(archive.read("0-car.json")) == {"customSkinName": skin_name}
    with zipfile.ZipFile(package_dir / "liveries.zip") as archive:
        assert archive.namelist() == [f"{skin_name}/livery.json"]
    assert user_livery_asset_path(42, package_id, "cars.zip", tmp_path) == package_dir / "cars.zip"


def test_rejects_a_folder_that_does_not_match_the_json(tmp_path):
    with pytest.raises(HTTPException) as error:
        create_package(tmp_path, b'{"customSkinName":"sui"}', "zumbaa/skin.json")
    assert error.value.status_code == 400
    assert "exactly 'sui'" in error.value.detail


def test_rejects_path_traversal_in_uploaded_folder(tmp_path):
    with pytest.raises(HTTPException) as error:
        create_package(tmp_path, b'{"customSkinName":"sui"}', "sui/../outside.json")
    assert error.value.status_code == 400


def test_skin_name_is_required_and_path_safe():
    with pytest.raises(HTTPException):
        skin_folder_from_car_json(b'{"teamName":"sui"}')
    with pytest.raises(HTTPException):
        skin_folder_from_car_json(b'{"customSkinName":"../outside"}')


def test_livery_asset_paths_are_confined_to_the_package(tmp_path):
    package_id = "a" * 32
    package_dir = tmp_path / "42" / package_id / "images"
    package_dir.mkdir(parents=True)
    image_path = package_dir / "preview.png"
    image_path.write_bytes(b"image")

    assert user_livery_asset_path(42, package_id, "images/preview.png", tmp_path) == image_path
    assert user_livery_asset_path(42, package_id, "../../secrets", tmp_path) is None
    assert user_livery_asset_path(42, "not-a-package", "cars.zip", tmp_path) is None


def test_cache_pruning_keeps_current_and_previous_versions(tmp_path):
    user_dir = tmp_path / "42"
    current, previous, stale = "a" * 32, "b" * 32, "c" * 32
    for package_id in (current, previous, stale):
        package = user_dir / package_id
        package.mkdir(parents=True)
        (package / "cars.zip").write_bytes(b"cached")

    prune_user_livery_packages(42, {current, previous}, tmp_path)

    assert (user_dir / current).is_dir()
    assert (user_dir / previous).is_dir()
    assert not (user_dir / stale).exists()

    prune_user_livery_packages(42, set(), tmp_path)
    assert list(user_dir.iterdir()) == []


def test_livery_catalog_contains_only_download_metadata_and_public_pilot_identity():
    livery = SimpleNamespace(
        user_id=42,
        package_id="a" * 32,
        custom_skin_name="sui",
        cars_archive_size=123,
        liveries_archive_size=456,
        uploaded_at=datetime(2026, 10, 6, tzinfo=timezone.utc),
    )

    response = user_livery_catalog_response(livery, "Sui Racer", 58)

    assert response["pilot_name"] == "Sui Racer"
    assert response["pilot_number"] == 58
    assert response["cars_archive_url"] == f"/api/users/42/livery-assets/{'a' * 32}/cars.zip"
    assert response["liveries_archive_url"] == f"/api/users/42/livery-assets/{'a' * 32}/liveries.zip"
    assert response["images"] == []
    assert "email" not in response
    assert "login" not in response


def test_public_livery_catalog_route_returns_all_metadata_with_short_cache():
    livery = SimpleNamespace(
        user_id=42,
        package_id="b" * 32,
        custom_skin_name="sui",
        cars_archive_size=123,
        liveries_archive_size=456,
        uploaded_at=datetime(2026, 10, 6, tzinfo=timezone.utc),
    )

    class FakeSession:
        async def execute(self, _query):
            return [(livery, "Sui Racer", 58)]

    async def override_session():
        yield FakeSession()

    app.dependency_overrides[get_session] = override_session
    try:
        response = TestClient(app).get("/api/users/liveries")
    finally:
        app.dependency_overrides.pop(get_session, None)

    assert response.status_code == 200
    assert response.headers["cache-control"] == "public, max-age=60, stale-while-revalidate=300"
    assert response.json()[0]["user_id"] == 42
    assert response.json()[0]["pilot_name"] == "Sui Racer"
    assert response.json()[0]["pilot_number"] == 58
    assert response.json()[0]["images"] == []


def test_admin_livery_upload_checks_staff_role_and_never_replaces_by_default(monkeypatch):
    files = [
        ("car_file", ("0-car.json", b'{"customSkinName":"sui"}', "application/json")),
        ("livery_files", ("sui/livery.json", b"{}", "application/json")),
    ]

    async def pilot_user():
        return SimpleNamespace(role=Role.pilot, status=UserStatus.active)

    monkeypatch.setitem(app.dependency_overrides, get_current_user, pilot_user)
    response = TestClient(app).put("/api/users/42/livery", files=files)
    assert response.status_code == 403

    async def admin_user():
        return SimpleNamespace(role=Role.admin, status=UserStatus.active)

    class FakeSession:
        statements = []

        async def scalar(self, statement):
            self.statements.append(str(statement))
            return SimpleNamespace(id=42)

    fake_session = FakeSession()

    async def override_session():
        yield fake_session

    monkeypatch.setitem(app.dependency_overrides, get_current_user, admin_user)
    monkeypatch.setitem(app.dependency_overrides, get_session, override_session)
    response = TestClient(app).put("/api/users/42/livery", files=files)

    assert response.status_code == 409
    assert "users.role" in fake_session.statements[0]
    assert "users.status" in fake_session.statements[0]
