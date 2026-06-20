from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from werkzeug.utils import secure_filename
import os
from models import TournamentModel, PlayerModel, MatchModel
from services import FinanceService, MatchSchedulerService
from knockout_logic import KnockoutLogic
from auth import AuthService, login_required, admin_required
from config import DB_CONFIG, FLASK_SECRET_KEY, get_logger, LogHelper
import psycopg2
import math

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY
logger = get_logger('pickleball.app')

# ============ ROUTES ============

@app.route('/')
@login_required
def trang_chu():
    """Trang chủ"""
    user = session.get('user', {})
    LogHelper.log_request('GET', '/', user.get('email'))
    
    if user.get('role') != 'admin':
        return redirect(url_for('vdv_dashboard'))
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        # ✅ FIX: Specify columns explicitly
        cursor.execute("""
            SELECT g.id, g.ten_giai_dau, g.so_luong_san, g.dia_diem, 
                   g.chi_phi_san_bai, g.chi_phi_nuoc_noi, g.chi_phi_giai_thuong, g.chi_phi_khac, 
                   g.ty_le_giai_1, g.ty_le_giai_2, g.ty_le_giai_3, g.so_nguoi_du_kien,
                   g.thoi_gian_bat_dau, g.banner_image, g.qr_image, 
                   COUNT(n.id) as so_luong_nguoi 
            FROM giai_dau g 
            LEFT JOIN nguoi_choi n ON g.id = n.giai_dau_id 
            GROUP BY g.id 
            ORDER BY g.id DESC;
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        LogHelper.log_success(f"Loaded {len(rows)} tournaments for admin {user.get('email')}")
        
        danh_sach_giai = []
        for row in rows:
            giai_raw = tuple(row[:15])
            players_raw = PlayerModel.get_all_by_tournament(row[0])
            giai_detail = FinanceService.tinh_toan_dong_tien(giai_raw, players_raw)
            danh_sach_giai.append(giai_detail)
        
        return render_template('index.html', danh_sach_giai=danh_sach_giai)
    
    except Exception as e:
        LogHelper.log_error(f"Error loading tournaments: {str(e)}", f"User: {user.get('email')}")
        return f"❌ Error: {str(e)}", 500

@app.route('/them-giai-dau', methods=['POST'])
def them_giai_dau():
    """Tạo giải mới"""
    try:
        LogHelper.log_request('POST', '/them-giai-dau')
        
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
            request.form.get('ty_le_giai_3', 2), request.form.get('so_nguoi_du_kien', 10)
        ))
        conn.commit()
        cursor.close()
        conn.close()
        
        LogHelper.log_success(f"Tournament created: {request.form['ten_giai_dau']}")
        return redirect('/')
    
    except Exception as e:
        LogHelper.log_error(f"Error creating tournament: {str(e)}")
        return f"❌ Error: {str(e)}", 500

@app.route('/xoa-giai-dau/<int:giai_id>')
@admin_required
def xoa_giai_dau(giai_id):
    """Xóa giải"""
    try:
        LogHelper.log_request('GET', f'/xoa-giai-dau/{giai_id}')
        
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM giai_dau WHERE id = %s;", (giai_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        LogHelper.log_success(f"Tournament {giai_id} deleted")
        return redirect('/')
    
    except Exception as e:
        LogHelper.log_error(f"Error deleting tournament {giai_id}: {str(e)}")
        return f"❌ Error: {str(e)}", 500

@app.route('/giai-dau/<int:giai_id>')
@login_required
def chi_tiet_giai(giai_id):
    """Chi tiết giải"""
    user = session.get('user', {})
    LogHelper.log_request('GET', f'/giai-dau/{giai_id}', user.get('email'))
    
    try:
        if user.get('role') == 'admin':
            pass
        elif user.get('role') == 'vdv':
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("SELECT giai_dau_id FROM nguoi_choi WHERE id = %s AND giai_dau_id = %s;",
                           (user.get('id'), giai_id))
            if not cursor.fetchone():
                cursor.close()
                conn.close()
                LogHelper.log_warning(f"VĐV {user.get('email')} unauthorized access to tournament {giai_id}")
                return "❌ Bạn không có quyền xem giải này", 403
            cursor.close()
            conn.close()
        else:
            return redirect(url_for('login'))
        
        giai_raw = TournamentModel.get_details(giai_id)
        if not giai_raw:
            LogHelper.log_warning(f"Tournament {giai_id} not found")
            return "Không tìm thấy giải!", 404
        
        players_raw = PlayerModel.get_all_by_tournament(giai_id)
        matches = MatchModel.get_all_by_tournament(giai_id)
        
        giai_detail = FinanceService.tinh_toan_dong_tien(giai_raw, players_raw)
        
        # ✅ Tính top 3 donate
        top_3_donate = []
        if giai_detail.get('nguoi_choi_list'):
            sorted_players = sorted(
                giai_detail['nguoi_choi_list'],
                key=lambda x: x['tien_dong'],
                reverse=True
            )
            top_3_donate = [(p['ten'], p['tien_dong']) for p in sorted_players[:3]]
        giai_detail['top_3_donate'] = top_3_donate
        
        # Bảng xếp hạng & matches
        xep_hang = MatchModel.get_bang_xep_hang_by_matches(matches) if matches else []
        giai_detail['bang_xep_hang'] = xep_hang
        giai_detail['matches'] = matches
        giai_detail['players'] = players_raw
        giai_detail['user_role'] = user.get('role')
        
        LogHelper.log_success(f"Tournament {giai_id} details loaded ({len(players_raw)} players, {len(matches)} matches)")
        
        return render_template('chi_tiet.html', giai=giai_detail, players=players_raw, 
                              matches=matches, xep_hang=xep_hang)
    
    except Exception as e:
        LogHelper.log_error(f"Error loading tournament {giai_id}: {str(e)}")
        return f"❌ Error: {str(e)}", 500

@app.route('/giai-dau/<int:giai_id>/chia-lich', methods=['POST'])
@admin_required
def auto_chia_lich(giai_id):
    """Tự sinh lịch"""
    try:
        logger.info(f"Generating schedule for tournament {giai_id}")
        
        loai_chia = request.form.get('loai_chia', 'vong_tron')
        
        players_raw = PlayerModel.get_all_by_tournament(giai_id)
        giai_raw = TournamentModel.get_details(giai_id)
        so_san = giai_raw[2] if giai_raw else 1
        
        MatchModel.delete_by_tournament(giai_id)
        
        if loai_chia == 'vong_tron':
            team_names = [p[2] for p in players_raw]
            matches = MatchSchedulerService.generate_round_robin(team_names, so_san)
            MatchModel.save_matches(giai_id, matches)
            LogHelper.log_success(f"Schedule generated for {giai_id}: {len(matches)} matches")
        
        return redirect(f'/giai-dau/{giai_id}')
    
    except Exception as e:
        LogHelper.log_error(f"Error generating schedule for {giai_id}: {str(e)}")
        return f"❌ Error: {str(e)}", 500

@app.route('/tran-dau/<int:tran_id>/cap-nhat-ty-so', methods=['POST'])
@admin_required
def cap_nhat_ty_so(tran_id):
    """Cập nhật tỷ số"""
    try:
        diem_a = request.form.get('diem_a')
        diem_b = request.form.get('diem_b')
        diem_a = int(diem_a) if diem_a else None
        diem_b = int(diem_b) if diem_b else None
        
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT giai_dau_id FROM tran_dau WHERE id = %s;", (tran_id,))
        result = cursor.fetchone()
        giai_id = result[0] if result else None
        
        MatchModel.update_score(tran_id, diem_a, diem_b)
        cursor.close()
        conn.close()
        
        LogHelper.log_success(f"Match {tran_id} score updated: {diem_a} vs {diem_b}")
        
        return redirect(f'/giai-dau/{giai_id}')
    
    except Exception as e:
        LogHelper.log_error(f"Error updating match {tran_id}: {str(e)}")
        return f"❌ Error: {str(e)}", 500

@app.route('/giai-dau/<int:giai_id>/them-nguoi-choi', methods=['POST'])
@admin_required
def them_nguoi_choi(giai_id):
    """Thêm người chơi"""
    try:
        LogHelper.log_request('POST', f'/giai-dau/{giai_id}/them-nguoi-choi')
        
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO nguoi_choi (giai_dau_id, ten_nguoi_choi, trinh_do, so_tien_da_dong, email, ghi_chu)
            VALUES (%s, %s, %s, %s, %s, %s);
        """, (
            giai_id, request.form['ten_nguoi_choi'], request.form['trinh_do'],
            request.form.get('so_tien_da_dong', 0),
            request.form.get('email', ''),
            request.form.get('ghi_chu', '')
        ))
        conn.commit()
        cursor.close()
        conn.close()
        
        LogHelper.log_success(f"Player added: {request.form['ten_nguoi_choi']} to tournament {giai_id}")
        return redirect(f'/giai-dau/{giai_id}')
    
    except Exception as e:
        LogHelper.log_error(f"Error adding player: {str(e)}")
        return f"❌ Error: {str(e)}", 500

@app.route('/giai-dau/<int:giai_id>/sua-nguoi-choi/<int:nguoi_id>', methods=['GET', 'POST'])
@admin_required
def sua_nguoi_choi(giai_id, nguoi_id):
    """Sửa người chơi"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        if request.method == 'GET':
            cursor.execute("SELECT * FROM nguoi_choi WHERE id = %s AND giai_dau_id = %s;",
                          (nguoi_id, giai_id))
            nguoi_choi = cursor.fetchone()
            cursor.close()
            conn.close()
            if not nguoi_choi:
                return "Không tìm thấy!", 404
            return render_template('sua_nguoi_choi.html', giai_id=giai_id, nguoi_choi=nguoi_choi)
        
        # POST
        cursor.execute("SELECT ten_nguoi_choi FROM nguoi_choi WHERE id = %s;", (nguoi_id,))
        old_name = cursor.fetchone()[0]
        new_name = request.form['ten_nguoi_choi']
        
        cursor.execute("""
            UPDATE nguoi_choi 
            SET ten_nguoi_choi=%s, trinh_do=%s, so_tien_da_dong=%s, ghi_chu=%s, email=%s
            WHERE id=%s;
        """, (new_name, request.form['trinh_do'], request.form.get('so_tien_da_dong', 0),
              request.form.get('ghi_chu', ''), request.form.get('email', ''), nguoi_id))
        
        if old_name != new_name:
            MatchModel.update_player_name_in_matches(giai_id, old_name, new_name)
            logger.info(f"Player name updated: {old_name} → {new_name}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        LogHelper.log_success(f"Player {nguoi_id} updated")
        return redirect(f'/giai-dau/{giai_id}')
    
    except Exception as e:
        LogHelper.log_error(f"Error updating player {nguoi_id}: {str(e)}")
        return f"❌ Error: {str(e)}", 500

@app.route('/xoa-nguoi-choi/<int:giai_id>/<int:nguoi_id>')
@admin_required
def xoa_nguoi_choi(giai_id, nguoi_id):
    """Xóa người chơi"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM nguoi_choi WHERE id = %s AND giai_dau_id = %s;",
                       (nguoi_id, giai_id))
        conn.commit()
        cursor.close()
        conn.close()
        
        LogHelper.log_success(f"Player {nguoi_id} deleted from tournament {giai_id}")
        return redirect(f'/giai-dau/{giai_id}')
    
    except Exception as e:
        LogHelper.log_error(f"Error deleting player {nguoi_id}: {str(e)}")
        return f"❌ Error: {str(e)}", 500

@app.route('/giai-dau/<int:giai_id>/get-email')
def get_email(giai_id):
    """Lấy email list"""
    try:
        players = PlayerModel.get_all_by_tournament(giai_id)
        emails = [p[6] for p in players if p[6]]
        email_list = '; '.join(emails)
        
        logger.debug(f"Email list requested for tournament {giai_id}: {len(emails)} emails")
        
        return jsonify({'emails': email_list, 'count': len(emails)})
    
    except Exception as e:
        LogHelper.log_error(f"Error getting emails for tournament {giai_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/giai-dau/<int:giai_id>/email-template')
def email_template(giai_id):
    """Email mẫu"""
    try:
        giai_raw = TournamentModel.get_details(giai_id)
        giai_name = giai_raw[1] if giai_raw else "Giải Pickleball"
        dia_diem = giai_raw[3] if giai_raw else "Chưa xác định"
        thoi_gian = giai_raw[12] if giai_raw else "Chưa xác định"
        
        template = f"""
Xin chào Anh/Chị,

Chào mừng Anh/Chị đến với giải đấu "{giai_name}", sẽ được tổ chức tại địa chỉ "{dia_diem}" vào lúc "{thoi_gian}".

Thông tin chi tiết giải đấu xem tại website: https://pickleball-m7wn.onrender.com/giai-dau/{giai_id}

Thông tin đăng nhập:
- Email: [email người chơi]
- Mật khẩu: 123456789 (mặc định)

Ban tổ chức rất mong Anh/Chị có mặt đầy đủ và đúng giờ để giải đấu được tổ chức thành công tốt đẹp.

Xin trân trọng cảm ơn.

Ban Tổ Chức
"""
        return render_template('email_template.html', template=template, giai_name=giai_name)
    
    except Exception as e:
        LogHelper.log_error(f"Error loading email template: {str(e)}")
        return f"❌ Error: {str(e)}", 500

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Đăng nhập"""
    try:
        if request.method == 'GET':
            return render_template('login.html')
        
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        
        LogHelper.log_request('POST', '/login', email)
        
        if role == 'admin':
            user, error = AuthService.login_admin(email, password)
        else:
            user, error = AuthService.login_vdv(email, password)
        
        if user:
            session['user'] = user
            LogHelper.log_success(f"User {email} ({role}) logged in")
            if user.get('role') == 'vdv':
                return redirect(url_for('vdv_dashboard'))
            else:
                return redirect(url_for('trang_chu'))
        
        LogHelper.log_warning(f"Login failed for {email}: {error}")
        return render_template('login.html', error=error)
    
    except Exception as e:
        LogHelper.log_error(f"Error during login: {str(e)}")
        return render_template('login.html', error="Lỗi hệ thống"), 500

@app.route('/dang-xuat')
def logout():
    """Đăng xuất"""
    email = session.get('user', {}).get('email')
    LogHelper.log_success(f"User {email} logged out")
    session.clear()
    return redirect(url_for('login'))

@app.route('/admin-settings')
@admin_required
def admin_settings():
    """Admin settings"""
    LogHelper.log_request('GET', '/admin-settings')
    return render_template('admin_settings.html')

@app.route('/tao-admin', methods=['POST'])
@admin_required
def tao_admin():
    """Tạo admin"""
    try:
        email = request.form.get('email')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        
        LogHelper.log_request('POST', '/tao-admin', email)
        
        if not email or not password:
            return render_template('admin_settings.html', error="Email và mật khẩu không được bỏ trống")
        
        if password != confirm:
            return render_template('admin_settings.html', error="Mật khẩu không khớp")
        
        if len(password) < 6:
            return render_template('admin_settings.html', error="Mật khẩu phải có ít nhất 6 ký tự")
        
        success, msg = AuthService.register_admin(email, password)
        
        if success:
            LogHelper.log_success(f"Admin account created: {email}")
            return render_template('admin_settings.html', success=msg)
        else:
            LogHelper.log_warning(f"Admin creation failed: {msg}")
            return render_template('admin_settings.html', error=msg)
    
    except Exception as e:
        LogHelper.log_error(f"Error creating admin: {str(e)}")
        return render_template('admin_settings.html', error=f"Error: {str(e)}")

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
        
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        # ✅ FIX: Get ALL tournaments for this VĐV (even if same email)
        cursor.execute("""
            SELECT DISTINCT g.id, 
                   g.ten_giai_dau, 
                   g.so_luong_san, 
                   g.dia_diem,
                   g.chi_phi_san_bai, 
                   g.chi_phi_nuoc_noi, 
                   g.chi_phi_giai_thuong, 
                   g.chi_phi_khac,
                   g.ty_le_giai_1, 
                   g.ty_le_giai_2, 
                   g.ty_le_giai_3, 
                   g.so_nguoi_du_kien,
                   g.thoi_gian_bat_dau, 
                   g.banner_image, 
                   g.qr_image
            FROM giai_dau g
            INNER JOIN nguoi_choi n ON g.id = n.giai_dau_id
            WHERE n.id = %s
            ORDER BY g.id DESC;
        """, (vdv_id,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        LogHelper.log_success(f"Loaded {len(rows)} tournaments for VĐV {user.get('email')} (ID: {vdv_id})")
        
        vdv_giai = []
        for row in rows:
            giai_raw = tuple(row[:15])
            players_raw = PlayerModel.get_all_by_tournament(row[0])
            giai_detail = FinanceService.tinh_toan_dong_tien(giai_raw, players_raw)
            vdv_giai.append(giai_detail)
        
        return render_template('vdv_dashboard.html', vdv_giai=vdv_giai)
    
    except Exception as e:
        LogHelper.log_error(f"Error loading VĐV dashboard: {str(e)}")
        return f"❌ Error: {str(e)}", 500

if __name__ == '__main__':
    logger.info("Starting Pickleball Tournament Manager")
    app.run(debug=False, host='0.0.0.0', port=5000)