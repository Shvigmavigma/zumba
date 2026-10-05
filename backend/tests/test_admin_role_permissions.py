import unittest

from fastapi import HTTPException

from app.config import get_settings
from app.deps import ensure_user_role_change_allowed
from app.models import Role, User


class AdminRolePermissionsTest(unittest.TestCase):
    def test_regular_admin_cannot_grant_admin_role(self):
        admin = User(login="staff-admin", role=Role.admin)
        target = User(login="pilot", role=Role.pilot)

        with self.assertRaises(HTTPException) as context:
            ensure_user_role_change_allowed(admin, target, Role.admin)

        self.assertEqual(context.exception.status_code, 403)

    def test_regular_admin_can_assign_non_admin_roles(self):
        admin = User(login="staff-admin", role=Role.admin)
        target = User(login="pilot", role=Role.pilot)

        ensure_user_role_change_allowed(admin, target, Role.moder)

    def test_system_admin_can_grant_admin_role(self):
        admin = User(login=get_settings().admin_login, role=Role.admin)
        target = User(login="pilot", role=Role.pilot)

        ensure_user_role_change_allowed(admin, target, Role.admin)

    def test_system_admin_cannot_be_demoted(self):
        admin = User(login=get_settings().admin_login, role=Role.admin)
        target = User(login=get_settings().admin_login, role=Role.admin)

        with self.assertRaises(HTTPException) as context:
            ensure_user_role_change_allowed(admin, target, Role.pilot)

        self.assertEqual(context.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
