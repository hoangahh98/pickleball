import math
import random

class FinanceService:
    @staticmethod
    def tinh_toan_dong_tien(giai_raw, players_raw):
        if not giai_raw:
            return {}
            
        giai_id, ten, so_san, dia_diem, cp_san, cp_nuoc, cp_giai_goc, cp_khac, tl1, tl2, tl3, so_nguoi_du_kien = giai_raw
        
        cp_san, cp_nuoc, cp_giai_goc, cp_khac = cp_san or 0, cp_nuoc or 0, cp_giai_goc or 0, cp_khac or 0
        tl1, tl2, tl3, so_nguoi_du_kien = tl1 or 5, tl2 or 3, tl3 or 2, so_nguoi_du_kien or 10
        tong_chi_phi_goc = cp_san + cp_nuoc + cp_giai_goc + cp_khac
        
        muc_chia_deu = tong_chi_phi_goc / so_nguoi_du_kien if so_nguoi_du_kien > 0 else 0
        chi_phi_moi_nguoi = math.ceil(muc_chia_deu / 50000) * 50000
        
        nguoi_choi_list = []
        tong_tien_thuc_thu = 0
        tong_tien_donate = 0
        
        for p in players_raw:
            p_id, _, ten_p, trinh, da_dong, ghi_chu = p
            da_dong = da_dong or 0
            chenh_lech = da_dong - chi_phi_moi_nguoi
            
            if chenh_lech > 0:
                tong_tien_donate += chenh_lech
                
            tong_tien_thuc_thu += da_dong
            nguoi_choi_list.append({
                "id": p_id, "ten": ten_p, "trinh_do": trinh,
                "tien_dong": da_dong, "chenh_lech": chenh_lech, "ghi_chu": ghi_chu
            })
            
        # Quỹ thưởng = tổng tiền thực thu - chi phí vận hành (sân + nước + khác)
        # Tiền thưởng gốc (cp_giai_goc) đã nằm trong chi_phi_moi_nguoi nên không trừ lại
        cp_van_hanh = cp_san + cp_nuoc + cp_khac
        quy_giai_thuong_thuc_te = max(0, tong_tien_thuc_thu - cp_van_hanh)
        # Giữ lại quy_giai_thuong_moi để tương thích với chi_tiet.html
        quy_giai_thuong_moi = quy_giai_thuong_thuc_te
        tong_ty_le = tl1 + tl2 + tl3

        return {
            "id": giai_id, "ten_giai_dau": ten, "so_luong_san": so_san, "dia_diem": dia_diem,
            "so_nguoi_du_kien": so_nguoi_du_kien, "so_luong_nguoi": len(players_raw),
            "chi_phi_moi_nguoi": chi_phi_moi_nguoi,
            "tong_tien_thuc_thu": tong_tien_thuc_thu,
            "tong_tien_donate": tong_tien_donate,
            "cp_san_bai": cp_san, "cp_nuoc_noi": cp_nuoc,
            "cp_giai_thuong_goc": cp_giai_goc, "cp_khac": cp_khac,
            "quy_giai_thuong_moi": quy_giai_thuong_moi,
            "quy_giai_thuong_thuc_te": quy_giai_thuong_thuc_te,
            "giai_1": (quy_giai_thuong_moi * tl1 / tong_ty_le) if tong_ty_le > 0 else 0,
            "giai_2": (quy_giai_thuong_moi * tl2 / tong_ty_le) if tong_ty_le > 0 else 0,
            "giai_3": (quy_giai_thuong_moi * tl3 / tong_ty_le) if tong_ty_le > 0 else 0,
            "ty_le_1": tl1, "ty_le_2": tl2, "ty_le_3": tl3,
            "nguoi_choi_list": nguoi_choi_list
        }


class MatchSchedulerService:
    @staticmethod
    def auto_pairing_teams(players_raw):
        """Ghép đôi partner ngẫu nhiên theo luật trình độ"""
        list_A = [p for p in players_raw if p[3] == 'A']
        list_B = [p for p in players_raw if p[3] == 'B']
        list_C = [p for p in players_raw if p[3] == 'C']
        list_D = [p for p in players_raw if p[3] == 'D']

        # Shuffle ngẫu nhiên từng nhóm
        random.shuffle(list_A)
        random.shuffle(list_B)
        random.shuffle(list_C)
        random.shuffle(list_D)

        trinh_do_hien_co = set(p[3] for p in players_raw)
        teams = []

        if 'A' in trinh_do_hien_co and 'D' in trinh_do_hien_co:
            # 4 trình độ: A+D, B+C
            while list_A and list_D:
                teams.append(f"{list_A.pop()[2]} + {list_D.pop()[2]}")
            while list_B and list_C:
                teams.append(f"{list_B.pop()[2]} + {list_C.pop()[2]}")
            # Dư: ghép theo cặp còn lại
            con_lai = list_A + list_B + list_C + list_D

        elif 'A' in trinh_do_hien_co and 'C' in trinh_do_hien_co and 'D' not in trinh_do_hien_co:
            # 3 trình độ A+B+C: A+C, B+B
            while list_A and list_C:
                teams.append(f"{list_A.pop()[2]} + {list_C.pop()[2]}")
            while len(list_B) >= 2:
                teams.append(f"{list_B.pop()[2]} + {list_B.pop()[2]}")
            con_lai = list_A + list_B + list_C

        elif len(trinh_do_hien_co) == 2:
            # 2 trình độ: ghép chéo
            sorted_keys = sorted(trinh_do_hien_co)
            g1 = [p for p in players_raw if p[3] == sorted_keys[0]]
            g2 = [p for p in players_raw if p[3] == sorted_keys[1]]
            random.shuffle(g1)
            random.shuffle(g2)
            while g1 and g2:
                teams.append(f"{g1.pop()[2]} + {g2.pop()[2]}")
            con_lai = g1 + g2

        else:
            con_lai = list_A + list_B + list_C + list_D

        # Xử lý người dư
        while len(con_lai) >= 2:
            teams.append(f"{con_lai.pop()[2]} + {con_lai.pop()[2]}")
        if con_lai:
            teams.append(f"{con_lai.pop()[2]} + Lẻ (Chờ ghép)")

        return teams

    @staticmethod
    def generate_round_robin(teams, so_san=1):
        """
        Tạo lịch vòng tròn phân sân.
        - Mỗi vòng: các trận thi đấu song song trên các sân
        - Xoay vòng để tránh đánh liên tục (ai vừa đánh vòng này thì vòng sau nghỉ)
        Trả về list dict: {vong, san, doi_a, doi_b}
        """
        teams = list(teams)
        if len(teams) % 2 == 1:
            teams.append("BYE")
        n = len(teams)
        all_matches = []

        for vong in range(n - 1):
            vong_matches = []
            for i in range(n // 2):
                home = teams[i]
                away = teams[n - 1 - i]
                if home != "BYE" and away != "BYE":
                    vong_matches.append({
                        "vong": vong + 1,
                        "doi_a": home,
                        "doi_b": away,
                        "san": (len(vong_matches) % so_san) + 1  # phân sân tuần tự
                    })
            all_matches.extend(vong_matches)
            # Xoay vòng: giữ nguyên phần tử 0, xoay phần còn lại
            teams = [teams[0]] + [teams[-1]] + teams[1:-1]

        return all_matches