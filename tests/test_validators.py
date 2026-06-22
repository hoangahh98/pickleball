import unittest

from validators import normalize_vdv_form


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


if __name__ == "__main__":
    unittest.main()
