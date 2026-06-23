import unittest

from validators import (
    normalize_team_form,
    normalize_team_member_form,
    normalize_team_month_form,
    normalize_tournament_form,
    normalize_vdv_form,
)


class NormalizeVdvFormTest(unittest.TestCase):
    def test_normalizes_valid_form(self):
        data, errors = normalize_vdv_form({
            "ten_vdv": "  Nguyen Van A  ",
            "email": "  VDV@Example.COM ",
            "trinh_do": "b",
            "ghi_chu": "  Ghi chu  ",
        })

        self.assertEqual(errors, [])
        self.assertEqual(data["ten_vdv"], "Nguyen Van A")
        self.assertEqual(data["email"], "vdv@example.com")
        self.assertEqual(data["trinh_do"], "B")
        self.assertEqual(data["ghi_chu"], "Ghi chu")

    def test_rejects_missing_name_bad_email_and_bad_level(self):
        data, errors = normalize_vdv_form({
            "ten_vdv": " ",
            "email": "not-an-email",
            "trinh_do": "X",
        })

        self.assertEqual(data["trinh_do"], "C")
        self.assertIn("Tên VĐV không được để trống.", errors)
        self.assertIn("Email không đúng định dạng.", errors)
        self.assertIn("Trình độ chỉ được chọn A, B, C hoặc D.", errors)


class NormalizeTournamentFormTest(unittest.TestCase):
    def test_allows_blank_optional_time_as_none(self):
        data, errors = normalize_tournament_form({
            "ten_giai_dau": "  Giai dau  ",
            "so_luong_san": "2",
            "so_nguoi_du_kien": "16",
            "thoi_gian_bat_dau": "",
            "diem_cham": "",
            "diem_toi_da": "",
        })

        self.assertEqual(errors, [])
        self.assertEqual(data["ten_giai_dau"], "Giai dau")
        self.assertIsNone(data["thoi_gian_bat_dau"])
        self.assertEqual(data["diem_cham"], 11)
        self.assertEqual(data["diem_toi_da"], 15)

    def test_rejects_missing_name_and_bad_number(self):
        data, errors = normalize_tournament_form({
            "ten_giai_dau": " ",
            "so_luong_san": "abc",
        })

        self.assertEqual(data["so_luong_san"], 1)
        self.assertIn("Tên giải không được để trống.", errors)
        self.assertIn("Các trường số chỉ được nhập số hợp lệ.", errors)

    def test_allows_zero_prize_ratio(self):
        data, errors = normalize_tournament_form({
            "ten_giai_dau": "Giai 1 va 2",
            "ty_le_giai_1": "7",
            "ty_le_giai_2": "3",
            "ty_le_giai_3": "0",
        })

        self.assertEqual(errors, [])
        self.assertEqual(data["ty_le_giai_1"], 7)
        self.assertEqual(data["ty_le_giai_2"], 3)
        self.assertEqual(data["ty_le_giai_3"], 0)

class NormalizeTeamFormTest(unittest.TestCase):
    def test_normalizes_team_and_member_forms(self):
        team, team_errors = normalize_team_form({"ten_doi": "  Team A  ", "mo_ta": "  Note  "})
        member, member_errors = normalize_team_member_form({
            "ten_thanh_vien": "  Player A ",
            "trinh_do": "b",
            "loai_thanh_vien": "vang_lai",
            "ghi_chu": "  ok ",
        })

        self.assertEqual(team_errors, [])
        self.assertEqual(team["ten_doi"], "Team A")
        self.assertEqual(member_errors, [])
        self.assertEqual(member["trinh_do"], "B")
        self.assertEqual(member["loai_thanh_vien"], "vang_lai")

    def test_normalizes_team_month_money_fields(self):
        data, errors = normalize_team_month_form({
            "muc_phi_thang": "100000",
            "chi_phi_san_bai": "50000",
            "chi_phi_nuoc_noi": "",
            "chi_phi_khac": "25000",
        })

        self.assertEqual(errors, [])
        self.assertEqual(data["muc_phi_thang"], 100000)
        self.assertEqual(data["chi_phi_nuoc_noi"], 0)


if __name__ == "__main__":
    unittest.main()
