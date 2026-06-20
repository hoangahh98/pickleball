import psycopg2
from config import DB_CONFIG

class TournamentModel:
    @staticmethod
    def get_details(giai_id):
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, ten_giai_dau, so_luong_san, dia_diem, 
                   chi_phi_san_bai, chi_phi_nuoc_noi, chi_phi_giai_thuong, chi_phi_khac, 
                   ty_le_giai_1, ty_le_giai_2, ty_le_giai_3, so_nguoi_du_kien,
                   thoi_gian_bat_dau, banner_image, qr_image
            FROM giai_dau WHERE id = %s;
        """, (giai_id,))
        giai_raw = cursor.fetchone()
        cursor.close()
        conn.close()
        return giai_raw

class PlayerModel:
    @staticmethod
    def get_all_by_tournament(giai_id):
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, giai_dau_id, ten_nguoi_choi, trinh_do, so_tien_da_dong, ghi_chu, email 
            FROM nguoi_choi WHERE giai_dau_id = %s ORDER BY id ASC;
        """, (giai_id,))
        players = cursor.fetchall()
        cursor.close()
        conn.close()
        return players

    @staticmethod
    def get_top_donators(giai_id, muc_co_ban):
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ten_nguoi_choi, so_tien_da_dong 
            FROM nguoi_choi 
            WHERE giai_dau_id = %s AND so_tien_da_dong > %s 
            ORDER BY so_tien_da_dong DESC LIMIT 3;
        """, (giai_id, muc_co_ban))
        top_3 = cursor.fetchall()
        cursor.close()
        conn.close()
        return top_3

class MatchModel:
    @staticmethod
    def delete_by_tournament(giai_id):
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tran_dau WHERE giai_dau_id = %s;", (giai_id,))
        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def save_matches(giai_id, matches):
        """matches: list dict {vong, san, doi_a, doi_b}"""
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        for m in matches:
            cursor.execute("""
                INSERT INTO tran_dau (giai_dau_id, doi_a, doi_b, trang_thai, san_so_may, vong_dau)
                VALUES (%s, %s, %s, %s, %s, %s);
            """, (giai_id, m['doi_a'], m['doi_b'], 'Chưa diễn ra',
                  m.get('san', 1), m.get('vong', 1)))
        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def get_all_by_tournament(giai_id):
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, doi_a, doi_b, diem_doi_a, diem_doi_b, trang_thai, san_so_may, vong_dau
            FROM tran_dau WHERE giai_dau_id = %s ORDER BY vong_dau ASC, san_so_may ASC, id ASC;
        """, (giai_id,))
        matches = cursor.fetchall()
        cursor.close()
        conn.close()
        return matches

    @staticmethod
    def update_score(tran_id, diem_a, diem_b):
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        trang_thai = 'Đã xong' if (diem_a is not None and diem_b is not None) else 'Chưa diễn ra'
        cursor.execute("""
            UPDATE tran_dau SET diem_doi_a=%s, diem_doi_b=%s, trang_thai=%s WHERE id=%s;
        """, (diem_a, diem_b, trang_thai, tran_id))
        conn.commit()
        cursor.close()
        conn.close()

    @staticmethod
    def get_bang_xep_hang(giai_id):
        """Tính điểm, hiệu số cho từng đội trong giải"""
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT doi_a, doi_b, diem_doi_a, diem_doi_b
            FROM tran_dau
            WHERE giai_dau_id = %s AND trang_thai = 'Đã xong';
        """, (giai_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        bang = {}
        for doi_a, doi_b, d_a, d_b in rows:
            for doi in [doi_a, doi_b]:
                if doi not in bang:
                    bang[doi] = {"ten": doi, "thang": 0, "thua": 0, "hieu_so": 0, "diem": 0, "so_tran": 0}

            d_a = d_a or 0
            d_b = d_b or 0
            bang[doi_a]["so_tran"] += 1
            bang[doi_b]["so_tran"] += 1
            bang[doi_a]["hieu_so"] += d_a - d_b
            bang[doi_b]["hieu_so"] += d_b - d_a

            if d_a > d_b:
                bang[doi_a]["thang"] += 1
                bang[doi_a]["diem"] += 1
                bang[doi_b]["thua"] += 1
            elif d_b > d_a:
                bang[doi_b]["thang"] += 1
                bang[doi_b]["diem"] += 1
                bang[doi_a]["thua"] += 1

        xep_hang = sorted(bang.values(), key=lambda x: (-x["diem"], -x["hieu_so"]))
        return xep_hang

    @staticmethod
    def get_bang_xep_hang_by_matches(matches):
        """Tính xếp hạng từ danh sách trận (không query DB)"""
        bang = {}
        for m in matches:
            doi_a, doi_b, d_a, d_b = m[1], m[2], m[3], m[4]
            for doi in [doi_a, doi_b]:
                if doi not in bang:
                    bang[doi] = {"ten": doi, "thang": 0, "thua": 0, "hieu_so": 0, "diem": 0, "so_tran": 0}
            d_a = d_a or 0
            d_b = d_b or 0
            bang[doi_a]["so_tran"] += 1
            bang[doi_b]["so_tran"] += 1
            bang[doi_a]["hieu_so"] += d_a - d_b
            bang[doi_b]["hieu_so"] += d_b - d_a
            if d_a > d_b:
                bang[doi_a]["thang"] += 1
                bang[doi_a]["diem"] += 1
                bang[doi_b]["thua"] += 1
            elif d_b > d_a:
                bang[doi_b]["thang"] += 1
                bang[doi_b]["diem"] += 1
                bang[doi_a]["thua"] += 1
        return sorted(bang.values(), key=lambda x: (-x["diem"], -x["hieu_so"]))

    @staticmethod
    def save_knockout_config(giai_id, so_bang, so_doi_di_tiep):
        """Lưu cấu hình knockout"""
        pass

    @staticmethod
    def save_knockout_match(giai_id, doi_a, doi_b, vong, san):
        """Lưu trận knockout"""
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tran_dau (giai_dau_id, doi_a, doi_b, trang_thai, san_so_may, vong_dau)
            VALUES (%s, %s, %s, %s, %s, %s);
        """, (giai_id, doi_a, doi_b, 'Chưa diễn ra', san, f"{vong} - Knockout"))
        conn.commit()
        cursor.close()
        conn.close()
        
    @staticmethod
    def update_player_name_in_matches(giai_id, old_name, new_name):
        """FIX: Cập nhật tên VĐV ở lịch thi đấu khi sửa tên"""
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Update doi_a
        cursor.execute("""
            UPDATE tran_dau 
            SET doi_a = %s 
            WHERE giai_dau_id = %s AND doi_a = %s;
        """, (new_name, giai_id, old_name))
        
        # Update doi_b
        cursor.execute("""
            UPDATE tran_dau 
            SET doi_b = %s 
            WHERE giai_dau_id = %s AND doi_b = %s;
        """, (new_name, giai_id, old_name))
        
        conn.commit()
        cursor.close()
        conn.close()