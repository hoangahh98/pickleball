import psycopg2
from config import DB_CONFIG

class VanDongVienModel:
    """Vận động viên (Players)"""
    
    @staticmethod
    def get_all():
        """Get all VĐV"""
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT id, ten_vdv, trinh_do, email, ghi_chu FROM van_dong_vien ORDER BY ten_vdv ASC;")
        vdv_list = cursor.fetchall()
        cursor.close()
        conn.close()
        return vdv_list
    
    @staticmethod
    def get_by_id(vdv_id):
        """Get VĐV by ID"""
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM van_dong_vien WHERE id = %s;", (vdv_id,))
        vdv = cursor.fetchone()
        cursor.close()
        conn.close()
        return vdv
    
    @staticmethod
    def get_by_email(email):
        """Get VĐV by email"""
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT id, ten_vdv, email, trinh_do FROM van_dong_vien WHERE email = %s;", (email,))
        vdv = cursor.fetchone()
        cursor.close()
        conn.close()
        return vdv
    
    @staticmethod
    def create(ten_vdv, trinh_do, email, ghi_chu=''):
        """Create new VĐV"""
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO van_dong_vien (ten_vdv, trinh_do, email, ghi_chu)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
            """, (ten_vdv, trinh_do, email, ghi_chu))
            vdv_id = cursor.fetchone()[0]
            conn.commit()
            return vdv_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def update(vdv_id, ten_vdv, trinh_do, email, ghi_chu=''):
        """Update VĐV"""
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE van_dong_vien 
                SET ten_vdv=%s, trinh_do=%s, email=%s, ghi_chu=%s
                WHERE id=%s;
            """, (ten_vdv, trinh_do, email, ghi_chu, vdv_id))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def delete(vdv_id):
        """Delete VĐV"""
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM van_dong_vien WHERE id = %s;", (vdv_id,))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

class TournamentModel:
    """Giải đấu"""
    
    @staticmethod
    def ensure_score_rule_columns():
        """Ensure tournament scoring rule columns exist."""
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                ALTER TABLE giai_dau
                ADD COLUMN IF NOT EXISTS diem_cham INTEGER DEFAULT 11,
                ADD COLUMN IF NOT EXISTS diem_toi_da INTEGER DEFAULT 15;
            """)
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_details(giai_id):
        """Get tournament details"""
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, ten_giai_dau, so_luong_san, dia_diem,
                   chi_phi_san_bai, chi_phi_nuoc_noi, chi_phi_giai_thuong, chi_phi_khac,
                   ty_le_giai_1, ty_le_giai_2, ty_le_giai_3, so_nguoi_du_kien,
                   thoi_gian_bat_dau, banner_image, qr_image
            FROM giai_dau WHERE id = %s;
        """, (giai_id,))
        giai = cursor.fetchone()
        cursor.close()
        conn.close()
        return giai
    
    @staticmethod
    def get_all():
        """Get all tournaments"""
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT id, ten_giai_dau, so_luong_san, dia_diem, thoi_gian_bat_dau, ngay_tao FROM giai_dau ORDER BY id DESC;")
        giải_list = cursor.fetchall()
        cursor.close()
        conn.close()
        return giải_list

    @staticmethod
    def get_score_rules(giai_id):
        """Get scoring rules for tournament."""
        TournamentModel.ensure_score_rule_columns()
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COALESCE(diem_cham, 11), COALESCE(diem_toi_da, 15)
            FROM giai_dau
            WHERE id = %s;
        """, (giai_id,))
        rules = cursor.fetchone()
        cursor.close()
        conn.close()
        return rules or (11, 15)

class DangKyGiaiModel:
    """Đăng ký giải (Registration)"""
    
    @staticmethod
    def get_by_tournament(giai_id):
        """Get all registrations for tournament"""
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT dkg.id, dkg.van_dong_vien_id, vdv.ten_vdv, vdv.trinh_do, vdv.email,
                   dkg.so_tien_da_dong, dkg.trang_thai_dong_tien, dkg.ghi_chu
            FROM dang_ky_giai dkg
            INNER JOIN van_dong_vien vdv ON dkg.van_dong_vien_id = vdv.id
            WHERE dkg.giai_dau_id = %s
            ORDER BY vdv.ten_vdv ASC;
        """, (giai_id,))
        registrations = cursor.fetchall()
        cursor.close()
        conn.close()
        return registrations
    
    @staticmethod
    def get_by_vdv(vdv_id):
        """Get all tournaments VĐV registered in"""
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT dkg.id, dkg.giai_dau_id, g.ten_giai_dau, g.so_luong_san, g.dia_diem,
                   g.chi_phi_san_bai, g.chi_phi_nuoc_noi, g.chi_phi_giai_thuong, g.chi_phi_khac,
                   g.ty_le_giai_1, g.ty_le_giai_2, g.ty_le_giai_3, g.so_nguoi_du_kien,
                   g.thoi_gian_bat_dau, g.banner_image, g.qr_image,
                   dkg.so_tien_da_dong, dkg.trang_thai_dong_tien
            FROM dang_ky_giai dkg
            INNER JOIN giai_dau g ON dkg.giai_dau_id = g.id
            WHERE dkg.van_dong_vien_id = %s
            ORDER BY g.id DESC;
        """, (vdv_id,))
        tournaments = cursor.fetchall()
        cursor.close()
        conn.close()
        return tournaments
    
    @staticmethod
    def register(van_dong_vien_id, giai_dau_id):
        """Register VĐV for tournament"""
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO dang_ky_giai (van_dong_vien_id, giai_dau_id)
                VALUES (%s, %s);
            """, (van_dong_vien_id, giai_dau_id))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def update_payment(dang_ky_id, so_tien, trang_thai):
        """Update payment info"""
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE dang_ky_giai
                SET so_tien_da_dong=%s, trang_thai_dong_tien=%s
                WHERE id=%s;
            """, (so_tien, trang_thai, dang_ky_id))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def remove(dang_ky_id):
        """Remove VĐV from tournament"""
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM dang_ky_giai WHERE id = %s;", (dang_ky_id,))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()

class MatchModel:
    """Trận đấu"""

    @staticmethod
    def ensure_score_order_column():
        """Ensure pickleball server/order score column exists."""
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                ALTER TABLE tran_dau
                ADD COLUMN IF NOT EXISTS thu_tu_danh INTEGER DEFAULT 2;
            """)
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_all_by_tournament(giai_id):
        """Get all matches for tournament"""
        MatchModel.ensure_score_order_column()
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, doi_a, doi_b, diem_doi_a, diem_doi_b, trang_thai, san_so_may, vong_dau,
                   COALESCE(thu_tu_danh, 2)
            FROM tran_dau WHERE giai_dau_id = %s
            ORDER BY vong_dau ASC, san_so_may ASC, id ASC;
        """, (giai_id,))
        matches = cursor.fetchall()
        cursor.close()
        conn.close()
        return matches
    
    @staticmethod
    def delete_by_tournament(giai_id):
        """Delete all matches for tournament"""
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM tran_dau WHERE giai_dau_id = %s;", (giai_id,))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def save_matches(giai_id, matches):
        """Save matches"""
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        try:
            for m in matches:
                cursor.execute("""
                    INSERT INTO tran_dau (giai_dau_id, doi_a, doi_b, trang_thai, san_so_may, vong_dau)
                    VALUES (%s, %s, %s, %s, %s, %s);
                """, (giai_id, m['doi_a'], m['doi_b'], 'Chưa diễn ra',
                      m.get('san', 1), m.get('vong', 1)))
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def update_score(tran_id, diem_a, diem_b, thu_tu_danh=2):
        """Update match score"""
        MatchModel.ensure_score_order_column()
        TournamentModel.ensure_score_rule_columns()
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT COALESCE(g.diem_cham, 11), COALESCE(g.diem_toi_da, 15)
                FROM tran_dau td
                INNER JOIN giai_dau g ON td.giai_dau_id = g.id
                WHERE td.id = %s;
            """, (tran_id,))
            rules = cursor.fetchone() or (11, 15)
            diem_cham, diem_toi_da = int(rules[0]), int(rules[1])

            def max_allowed(opponent_score):
                opponent_score = opponent_score or 0
                if opponent_score >= diem_cham - 1:
                    return min(opponent_score + 2, diem_toi_da)
                return min(diem_cham, diem_toi_da)

            if diem_a is not None and diem_b is not None:
                diem_a = min(diem_a, max_allowed(diem_b))
                diem_b = min(diem_b, max_allowed(diem_a))

            trang_thai = 'Chưa diễn ra'
            if diem_a is not None and diem_b is not None:
                diem_cao = max(diem_a, diem_b)
                chen_lech = abs(diem_a - diem_b)
                if diem_cao >= diem_toi_da or (diem_cao >= diem_cham and chen_lech >= 2):
                    trang_thai = 'Đã xong'

            thu_tu_danh = int(thu_tu_danh) if thu_tu_danh in (1, 2, '1', '2') else 2
            cursor.execute("""
                UPDATE tran_dau
                SET diem_doi_a=%s, diem_doi_b=%s, thu_tu_danh=%s, trang_thai=%s
                WHERE id=%s;
            """, (diem_a, diem_b, thu_tu_danh, trang_thai, tran_id))
            conn.commit()
            return trang_thai, diem_a, diem_b
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
    
    @staticmethod
    def get_bang_xep_hang_by_matches(matches):
        """Calculate ranking from matches"""
        bang = {}
        for m in matches:
            if len(m) > 5 and m[5] != 'Đã xong':
                continue
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
