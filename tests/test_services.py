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

    def test_tinh_toan_quy_doi_bong_includes_carryover_expenses_and_donate(self):
        month_config = (1, "2026-06-01", 100000, 150000, 200000, "")
        members = [
            (1, 10, "A", "B", "a@example.com", "co_dinh", "", 100000, "Đã đóng", "", 1),
            (2, 11, "B", "C", "b@example.com", "vang_lai", "", 150000, "Đã đóng", "", 2),
        ]
        expenses = [(1, "2026-06-23", "Uong nuoc", 100000, "")]

        result = FinanceService.tinh_toan_quy_doi_bong(month_config, members, expenses)

        self.assertEqual(result["tong_thu"], 250000)
        self.assertEqual(result["tong_donate"], 50000)
        self.assertEqual(result["tong_khoan_chi"], 100000)
        self.assertEqual(result["tong_chi"], 250000)
        self.assertEqual(result["quy_con_lai"], 200000)
        self.assertEqual(result["thanh_vien_list"][1]["loai_hien_thi"], "Vãng lai")

    def test_tinh_toan_dong_tien_allows_zero_prize_ratio(self):
        giai_raw = (
            1, "Giai test", 2, "San A",
            0, 0, 0, 0,
            7, 3, 0, 2,
            None, None, None,
        )
        players_raw = [
            (1, 1, "A", "A", 70000, "", "a@example.com", "Đã đóng"),
            (2, 1, "B", "B", 30000, "", "b@example.com", "Đã đóng"),
        ]

        result = FinanceService.tinh_toan_dong_tien(giai_raw, players_raw)

        self.assertEqual(result["giai_1"], 70000)
        self.assertEqual(result["giai_2"], 30000)
        self.assertEqual(result["giai_3"], 0)

    def test_tinh_toan_dong_tien_uses_manual_prizes_when_valid(self):
        giai_raw = (
            1, "Giai test", 2, "San A",
            0, 0, 0, 0,
            0, 0, 0, 2,
            None, None, None, "don", 11, 15,
            60000, 40000, 0,
        )
        players_raw = [
            (1, 1, "A", "A", 60000, "", "a@example.com", "Đã đóng"),
            (2, 1, "B", "B", 40000, "", "b@example.com", "Đã đóng"),
        ]

        result = FinanceService.tinh_toan_dong_tien(giai_raw, players_raw)

        self.assertEqual(result["giai_1"], 60000)
        self.assertEqual(result["giai_2"], 40000)
        self.assertEqual(result["giai_3"], 0)


if __name__ == "__main__":
    unittest.main()
