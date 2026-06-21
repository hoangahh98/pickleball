"""
DEBUG VERSION - Print data format to trace error
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
    DEBUG: Print data format
    """
    print(f"\n=== DEBUG prepare_tournament_detail ===")
    print(f"giai_raw length: {len(giai_raw)}")
    print(f"giai_raw: {giai_raw[:5]}...")  # Print first 5 items
    print(f"registrations count: {len(registrations)}")
    if registrations:
        print(f"First registration length: {len(registrations[0])}")
        print(f"First registration: {registrations[0]}")
    
    players_for_calc = []
    for reg in registrations:
        # Reformat to old PlayerModel format
        reformatted = (
            reg[0],        # id
            reg[1],        # van_dong_vien_id (as giai_dau_id)
            reg[2],        # ten
            reg[3],        # trinh_do
            reg[5],        # so_tien_da_dong
            reg[7],        # ghi_chu
            reg[4]         # email
        )
        print(f"Reformatted tuple length: {len(reformatted)}")
        print(f"Reformatted tuple: {reformatted}")
        players_for_calc.append(reformatted)
    
    print(f"Calling FinanceService.tinh_toan_dong_tien() with:")
    print(f"  giai_raw: {len(giai_raw)} items")
    print(f"  players_for_calc: {len(players_for_calc)} items")
    
    try:
        result = FinanceService.tinh_toan_dong_tien(giai_raw, players_for_calc)
        print(f"✅ FinanceService call successful")
        return result
    except Exception as e:
        print(f"❌ FinanceService ERROR: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        print(f"Traceback:\n{traceback.format_exc()}")
        raise

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
        
        print(f"\n=== DEBUG trang_chu ===")
        print(f"Total tournaments: {len(rows)}")
        if rows:
            print(f"First row length: {len(rows[0])}")
            print(f"First row: {rows[0]}")
        
        danh_sach_giai = []
        for row in rows:
            giai_raw = tuple(row[:15])
            print(f"\nProcessing tournament ID {row[0]}")
            registrations = DangKyGiaiModel.get_by_tournament(row[0])
            giai_detail = prepare_tournament_detail(giai_raw, registrations)
            danh_sach_giai.append(giai_detail)
        
        return render_template('index.html', danh_sach_giai=danh_sach_giai)
    except Exception as e:
        print(f"\n❌ EXCEPTION in trang_chu: {str(e)}")
        import traceback
        print(f"Full traceback:\n{traceback.format_exc()}")
        LogHelper.log_error(f"Error loading tournaments: {str(e)}")
        return f"❌ Error: {str(e)}", 500

# ... [Keep other routes same as before] ...

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

@app.route('/vdv-dashboard')
@login_required
def vdv_dashboard():
    """VĐV dashboard"""
    user = session.get('user', {})
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
        
        return render_template('vdv_dashboard.html', vdv_giai=vdv_giai)
    except Exception as e:
        return f"❌ Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)