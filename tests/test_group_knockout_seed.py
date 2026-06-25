import unittest

from app import _seed_knockout_from_group_rankings


def done_match(doi_a, doi_b, diem_a, diem_b, bang):
    return (
        1,
        doi_a,
        doi_b,
        diem_a,
        diem_b,
        "Đã xong",
        1,
        1,
        2,
        "A",
        "bang",
        bang,
    )


class GroupKnockoutSeedTest(unittest.TestCase):
    def test_seeds_semifinal_cross_group_winners_and_runners_up(self):
        grouped = {
            "A": [
                done_match("Nhat A", "Nhi A", 11, 5, "A"),
                done_match("Nhat A", "Ba A", 11, 4, "A"),
                done_match("Nhi A", "Ba A", 11, 9, "A"),
            ],
            "B": [
                done_match("Nhat B", "Nhi B", 11, 6, "B"),
                done_match("Nhat B", "Ba B", 11, 3, "B"),
                done_match("Nhi B", "Ba B", 11, 8, "B"),
            ],
        }

        self.assertEqual(
            _seed_knockout_from_group_rankings(grouped, 4),
            ["Nhat A", "Nhi B", "Nhat B", "Nhi A"],
        )

    def test_seeds_quarterfinals_cross_adjacent_groups(self):
        grouped = {
            "A": [done_match("Nhat A", "Nhi A", 11, 5, "A")],
            "B": [done_match("Nhat B", "Nhi B", 11, 5, "B")],
            "C": [done_match("Nhat C", "Nhi C", 11, 5, "C")],
            "D": [done_match("Nhat D", "Nhi D", 11, 5, "D")],
        }

        self.assertEqual(
            _seed_knockout_from_group_rankings(grouped, 8),
            [
                "Nhat A", "Nhi B",
                "Nhat B", "Nhi A",
                "Nhat C", "Nhi D",
                "Nhat D", "Nhi C",
            ],
        )

    def test_seeds_quarterfinals_from_two_groups_with_top_four_each(self):
        grouped = {
            "A": [
                done_match("Nhat A", "Nhi A", 11, 8, "A"),
                done_match("Nhat A", "Ba A", 11, 7, "A"),
                done_match("Nhat A", "Tu A", 11, 6, "A"),
                done_match("Nhi A", "Ba A", 11, 9, "A"),
                done_match("Nhi A", "Tu A", 11, 8, "A"),
                done_match("Ba A", "Tu A", 11, 9, "A"),
            ],
            "B": [
                done_match("Nhat B", "Nhi B", 11, 8, "B"),
                done_match("Nhat B", "Ba B", 11, 7, "B"),
                done_match("Nhat B", "Tu B", 11, 6, "B"),
                done_match("Nhi B", "Ba B", 11, 9, "B"),
                done_match("Nhi B", "Tu B", 11, 8, "B"),
                done_match("Ba B", "Tu B", 11, 9, "B"),
            ],
        }

        self.assertEqual(
            _seed_knockout_from_group_rankings(grouped, 8),
            [
                "Nhat A", "Nhi B",
                "Nhat B", "Nhi A",
                "Ba A", "Tu B",
                "Ba B", "Tu A",
            ],
        )


if __name__ == "__main__":
    unittest.main()
