import unittest

from validators import normalize_tournament_form, normalize_vdv_form


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


if __name__ == "__main__":
    unittest.main()
