import unittest

from knockout_logic import MatchSchedulerService


class MatchSchedulerServiceTest(unittest.TestCase):
    def test_round_robin_single_players(self):
        matches = MatchSchedulerService.generate_round_robin(["A", "B", "C"], num_courts=2, match_type="don")

        pairs = {(match["doi_a"], match["doi_b"]) for match in matches}
        self.assertEqual(len(matches), 3)
        self.assertEqual(pairs, {("A", "B"), ("A", "C"), ("B", "C")})
        self.assertTrue(all(match["san"] in (1, 2) for match in matches))

    def test_smart_pairing_balances_four_levels(self):
        players = [
            ("Player A", "A"),
            ("Player B", "B"),
            ("Player C", "C"),
            ("Player D", "D"),
        ]

        pairs = MatchSchedulerService._smart_pair(players)

        self.assertEqual(len(pairs), 2)
        self.assertIn("Player A + Player D", pairs)
        self.assertIn("Player B + Player C", pairs)


if __name__ == "__main__":
    unittest.main()
