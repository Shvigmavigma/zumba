import unittest
from types import SimpleNamespace

from app.models import RACE_GAMES, default_game_ratings
from app.services import record_rating_adjustments, reset_ratings_for_recalculation


class RatingAdjustmentsTest(unittest.TestCase):
    def test_manual_delta_survives_recalculation_reset(self):
        user = SimpleNamespace(
            rating_adjustments={},
            game_ratings=default_game_ratings(),
            rating=1000,
            rating_race_count=0,
        )
        previous = {game: 1000 for game in RACE_GAMES}
        current = {**previous, "ACC": 1125}

        record_rating_adjustments(user, previous, current)
        reset_ratings_for_recalculation(user)

        self.assertEqual(user.rating_adjustments, {"ACC": 125})
        self.assertEqual(user.game_ratings["ACC"]["rating"], 1125)
        self.assertEqual(user.rating, 1125)

    def test_manual_delta_can_be_reversed(self):
        user = SimpleNamespace(rating_adjustments={"ACC": 125})

        record_rating_adjustments(
            user,
            {game: 1000 for game in RACE_GAMES},
            {**{game: 1000 for game in RACE_GAMES}, "ACC": 875},
        )

        self.assertEqual(user.rating_adjustments, {})


if __name__ == "__main__":
    unittest.main()
