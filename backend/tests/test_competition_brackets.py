import unittest

from app.routers.competitions import (
    advance_bracket,
    advance_double_elimination,
    build_matches,
    build_tournament_results,
    tournament_results_ready,
)


def participants(count=8):
    return [{"id": f"p{index}", "name": f"Участник {index}"} for index in range(1, count + 1)]


def close_match(match, winner):
    match["winner"] = winner
    match["status"] = "closed"
    match["votes_a"] = 2 if match.get("a") == winner else 1
    match["votes_b"] = 2 if match.get("b") == winner else 1


class CompetitionBracketTest(unittest.TestCase):
    def test_double_elimination_keeps_upper_and_lower_semifinals_separate(self):
        data = {"participants": participants(), "settings": {"variant": "double_elimination"}}
        build_matches(data)

        for match in data["matches"]:
            close_match(match, match["a"])
        advance_double_elimination(data)
        self.assertEqual({(match["bracket"], match["round"]) for match in data["matches"]}, {("upper", 1), ("upper", 2), ("lower", 1)})

        for match in data["matches"]:
            if match["status"] == "open":
                close_match(match, match["a"])
        advance_double_elimination(data)
        semifinals = [match for match in data["matches"] if match["stage"] == "semifinal"]
        self.assertEqual({match["bracket"] for match in semifinals}, {"upper", "lower"})
        self.assertEqual((semifinals[0]["a"], semifinals[0]["b"]), ("p1", "p5"))
        self.assertEqual((semifinals[1]["a"], semifinals[1]["b"]), ("p2", "p6"))

        for match in semifinals:
            close_match(match, match["a"])
        advance_double_elimination(data)
        final = next(match for match in data["matches"] if match.get("bracket") == "final")
        third = next(match for match in data["matches"] if match.get("bracket") == "third_place")
        self.assertEqual((final["a"], final["b"]), ("p1", "p2"))
        self.assertEqual((third["a"], third["b"]), ("p5", "p6"))

        close_match(final, final["a"])
        close_match(third, third["a"])
        self.assertTrue(tournament_results_ready(data))
        self.assertEqual([row["participant_id"] for row in build_tournament_results(data)[:4]], ["p1", "p2", "p5", "p6"])

    def test_direct_bracket_marks_results_ready_after_final(self):
        data = {"participants": participants(4), "settings": {"variant": "direct"}}
        build_matches(data)
        for match in data["matches"]:
            close_match(match, match["a"])
        advance_bracket(data)
        final = next(match for match in data["matches"] if match["round"] == 2 and match["stage"] == "playoff")
        close_match(final, final["a"])
        third = next(match for match in data["matches"] if match.get("stage") == "third_place")
        close_match(third, third["a"])
        self.assertTrue(tournament_results_ready(data))
        self.assertEqual(build_tournament_results(data)[0]["participant_id"], "p1")


if __name__ == "__main__":
    unittest.main()
