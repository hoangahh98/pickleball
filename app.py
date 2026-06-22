"""
Complete App with Database Logging
All logs stored in app_logs table
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from models import VanDongVienModel, TournamentModel, DangKyGiaiModel, MatchModel
from services import FinanceService
from knockout_logic import MatchSchedulerService
from auth import AuthService, login_required, admin_required
from config import DB_CONFIG, FLASK_SECRET_KEY, BASE_URL
from logging_service import DBLogger, DBLogViewer
import psycopg2
import traceback

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY

# ============ HELPER FUNCTION ============

def prepare_tournament_detail(giai_raw, registrations):
    """Prepare tournament details with correct data format"""
    players_for_calc = []
    for reg in registrations:
        # reg: (dkg.id, van_dong_vien_id, ten_vdv, trinh_do, email, so_tien_da_dong, trang_thai_dong_tien, ghi_chu)
        reformatted = (
            reg[0], reg[1], reg[2], reg[3], reg[5], reg[7], reg[4], reg[6]
            # id,   vdv_id, ten,    trinh,   tien,   ghi_chu, email,  trang_thai
        )
        players_for_calc.append(reformatted)
    
    return FinanceService.tinh_toan_dong_tien(giai_raw, players_for_calc)

# ============ ADMIN ROUTES ============

@app.route('/')
@login_required
def trang_chu():
    """Trang chủ admin"""
    user = session.get('user', {})
    DBLogger.log_request('GET', '/', user.get('email'))
    
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
            try:
                giai_raw = tuple(row[:15])
                registrations = DangKyGiaiModel.get_by_tournament(row[0])
                giai_detail = prepare_tournament_detail(giai_raw, registrations)
                danh_sach_giai.append(giai_detail)
            except Exception as e:
                error_msg = f"Error loading tournament {row[0]}: {str(e)}"
                DBLogger.log_error(error_msg, user.get('email'), '/', context=traceback.format_exc())
                continue
        
        DBLogger.log_success(f"Loaded {len(danh_sach_giai)} tournaments", user.get('email'), '/')
        return render_template('index.html', danh_sach_giai=danh_sach_giai)
    except Exception as e:
        DBLogger.log_error(f"Error loading tournaments: {str(e)}", user.get('email'), '/', context=traceback.format_exc())
        return f"❌ Error: {str(e)}", 500

# ============ LOGGING VIEWER (ADMIN ONLY) ============

@app.route('/logs')
@admin_required
def view_logs():
    """View application logs"""
    try:
        filter_level = request.args.get('level')  # ERROR, SUCCESS, etc
        filter_days = int(request.args.get('days', 1))
        
        # Get logs
        if filter_level:
            logs = DBLogViewer.get_recent_logs(limit=100, level=filter_level)
        else:
            logs = DBLogViewer.get_recent_logs(limit=100)
        
        # Get stats
        stats = DBLogViewer.get_log_stats()
        
        # Get today's errors count
        errors_today = DBLogViewer.get_errors_today()
        
        return render_template('logs_viewer.html', 
                             logs=logs, 
                             stats=stats,
                             errors_count=len(errors_today),
                             filter_level=filter_level,
                             enumerate=enumerate)
    except Exception as e:
        user = session.get('user', {})
        DBLogger.log_error(f"Error viewing logs: {str(e)}", user.get('email'), '/logs')
        return f"❌ Error: {str(e)}", 500

@app.route('/logs-api/errors-today')
@admin_required
def api_errors_today():
    """API endpoint for errors today"""
    try:
        errors = DBLogViewer.get_errors_today()
        return jsonify({
            'count': len(errors),
            'errors': [{'message': e[1], 'user': e[2], 'route': e[3], 'time': str(e[4])} for e in errors]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/logs-api/user-actions/<email>')
@admin_required
def api_user_actions(email):
    """API endpoint for specific user actions"""
    try:
        actions = DBLogViewer.get_user_actions(email)
        return jsonify({
            'user': email,
            'actions': [{'level': a[1], 'message': a[2], 'route': a[3], 'time': str(a[4])} for a in actions]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ============ VĐV MANAGEMENT (ADMIN) ============

@app.route('/van-dong-vien')
@admin_required
def van_dong_vien_list():
    """Danh sách VĐV"""
    user = session.get('user', {})
    try:
        vdv_list = VanDongVienModel.get_all()
        DBLogger.log_request('GET', '/van-dong-vien', user.get('email'))
        return render_template('van_dong_vien.html', vdv_list=vdv_list)
    except Exception as e:
        DBLogger.log_error(f"Error loading VĐV list: {str(e)}", user.get('email'), '/van-dong-vien', context=traceback.format_exc())
        return f"❌ Error: {str(e)}", 500

@app.route('/van-dong-vien/them', methods=['GET', 'POST'])
@admin_required
def them_van_dong_vien():
    """Thêm VĐV mới"""
    user = session.get('user', {})
    try:
        if request.method == 'GET':
            return render_template('them_van_dong_vien.html')
        
        ten_vdv = request.form['ten_vdv']
        trinh_do = request.form.get('trinh_do', 'C')
        email = request.form['email']
        ghi_chu = request.form.get('ghi_chu', '')
        
        VanDongVienModel.create(ten_vdv, trinh_do, email, ghi_chu)
        DBLogger.log_success(f"VĐV created: {ten_vdv}", user.get('email'), '/van-dong-vien/them')
        return redirect('/van-dong-vien')
    except Exception as e:
        DBLogger.log_error(f"Error creating VĐV: {str(e)}", user.get('email'), '/van-dong-vien/them', context=traceback.format_exc())
        return f"❌ Error: {str(e)}", 500

@app.route('/van-dong-vien/<int:vdv_id>/sua', methods=['GET', 'POST'])
@admin_required
def sua_van_dong_vien(vdv_id):
    """Sửa VĐV"""
    user = session.get('user', {})
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
        DBLogger.log_success(f"VĐV {vdv_id} updated: {ten_vdv}", user.get('email'), f'/van-dong-vien/{vdv_id}/sua')
        return redirect('/van-dong-vien')
    except Exception as e:
        DBLogger.log_error(f"Error updating VĐV: {str(e)}", user.get('email'), f'/van-dong-vien/{vdv_id}/sua', context=traceback.format_exc())
        return f"❌ Error: {str(e)}", 500

@app.route('/van-dong-vien/<int:vdv_id>/xoa')
@admin_required
def xoa_van_dong_vien(vdv_id):
    """Xóa VĐV"""
    user = session.get('user', {})
    try:
        vdv = VanDongVienModel.get_by_id(vdv_id)
        ten = vdv[1] if vdv else f"ID {vdv_id}"
        VanDongVienModel.delete(vdv_id)
        DBLogger.log_success(f"VĐV deleted: {ten}", user.get('email'), f'/van-dong-vien/{vdv_id}/xoa')
        return redirect('/van-dong-vien')
    except Exception as e:
        DBLogger.log_error(f"Error deleting VĐV: {str(e)}", user.get('email'), f'/van-dong-vien/{vdv_id}/xoa', context=traceback.format_exc())
        return f"❌ Error: {str(e)}", 500

# ============ TOURNAMENT MANAGEMENT ============

@app.route('/them-giai-dau', methods=['POST'])
@admin_required
def them_giai_dau():
    """Tạo giải mới - ENSURE loai_dau is saved"""
    user = session.get('user', {})
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        loai_dau = request.form.get('loai_dau', 'don')
        DBLogger.log_info(f"Creating tournament with loai_dau={loai_dau}", user.get('email'), '/them-giai-dau')
        
        cursor.execute("""
            INSERT INTO giai_dau 
                (ten_giai_dau, so_luong_san, dia_diem,
                 chi_phi_san_bai, chi_phi_nuoc_noi, chi_phi_giai_thuong, chi_phi_khac,
                 ty_le_giai_1, ty_le_giai_2, ty_le_giai_3, so_nguoi_du_kien, thoi_gian_bat_dau, loai_dau)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """, (
            request.form['ten_giai_dau'], 
            request.form['so_luong_san'],
            request.form.get('dia_diem', ''),
            request.form.get('chi_phi_san_bai', 0), 
            request.form.get('chi_phi_nuoc_noi', 0),
            request.form.get('chi_phi_giai_thuong', 0), 
            request.form.get('chi_phi_khac', 0),
            request.form.get('ty_le_giai_1', 5), 
            request.form.get('ty_le_giai_2', 3),
            request.form.get('ty_le_giai_3', 2), 
            request.form.get('so_nguoi_du_kien', 10),
            request.form.get('thoi_gian_bat_dau', None),
            loai_dau  # ← Make sure this is included!
        ))
        conn.commit()
        cursor.close()
        conn.close()
        DBLogger.log_success(f"Tournament created: {request.form['ten_giai_dau']} ({loai_dau})", user.get('email'), '/them-giai-dau')
        return redirect('/')
    except Exception as e:
        DBLogger.log_error(f"Error creating tournament: {str(e)}", user.get('email'), '/them-giai-dau', context=traceback.format_exc())
        return f"❌ Error: {str(e)}", 500

@app.route('/sua-giai-dau/<int:giai_id>', methods=['GET', 'POST'])
@admin_required
def sua_giai_dau(giai_id):
    """Sửa giải đấu - ENSURE loai_dau is updated"""
    user = session.get('user', {})
    try:
        if request.method == 'GET':
            giai_raw = TournamentModel.get_details(giai_id)
            if not giai_raw:
                return "Không tìm thấy", 404
            # ← Get loai_dau from database
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("SELECT loai_dau FROM giai_dau WHERE id = %s;", (giai_id,))
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            giai_raw = giai_raw + (result[0] if result else 'don',)  # Add loai_dau to tuple
            return render_template('sua_giai.html', giai=giai_raw)
        
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        loai_dau = request.form.get('loai_dau', 'don')
        DBLogger.log_info(f"Updating tournament {giai_id} with loai_dau={loai_dau}", user.get('email'), f'/sua-giai-dau/{giai_id}')
        
        cursor.execute("""
            UPDATE giai_dau SET
                ten_giai_dau=%s, so_luong_san=%s, dia_diem=%s,
                chi_phi_san_bai=%s, chi_phi_nuoc_noi=%s,
                chi_phi_giai_thuong=%s, chi_phi_khac=%s,
                ty_le_giai_1=%s, ty_le_giai_2=%s, ty_le_giai_3=%s,
                so_nguoi_du_kien=%s, thoi_gian_bat_dau=%s, loai_dau=%s
            WHERE id=%s;
        """, (
            request.form['ten_giai_dau'], 
            request.form['so_luong_san'],
            request.form.get('dia_diem'), 
            request.form.get('chi_phi_san_bai', 0),
            request.form.get('chi_phi_nuoc_noi', 0), 
            request.form.get('chi_phi_giai_thuong', 0),
            request.form.get('chi_phi_khac', 0), 
            request.form.get('ty_le_giai_1', 5),
            request.form.get('ty_le_giai_2', 3), 
            request.form.get('ty_le_giai_3', 2),
            request.form.get('so_nguoi_du_kien', 10),
            request.form.get('thoi_gian_bat_dau', None),
            loai_dau,  # ← Make sure this is included!
            giai_id
        ))
        conn.commit()
        cursor.close()
        conn.close()
        DBLogger.log_success(f"Tournament {giai_id} updated ({loai_dau})", user.get('email'), f'/sua-giai-dau/{giai_id}')
        return redirect('/')
    except Exception as e:
        DBLogger.log_error(f"Error updating tournament: {str(e)}", user.get('email'), f'/sua-giai-dau/{giai_id}', context=traceback.format_exc())
        return f"❌ Error: {str(e)}", 500

@app.route('/xoa-giai-dau/<int:giai_id>')
@admin_required
def xoa_giai_dau(giai_id):
    """Xóa giải"""
    user = session.get('user', {})
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM giai_dau WHERE id = %s;", (giai_id,))
        conn.commit()
        cursor.close()
        conn.close()
        DBLogger.log_success(f"Tournament {giai_id} deleted", user.get('email'), f'/xoa-giai-dau/{giai_id}')
        return redirect('/')
    except Exception as e:
        DBLogger.log_error(f"Error deleting tournament: {str(e)}", user.get('email'), f'/xoa-giai-dau/{giai_id}', context=traceback.format_exc())
        return f"❌ Error: {str(e)}", 500

@app.route('/giai-dau/<int:giai_id>/admin')
@admin_required
def chi_tiet_giai_admin(giai_id):
    """Chi tiết giải (ADMIN) - FIXED VERSION"""
    user = session.get('user', {})
    try:
        giai_raw = TournamentModel.get_details(giai_id)
        if not giai_raw:
            return "Không tìm thấy", 404
        
        registrations = DangKyGiaiModel.get_by_tournament(giai_id)
        all_vdv = VanDongVienModel.get_all()
        matches = MatchModel.get_all_by_tournament(giai_id)
        
        giai_detail = prepare_tournament_detail(giai_raw, registrations)
        
        top_3_donate = []
        if giai_detail.get('nguoi_choi_list'):
            sorted_players = sorted(giai_detail['nguoi_choi_list'], key=lambda x: x['tien_dong'], reverse=True)
            top_3_donate = [(p['ten'], p['tien_dong']) for p in sorted_players[:3]]
        giai_detail['top_3_donate'] = top_3_donate
        
        xep_hang = MatchModel.get_bang_xep_hang_by_matches(matches) if matches else []
        giai_detail['bang_xep_hang'] = xep_hang
        giai_detail['matches'] = matches
        giai_detail['registrations'] = registrations
        giai_detail['all_vdv'] = all_vdv

        # Build vong_dict: { vong_number: [match_dict, ...] } for the template
        vong_dict = {}
        for m in matches:
            vong = m[7] or 1
            if vong not in vong_dict:
                vong_dict[vong] = []
            vong_dict[vong].append({
                "id": m[0], "doi_a": m[1], "doi_b": m[2],
                "diem_a": m[3], "diem_b": m[4],
                "trang_thai": m[5], "san": m[6] or 1, "vong": vong
            })
        giai_detail['vong_dict'] = vong_dict
        
        # ← FIX #1: Properly get loai_dau with error handling
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("SELECT loai_dau FROM giai_dau WHERE id = %s;", (giai_id,))
            result = cursor.fetchone()
            loai_dau = result[0] if result and result[0] else 'don'
            giai_detail['loai_dau'] = loai_dau
            DBLogger.log_info(f"Tournament {giai_id} loai_dau={loai_dau}", user.get('email'), f'/giai-dau/{giai_id}/admin')
            cursor.close()
            conn.close()
        except Exception as e:
            DBLogger.log_warning(f"Could not get loai_dau: {str(e)}", user.get('email'), f'/giai-dau/{giai_id}/admin')
            giai_detail['loai_dau'] = 'don'
        
        canh_bao = None
        if request.args.get('error') == 'full':
            canh_bao = "⚠️ Giải đã đủ số người dự kiến, không thể thêm VĐV nữa. Hãy tăng 'Số người dự kiến' trong phần Sửa giải nếu muốn nhận thêm."

        DBLogger.log_request('GET', f'/giai-dau/{giai_id}/admin', user.get('email'))
        return render_template('chi_tiet_giai_admin.html', giai=giai_detail, registrations=registrations, canh_bao=canh_bao, enumerate=enumerate, base_url=BASE_URL)
    except Exception as e:
        DBLogger.log_error(f"Error loading tournament: {str(e)}", user.get('email'), f'/giai-dau/{giai_id}/admin', context=traceback.format_exc())
        return f"❌ Error: {str(e)}", 500

@app.route('/giai-dau/<int:giai_id>/dang-ky', methods=['POST'])
@admin_required
def dang_ky_vdv(giai_id):
    """Đăng ký VĐV"""
    user = session.get('user', {})
    try:
        van_dong_vien_id = request.form['van_dong_vien_id']

        giai_raw = TournamentModel.get_details(giai_id)
        so_nguoi_du_kien = giai_raw[11] if giai_raw and giai_raw[11] else 0
        registrations = DangKyGiaiModel.get_by_tournament(giai_id)

        if so_nguoi_du_kien and len(registrations) >= so_nguoi_du_kien:
            DBLogger.log_warning(
                f"Registration rejected: tournament {giai_id} already full ({len(registrations)}/{so_nguoi_du_kien})",
                user.get('email'), f'/giai-dau/{giai_id}/dang-ky'
            )
            return redirect(f'/giai-dau/{giai_id}/admin?error=full')

        DangKyGiaiModel.register(van_dong_vien_id, giai_id)
        DBLogger.log_success(f"VĐV {van_dong_vien_id} registered for tournament {giai_id}", user.get('email'), f'/giai-dau/{giai_id}/dang-ky')
        return redirect(f'/giai-dau/{giai_id}/admin')
    except Exception as e:
        DBLogger.log_error(f"Error registering VĐV: {str(e)}", user.get('email'), f'/giai-dau/{giai_id}/dang-ky', context=traceback.format_exc())
        return f"❌ Error: {str(e)}", 500

@app.route('/dang-ky-giai/<int:dang_ky_id>/xoa')
@admin_required
def xoa_dang_ky(dang_ky_id):
    """Xóa đăng ký"""
    user = session.get('user', {})
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT giai_dau_id FROM dang_ky_giai WHERE id = %s;", (dang_ky_id,))
        result = cursor.fetchone()
        giai_id = result[0] if result else None
        cursor.close()
        conn.close()
        
        DangKyGiaiModel.remove(dang_ky_id)
        DBLogger.log_success(f"Registration {dang_ky_id} removed", user.get('email'), f'/dang-ky-giai/{dang_ky_id}/xoa')
        return redirect(f'/giai-dau/{giai_id}/admin')
    except Exception as e:
        DBLogger.log_error(f"Error removing registration: {str(e)}", user.get('email'), f'/dang-ky-giai/{dang_ky_id}/xoa', context=traceback.format_exc())
        return f"❌ Error: {str(e)}", 500

@app.route('/dang-ky-giai/<int:dang_ky_id>/cap-nhat-tien', methods=['POST'])
@admin_required
def cap_nhat_tien_dang_ky(dang_ky_id):
    """Cập nhật tiền"""
    user = session.get('user', {})
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
        DBLogger.log_success(f"Payment updated: {so_tien}đ", user.get('email'), f'/dang-ky-giai/{dang_ky_id}/cap-nhat-tien')
        return redirect(f'/giai-dau/{giai_id}/admin')
    except Exception as e:
        DBLogger.log_error(f"Error updating payment: {str(e)}", user.get('email'), f'/dang-ky-giai/{dang_ky_id}/cap-nhat-tien', context=traceback.format_exc())
        return f"❌ Error: {str(e)}", 500

@app.route('/giai-dau/<int:giai_id>/chia-lich', methods=['POST'])  # ← CRITICAL: methods=['POST']
@admin_required
def auto_chia_lich(giai_id):
    """Tự sinh lịch thi đấu - FIXED VERSION"""
    user = session.get('user', {})
    try:
        registrations = DangKyGiaiModel.get_by_tournament(giai_id)
        giai_raw = TournamentModel.get_details(giai_id)
        so_san = giai_raw[2] if giai_raw else 1
        
        # ← FIX #1: Get loai_dau with error handling
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("SELECT loai_dau FROM giai_dau WHERE id = %s;", (giai_id,))
            result = cursor.fetchone()
            loai_dau = result[0] if result and result[0] else 'don'
            cursor.close()
            conn.close()
        except Exception as e:
            DBLogger.log_warning(f"Could not get loai_dau: {str(e)}", user.get('email'), f'/giai-dau/{giai_id}/chia-lich')
            loai_dau = 'don'
        
        MatchModel.delete_by_tournament(giai_id)
        team_names = [r[2] for r in registrations]
        
        # ← Use loai_dau from database
        matches = MatchSchedulerService.generate_round_robin(team_names, so_san, loai_dau)
        MatchModel.save_matches(giai_id, matches)
        
        DBLogger.log_success(f"Schedule generated: {len(matches)} matches ({loai_dau})", user.get('email'), f'/giai-dau/{giai_id}/chia-lich')
        return redirect(f'/giai-dau/{giai_id}/admin')
    except Exception as e:
        DBLogger.log_error(f"Error generating schedule: {str(e)}", user.get('email'), f'/giai-dau/{giai_id}/chia-lich', context=traceback.format_exc())
        return f"❌ Error: {str(e)}", 500

@app.route('/tran-dau/<int:tran_id>/cap-nhat-ty-so', methods=['POST'])
@admin_required
def cap_nhat_ty_so(tran_id):
    """Cập nhật tỷ số"""
    user = session.get('user', {})
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
        DBLogger.log_success(f"Match {tran_id} score updated: {diem_a}-{diem_b}", user.get('email'), f'/tran-dau/{tran_id}/cap-nhat-ty-so')
        return redirect(f'/giai-dau/{giai_id}/admin')
    except Exception as e:
        DBLogger.log_error(f"Error updating match: {str(e)}", user.get('email'), f'/tran-dau/{tran_id}/cap-nhat-ty-so', context=traceback.format_exc())
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
            DBLogger.log_success(f"User {email} ({role}) logged in", email, '/login')
            return redirect(url_for('vdv_dashboard') if user.get('role') == 'vdv' else url_for('trang_chu'))
        
        DBLogger.log_warning(f"Failed login attempt: {email}", email, '/login')
        return render_template('login.html', error=error)
    except Exception as e:
        DBLogger.log_error(f"Error during login: {str(e)}", context=traceback.format_exc())
        return render_template('login.html', error="Lỗi hệ thống"), 500

@app.route('/dang-xuat')
def logout():
    """Đăng xuất"""
    user = session.get('user', {})
    DBLogger.log_success(f"User logged out", user.get('email'), '/dang-xuat')
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin-settings')
@admin_required
def admin_settings():
    """Cài đặt"""
    return render_template('admin_settings.html')

@app.route('/tao-admin', methods=['POST'])
@admin_required
def tao_admin():
    """Tạo admin"""
    user = session.get('user', {})
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
            DBLogger.log_success(f"Admin created: {email}", user.get('email'), '/tao-admin')
            return render_template('admin_settings.html', success=msg)
        else:
            DBLogger.log_warning(f"Failed to create admin: {email}", user.get('email'), '/tao-admin')
            return render_template('admin_settings.html', error=msg)
    except Exception as e:
        DBLogger.log_error(f"Error creating admin: {str(e)}", user.get('email'), '/tao-admin', context=traceback.format_exc())
        return render_template('admin_settings.html', error=f"Error: {str(e)}")

# ============ VĐV ROUTES ============

@app.route('/vdv-dashboard')
@login_required
def vdv_dashboard():
    """VĐV Dashboard"""
    user = session.get('user', {})
    DBLogger.log_request('GET', '/vdv-dashboard', user.get('email'))
    
    if user.get('role') != 'vdv':
        return redirect(url_for('login'))
    
    try:
        vdv_id = user['id']
        tournaments_raw = DangKyGiaiModel.get_by_vdv(vdv_id)
        
        vdv_giai = []
        for row in tournaments_raw:
            try:
                giai_raw = tuple(row[1:16])
                registrations = DangKyGiaiModel.get_by_tournament(row[1])
                giai_detail = prepare_tournament_detail(giai_raw, registrations)
                vdv_giai.append(giai_detail)
            except Exception as e:
                DBLogger.log_error(f"Error loading tournament for VĐV: {str(e)}", user.get('email'), '/vdv-dashboard', context=traceback.format_exc())
                continue
        
        return render_template('vdv_dashboard.html', vdv_giai=vdv_giai)
    except Exception as e:
        DBLogger.log_error(f"Error loading VĐV dashboard: {str(e)}", user.get('email'), '/vdv-dashboard', context=traceback.format_exc())
        return f"❌ Error: {str(e)}", 500

@app.route('/giai-dau/<int:giai_id>/vdv')
@login_required
def chi_tiet_giai_vdv(giai_id):
    """Chi tiết giải (VĐV)"""
    user = session.get('user', {})
    
    if user.get('role') != 'vdv':
        return redirect(url_for('login'))
    
    try:
        vdv_id = user['id']
        tournaments = DangKyGiaiModel.get_by_vdv(vdv_id)
        if not any(t[1] == giai_id for t in tournaments):
            return "❌ Không có quyền", 403
        
        giai_raw = TournamentModel.get_details(giai_id)
        if not giai_raw:
            return "Không tìm thấy", 404
        
        registrations = DangKyGiaiModel.get_by_tournament(giai_id)
        giai_detail = prepare_tournament_detail(giai_raw, registrations)
        
        matches = MatchModel.get_all_by_tournament(giai_id)
        xep_hang = MatchModel.get_bang_xep_hang_by_matches(matches) if matches else []
        
        top_3_donate = []
        if giai_detail.get('nguoi_choi_list'):
            sorted_players = sorted(giai_detail['nguoi_choi_list'], key=lambda x: x['tien_dong'], reverse=True)
            top_3_donate = [(p['ten'], p['tien_dong']) for p in sorted_players[:3]]
        giai_detail['top_3_donate'] = top_3_donate
        giai_detail['bang_xep_hang'] = xep_hang
        giai_detail['matches'] = matches
        giai_detail['registrations'] = registrations
        giai_detail['user_role'] = 'vdv'

        # Build vong_dict for schedule display (same as admin route)
        vong_dict = {}
        for m in matches:
            vong = m[7] or 1
            if vong not in vong_dict:
                vong_dict[vong] = []
            vong_dict[vong].append({
                "id": m[0], "doi_a": m[1], "doi_b": m[2],
                "diem_a": m[3], "diem_b": m[4],
                "trang_thai": m[5], "san": m[6] or 1, "vong": vong
            })
        giai_detail['vong_dict'] = vong_dict

        # Get loai_dau
        try:
            conn2 = psycopg2.connect(**DB_CONFIG)
            cur2 = conn2.cursor()
            cur2.execute("SELECT loai_dau FROM giai_dau WHERE id = %s;", (giai_id,))
            r = cur2.fetchone()
            giai_detail['loai_dau'] = r[0] if r and r[0] else 'don'
            cur2.close()
            conn2.close()
        except Exception:
            giai_detail['loai_dau'] = 'don'
        
        DBLogger.log_request('GET', f'/giai-dau/{giai_id}/vdv', user.get('email'))
        return render_template('chi_tiet_giai_vdv.html', giai=giai_detail, registrations=registrations, enumerate=enumerate)
    except Exception as e:
        DBLogger.log_error(f"Error loading tournament: {str(e)}", user.get('email'), f'/giai-dau/{giai_id}/vdv', context=traceback.format_exc())
        return f"❌ Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)