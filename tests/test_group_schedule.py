import unittest

from app import _build_group_stage_matches


def teams_in_group(matches, group_name):
    teams = []
    for match in matches:
        if match.get("bang") != group_name:
            continue
        for team_name in (match["doi_a"], match["doi_b"]):
            if team_name not in teams:
                teams.append(team_name)
    return teams


class GroupScheduleTest(unittest.TestCase):
    def test_splits_six_teams_evenly_into_two_groups(self):
        matches = _build_group_stage_matches(
            ["A1", "A2", "A3", "B1", "B2", "B3"],
            num_courts=2,
            qualifier_count=2,
            teams_per_group=4,
            group_count=2,
        )

        self.assertEqual(len(teams_in_group(matches, "A")), 3)
        self.assertEqual(len(teams_in_group(matches, "B")), 3)

    def test_splits_odd_teams_as_evenly_as_possible(self):
        matches = _build_group_stage_matches(
            ["A1", "A2", "A3", "A4", "B1", "B2", "B3"],
            num_courts=2,
            qualifier_count=2,
            teams_per_group=4,
            group_count=2,
        )

        self.assertEqual(len(teams_in_group(matches, "A")), 4)
        self.assertEqual(len(teams_in_group(matches, "B")), 3)


if __name__ == "__main__":
    unittest.main()
