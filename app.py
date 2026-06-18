from flask import Flask, render_template, request, redirect, url_for, jsonify
from models import TournamentModel, PlayerModel, MatchModel
from services import FinanceService, MatchSchedulerService
from config import DB_CONFIG
import psycopg2
import math

app = Flask(__name__)

# ─── TRANG CHỦ ───────────────────────────────────────────────────────────────
@app.route('/')
def trang_chu():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, ten_giai_dau, so_luong_san, dia_diem, chi_phi_san_bai, 
               chi_phi_nuoc_noi, chi_phi_giai_thuong, chi_phi_khac, 
               ty_le_giai_1, ty_le_giai_2, ty_le_giai_3, so_nguoi_du_kien 
        FROM giai_dau ORDER BY id DESC;
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    danh_sach_giai = []
    for giai_raw in rows:
        players_raw = PlayerModel.get_all_by_tournament(giai_raw[0])
        data = FinanceService.tinh_toan_dong_tien(giai_raw, players_raw)

        # FinanceService đã tính đủ, chỉ cần append thẳng
        danh_sach_giai.append(data)

    return render_template('index.html', danh_sach_giai=danh_sach_giai)


# ─── TẠO GIẢI ────────────────────────────────────────────────────────────────
@app.route('/them-giai-dau', methods=['POST'])
def them_giai_dau():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO giai_dau 
            (ten_giai_dau, so_luong_san, dia_diem,
             chi_phi_san_bai, chi_phi_nuoc_noi, chi_phi_giai_thuong, chi_phi_khac,
             ty_le_giai_1, ty_le_giai_2, ty_le_giai_3, so_nguoi_du_kien)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
    """, (
        request.form['ten_giai_dau'], request.form['so_luong_san'],
        request.form.get('dia_diem', ''),
        request.form.get('chi_phi_san_bai', 0), request.form.get('chi_phi_nuoc_noi', 0),
        request.form.get('chi_phi_giai_thuong', 0), request.form.get('chi_phi_khac', 0),
        request.form.get('ty_le_giai_1', 5), request.form.get('ty_le_giai_2', 3),
        request.form.get('ty_le_giai_3', 2), request.form.get('so_nguoi_du_kien', 10),
    ))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/')


# ─── SỬA GIẢI ────────────────────────────────────────────────────────────────
@app.route('/sua-giai-dau/<int:giai_id>')
def sua_giai_dau_form(giai_id):
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, ten_giai_dau, so_luong_san, dia_diem,
               chi_phi_san_bai, chi_phi_nuoc_noi, chi_phi_giai_thuong, chi_phi_khac,
               ty_le_giai_1, ty_le_giai_2, ty_le_giai_3, so_nguoi_du_kien
        FROM giai_dau WHERE id = %s;
    """, (giai_id,))
    giai = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('sua_giai.html', giai=giai)

@app.route('/sua-giai-dau/<int:giai_id>', methods=['POST'])
def sua_giai_dau(giai_id):
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE giai_dau SET
            ten_giai_dau=%s, so_luong_san=%s, dia_diem=%s,
            chi_phi_san_bai=%s, chi_phi_nuoc_noi=%s,
            chi_phi_giai_thuong=%s, chi_phi_khac=%s,
            ty_le_giai_1=%s, ty_le_giai_2=%s, ty_le_giai_3=%s, so_nguoi_du_kien=%s
        WHERE id=%s;
    """, (
        request.form['ten_giai_dau'], request.form['so_luong_san'],
        request.form.get('dia_diem', ''),
        request.form.get('chi_phi_san_bai', 0), request.form.get('chi_phi_nuoc_noi', 0),
        request.form.get('chi_phi_giai_thuong', 0), request.form.get('chi_phi_khac', 0),
        request.form.get('ty_le_giai_1', 5), request.form.get('ty_le_giai_2', 3),
        request.form.get('ty_le_giai_3', 2), request.form.get('so_nguoi_du_kien', 10),
        giai_id,
    ))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/')

@app.route('/xoa-giai-dau/<int:giai_id>')
def xoa_giai_dau(giai_id):
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM giai_dau WHERE id = %s;", (giai_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/')


# ─── CHI TIẾT GIẢI ───────────────────────────────────────────────────────────
@app.route('/giai-dau/<int:giai_id>')
def chi_tiet_giai(giai_id):
    giai_raw     = TournamentModel.get_details(giai_id)
    players_raw  = PlayerModel.get_all_by_tournament(giai_id)
    giai_chi_tiet = FinanceService.tinh_toan_dong_tien(giai_raw, players_raw)
    
    giai_chi_tiet["top_3_donate"] = PlayerModel.get_top_donators(
        giai_id, giai_chi_tiet.get("chi_phi_moi_nguoi", 0)
    )

    # Lấy danh sách trận đấu & nhóm theo vòng
    matches_raw = MatchModel.get_all_by_tournament(giai_id)
    # matches_raw: (id, doi_a, doi_b, diem_a, diem_b, trang_thai, san, vong)
    vong_dict = {}
    for m in matches_raw:
        tran_id, doi_a, doi_b, d_a, d_b, trang_thai, san, vong = m
        if vong not in vong_dict:
            vong_dict[vong] = []
        vong_dict[vong].append({
            "id": tran_id, "doi_a": doi_a, "doi_b": doi_b,
            "diem_a": d_a, "diem_b": d_b,
            "trang_thai": trang_thai, "san": san
        })

    giai_chi_tiet["vong_dict"]    = dict(sorted(vong_dict.items()))
    giai_chi_tiet["bang_xep_hang"] = MatchModel.get_bang_xep_hang(giai_id)

    return render_template('chi_tiet.html', giai=giai_chi_tiet)


# ─── SINH LỊCH ───────────────────────────────────────────────────────────────
@app.route('/giai-dau/<int:giai_id>/chia-lich', methods=['POST'])
def auto_chia_lich(giai_id):
    the_thuc    = request.form.get('the_thuc', 'vong_tron')
    players_raw = PlayerModel.get_all_by_tournament(giai_id)

    if len(players_raw) < 2:
        return "Cần tối thiểu 2 người chơi để ghép cặp!"

    # Lấy số sân đã cấu hình
    giai_raw = TournamentModel.get_details(giai_id)
    so_san   = giai_raw[2] if giai_raw else 1

    teams = MatchSchedulerService.auto_pairing_teams(players_raw)
    MatchModel.delete_by_tournament(giai_id)

    if the_thuc == 'vong_tron':
        matches = MatchSchedulerService.generate_round_robin(teams, so_san=so_san)
        MatchModel.save_matches(giai_id, matches)

    elif the_thuc == 'chia_bang':
        bang_A = [t for i, t in enumerate(teams) if i % 2 == 0]
        bang_B = [t for i, t in enumerate(teams) if i % 2 != 0]

        matches_A = MatchSchedulerService.generate_round_robin(bang_A, so_san=max(1, so_san // 2))
        matches_B = MatchSchedulerService.generate_round_robin(bang_B, so_san=max(1, so_san // 2))

        for m in matches_A:
            m['san_label'] = f"Bảng A - Sân {m['san']}"
        for m in matches_B:
            m['san_label'] = f"Bảng B - Sân {m['san']}"
            m['san']       = m['san'] + (so_san // 2)  # offset sân cho bảng B

        MatchModel.save_matches(giai_id, matches_A + matches_B)

    return redirect(url_for('chi_tiet_giai', giai_id=giai_id))


# ─── CẬP NHẬT TỶ SỐ ─────────────────────────────────────────────────────────
@app.route('/tran-dau/<int:tran_id>/cap-nhat-ty-so', methods=['POST'])
def cap_nhat_ty_so(tran_id):
    giai_id = request.form.get('giai_id', type=int)
    diem_a  = request.form.get('diem_a',  type=int)
    diem_b  = request.form.get('diem_b',  type=int)
    MatchModel.update_score(tran_id, diem_a, diem_b)
    return redirect(url_for('chi_tiet_giai', giai_id=giai_id))


# ─── THÊM NGƯỜI CHƠI ─────────────────────────────────────────────────────────
@app.route('/giai-dau/<int:giai_id>/them-nguoi-choi', methods=['POST'])
def them_nguoi_choi(giai_id):
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO nguoi_choi (giai_dau_id, ten_nguoi_choi, trinh_do, so_tien_da_dong, ghi_chu)
        VALUES (%s, %s, %s, %s, %s);
    """, (
        giai_id,
        request.form['ten_nguoi_choi'],
        request.form.get('trinh_do', 'B'),
        request.form.get('so_tien_da_dong', 0) or 0,
        request.form.get('ghi_chu', ''),
    ))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('chi_tiet_giai', giai_id=giai_id))


# ─── SỬA / XÓA NGƯỜI CHƠI ────────────────────────────────────────────────────
@app.route('/giai-dau/<int:giai_id>/sua-nguoi-choi/<int:nguoi_id>')
def sua_nguoi_choi_form(giai_id, nguoi_id):
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, giai_dau_id, ten_nguoi_choi, trinh_do, so_tien_da_dong, ghi_chu
        FROM nguoi_choi WHERE id = %s;
    """, (nguoi_id,))
    nguoi_choi = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('sua_nguoi_choi.html', giai_id=giai_id, nguoi_choi=nguoi_choi)

@app.route('/giai-dau/<int:giai_id>/sua-nguoi-choi/<int:nguoi_id>', methods=['POST'])
def sua_nguoi_choi(giai_id, nguoi_id):
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE nguoi_choi SET ten_nguoi_choi=%s, trinh_do=%s, so_tien_da_dong=%s, ghi_chu=%s
        WHERE id=%s;
    """, (
        request.form['ten_nguoi_choi'], request.form.get('trinh_do', 'B'),
        request.form.get('so_tien_da_dong', 0), request.form.get('ghi_chu', ''),
        nguoi_id,
    ))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('chi_tiet_giai', giai_id=giai_id))

@app.route('/xoa-nguoi-choi/<int:giai_id>/<int:nguoi_id>')
def xoa_nguoi_choi(giai_id, nguoi_id):
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM nguoi_choi WHERE id = %s;", (nguoi_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('chi_tiet_giai', giai_id=giai_id))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
    
    