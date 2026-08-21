import unittest

from app.routers.users import reassign_restricted_user_references


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


if __name__ == "__main__":
    unittest.main()
