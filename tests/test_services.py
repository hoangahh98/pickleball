import unittest

from services import FinanceService


class FinanceServiceTest(unittest.TestCase):
    def test_tinh_toan_dong_tien_rounds_cost_and_prizes(self):
        giai_raw = (
            1, "Giai test", 2, "San A",
            120000, 30000, 50000, 0,
            5, 3, 2, 4,
            None, None, None,
        )
        players_raw = [
            (1, 1, "A", "A", 50000, "", "a@example.com", "Đã đóng"),
            (2, 1, "B", "B", 100000, "", "b@example.com", "Đã đóng"),
        ]

        result = FinanceService.tinh_toan_dong_tien(giai_raw, players_raw)

        self.assertEqual(result["chi_phi_moi_nguoi"], 50000)
        self.assertEqual(result["tong_tien_thuc_thu"], 150000)
        self.assertEqual(result["tong_tien_donate"], 50000)
        self.assertEqual(result["quy_giai_thuong_thuc_te"], 0)


if __name__ == "__main__":
    unittest.main()
