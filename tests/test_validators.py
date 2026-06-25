import unittest

from validators import (
    normalize_team_expense_form,
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

    def test_rejects_missing_name_and_bad_number_without_resetting_field(self):
        data, errors = normalize_tournament_form({
            "ten_giai_dau": " ",
            "so_luong_san": "abc",
        })

        self.assertEqual(data["so_luong_san"], "abc")
        self.assertIn("Tên giải không được để trống.", errors)
        self.assertIn("Các trường số chỉ được nhập số hợp lệ.", errors)

    def test_accepts_decimal_integer_prize_ratios_from_db_form(self):
        data, errors = normalize_tournament_form({
            "ten_giai_dau": "Giai decimal",
            "so_luong_san": "2.0",
            "so_nguoi_du_kien": "16.0",
            "diem_cham": "11.0",
            "diem_toi_da": "15.0",
            "chi_phi_san_bai": "100000.0",
            "ty_le_giai_1": "7.0",
            "ty_le_giai_2": "3.0",
            "ty_le_giai_3": "0.0",
        })

        self.assertEqual(errors, [])
        self.assertEqual(data["so_luong_san"], 2)
        self.assertEqual(data["chi_phi_san_bai"], 100000)
        self.assertEqual(data["ty_le_giai_1"], 7)
        self.assertEqual(data["ty_le_giai_2"], 3)
        self.assertEqual(data["ty_le_giai_3"], 0)

    def test_keeps_tournament_format_config(self):
        data, errors = normalize_tournament_form({
            "ten_giai_dau": "Giai bang",
            "loai_dau": "doi",
            "the_thuc": "bang",
            "so_nguoi_du_kien": "32",
            "so_doi_moi_bang": "4",
            "so_bang": "2",
            "so_doi_vao_vong_trong": "8",
        })

        self.assertEqual(errors, [])
        self.assertEqual(data["the_thuc"], "bang")
        self.assertEqual(data["so_doi_moi_bang"], 4)
        self.assertEqual(data["so_bang"], 2)
        self.assertEqual(data["so_doi_vao_vong_trong"], 8)

    def test_knockout_stage_checkboxes_set_qualifier_count(self):
        base_form = {
            "ten_giai_dau": "Giai bang",
            "loai_dau": "don",
            "the_thuc": "bang",
            "so_nguoi_du_kien": "16",
        }

        data, errors = normalize_tournament_form({**base_form, "knockout_chung_ket": "1"})
        self.assertEqual(errors, [])
        self.assertEqual(data["so_doi_vao_vong_trong"], 2)

        data, errors = normalize_tournament_form({
            **base_form,
            "knockout_chung_ket": "1",
            "knockout_ban_ket": "1",
        })
        self.assertEqual(errors, [])
        self.assertEqual(data["so_doi_vao_vong_trong"], 4)

        data, errors = normalize_tournament_form({
            **base_form,
            "knockout_chung_ket": "1",
            "knockout_ban_ket": "1",
            "knockout_tu_ket": "1",
        })
        self.assertEqual(errors, [])
        self.assertEqual(data["so_doi_vao_vong_trong"], 8)

    def test_knockout_stage_requires_enough_estimated_teams(self):
        data, errors = normalize_tournament_form({
            "ten_giai_dau": "Giai it doi",
            "loai_dau": "doi",
            "the_thuc": "bang",
            "so_nguoi_du_kien": "20",
            "knockout_tu_ket": "1",
        })

        self.assertEqual(data["so_doi_vao_vong_trong"], 8)
        self.assertTrue(any("ít nhất 16 đội" in error for error in errors))

    def test_blank_prize_ratio_defaults_to_zero(self):
        data, errors = normalize_tournament_form({
            "ten_giai_dau": "Giai 1 va 2",
            "ty_le_giai_1": "7",
            "ty_le_giai_2": "",
            "ty_le_giai_3": "0",
        })

        self.assertEqual(errors, [])
        self.assertEqual(data["ty_le_giai_1"], 7)
        self.assertEqual(data["ty_le_giai_2"], 0)
        self.assertEqual(data["ty_le_giai_3"], 0)


class NormalizeTeamFormTest(unittest.TestCase):
    def test_normalizes_team_and_member_forms(self):
        team, team_errors = normalize_team_form({"ten_doi": "  Team A  ", "mo_ta": "  Note  "})
        member, member_errors = normalize_team_member_form({
            "van_dong_vien_id": "12",
            "loai_thanh_vien": "vang_lai",
            "ghi_chu": "  ok ",
        })

        self.assertEqual(team_errors, [])
        self.assertEqual(team["ten_doi"], "Team A")
        self.assertEqual(member_errors, [])
        self.assertEqual(member["van_dong_vien_id"], 12)
        self.assertEqual(member["loai_thanh_vien"], "vang_lai")

    def test_normalizes_team_month_money_fields(self):
        data, errors = normalize_team_month_form({
            "muc_phi_thang": "100000",
            "chi_phi_san_bai": "50000",
            "tien_san_con_lai_thang_truoc": "25000",
        })

        self.assertEqual(errors, [])
        self.assertEqual(data["muc_phi_thang"], 100000)
        self.assertEqual(data["tien_san_con_lai_thang_truoc"], 25000)

    def test_normalizes_team_expense(self):
        data, errors = normalize_team_expense_form({
            "ngay_chi": "2026-06-23",
            "noi_dung": "Uong nuoc",
            "so_tien": "100000",
        })

        self.assertEqual(errors, [])
        self.assertEqual(data["so_tien"], 100000)


if __name__ == "__main__":
    unittest.main()
