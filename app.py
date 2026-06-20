"""
FIXED: Unpacking issue + correct player calculation
"""

from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import os
from models_NEW import VanDongVienModel, TournamentModel, DangKyGiaiModel, MatchModel
from services import FinanceService, MatchSchedulerService
from auth import AuthService, login_required, admin_required
from config import DB_CONFIG, FLASK_SECRET_KEY, get_logger, LogHelper
import psycopg2

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY
logger = get_logger('pickleball.app')

# ============ HELPER FUNCTION ============

def prepare_tournament_detail(giai_raw, registrations):
    """
    ✅ FIXED: Correctly prepare player data for financial calculation
    
    registrations from DangKyGiaiModel.get_by_tournament() returns:
    (dkg.id, dkg.van_dong_vien_id, vdv.ten_vdv, vdv.trinh_do, vdv.email,
     dkg.so_tien_da_dong, dkg.trang_thai_dong_tien, dkg.ghi_chu)
    
    FinanceService expects: (id, ten, trinh_do, email, so_tien)
    """
    players_for_calc = []
    for reg in registrations:
        # reg[0]=id, reg[1]=van_dong_vien_id, reg[2]=ten, reg[3]=trinh_do, reg[4]=email, reg[5]=so_tien
        player_tuple = (reg[1], reg[2], reg[3], reg[4], reg[5])
        players_for_calc.append(player_tuple)
    
    return FinanceService.tinh_toan_dong_tien(giai_raw, players_for_calc)

# ============ ADMIN ROUTES ============

@app.route('/')
@login_required
def trang_chu():
    """Trang chủ admin"""
    user = session.get('user', {})
    LogHelper.log_request('GET', '/', user.get('email'))
    
    if user.get('role') != 'admin':
        return redirect(url_for('vdv_dashboard'))
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT g.id, g.ten_giai_dau, g.so_luong_san, g.dia_diem, 
                   g.chi_phi_san_bai, g.chi_phi_nuoc_noi, g.chi_phi_giai_thuong, g.chi_phi_khac, 
                   g.ty_le_giai_1, g.ty_le_giai_2, g.ty_le_giai_3, g.so_nguoi_du_kien,
                   g.thoi_gian_bat_dau, g.banner_image, g.qr_image,
                   COUNT(dkg.id) as so_luong_nguoi
            FROM giai_dau g
            LEFT JOIN dang_ky_giai dkg ON g.id = dkg.giai_dau_id
            GROUP BY g.id
            ORDER BY g.id DESC;
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        danh_sach_giai = []
        for row in rows:
            giai_raw = tuple(row[:15])
            registrations = DangKyGiaiModel.get_by_tournament(row[0])
            giai_detail = prepare_tournament_detail(giai_raw, registrations)
            danh_sach_giai.append(giai_detail)
        
        return render_template('index.html', danh_sach_giai=danh_sach_giai)
    except Exception as e:
        LogHelper.log_error(f"Error loading tournaments: {str(e)}")
        return f"❌ Error: {str(e)}", 500

# ============ VĐV MANAGEMENT (ADMIN) ============

@app.route('/van-dong-vien')
@admin_required
def van_dong_vien_list():
    """Danh sách VĐV"""
    try:
        vdv_list = VanDongVienModel.get_all()
        return render_template('van_dong_vien.html', vdv_list=vdv_list)
    except Exception as e:
        LogHelper.log_error(f"Error loading VĐV list: {str(e)}")
        return f"❌ Error: {str(e)}", 500

@app.route('/van-dong-vien/them', methods=['GET', 'POST'])
@admin_required
def them_van_dong_vien():
    """Thêm VĐV mới"""
    try:
        if request.method == 'GET':
            return render_template('them_van_dong_vien.html')
        
        ten_vdv = request.form['ten_vdv']
        trinh_do = request.form.get('trinh_do', 'C')
        email = request.form['email']
        ghi_chu = request.form.get('ghi_chu', '')
        
        VanDongVienModel.create(ten_vdv, trinh_do, email, ghi_chu)
        LogHelper.log_success(f"VĐV created: {ten_vdv}")
        return redirect('/van-dong-vien')
    except Exception as e:
        LogHelper.log_error(f"Error creating VĐV: {str(e)}")
        return f"❌ Error: {str(e)}", 500

@app.route('/van-dong-vien/<int:vdv_id>/sua', methods=['GET', 'POST'])
@admin_required
def sua_van_dong_vien(vdv_id):
    """Sửa VĐV"""
    try:
        if request.method == 'GET':
            vdv = VanDongVienModel.get_by_id(vdv_id)
            if not vdv:
                return "Không tìm thấy", 404
            return render_template('sua_van_dong_vien.html', vdv=vdv)
        
        ten_vdv = request.form['ten_vdv']
        trinh_do = request.form.get('trinh_do', 'C')
        email = request.form['email']
        ghi_chu = request.form.get('ghi_chu', '')
        
        VanDongVienModel.update(vdv_id, ten_vdv, trinh_do, email, ghi_chu)
        LogHelper.log_success(f"VĐV {vdv_id} updated")
        return redirect('/van-dong-vien')
    except Exception as e:
        LogHelper.log_error(f"Error updating VĐV: {str(e)}")
        return f"❌ Error: {str(e)}", 500

@app.route('/van-dong-vien/<int:vdv_id>/xoa')
@admin_required
def xoa_van_dong_vien(vdv_id):
    """Xóa VĐV"""
    try:
        VanDongVienModel.delete(vdv_id)
        LogHelper.log_success(f"VĐV {vdv_id} deleted")
        return redirect('/van-dong-vien')
    except Exception as e:
        LogHelper.log_error(f"Error deleting VĐV: {str(e)}")
        return f"❌ Error: {str(e)}", 500

# ============ TOURNAMENT MANAGEMENT ============

@app.route('/them-giai-dau', methods=['POST'])
@admin_required
def them_giai_dau():
    """Tạo giải mới"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO giai_dau 
                (ten_giai_dau, so_luong_san, dia_diem,
                 chi_phi_san_bai, chi_phi_nuoc_noi, chi_phi_giai_thuong, chi_phi_khac,
                 ty_le_giai_1, ty_le_giai_2, ty_le_giai_3, so_nguoi_du_kien, thoi_gian_bat_dau)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """, (
            request.form['ten_giai_dau'], request.form['so_luong_san'],
            request.form.get('dia_diem', ''),
            request.form.get('chi_phi_san_bai', 0), request.form.get('chi_phi_nuoc_noi', 0),
            request.form.get('chi_phi_giai_thuong', 0), request.form.get('chi_phi_khac', 0),
            request.form.get('ty_le_giai_1', 5), request.form.get('ty_le_giai_2', 3),
            request.form.get('ty_le_giai_3', 2), request.form.get('so_nguoi_du_kien', 10),
            request.form.get('thoi_gian_bat_dau', None)
        ))
        conn.commit()
        cursor.close()
        conn.close()
        LogHelper.log_success(f"Tournament created: {request.form['ten_giai_dau']}")
        return redirect('/')
    except Exception as e:
        LogHelper.log_error(f"Error creating tournament: {str(e)}")
        return f"❌ Error: {str(e)}", 500

@app.route('/sua-giai-dau/<int:giai_id>', methods=['GET', 'POST'])
@admin_required
def sua_giai_dau(giai_id):
    """Sửa giải đấu"""
    try:
        if request.method == 'GET':
            giai_raw = TournamentModel.get_details(giai_id)
            if not giai_raw:
                return "Không tìm thấy", 404
            return render_template('sua_giai.html', giai=giai_raw)
        
        # POST - Update
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE giai_dau SET
                ten_giai_dau=%s, so_luong_san=%s, dia_diem=%s,
                chi_phi_san_bai=%s, chi_phi_nuoc_noi=%s,
                chi_phi_giai_thuong=%s, chi_phi_khac=%s,
                ty_le_giai_1=%s, ty_le_giai_2=%s, ty_le_giai_3=%s,
                so_nguoi_du_kien=%s, thoi_gian_bat_dau=%s
            WHERE id=%s;
        """, (
            request.form['ten_giai_dau'], request.form['so_luong_san'],
            request.form.get('dia_diem'), request.form.get('chi_phi_san_bai', 0),
            request.form.get('chi_phi_nuoc_noi', 0), request.form.get('chi_phi_giai_thuong', 0),
            request.form.get('chi_phi_khac', 0), request.form.get('ty_le_giai_1', 5),
            request.form.get('ty_le_giai_2', 3), request.form.get('ty_le_giai_3', 2),
            request.form.get('so_nguoi_du_kien', 10),
            request.form.get('thoi_gian_bat_dau', None),
            giai_id
        ))
        conn.commit()
        cursor.close()
        conn.close()
        LogHelper.log_success(f"Tournament {giai_id} updated")
        return redirect('/')
    except Exception as e:
        LogHelper.log_error(f"Error updating tournament: {str(e)}")
        return f"❌ Error: {str(e)}", 500

@app.route('/xoa-giai-dau/<int:giai_id>')
@admin_required
def xoa_giai_dau(giai_id):
    """Xóa giải"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM giai_dau WHERE id = %s;", (giai_id,))
        conn.commit()
        cursor.close()
        conn.close()
        LogHelper.log_success(f"Tournament {giai_id} deleted")
        return redirect('/')
    except Exception as e:
        LogHelper.log_error(f"Error deleting tournament: {str(e)}")
        return f"❌ Error: {str(e)}", 500

# ============ TOURNAMENT DETAILS (ADMIN EDIT MODE) ============

@app.route('/giai-dau/<int:giai_id>/admin')
@admin_required
def chi_tiet_giai_admin(giai_id):
    """Chi tiết giải (ADMIN - Edit mode) ✅ FIXED"""
    try:
        giai_raw = TournamentModel.get_details(giai_id)
        if not giai_raw:
            return "Không tìm thấy giải!", 404
        
        # Get registrations
        registrations = DangKyGiaiModel.get_by_tournament(giai_id)
        
        # Get all VĐV for dropdown
        all_vdv = VanDongVienModel.get_all()
        
        # Get matches
        matches = MatchModel.get_all_by_tournament(giai_id)
        
        # ✅ FIXED: Use helper function to correctly prepare data
        giai_detail = prepare_tournament_detail(giai_raw, registrations)
        
        # Top 3 donate
        top_3_donate = []
        if giai_detail.get('nguoi_choi_list'):
            sorted_players = sorted(giai_detail['nguoi_choi_list'], key=lambda x: x['tien_dong'], reverse=True)
            top_3_donate = [(p['ten'], p['tien_dong']) for p in sorted_players[:3]]
        giai_detail['top_3_donate'] = top_3_donate
        
        # Ranking
        xep_hang = MatchModel.get_bang_xep_hang_by_matches(matches) if matches else []
        giai_detail['bang_xep_hang'] = xep_hang
        giai_detail['matches'] = matches
        giai_detail['registrations'] = registrations
        giai_detail['all_vdv'] = all_vdv
        giai_detail['user_role'] = 'admin'
        
        return render_template('chi_tiet_giai_admin.html', giai=giai_detail, enumerate=enumerate)
    except Exception as e:
        LogHelper.log_error(f"Error loading tournament: {str(e)}")
        return f"❌ Error: {str(e)}", 500

# ============ REGISTRATION MANAGEMENT ============

@app.route('/giai-dau/<int:giai_id>/dang-ky', methods=['POST'])
@admin_required
def dang_ky_vdv(giai_id):
    """Đăng ký VĐV vào giải"""
    try:
        van_dong_vien_id = request.form['van_dong_vien_id']
        DangKyGiaiModel.register(van_dong_vien_id, giai_id)
        LogHelper.log_success(f"VĐV {van_dong_vien_id} registered for tournament {giai_id}")
        return redirect(f'/giai-dau/{giai_id}/admin')
    except Exception as e:
        LogHelper.log_error(f"Error registering VĐV: {str(e)}")
        return f"❌ Error: {str(e)}", 500

@app.route('/dang-ky-giai/<int:dang_ky_id>/xoa')
@admin_required
def xoa_dang_ky(dang_ky_id):
    """Xóa đăng ký VĐV khỏi giải"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT giai_dau_id FROM dang_ky_giai WHERE id = %s;", (dang_ky_id,))
        result = cursor.fetchone()
        giai_id = result[0] if result else None
        cursor.close()
        conn.close()
        
        DangKyGiaiModel.remove(dang_ky_id)
        LogHelper.log_success(f"Registration {dang_ky_id} removed")
        return redirect(f'/giai-dau/{giai_id}/admin')
    except Exception as e:
        LogHelper.log_error(f"Error removing registration: {str(e)}")
        return f"❌ Error: {str(e)}", 500

@app.route('/dang-ky-giai/<int:dang_ky_id>/cap-nhat-tien', methods=['POST'])
@admin_required
def cap_nhat_tien_dang_ky(dang_ky_id):
    """Cập nhật tiền đóng cho VĐV"""
    try:
        so_tien = request.form.get('so_tien', 0)
        trang_thai = request.form.get('trang_thai', 'Chưa đóng')
        
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT giai_dau_id FROM dang_ky_giai WHERE id = %s;", (dang_ky_id,))
        result = cursor.fetchone()
        giai_id = result[0] if result else None
        cursor.close()
        conn.close()
        
        DangKyGiaiModel.update_payment(dang_ky_id, so_tien, trang_thai)
        return redirect(f'/giai-dau/{giai_id}/admin')
    except Exception as e:
        LogHelper.log_error(f"Error updating payment: {str(e)}")
        return f"❌ Error: {str(e)}", 500

# ============ SCHEDULE MANAGEMENT ============

@app.route('/giai-dau/<int:giai_id>/chia-lich', methods=['POST'])
@admin_required
def auto_chia_lich(giai_id):
    """Tự sinh lịch thi đấu"""
    try:
        registrations = DangKyGiaiModel.get_by_tournament(giai_id)
        giai_raw = TournamentModel.get_details(giai_id)
        so_san = giai_raw[2] if giai_raw else 1
        
        MatchModel.delete_by_tournament(giai_id)
        
        team_names = [r[2] for r in registrations]
        matches = MatchSchedulerService.generate_round_robin(team_names, so_san)
        MatchModel.save_matches(giai_id, matches)
        
        LogHelper.log_success(f"Schedule generated for tournament {giai_id}")
        return redirect(f'/giai-dau/{giai_id}/admin')
    except Exception as e:
        LogHelper.log_error(f"Error generating schedule: {str(e)}")
        return f"❌ Error: {str(e)}", 500

@app.route('/tran-dau/<int:tran_id>/cap-nhat-ty-so', methods=['POST'])
@admin_required
def cap_nhat_ty_so(tran_id):
    """Cập nhật tỷ số trận"""
    try:
        diem_a = int(request.form.get('diem_a')) if request.form.get('diem_a') else None
        diem_b = int(request.form.get('diem_b')) if request.form.get('diem_b') else None
        
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT giai_dau_id FROM tran_dau WHERE id = %s;", (tran_id,))
        giai_id = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        MatchModel.update_score(tran_id, diem_a, diem_b)
        return redirect(f'/giai-dau/{giai_id}/admin')
    except Exception as e:
        LogHelper.log_error(f"Error updating match score: {str(e)}")
        return f"❌ Error: {str(e)}", 500

# ============ AUTH ROUTES ============

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Đăng nhập"""
    try:
        if request.method == 'GET':
            return render_template('login.html')
        
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        
        if role == 'admin':
            user, error = AuthService.login_admin(email, password)
        else:
            vdv = VanDongVienModel.get_by_email(email)
            if vdv and password == '123456789':
                user = {"id": vdv[0], "ten": vdv[1], "email": vdv[2], "role": "vdv"}
                error = None
            else:
                user, error = None, "Email hoặc mật khẩu sai"
        
        if user:
            session['user'] = user
            LogHelper.log_success(f"User {email} ({role}) logged in")
            return redirect(url_for('vdv_dashboard') if user.get('role') == 'vdv' else url_for('trang_chu'))
        
        return render_template('login.html', error=error)
    except Exception as e:
        LogHelper.log_error(f"Error during login: {str(e)}")
        return render_template('login.html', error="Lỗi hệ thống"), 500

@app.route('/dang-xuat')
def logout():
    """Đăng xuất"""
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin-settings')
@admin_required
def admin_settings():
    """Admin settings"""
    return render_template('admin_settings.html')

@app.route('/tao-admin', methods=['POST'])
@admin_required
def tao_admin():
    """Tạo admin mới"""
    try:
        email = request.form.get('email')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        
        if not email or not password:
            return render_template('admin_settings.html', error="Email & password required")
        if password != confirm:
            return render_template('admin_settings.html', error="Passwords don't match")
        if len(password) < 6:
            return render_template('admin_settings.html', error="Password min 6 chars")
        
        success, msg = AuthService.register_admin(email, password)
        
        if success:
            LogHelper.log_success(f"Admin created: {email}")
            return render_template('admin_settings.html', success=msg)
        else:
            return render_template('admin_settings.html', error=msg)
    except Exception as e:
        LogHelper.log_error(f"Error creating admin: {str(e)}")
        return render_template('admin_settings.html', error=f"Error: {str(e)}")

# ============ VĐV ROUTES ============

@app.route('/vdv-dashboard')
@login_required
def vdv_dashboard():
    """VĐV dashboard"""
    user = session.get('user', {})
    LogHelper.log_request('GET', '/vdv-dashboard', user.get('email'))
    
    if user.get('role') != 'vdv':
        return redirect(url_for('login'))
    
    try:
        vdv_id = user['id']
        tournaments_raw = DangKyGiaiModel.get_by_vdv(vdv_id)
        
        vdv_giai = []
        for row in tournaments_raw:
            giai_raw = tuple(row[1:16])
            registrations = DangKyGiaiModel.get_by_tournament(row[1])
            giai_detail = prepare_tournament_detail(giai_raw, registrations)
            vdv_giai.append(giai_detail)
        
        LogHelper.log_success(f"Loaded {len(vdv_giai)} tournaments for VĐV {user.get('email')}")
        return render_template('vdv_dashboard.html', vdv_giai=vdv_giai)
    except Exception as e:
        LogHelper.log_error(f"Error loading VĐV dashboard: {str(e)}")
        return f"❌ Error: {str(e)}", 500

@app.route('/giai-dau/<int:giai_id>/vdv')
@login_required
def chi_tiet_giai_vdv(giai_id):
    """Chi tiết giải (VĐV - Read only) ✅ FIXED"""
    user = session.get('user', {})
    
    if user.get('role') != 'vdv':
        return redirect(url_for('login'))
    
    try:
        vdv_id = user['id']
        tournaments = DangKyGiaiModel.get_by_vdv(vdv_id)
        if not any(t[1] == giai_id for t in tournaments):
            return "❌ Bạn không có quyền xem giải này", 403
        
        giai_raw = TournamentModel.get_details(giai_id)
        if not giai_raw:
            return "Không tìm thấy giải!", 404
        
        registrations = DangKyGiaiModel.get_by_tournament(giai_id)
        giai_detail = prepare_tournament_detail(giai_raw, registrations)
        
        matches = MatchModel.get_all_by_tournament(giai_id)
        xep_hang = MatchModel.get_bang_xep_hang_by_matches(matches) if matches else []
        
        # Top 3
        top_3_donate = []
        if giai_detail.get('nguoi_choi_list'):
            sorted_players = sorted(giai_detail['nguoi_choi_list'], key=lambda x: x['tien_dong'], reverse=True)
            top_3_donate = [(p['ten'], p['tien_dong']) for p in sorted_players[:3]]
        giai_detail['top_3_donate'] = top_3_donate
        giai_detail['bang_xep_hang'] = xep_hang
        giai_detail['matches'] = matches
        giai_detail['registrations'] = registrations
        giai_detail['user_role'] = 'vdv'
        
        return render_template('chi_tiet_giai_vdv.html', giai=giai_detail, enumerate=enumerate)
    except Exception as e:
        LogHelper.log_error(f"Error loading tournament for VĐV: {str(e)}")
        return f"❌ Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)