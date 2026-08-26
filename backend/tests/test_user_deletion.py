import unittest

from fastapi import HTTPException

from app.config import get_settings
from app.deps import ensure_not_system_admin, is_system_admin
from app.models import User
from app.routers.users import ensure_danger_request, reassign_restricted_user_references
from app.schemas import AdminDangerDeleteRequest
from app.security import hash_password


class RecordingSession:
    def __init__(self):
        self.tables = []

    async def execute(self, statement):
        self.tables.append(statement.table.name)


class UserDeletionTest(unittest.IsolatedAsyncioTestCase):
    async def test_all_restricting_creator_references_are_reassigned(self):
        session = RecordingSession()
        await reassign_restricted_user_references(session, [42], 1)
        self.assertEqual(session.tables, ["championships", "races", "penalties"])

    def test_configured_admin_is_immutable(self):
        system_admin = User(login=get_settings().admin_login)
        regular_admin = User(login="another-admin")

        self.assertTrue(is_system_admin(system_admin))
        self.assertFalse(is_system_admin(regular_admin))
        with self.assertRaises(HTTPException):
            ensure_not_system_admin(system_admin)
        ensure_not_system_admin(regular_admin)

    def test_bulk_delete_uses_separate_password_hash(self):
        settings = get_settings()
        previous_hash = settings.admin_danger_password_hash
        try:
            settings.admin_danger_password_hash = hash_password("danger-only-password")
            admin = User(login=settings.admin_login, password_hash=hash_password("normal-admin-password"))
            request = AdminDangerDeleteRequest(
                confirmation="DELETE PILOTS",
                confirmation_repeat="DELETE PILOTS",
                password="danger-only-password",
            )
            ensure_danger_request(request, admin, "DELETE PILOTS")

            with self.assertRaises(HTTPException):
                ensure_danger_request(
                    request.model_copy(update={"password": "normal-admin-password"}),
                    admin,
                    "DELETE PILOTS",
                )
        finally:
            settings.admin_danger_password_hash = previous_hash

    def test_invalid_bulk_delete_hash_is_configuration_error(self):
        settings = get_settings()
        previous_hash = settings.admin_danger_password_hash
        try:
            settings.admin_danger_password_hash = "not-a-bcrypt-hash"
            admin = User(login=settings.admin_login)
            request = AdminDangerDeleteRequest(
                confirmation="DELETE RACES",
                confirmation_repeat="DELETE RACES",
                password="anything",
            )

            with self.assertRaises(HTTPException) as context:
                ensure_danger_request(request, admin, "DELETE RACES")
            self.assertEqual(context.exception.status_code, 503)
        finally:
            settings.admin_danger_password_hash = previous_hash


if __name__ == "__main__":
    unittest.main()
