from db import db_cursor

class VanDongVienModel:
    """Vận động viên (Players)"""
    
    @staticmethod
    def get_all():
        """Get all VĐV"""
        with db_cursor() as cursor:
            cursor.execute("SELECT id, ten_vdv, trinh_do, email, ghi_chu FROM van_dong_vien ORDER BY ten_vdv ASC;")
            return cursor.fetchall()
    
    @staticmethod
    def get_by_id(vdv_id):
        """Get VĐV by ID"""
        with db_cursor() as cursor:
            cursor.execute("SELECT * FROM van_dong_vien WHERE id = %s;", (vdv_id,))
            return cursor.fetchone()
    
    @staticmethod
    def get_by_email(email):
        """Get VĐV by email"""
        with db_cursor() as cursor:
            cursor.execute("SELECT id, ten_vdv, email, trinh_do FROM van_dong_vien WHERE lower(email) = lower(%s);", (email,))
            return cursor.fetchone()

    @staticmethod
    def email_exists(email, exclude_id=None):
        """Check whether an email is already used by another VĐV."""
        with db_cursor() as cursor:
            if exclude_id:
                cursor.execute(
                    "SELECT 1 FROM van_dong_vien WHERE lower(email) = lower(%s) AND id <> %s LIMIT 1;",
                    (email, exclude_id),
                )
            else:
                cursor.execute("SELECT 1 FROM van_dong_vien WHERE lower(email) = lower(%s) LIMIT 1;", (email,))
            return cursor.fetchone() is not None
    
    @staticmethod
    def create(ten_vdv, trinh_do, email, ghi_chu=''):
        """Create new VĐV"""
        with db_cursor(commit=True) as cursor:
            cursor.execute("""
                INSERT INTO van_dong_vien (ten_vdv, trinh_do, email, ghi_chu)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
            """, (ten_vdv, trinh_do, email, ghi_chu))
            return cursor.fetchone()[0]
    
    @staticmethod
    def update(vdv_id, ten_vdv, trinh_do, email, ghi_chu=''):
        """Update VĐV"""
        with db_cursor(commit=True) as cursor:
            cursor.execute("""
                UPDATE van_dong_vien 
                SET ten_vdv=%s, trinh_do=%s, email=%s, ghi_chu=%s
                WHERE id=%s;
            """, (ten_vdv, trinh_do, email, ghi_chu, vdv_id))
    
    @staticmethod
    def delete(vdv_id):
        """Delete VĐV"""
        with db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM van_dong_vien WHERE id = %s;", (vdv_id,))

class TournamentModel:
    """Giải đấu"""
    
    @staticmethod
    def ensure_score_rule_columns():
        """Schema is maintained by init_db.py; kept for backward-compatible callers."""
        return None

    @staticmethod
    def get_details(giai_id):
        """Get tournament details"""
        with db_cursor() as cursor:
            cursor.execute("""
                SELECT id, ten_giai_dau, so_luong_san, dia_diem,
                       chi_phi_san_bai, chi_phi_nuoc_noi, chi_phi_giai_thuong, chi_phi_khac,
                       ty_le_giai_1, ty_le_giai_2, ty_le_giai_3, so_nguoi_du_kien,
                       thoi_gian_bat_dau, banner_image, qr_image,
                       COALESCE(loai_dau, 'don'), COALESCE(diem_cham, 11), COALESCE(diem_toi_da, 15)
                FROM giai_dau WHERE id = %s;
            """, (giai_id,))
            return cursor.fetchone()
    
    @staticmethod
    def get_all():
        """Get all tournaments"""
        with db_cursor() as cursor:
            cursor.execute("SELECT id, ten_giai_dau, so_luong_san, dia_diem, thoi_gian_bat_dau, ngay_tao FROM giai_dau ORDER BY id DESC;")
            return cursor.fetchall()

    @staticmethod
    def get_score_rules(giai_id):
        """Get scoring rules for tournament."""
        with db_cursor() as cursor:
            cursor.execute("""
                SELECT COALESCE(diem_cham, 11), COALESCE(diem_toi_da, 15)
                FROM giai_dau
                WHERE id = %s;
            """, (giai_id,))
            return cursor.fetchone() or (11, 15)

class DangKyGiaiModel:
    """Đăng ký giải (Registration)"""
    
    @staticmethod
    def get_by_tournament(giai_id):
        """Get all registrations for tournament"""
        with db_cursor() as cursor:
            cursor.execute("""
                SELECT dkg.id, dkg.van_dong_vien_id, vdv.ten_vdv, vdv.trinh_do, vdv.email,
                       dkg.so_tien_da_dong, dkg.trang_thai_dong_tien, dkg.ghi_chu
                FROM dang_ky_giai dkg
                INNER JOIN van_dong_vien vdv ON dkg.van_dong_vien_id = vdv.id
                WHERE dkg.giai_dau_id = %s
                ORDER BY vdv.ten_vdv ASC;
            """, (giai_id,))
            return cursor.fetchall()
    
    @staticmethod
    def get_by_vdv(vdv_id):
        """Get all tournaments VĐV registered in"""
        with db_cursor() as cursor:
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
            return cursor.fetchall()

    @staticmethod
    def get_by_tournaments(giai_ids):
        """Get registrations for many tournaments in one query, grouped by tournament ID."""
        ids = [int(giai_id) for giai_id in giai_ids if giai_id]
        if not ids:
            return {}

        with db_cursor() as cursor:
            cursor.execute("""
                SELECT dkg.giai_dau_id, dkg.id, dkg.van_dong_vien_id, vdv.ten_vdv, vdv.trinh_do, vdv.email,
                       dkg.so_tien_da_dong, dkg.trang_thai_dong_tien, dkg.ghi_chu
                FROM dang_ky_giai dkg
                INNER JOIN van_dong_vien vdv ON dkg.van_dong_vien_id = vdv.id
                WHERE dkg.giai_dau_id = ANY(%s)
                ORDER BY dkg.giai_dau_id DESC, vdv.ten_vdv ASC;
            """, (ids,))
            grouped = {giai_id: [] for giai_id in ids}
            for row in cursor.fetchall():
                grouped.setdefault(row[0], []).append(row[1:])
            return grouped
    
    @staticmethod
    def register(van_dong_vien_id, giai_dau_id):
        """Register VĐV for tournament"""
        with db_cursor(commit=True) as cursor:
            cursor.execute("""
                INSERT INTO dang_ky_giai (van_dong_vien_id, giai_dau_id)
                VALUES (%s, %s);
            """, (van_dong_vien_id, giai_dau_id))

    @staticmethod
    def register_many(van_dong_vien_ids, giai_dau_id):
        """Register many players for one tournament using one transaction."""
        rows = [(vdv_id, giai_dau_id) for vdv_id in van_dong_vien_ids]
        if not rows:
            return 0
        with db_cursor(commit=True) as cursor:
            cursor.executemany("""
                INSERT INTO dang_ky_giai (van_dong_vien_id, giai_dau_id)
                VALUES (%s, %s);
            """, rows)
        return len(rows)
    
    @staticmethod
    def update_payment(dang_ky_id, so_tien, trang_thai):
        """Update payment info"""
        with db_cursor(commit=True) as cursor:
            cursor.execute("""
                UPDATE dang_ky_giai
                SET so_tien_da_dong=%s, trang_thai_dong_tien=%s
                WHERE id=%s;
            """, (so_tien, trang_thai, dang_ky_id))

    @staticmethod
    def update_payments(updates):
        """Update many registration payments in one transaction."""
        rows = [(so_tien, trang_thai, dang_ky_id) for dang_ky_id, so_tien, trang_thai in updates]
        if not rows:
            return 0
        with db_cursor(commit=True) as cursor:
            cursor.executemany("""
                UPDATE dang_ky_giai
                SET so_tien_da_dong=%s, trang_thai_dong_tien=%s
                WHERE id=%s;
            """, rows)
        return len(rows)
    
    @staticmethod
    def remove(dang_ky_id):
        """Remove VĐV from tournament"""
        with db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM dang_ky_giai WHERE id = %s;", (dang_ky_id,))

class MatchModel:
    """Trận đấu"""

    @staticmethod
    def ensure_score_order_column():
        """Schema is maintained by init_db.py; kept for backward-compatible callers."""
        return None
    
    @staticmethod
    def get_all_by_tournament(giai_id):
        """Get all matches for tournament"""
        with db_cursor() as cursor:
            cursor.execute("""
                SELECT id, doi_a, doi_b, diem_doi_a, diem_doi_b, trang_thai, san_so_may, vong_dau,
                       COALESCE(thu_tu_danh, 2), COALESCE(doi_dang_giao, 'A')
                FROM tran_dau WHERE giai_dau_id = %s
                ORDER BY vong_dau ASC, san_so_may ASC, id ASC;
            """, (giai_id,))
            return cursor.fetchall()
    
    @staticmethod
    def delete_by_tournament(giai_id):
        """Delete all matches for tournament"""
        with db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM tran_dau WHERE giai_dau_id = %s;", (giai_id,))
    
    @staticmethod
    def save_matches(giai_id, matches):
        """Save matches"""
        with db_cursor(commit=True) as cursor:
            for m in matches:
                cursor.execute("""
                    INSERT INTO tran_dau (giai_dau_id, doi_a, doi_b, trang_thai, san_so_may, vong_dau)
                    VALUES (%s, %s, %s, %s, %s, %s);
                """, (giai_id, m['doi_a'], m['doi_b'], 'Chưa diễn ra',
                      m.get('san', 1), m.get('vong', 1)))
    
    @staticmethod
    def update_score(tran_id, diem_a, diem_b, thu_tu_danh=2, doi_dang_giao='A'):
        """Update match score"""
        with db_cursor(commit=True) as cursor:
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
            doi_dang_giao = doi_dang_giao if doi_dang_giao in ('A', 'B') else 'A'
            cursor.execute("""
                UPDATE tran_dau
                SET diem_doi_a=%s, diem_doi_b=%s, thu_tu_danh=%s, doi_dang_giao=%s, trang_thai=%s
                WHERE id=%s;
            """, (diem_a, diem_b, thu_tu_danh, doi_dang_giao, trang_thai, tran_id))
            return trang_thai, diem_a, diem_b
    
    @staticmethod
    def get_bang_xep_hang_by_matches(matches):
        """Calculate ranking from matches"""
        bang = {}
        for m in matches:
            doi_a, doi_b, d_a, d_b = m[1], m[2], m[3], m[4]
            for doi in [doi_a, doi_b]:
                if doi not in bang:
                    bang[doi] = {"ten": doi, "thang": 0, "thua": 0, "hieu_so": 0, "diem": 0, "so_tran": 0}
            if len(m) > 5 and m[5] != 'Đã xong':
                continue
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
