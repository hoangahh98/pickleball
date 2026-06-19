from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from werkzeug.utils import secure_filename
import os
import time  # FIX: Bổ sung thư viện time
import base64
import requests
from models import TournamentModel, PlayerModel, MatchModel
from services import FinanceService, MatchSchedulerService
from email_service import EmailService
from knockout_logic import KnockoutLogic
from auth import AuthService, login_required, admin_required
from config import DB_CONFIG
import psycopg2
import math

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "aK8mN@2kL9pQw3xRz5v7j#hF4tUyI6oP")

UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_upload_file_to_github(file):
    """Upload file len GitHub"""
    if not file:
        return None
    filename = secure_filename(f"{int(time.time())}_{file.filename}")
    file_content = file.read()
    base64_content = base64.b64encode(file_content).decode()
    
    url = f"https://api.github.com/repos/hoangahh98/pickleball/contents/uploads/{filename}"
    payload = {
        "message": f"Upload {filename}",
        "content": base64_content,
        "branch": "main"
    }
    headers = {
        "Authorization": f"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", # Khuyên dùng biến môi trường thay vì hardcode token công khai
        "Content-Type": "application/json"
    }
    resp = requests.put(url, json=payload, headers=headers)
    if resp.status_code == 201:
        return f"https://raw.githubusercontent.com/hoangahh98/pickleball/main/uploads/{filename}"
    return None

# Trang chủ Admin
@app.route('/')
@login_required
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
        danh_sach_giai.append(data)

    return render_template('index.html', danh_sach_giai=danh_sach_giai)

@app.route('/them-giai-dau', methods=['POST'])
@admin_required
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
    return redirect(url_for('trang_chu'))

@app.route('/sua-giai-dau/<int:giai_id>', methods=['GET', 'POST'])
@admin_required
def sua_giai_dau(giai_id):
    if request.method == 'GET':
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, ten_giai_dau, so_luong_san, dia_diem,
                   chi_phi_san_bai, chi_phi_nuoc_noi, chi_phi_giai_thuong, chi_phi_khac,
                   ty_le_giai_1, ty_le_giai_2, ty_le_giai_3, so_nguoi_du_kien, thoi_gian_bat_dau,
                   banner_image, qr_image
            FROM giai_dau WHERE id = %s;
        """, (giai_id,))
        giai = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template('sua_giai.html', giai=giai)
        
    # POST Method
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # FIX: Đổi đúng tên hàm save_upload_file_to_github
    banner_image = save_upload_file_to_github(request.files.get('banner_image'))
    qr_image = save_upload_file_to_github(request.files.get('qr_image'))
    
    if request.form.get('delete_banner'):
        banner_image = None
    if request.form.get('delete_qr'):
        qr_image = None
    
    giai_old = TournamentModel.get_details(giai_id)
    if not banner_image and not request.form.get('delete_banner'):
        banner_image = giai_old[13] if giai_old and len(giai_old) > 13 else None
    if not qr_image and not request.form.get('delete_qr'):
        qr_image = giai_old[14] if giai_old and len(giai_old) > 14 else None
    
    cursor.execute("""
        UPDATE giai_dau SET
            ten_giai_dau=%s, so_luong_san=%s, dia_diem=%s, thoi_gian_bat_dau=%s,
            chi_phi_san_bai=%s, chi_phi_nuoc_noi=%s,
            chi_phi_giai_thuong=%s, chi_phi_khac=%s,
            ty_le_giai_1=%s, ty_le_giai_2=%s, ty_le_giai_3=%s, so_nguoi_du_kien=%s,
            banner_image=%s, qr_image=%s
        WHERE id=%s;
    """, (
        request.form['ten_giai_dau'], request.form['so_luong_san'],
        request.form.get('dia_diem', ''),
        request.form.get('thoi_gian_bat_dau', None) or None,
        request.form.get('chi_phi_san_bai', 0), request.form.get('chi_phi_nuoc_noi', 0),
        request.form.get('chi_phi_giai_thuong', 0), request.form.get('chi_phi_khac', 0),
        request.form.get('ty_le_giai_1', 5), request.form.get('ty_le_giai_2', 3),
        request.form.get('ty_le_giai_3', 2), request.form.get('so_nguoi_du_kien', 10),
        banner_image, qr_image, giai_id,
    ))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('trang_chu'))

@app.route('/xoa-giai-dau/<int:giai_id>')
@admin_required
def xoa_giai_dau(giai_id):
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM giai_dau WHERE id = %s;", (giai_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('trang_chu'))

# FIX: Hoàn thiện chức năng xem chi tiết giải đấu
@app.route('/giai-dau/<int:giai_id>')
@login_required
def chi_tiet_giai(giai_id):
    """Chi tiết giải - hiển thị lịch thi đấu, bảng xếp hạng và dòng tiền"""
    user = session.get('user', {})
    
    if user.get('role') == 'vdv':
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT giai_dau_id FROM nguoi_choi WHERE id = %s AND giai_dau_id = %s;", (user.get('id'), giai_id))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return "❌ Bạn không có quyền xem giải này", 403
        cursor.close()
        conn.close()
        
    giai_raw = TournamentModel.get_details(giai_id)
    if not giai_raw:
        return "Giải đấu không tồn tại", 404
        
    players_raw = PlayerModel.get_all_by_tournament(giai_id)
    giai_detail = FinanceService.tinh_toan_dong_tien(giai_raw, players_raw)
    
    matches = MatchModel.get_all_by_tournament(giai_id)
    bang_xep_hang = MatchModel.get_bang_xep_hang(giai_id)
    
    return render_template('chi_tiet.html', giai=giai_detail, matches=matches, bang_xep_hang=bang_xep_hang)

# FIX: Làm sạch logic Dashboard VĐV tránh lỗi Tuple mảng đảo thứ tự
@app.route('/vdv-dashboard')
@login_required
def vdv_dashboard():
    """VĐV xem tất cả các giải mình tham gia một cách an toàn"""
    if session.get('user', {}).get('role') != 'vdv':
        return redirect(url_for('login'))
    
    vdv_id = session['user']['id']
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT giai_dau_id FROM nguoi_choi WHERE id = %s;", (vdv_id,))
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    vdv_giai = []
    for row in rows:
        giai_id = row[0]
        giai_raw = TournamentModel.get_details(giai_id)
        if giai_raw:
            players_raw = PlayerModel.get_all_by_tournament(giai_id)
            giai_detail = FinanceService.tinh_toan_dong_tien(giai_raw, players_raw)
            vdv_giai.append(giai_detail)
    
    return render_template('vdv_dashboard.html', vdv_giai=vdv_giai)

@app.route('/giai-dau/<int:giai_id>/chia-lich', methods=['POST'])
@admin_required
def auto_chia_lich(giai_id):
    the_thuc = request.form.get('the_thuc', 'vong_tron')
    players_raw = PlayerModel.get_all_by_tournament(giai_id)

    if len(players_raw) < 2:
        return "Cần tối thiểu 2 người chơi để ghép cặp!"

    giai_raw = TournamentModel.get_details(giai_id)
    so_san = giai_raw[2] if giai_raw else 1

    teams = MatchSchedulerService.auto_pairing_teams(players_raw)
    MatchModel.delete_by_tournament(giai_id)

    if the_thuc == 'vong_tron':
        matches = MatchSchedulerService.generate_round_robin(teams, so_san=so_san)
        MatchModel.save_matches(giai_id, matches)
    elif the_thuc == 'chia_bang':
        so_bang = int(request.form.get('so_bang', 2))
        so_doi_di_tiep = int(request.form.get('so_doi_di_tiep', 2))
        
        bangs = [[] for _ in range(so_bang)]
        for i, team in enumerate(teams):
            bangs[i % so_bang].append(team)
        
        all_matches = []
        for idx, bang in enumerate(bangs):
            bang_name = chr(65 + idx)
            matches = MatchSchedulerService.generate_round_robin(bang, so_san=max(1, so_san // so_bang))
            for m in matches:
                m['san'] = (m['san'] - 1) + (idx * max(1, so_san // so_bang)) + 1
                m['bang'] = bang_name
            all_matches.extend(matches)
        
        MatchModel.save_matches(giai_id, all_matches)
        MatchModel.save_knockout_config(giai_id, so_bang, so_doi_di_tiep)

    return redirect(url_for('chi_tiet_giai', giai_id=giai_id))

@app.route('/tran-dau/<int:tran_id>/cap-nhat-ty-so', methods=['POST'])
@admin_required
def cap_nhat_ty_so(tran_id):
    giai_id = request.form.get('giai_id', type=int)
    diem_a = request.form.get('diem_a', type=int)
    diem_b = request.form.get('diem_b', type=int)
    MatchModel.update_score(tran_id, diem_a, diem_b)
    return redirect(url_for('chi_tiet_giai', giai_id=giai_id))

@app.route('/giai-dau/<int:giai_id>/them-nguoi-choi', methods=['POST'])
@admin_required
def them_nguoi_choi(giai_id):
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO nguoi_choi 
        (giai_dau_id, ten_nguoi_choi, trinh_do, so_tien_da_dong, ghi_chu, email)
        VALUES (%s, %s, %s, %s, %s, %s);
    """, (
        giai_id, request.form['ten_nguoi_choi'], request.form.get('trinh_do', 'B'),
        request.form.get('so_tien_da_dong', 0), request.form.get('ghi_chu', ''),
        request.form.get('email', '')
    ))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('chi_tiet_giai', giai_id=giai_id))

@app.route('/giai-dau/<int:giai_id>/sua-nguoi-choi/<int:nguoi_id>', methods=['GET', 'POST'])
@admin_required
def sua_nguoi_choi(giai_id, nguoi_id):
    if request.method == 'GET':
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, giai_dau_id, ten_nguoi_choi, trinh_do, so_tien_da_dong, ghi_chu, email
            FROM nguoi_choi WHERE id = %s;
        """, (nguoi_id,))
        nguoi_choi = cursor.fetchone()
        cursor.close()
        conn.close()
        return render_template('sua_nguoi_choi.html', giai_id=giai_id, nguoi_choi=nguoi_choi)
        
    # POST
    ten_moi = request.form['ten_nguoi_choi']
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT ten_nguoi_choi FROM nguoi_choi WHERE id = %s;", (nguoi_id,))
    row = cursor.fetchone()
    ten_cu = row[0] if row else None
    
    cursor.execute("""
        UPDATE nguoi_choi 
        SET ten_nguoi_choi=%s, trinh_do=%s, so_tien_da_dong=%s, ghi_chu=%s, email=%s
        WHERE id=%s;
    """, (ten_moi, request.form.get('trinh_do', 'B'), request.form.get('so_tien_da_dong', 0),
          request.form.get('ghi_chu', ''), request.form.get('email', ''), nguoi_id))
    conn.commit()
    cursor.close()
    conn.close()
    
    if ten_cu and ten_cu != ten_moi:
        MatchModel.update_player_name_in_matches(giai_id, ten_cu, ten_moi)
    
    return redirect(url_for('chi_tiet_giai', giai_id=giai_id))

@app.route('/xoa-nguoi-choi/<int:giai_id>/<int:nguoi_id>')
@admin_required
def xoa_nguoi_choi(giai_id, nguoi_id):
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM nguoi_choi WHERE id = %s;", (nguoi_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect(url_for('chi_tiet_giai', giai_id=giai_id))

@app.route('/giai-dau/<int:giai_id>/gui-email-thong-bao', methods=['POST'])
@admin_required
def gui_email_thong_bao(giai_id):
    giai_raw = TournamentModel.get_details(giai_id)
    if not giai_raw:
        return "Giải không tồn tại", 404
    
    players = PlayerModel.get_all_by_tournament(giai_id)
    giai_name = giai_raw[1]
    dia_diem = giai_raw[3] or "Chưa xác định"
    thoi_gian = giai_raw[12] or "Chưa xác định"
    
    results = EmailService.send_bulk_invitation(giai_id, giai_name, players, dia_diem, str(thoi_gian))
    return render_template('email_status.html', giai_id=giai_id, results=results)

# FIX: Lấy thông tin giai_raw chính xác trước khi đưa vào sinh Knockout
@app.route('/giai-dau/<int:giai_id>/sinh-knockout', methods=['POST'])
@admin_required
def sinh_knockout(giai_id):
    so_doi_di_tiep = int(request.form.get('so_doi_di_tiep', 2))
    giai_raw = TournamentModel.get_details(giai_id)
    matches_raw = MatchModel.get_all_by_tournament(giai_id)
    
    bang_matches = {}
    for m in matches_raw:
        bang = m[6] if len(m) > 6 else 1
        if bang not in bang_matches:
            bang_matches[bang] = []
        bang_matches[bang].append(m)
    
    bang_xep_hang_dict = {}
    for bang, tran_list in bang_matches.items():
        xep_hang = MatchModel.get_bang_xep_hang_by_matches(tran_list)
        bang_name = f"Bảng {chr(65 + list(bang_matches.keys()).index(bang)) if isinstance(bang, int) else bang}"
        bang_xep_hang_dict[bang_name] = xep_hang
    
    knockout_structure, qualified_teams = KnockoutLogic.generate_knockout_matches(
        bang_xep_hang_dict, so_doi_di_tiep, giai_raw[2] if giai_raw else 1
    )
    
    for vong_name, tran_list in knockout_structure.items():
        for tran in tran_list:
            MatchModel.save_knockout_match(giai_id, tran['doi_a'], tran['doi_b'], vong_name, tran['san'])
    
    return redirect(url_for('chi_tiet_giai', giai_id=giai_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    
    role = request.form.get('role')
    email = request.form.get('email')
    password = request.form.get('password')
    
    if role == 'admin':
        user, error = AuthService.login_admin(email, password)
    else:
        user, error = AuthService.login_vdv(email, password)
    
    if error:
        return render_template('login.html', error=error)
    
    session['user'] = user
    if user['role'] == 'admin':
        return redirect(url_for('trang_chu'))
    else:
        return redirect(url_for('vdv_dashboard'))

@app.route('/dang-xuat')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/tao-admin', methods=['POST'])
def tao_admin():
    email = request.form.get('email')
    password = request.form.get('password')
    confirm = request.form.get('confirm_password')
    
    if len(password) < 6:
        return render_template('login.html', register_error='Mật khẩu tối thiểu 6 ký tự')
    if password != confirm:
        return render_template('login.html', register_error='Mật khẩu không khớp')
    
    success, msg = AuthService.register_admin(email, password)
    if not success:
        return render_template('login.html', register_error=msg)
    return render_template('login.html', error=f'✅ {msg}. Hãy đăng nhập!')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)