import math


class FinanceService:
    @staticmethod
    def tinh_toan_dong_tien(giai_raw, players_raw):
        if not giai_raw:
            return {}

        giai_base = tuple(giai_raw[:15]) if len(giai_raw) >= 15 else tuple(giai_raw) + (None,) * (15 - len(giai_raw))
        giai_id, ten, so_san, dia_diem, cp_san, cp_nuoc, cp_giai_goc, cp_khac, tl1, tl2, tl3, so_nguoi_du_kien, thoi_gian, banner, qr = giai_base
        
        cp_san, cp_nuoc, cp_giai_goc, cp_khac = cp_san or 0, cp_nuoc or 0, cp_giai_goc or 0, cp_khac or 0
        tl1 = 5 if tl1 is None else tl1
        tl2 = 3 if tl2 is None else tl2
        tl3 = 2 if tl3 is None else tl3
        so_nguoi_du_kien = so_nguoi_du_kien or 10
        tong_chi_phi_goc = cp_san + cp_nuoc + cp_giai_goc + cp_khac
        
        muc_chia_deu = tong_chi_phi_goc / so_nguoi_du_kien if so_nguoi_du_kien > 0 else 0
        chi_phi_moi_nguoi = math.ceil(muc_chia_deu / 50000) * 50000
        
        nguoi_choi_list = []
        tong_tien_thuc_thu = 0
        tong_tien_donate = 0
        
        # players_raw format: (id, giai_dau_id, ten, trinh_do, tien, ghi_chu, email, trang_thai_dong_tien)
        for p in players_raw:
            p_id, giai_id_check, ten_p, trinh, da_dong, ghi_chu, email, trang_thai = p if len(p) >= 8 else p + (None,)
            da_dong = da_dong or 0
            chenh_lech = da_dong - chi_phi_moi_nguoi
            
            if chenh_lech > 0:
                tong_tien_donate += chenh_lech
                
            tong_tien_thuc_thu += da_dong
            nguoi_choi_list.append({
                "id": p_id, "ten": ten_p, "trinh_do": trinh,
                "tien_dong": da_dong, "chenh_lech": chenh_lech,
                "ghi_chu": ghi_chu, "trang_thai_dong_tien": trang_thai or "Chưa đóng"
            })
            
        # Quỹ thưởng = tổng tiền thực thu - chi phí vận hành (sân + nước + khác)
        cp_van_hanh = cp_san + cp_nuoc + cp_khac
        quy_giai_thuong_thuc_te = max(0, tong_tien_thuc_thu - cp_van_hanh)
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
            "nguoi_choi_list": nguoi_choi_list,
            "thoi_gian_bat_dau": thoi_gian,
            "banner_image": banner,
            "qr_image": qr
        }

    @staticmethod
    def tinh_toan_quy_doi_bong(month_config, members, quy_du_thang_truoc=0):
        if not month_config:
            month_config = (None, None, 0, 0, 0, 0, "")

        _, thang, muc_phi_thang, cp_san, cp_nuoc, cp_khac, ghi_chu = month_config
        muc_phi_thang = float(muc_phi_thang or 0)
        cp_san = float(cp_san or 0)
        cp_nuoc = float(cp_nuoc or 0)
        cp_khac = float(cp_khac or 0)
        quy_du_thang_truoc = float(quy_du_thang_truoc or 0)

        member_rows = []
        tong_thu = 0
        tong_donate = 0
        for member in members:
            (
                member_id, ten, trinh_do, loai_thanh_vien, ghi_chu_tv,
                so_tien_da_dong, trang_thai_dong_tien, ghi_chu_phi, payment_id
            ) = member
            so_tien_da_dong = float(so_tien_da_dong or 0)
            donate = max(0, so_tien_da_dong - muc_phi_thang)
            tong_thu += so_tien_da_dong
            tong_donate += donate
            member_rows.append({
                "id": member_id,
                "payment_id": payment_id,
                "ten": ten,
                "trinh_do": trinh_do,
                "loai_thanh_vien": loai_thanh_vien,
                "loai_hien_thi": "Vãng lai" if loai_thanh_vien == "vang_lai" else "Cố định",
                "ghi_chu": ghi_chu_tv,
                "so_tien_da_dong": so_tien_da_dong,
                "trang_thai_dong_tien": trang_thai_dong_tien or "Chưa đóng",
                "ghi_chu_phi": ghi_chu_phi,
                "donate": donate,
                "chenh_lech": so_tien_da_dong - muc_phi_thang,
            })

        tong_chi = cp_san + cp_nuoc + cp_khac
        quy_con_lai = quy_du_thang_truoc + tong_thu - tong_chi

        return {
            "thang": thang,
            "muc_phi_thang": muc_phi_thang,
            "chi_phi_san_bai": cp_san,
            "chi_phi_nuoc_noi": cp_nuoc,
            "chi_phi_khac": cp_khac,
            "ghi_chu": ghi_chu,
            "quy_du_thang_truoc": quy_du_thang_truoc,
            "tong_thu": tong_thu,
            "tong_donate": tong_donate,
            "tong_chi": tong_chi,
            "quy_con_lai": quy_con_lai,
            "thanh_vien_list": member_rows,
        }
