"""
Complete App with Database Logging
All logs stored in app_logs table
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, g, send_from_directory, make_response
from models import VanDongVienModel, AdminUserModel, TournamentModel, DangKyGiaiModel, DoiBongModel, MatchModel
from services import FinanceService
from knockout_logic import MatchSchedulerService
from auth import AuthService, login_required, admin_required
from config import FLASK_SECRET_KEY, FLASK_SECRET_KEY_ERROR, BASE_URL, LOG_ALL_REQUESTS, SLOW_REQUEST_MS
from db import db_cursor
from logging_service import DBLogger, DBLogViewer
import traceback
import time
from datetime import date
from validators import (
    normalize_tournament_form,
    normalize_vdv_form,
    normalize_team_form,
    normalize_team_member_form,
    normalize_team_month_form,
    normalize_team_expense_form,
)
from werkzeug.exceptions import HTTPException

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY


@app.route('/service-worker.js')
def service_worker():
    response = make_response(send_from_directory(app.static_folder, 'service-worker.js'))
    response.headers['Content-Type'] = 'application/javascript'
    response.headers['Service-Worker-Allowed'] = '/'
    response.headers['Cache-Control'] = 'no-cache'
    return response


@app.route('/healthz')
def healthz():
    return "ok", 200


def _safe_request_details():
    """Return request details for logs without storing passwords/secrets."""
    details = {
        "args": request.args.to_dict(flat=False),
        "form": {},
        "json": None,
    }
    sensitive_keys = {"password", "confirm_password", "token", "secret", "db_password"}
    for key, value in request.form.items():
        details["form"][key] = "***" if key.lower() in sensitive_keys else value
    if request.is_json:
        payload = request.get_json(silent=True)
        if isinstance(payload, dict):
            details["json"] = {
                key: "***" if key.lower() in sensitive_keys else value
                for key, value in payload.items()
            }
    return details


@app.before_request
def capture_action_start():
    g.request_started_at = time.time()


@app.after_request
def log_user_action(response):
    duration_ms = int((time.time() - getattr(g, "request_started_at", time.time())) * 1000)
    skip_action_log = (
        request.endpoint == "static"
        or request.method == "HEAD"
        or request.path in ("/favicon.ico", "/healthz")
        or (
            not LOG_ALL_REQUESTS
            and request.method == "GET"
            and response.status_code < 400
            and duration_ms < SLOW_REQUEST_MS
        )
    )
    if not skip_action_log:
        user = session.get("user", {})
        details = _safe_request_details()
        details["duration_ms"] = duration_ms
        DBLogger.log_user_action(
            user_email=user.get("email") or request.form.get("email"),
            user_role=user.get("role") or request.form.get("role"),
            action=f"{request.method} {request.path}",
            route=request.path,
            endpoint=request.endpoint,
            method=request.method,
            status_code=response.status_code,
            ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
            user_agent=request.headers.get("User-Agent"),
            details=details,
        )
    return response


@app.errorhandler(Exception)
def log_unhandled_exception(error):
    if isinstance(error, HTTPException):
        return error

    user = session.get("user", {})
    DBLogger.log_exception(
        f"Unhandled exception: {str(error)}",
        error,
        user_email=user.get("email") or request.form.get("email"),
        route=request.path,
        method=request.method,
        status_code=500,
        context=traceback.format_exc(),
        request_path=request.path,
        ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
        user_agent=request.headers.get("User-Agent"),
    )
    return "❌ Lỗi hệ thống", 500


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


def _giai_tuple_from_form(giai_id, form_data):
    return (
        giai_id,
        form_data.get('ten_giai_dau'),
        form_data.get('so_luong_san'),
        form_data.get('dia_diem'),
        form_data.get('chi_phi_san_bai'),
        form_data.get('chi_phi_nuoc_noi'),
        form_data.get('chi_phi_giai_thuong'),
        form_data.get('chi_phi_khac'),
        form_data.get('ty_le_giai_1'),
        form_data.get('ty_le_giai_2'),
        form_data.get('ty_le_giai_3'),
        form_data.get('so_nguoi_du_kien'),
        form_data.get('thoi_gian_bat_dau'),
        None,
        None,
        form_data.get('loai_dau'),
        form_data.get('diem_cham'),
        form_data.get('diem_toi_da'),
    )


@app.route('/doc-diem-giao-luu')
@login_required
def doc_diem_giao_luu():
    """Trang doc diem giao luu, chi luu tam tren trinh duyet."""
    user = session.get('user', {})
    DBLogger.log_request('GET', '/doc-diem-giao-luu', user.get('email'))
    return render_template('doc_diem_giao_luu.html', user=user)

# ============ ADMIN ROUTES ============

@app.route('/')
@login_required
def trang_chu():
    user = session.get('user', {})
    DBLogger.log_request('GET', '/', user.get('email'))

    if user.get('role') != 'admin':
        return redirect(url_for('vdv_dashboard'))

    return render_template('chon_cau_phan.html')


@app.route('/giai-dau')
@login_required
def quan_ly_giai_dau():
    """Trang chủ admin"""
    user = session.get('user', {})
    DBLogger.log_request('GET', '/giai-dau', user.get('email'))
    
    if user.get('role') != 'admin':
        return redirect(url_for('vdv_dashboard'))
    
    try:
        scope_admin_id = _admin_scope_id(user)
        with db_cursor() as cursor:
            if scope_admin_id:
                cursor.execute("""
                    SELECT g.id, g.ten_giai_dau, g.so_luong_san, g.dia_diem,
                           g.chi_phi_san_bai, g.chi_phi_nuoc_noi, g.chi_phi_giai_thuong, g.chi_phi_khac,
                           g.ty_le_giai_1, g.ty_le_giai_2, g.ty_le_giai_3, g.so_nguoi_du_kien,
                           g.thoi_gian_bat_dau, g.banner_image, g.qr_image,
                           COUNT(dkg.id) as so_luong_nguoi
                    FROM giai_dau g
                    LEFT JOIN dang_ky_giai dkg ON g.id = dkg.giai_dau_id
                    LEFT JOIN giai_dau_admin_quyen q ON g.id = q.giai_dau_id AND q.admin_id = %s
                    WHERE g.owner_admin_id = %s OR q.admin_id IS NOT NULL
                    GROUP BY g.id
                    ORDER BY g.id DESC;
                """, (scope_admin_id, scope_admin_id))
            else:
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
        
        danh_sach_giai = []
        registrations_by_tournament = DangKyGiaiModel.get_by_tournaments([row[0] for row in rows])
        for row in rows:
            try:
                giai_raw = tuple(row[:15])
                registrations = registrations_by_tournament.get(row[0], [])
                giai_detail = prepare_tournament_detail(giai_raw, registrations)
                danh_sach_giai.append(giai_detail)
            except Exception as e:
                error_msg = f"Error loading tournament {row[0]}: {str(e)}"
                DBLogger.log_error(error_msg, user.get('email'), '/giai-dau', context=traceback.format_exc())
                continue
        
        return render_template('index.html', danh_sach_giai=danh_sach_giai)
    except Exception as e:
        DBLogger.log_error(f"Error loading tournaments: {str(e)}", user.get('email'), '/giai-dau', context=traceback.format_exc())
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
            return render_template('them_van_dong_vien.html', form_data={}, errors=[])

        form_data, errors = normalize_vdv_form(request.form)
        if not errors and VanDongVienModel.email_exists(form_data['email']):
            errors.append("Email đã được dùng cho VĐV khác.")
        if errors:
            return render_template('them_van_dong_vien.html', form_data=form_data, errors=errors), 400

        ten_vdv = form_data['ten_vdv']
        trinh_do = form_data['trinh_do']
        email = form_data['email']
        ghi_chu = form_data['ghi_chu']

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
            return render_template('sua_van_dong_vien.html', vdv=vdv, errors=[])

        vdv = VanDongVienModel.get_by_id(vdv_id)
        if not vdv:
            return "Không tìm thấy", 404

        form_data, errors = normalize_vdv_form(request.form)
        if not errors and VanDongVienModel.email_exists(form_data['email'], exclude_id=vdv_id):
            errors.append("Email đã được dùng cho VĐV khác.")
        if errors:
            vdv_form = (vdv_id, form_data['ten_vdv'], form_data['trinh_do'], form_data['email'], None, form_data['ghi_chu'])
            return render_template('sua_van_dong_vien.html', vdv=vdv_form, errors=errors), 400

        ten_vdv = form_data['ten_vdv']
        trinh_do = form_data['trinh_do']
        email = form_data['email']
        ghi_chu = form_data['ghi_chu']

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

# ============ TEAM MANAGEMENT ============

def _current_month():
    return date.today().strftime('%Y-%m')


def _money_from_form(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0


def _get_team_for_admin_or_403(doi_bong_id, user):
    doi_bong = DoiBongModel.get_by_id(doi_bong_id, _admin_scope_id(user))
    if not doi_bong:
        return None
    return doi_bong


def _get_tournament_for_admin_or_403(giai_id, user):
    giai = TournamentModel.get_details(giai_id, _admin_scope_id(user))
    if not giai:
        return None
    return giai


def _is_super_admin(user=None):
    user = user or session.get('user', {})
    return (user.get('email') or '').strip().lower() == 'admin@pickleball'


def _admin_scope_id(user=None):
    user = user or session.get('user', {})
    if _is_super_admin(user):
        return None
    return user.get('id')


def _require_super_admin():
    if not _is_super_admin():
        return "Khong co quyen quan ly tai khoan admin", 403
    return None


@app.route('/doi-bong')
@admin_required
def doi_bong_list():
    user = session.get('user', {})
    try:
        doi_bong_list = DoiBongModel.get_all(_admin_scope_id(user))
        DBLogger.log_request('GET', '/doi-bong', user.get('email'))
        return render_template('doi_bong.html', doi_bong_list=doi_bong_list)
    except Exception as e:
        DBLogger.log_error(f"Error loading teams: {str(e)}", user.get('email'), '/doi-bong', context=traceback.format_exc())
        return f"Error: {str(e)}", 500


@app.route('/doi-bong/them', methods=['POST'])
@admin_required
def them_doi_bong():
    user = session.get('user', {})
    try:
        form_data, errors = normalize_team_form(request.form)
        if errors:
            doi_bong_list = DoiBongModel.get_all(_admin_scope_id(user))
            return render_template('doi_bong.html', doi_bong_list=doi_bong_list, errors=errors, form_data=form_data), 400

        doi_bong_id = DoiBongModel.create(form_data['ten_doi'], form_data['mo_ta'], user.get('id'))
        DBLogger.log_success(f"Team created: {form_data['ten_doi']}", user.get('email'), '/doi-bong/them')
        return redirect(f'/doi-bong/{doi_bong_id}')
    except Exception as e:
        DBLogger.log_error(f"Error creating team: {str(e)}", user.get('email'), '/doi-bong/them', context=traceback.format_exc())
        return f"Error: {str(e)}", 500


@app.route('/doi-bong/<int:doi_bong_id>/sua', methods=['GET', 'POST'])
@admin_required
def sua_doi_bong(doi_bong_id):
    user = session.get('user', {})
    try:
        doi_bong = _get_team_for_admin_or_403(doi_bong_id, user)
        if not doi_bong:
            return "Không tìm thấy đội bóng", 404
        if request.method == 'GET':
            return render_template('sua_doi_bong.html', doi_bong=doi_bong, errors=[])

        form_data, errors = normalize_team_form(request.form)
        if errors:
            doi_bong_form = (doi_bong_id, form_data['ten_doi'], form_data['mo_ta'])
            return render_template('sua_doi_bong.html', doi_bong=doi_bong_form, errors=errors), 400

        DoiBongModel.update(doi_bong_id, form_data['ten_doi'], form_data['mo_ta'])
        DBLogger.log_success(f"Team updated: {form_data['ten_doi']}", user.get('email'), f'/doi-bong/{doi_bong_id}/sua')
        return redirect('/doi-bong')
    except Exception as e:
        DBLogger.log_error(f"Error updating team: {str(e)}", user.get('email'), f'/doi-bong/{doi_bong_id}/sua', context=traceback.format_exc())
        return f"Error: {str(e)}", 500


@app.route('/doi-bong/<int:doi_bong_id>/xoa')
@admin_required
def xoa_doi_bong(doi_bong_id):
    user = session.get('user', {})
    try:
        if not _get_team_for_admin_or_403(doi_bong_id, user):
            return "Không có quyền xóa đội bóng này", 403
        DoiBongModel.delete(doi_bong_id)
        DBLogger.log_success(f"Team deleted: {doi_bong_id}", user.get('email'), f'/doi-bong/{doi_bong_id}/xoa')
        return redirect('/doi-bong')
    except Exception as e:
        DBLogger.log_error(f"Error deleting team: {str(e)}", user.get('email'), f'/doi-bong/{doi_bong_id}/xoa', context=traceback.format_exc())
        return f"Error: {str(e)}", 500


@app.route('/doi-bong/<int:doi_bong_id>')
@admin_required
def chi_tiet_doi_bong(doi_bong_id):
    user = session.get('user', {})
    try:
        doi_bong = _get_team_for_admin_or_403(doi_bong_id, user)
        if not doi_bong:
            return "Không tìm thấy đội bóng", 404

        selected_month = request.args.get('thang') or _current_month()
        selected_month_date = DoiBongModel.normalize_month(selected_month)
        month_config = DoiBongModel.get_month_config(doi_bong_id, selected_month_date)
        members = DoiBongModel.get_members_with_payments(doi_bong_id, selected_month_date)
        expenses = DoiBongModel.get_expenses(doi_bong_id, selected_month_date)
        finance = FinanceService.tinh_toan_quy_doi_bong(month_config, members, expenses)
        available_months = DoiBongModel.get_available_months(doi_bong_id)
        if selected_month[:7] not in available_months:
            available_months.insert(0, selected_month[:7])
        registered_vdv_ids = {member[1] for member in members if member[1]}
        all_vdv = [vdv for vdv in VanDongVienModel.get_all() if vdv[0] not in registered_vdv_ids]
        permissions = DoiBongModel.get_permissions(doi_bong_id)
        permission_admin_ids = {permission[1] for permission in permissions}
        owner_admin_id = doi_bong[3]
        admins = [
            admin for admin in AdminUserModel.get_all()
            if admin[0] != owner_admin_id and admin[0] != user.get('id') and admin[0] not in permission_admin_ids
        ]
        is_owner = _is_super_admin(user) or doi_bong[3] in (None, user.get('id'))

        DBLogger.log_request('GET', f'/doi-bong/{doi_bong_id}', user.get('email'))
        return render_template(
            'chi_tiet_doi_bong.html',
            doi_bong=doi_bong,
            finance=finance,
            selected_month=selected_month[:7],
            available_months=available_months,
            all_vdv=all_vdv,
            admins=admins,
            permissions=permissions,
            can_edit=True,
            is_owner=is_owner,
        )
    except Exception as e:
        DBLogger.log_error(f"Error loading team detail: {str(e)}", user.get('email'), f'/doi-bong/{doi_bong_id}', context=traceback.format_exc())
        return f"Error: {str(e)}", 500


@app.route('/doi-bong/<int:doi_bong_id>/cap-nhat-quy', methods=['POST'])
@admin_required
def cap_nhat_quy_doi_bong(doi_bong_id):
    user = session.get('user', {})
    selected_month = request.form.get('thang') or _current_month()
    try:
        if not _get_team_for_admin_or_403(doi_bong_id, user):
            return "Không có quyền cập nhật đội bóng này", 403
        form_data, errors = normalize_team_month_form(request.form)
        if not errors:
            DoiBongModel.upsert_month_config(
                doi_bong_id,
                selected_month,
                form_data['muc_phi_thang'],
                form_data['chi_phi_san_bai'],
                form_data['tien_san_con_lai_thang_truoc'],
                form_data['ghi_chu'],
            )
            DBLogger.log_success(f"Team month fund updated: {doi_bong_id} {selected_month}", user.get('email'), f'/doi-bong/{doi_bong_id}/cap-nhat-quy')
        return redirect(f'/doi-bong/{doi_bong_id}?thang={selected_month}')
    except Exception as e:
        DBLogger.log_error(f"Error updating team month fund: {str(e)}", user.get('email'), f'/doi-bong/{doi_bong_id}/cap-nhat-quy', context=traceback.format_exc())
        return f"Error: {str(e)}", 500


@app.route('/doi-bong/<int:doi_bong_id>/thanh-vien/them', methods=['POST'])
@admin_required
def them_thanh_vien_doi_bong(doi_bong_id):
    user = session.get('user', {})
    selected_month = request.form.get('thang') or _current_month()
    try:
        if not _get_team_for_admin_or_403(doi_bong_id, user):
            return "Không có quyền cập nhật đội bóng này", 403
        van_dong_vien_ids = request.form.getlist('van_dong_vien_ids')
        loai_thanh_vien = request.form.get('loai_thanh_vien', 'co_dinh')
        ghi_chu = (request.form.get('ghi_chu') or '').strip()
        added_count = 0
        for van_dong_vien_id in van_dong_vien_ids:
            form_data, errors = normalize_team_member_form({
                'van_dong_vien_id': van_dong_vien_id,
                'loai_thanh_vien': loai_thanh_vien,
                'ghi_chu': ghi_chu,
            })
            if not errors:
                added_id = DoiBongModel.add_member(
                    doi_bong_id,
                    form_data['van_dong_vien_id'],
                    form_data['loai_thanh_vien'],
                    form_data['ghi_chu'],
                )
                if added_id:
                    added_count += 1
        DBLogger.log_success(f"Team members added: {added_count}", user.get('email'), f'/doi-bong/{doi_bong_id}/thanh-vien/them')
        return redirect(f'/doi-bong/{doi_bong_id}?thang={selected_month}')
    except Exception as e:
        DBLogger.log_error(f"Error adding team member: {str(e)}", user.get('email'), f'/doi-bong/{doi_bong_id}/thanh-vien/them', context=traceback.format_exc())
        return f"Error: {str(e)}", 500


@app.route('/doi-bong/<int:doi_bong_id>/thanh-vien/<int:thanh_vien_id>/sua', methods=['POST'])
@admin_required
def sua_thanh_vien_doi_bong(doi_bong_id, thanh_vien_id):
    user = session.get('user', {})
    selected_month = request.form.get('thang') or _current_month()
    try:
        if not _get_team_for_admin_or_403(doi_bong_id, user):
            return "Không có quyền cập nhật đội bóng này", 403
        form_data, errors = normalize_team_member_form(request.form)
        if not errors:
            DoiBongModel.update_member(
                doi_bong_id,
                thanh_vien_id,
                form_data['loai_thanh_vien'],
                form_data['ghi_chu'],
            )
            DBLogger.log_success(f"Team member updated: {thanh_vien_id}", user.get('email'), f'/doi-bong/{doi_bong_id}/thanh-vien/{thanh_vien_id}/sua')
        return redirect(f'/doi-bong/{doi_bong_id}?thang={selected_month}')
    except Exception as e:
        DBLogger.log_error(f"Error updating team member: {str(e)}", user.get('email'), f'/doi-bong/{doi_bong_id}/thanh-vien/{thanh_vien_id}/sua', context=traceback.format_exc())
        return f"Error: {str(e)}", 500


@app.route('/doi-bong/<int:doi_bong_id>/thanh-vien/<int:thanh_vien_id>/xoa')
@admin_required
def xoa_thanh_vien_doi_bong(doi_bong_id, thanh_vien_id):
    user = session.get('user', {})
    selected_month = request.args.get('thang') or _current_month()
    try:
        if not _get_team_for_admin_or_403(doi_bong_id, user):
            return "Không có quyền cập nhật đội bóng này", 403
        DoiBongModel.delete_member(doi_bong_id, thanh_vien_id)
        DBLogger.log_success(f"Team member deleted: {thanh_vien_id}", user.get('email'), f'/doi-bong/{doi_bong_id}/thanh-vien/{thanh_vien_id}/xoa')
        return redirect(f'/doi-bong/{doi_bong_id}?thang={selected_month}')
    except Exception as e:
        DBLogger.log_error(f"Error deleting team member: {str(e)}", user.get('email'), f'/doi-bong/{doi_bong_id}/thanh-vien/{thanh_vien_id}/xoa', context=traceback.format_exc())
        return f"Error: {str(e)}", 500


@app.route('/doi-bong/<int:doi_bong_id>/khoan-chi/them', methods=['POST'])
@admin_required
def them_khoan_chi_doi_bong(doi_bong_id):
    user = session.get('user', {})
    selected_month = request.form.get('thang') or _current_month()
    try:
        if not _get_team_for_admin_or_403(doi_bong_id, user):
            return "Không có quyền cập nhật đội bóng này", 403
        form_data, errors = normalize_team_expense_form(request.form)
        if not errors:
            DoiBongModel.add_expense(
                doi_bong_id,
                selected_month,
                form_data['ngay_chi'],
                form_data['noi_dung'],
                form_data['so_tien'],
                form_data['ghi_chu'],
            )
            DBLogger.log_success(f"Team expense added: {doi_bong_id}", user.get('email'), f'/doi-bong/{doi_bong_id}/khoan-chi/them')
        return redirect(f'/doi-bong/{doi_bong_id}?thang={selected_month}')
    except Exception as e:
        DBLogger.log_error(f"Error adding team expense: {str(e)}", user.get('email'), f'/doi-bong/{doi_bong_id}/khoan-chi/them', context=traceback.format_exc())
        return f"Error: {str(e)}", 500


@app.route('/doi-bong/<int:doi_bong_id>/khoan-chi/<int:expense_id>/xoa')
@admin_required
def xoa_khoan_chi_doi_bong(doi_bong_id, expense_id):
    user = session.get('user', {})
    selected_month = request.args.get('thang') or _current_month()
    try:
        if not _get_team_for_admin_or_403(doi_bong_id, user):
            return "Không có quyền cập nhật đội bóng này", 403
        DoiBongModel.delete_expense(doi_bong_id, expense_id)
        DBLogger.log_success(f"Team expense deleted: {expense_id}", user.get('email'), f'/doi-bong/{doi_bong_id}/khoan-chi/{expense_id}/xoa')
        return redirect(f'/doi-bong/{doi_bong_id}?thang={selected_month}')
    except Exception as e:
        DBLogger.log_error(f"Error deleting team expense: {str(e)}", user.get('email'), f'/doi-bong/{doi_bong_id}/khoan-chi/{expense_id}/xoa', context=traceback.format_exc())
        return f"Error: {str(e)}", 500


@app.route('/doi-bong/<int:doi_bong_id>/phan-quyen/them', methods=['POST'])
@admin_required
def them_quyen_doi_bong(doi_bong_id):
    user = session.get('user', {})
    try:
        doi_bong = DoiBongModel.get_by_id(doi_bong_id, _admin_scope_id(user))
        if not doi_bong or (not _is_super_admin(user) and doi_bong[3] not in (None, user.get('id'))):
            return "Không có quyền phân quyền đội bóng này", 403
        admin_id = request.form.get('admin_id')
        if admin_id:
            DoiBongModel.add_permission(doi_bong_id, admin_id)
        return redirect(f'/doi-bong/{doi_bong_id}')
    except Exception as e:
        DBLogger.log_error(f"Error adding team permission: {str(e)}", user.get('email'), f'/doi-bong/{doi_bong_id}/phan-quyen/them', context=traceback.format_exc())
        return f"Error: {str(e)}", 500


@app.route('/doi-bong/<int:doi_bong_id>/phan-quyen/<int:permission_id>/xoa')
@admin_required
def xoa_quyen_doi_bong(doi_bong_id, permission_id):
    user = session.get('user', {})
    try:
        doi_bong = DoiBongModel.get_by_id(doi_bong_id, _admin_scope_id(user))
        if not doi_bong or (not _is_super_admin(user) and doi_bong[3] not in (None, user.get('id'))):
            return "Không có quyền phân quyền đội bóng này", 403
        DoiBongModel.remove_permission(doi_bong_id, permission_id)
        return redirect(f'/doi-bong/{doi_bong_id}')
    except Exception as e:
        DBLogger.log_error(f"Error removing team permission: {str(e)}", user.get('email'), f'/doi-bong/{doi_bong_id}/phan-quyen/{permission_id}/xoa', context=traceback.format_exc())
        return f"Error: {str(e)}", 500


@app.route('/doi-bong/<int:doi_bong_id>/cap-nhat-dong-phi', methods=['POST'])
@admin_required
def cap_nhat_dong_phi_doi_bong(doi_bong_id):
    user = session.get('user', {})
    selected_month = request.form.get('thang') or _current_month()
    try:
        if not _get_team_for_admin_or_403(doi_bong_id, user):
            return "Không có quyền cập nhật đội bóng này", 403
        members = DoiBongModel.get_members_with_payments(doi_bong_id, selected_month)
        updates = []
        for member in members:
            member_id = member[0]
            so_tien = _money_from_form(request.form.get(f'tien_{member_id}', 0))
            trang_thai = request.form.get(f'trang_thai_{member_id}', 'Chưa đóng')
            ghi_chu = (request.form.get(f'ghi_chu_phi_{member_id}') or '').strip()
            updates.append((member_id, so_tien, trang_thai, ghi_chu))
        updated = DoiBongModel.update_payments(selected_month, updates)
        DBLogger.log_success(f"Team fee updated: {updated} records for team {doi_bong_id}", user.get('email'), f'/doi-bong/{doi_bong_id}/cap-nhat-dong-phi')
        return redirect(f'/doi-bong/{doi_bong_id}?thang={selected_month}')
    except Exception as e:
        DBLogger.log_error(f"Error updating team fees: {str(e)}", user.get('email'), f'/doi-bong/{doi_bong_id}/cap-nhat-dong-phi', context=traceback.format_exc())
        return f"Error: {str(e)}", 500


# ============ TOURNAMENT MANAGEMENT ============

@app.route('/them-giai-dau', methods=['POST'])
@admin_required
def them_giai_dau():
    """Tạo giải mới - ENSURE loai_dau is saved"""
    user = session.get('user', {})
    try:
        form_data, errors = normalize_tournament_form(request.form)
        if errors:
            return render_template('them_giai_dau.html', form_data=form_data, errors=errors), 400

        loai_dau = form_data['loai_dau']
        DBLogger.log_info(f"Creating tournament with loai_dau={loai_dau}", user.get('email'), '/them-giai-dau')
        
        with db_cursor(commit=True) as cursor:
            cursor.execute("""
                INSERT INTO giai_dau
                    (ten_giai_dau, so_luong_san, dia_diem,
                     chi_phi_san_bai, chi_phi_nuoc_noi, chi_phi_giai_thuong, chi_phi_khac,
                     ty_le_giai_1, ty_le_giai_2, ty_le_giai_3, so_nguoi_du_kien, thoi_gian_bat_dau, loai_dau,
                     owner_admin_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                form_data['ten_giai_dau'],
                form_data['so_luong_san'],
                form_data['dia_diem'],
                form_data['chi_phi_san_bai'],
                form_data['chi_phi_nuoc_noi'],
                form_data['chi_phi_giai_thuong'],
                form_data['chi_phi_khac'],
                form_data['ty_le_giai_1'],
                form_data['ty_le_giai_2'],
                form_data['ty_le_giai_3'],
                form_data['so_nguoi_du_kien'],
                form_data['thoi_gian_bat_dau'],
                loai_dau,
                user.get('id')
            ))
        DBLogger.log_success(f"Tournament created: {form_data['ten_giai_dau']} ({loai_dau})", user.get('email'), '/them-giai-dau')
        return redirect('/giai-dau')
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
            TournamentModel.ensure_score_rule_columns()
            giai_raw = _get_tournament_for_admin_or_403(giai_id, user)
            if not giai_raw:
                return "Không tìm thấy", 404
            return render_template('sua_giai.html', giai=giai_raw)
        
        TournamentModel.ensure_score_rule_columns()
        if not _get_tournament_for_admin_or_403(giai_id, user):
            return "Khong co quyen sua giai dau nay", 403
        form_data, errors = normalize_tournament_form(request.form)
        if errors:
            return render_template('sua_giai.html', giai=_giai_tuple_from_form(giai_id, form_data), errors=errors), 400

        loai_dau = form_data['loai_dau']
        diem_cham = form_data['diem_cham']
        diem_toi_da = form_data['diem_toi_da']
        DBLogger.log_info(f"Updating tournament {giai_id} with loai_dau={loai_dau}", user.get('email'), f'/sua-giai-dau/{giai_id}')
        
        with db_cursor(commit=True) as cursor:
            cursor.execute("""
                UPDATE giai_dau SET
                    ten_giai_dau=%s, so_luong_san=%s, dia_diem=%s,
                    chi_phi_san_bai=%s, chi_phi_nuoc_noi=%s,
                    chi_phi_giai_thuong=%s, chi_phi_khac=%s,
                    ty_le_giai_1=%s, ty_le_giai_2=%s, ty_le_giai_3=%s,
                    so_nguoi_du_kien=%s, thoi_gian_bat_dau=%s, loai_dau=%s,
                    diem_cham=%s, diem_toi_da=%s
                WHERE id=%s;
            """, (
                form_data['ten_giai_dau'],
                form_data['so_luong_san'],
                form_data['dia_diem'],
                form_data['chi_phi_san_bai'],
                form_data['chi_phi_nuoc_noi'],
                form_data['chi_phi_giai_thuong'],
                form_data['chi_phi_khac'],
                form_data['ty_le_giai_1'],
                form_data['ty_le_giai_2'],
                form_data['ty_le_giai_3'],
                form_data['so_nguoi_du_kien'],
                form_data['thoi_gian_bat_dau'],
                loai_dau,
                diem_cham,
                diem_toi_da,
                giai_id
            ))
        DBLogger.log_success(f"Tournament {giai_id} updated ({loai_dau})", user.get('email'), f'/sua-giai-dau/{giai_id}')
        return redirect('/giai-dau')
    except Exception as e:
        DBLogger.log_error(f"Error updating tournament: {str(e)}", user.get('email'), f'/sua-giai-dau/{giai_id}', context=traceback.format_exc())
        return f"❌ Error: {str(e)}", 500

@app.route('/xoa-giai-dau/<int:giai_id>')
@admin_required
def xoa_giai_dau(giai_id):
    """Xóa giải"""
    user = session.get('user', {})
    try:
        giai_raw = _get_tournament_for_admin_or_403(giai_id, user)
        if not giai_raw:
            return "Khong co quyen xoa giai dau nay", 403
        with db_cursor(commit=True) as cursor:
            cursor.execute("DELETE FROM giai_dau WHERE id = %s;", (giai_id,))
        DBLogger.log_success(f"Tournament {giai_id} deleted", user.get('email'), f'/xoa-giai-dau/{giai_id}')
        return redirect('/giai-dau')
    except Exception as e:
        DBLogger.log_error(f"Error deleting tournament: {str(e)}", user.get('email'), f'/xoa-giai-dau/{giai_id}', context=traceback.format_exc())
        return f"❌ Error: {str(e)}", 500

@app.route('/giai-dau/<int:giai_id>/admin')
@admin_required
def chi_tiet_giai_admin(giai_id):
    """Chi tiết giải (ADMIN) - FIXED VERSION"""
    user = session.get('user', {})
    try:
        giai_raw = _get_tournament_for_admin_or_403(giai_id, user)
        if not giai_raw:
            return "Không có quyền xem giải đấu này", 403
        
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
        giai_detail['loai_dau'] = giai_raw[15] if len(giai_raw) > 15 and giai_raw[15] else 'don'
        giai_detail['diem_cham'] = int(giai_raw[16] if len(giai_raw) > 16 and giai_raw[16] else 11)
        giai_detail['diem_toi_da'] = int(giai_raw[17] if len(giai_raw) > 17 and giai_raw[17] else 15)
        giai_detail['owner_admin_id'] = giai_raw[21] if len(giai_raw) > 21 else None

        # Build vong_dict: { vong_number: [match_dict, ...] } for the template
        vong_dict = {}
        for m in matches:
            vong = m[7] or 1
            if vong not in vong_dict:
                vong_dict[vong] = []
            vong_dict[vong].append({
                "id": m[0], "doi_a": m[1], "doi_b": m[2],
                "diem_a": m[3], "diem_b": m[4],
                "trang_thai": m[5], "san": m[6] or 1, "vong": vong,
                "thu_tu_danh": m[8] if len(m) > 8 and m[8] else 2,
                "doi_dang_giao": m[9] if len(m) > 9 and m[9] else 'A'
            })
        giai_detail['vong_dict'] = vong_dict
        
        canh_bao = None
        if request.args.get('error') == 'full':
            canh_bao = "⚠️ Giải đã đủ số người dự kiến, không thể thêm VĐV nữa. Hãy tăng 'Số người dự kiến' trong phần Sửa giải nếu muốn nhận thêm."
        elif request.args.get('error') == 'prize_over':
            canh_bao = "Tổng tiền thưởng nhập tay không được vượt quá quỹ thưởng thực tế."

        DBLogger.log_request('GET', f'/giai-dau/{giai_id}/admin', user.get('email'))
        permissions = TournamentModel.get_permissions(giai_id)
        permission_admin_ids = {permission[1] for permission in permissions}
        owner_admin_id = giai_detail.get('owner_admin_id')
        admins = [
            admin for admin in AdminUserModel.get_all()
            if admin[0] != owner_admin_id and admin[0] != user.get('id') and admin[0] not in permission_admin_ids
        ]
        is_owner = _is_super_admin(user) or owner_admin_id in (None, user.get('id'))

        return render_template(
            'chi_tiet_giai_admin.html',
            giai=giai_detail,
            registrations=registrations,
            canh_bao=canh_bao,
            enumerate=enumerate,
            base_url=BASE_URL,
            admins=admins,
            permissions=permissions,
            is_owner=is_owner,
        )
    except Exception as e:
        DBLogger.log_error(f"Error loading tournament: {str(e)}", user.get('email'), f'/giai-dau/{giai_id}/admin', context=traceback.format_exc())
        return f"❌ Error: {str(e)}", 500

@app.route('/giai-dau/<int:giai_id>/dang-ky', methods=['POST'])
@admin_required
def dang_ky_vdv(giai_id):
    """Đăng ký VĐV"""
    user = session.get('user', {})
    try:
        van_dong_vien_ids = request.form.getlist('van_dong_vien_ids')
        if not van_dong_vien_ids and request.form.get('van_dong_vien_id'):
            van_dong_vien_ids = [request.form.get('van_dong_vien_id')]

        giai_raw = _get_tournament_for_admin_or_403(giai_id, user)
        if not giai_raw:
            return "Khong co quyen cap nhat giai dau nay", 403
        so_nguoi_du_kien = giai_raw[11] if giai_raw and giai_raw[11] else 0
        registrations = DangKyGiaiModel.get_by_tournament(giai_id)

        registered_ids = {str(reg[1]) for reg in registrations}
        van_dong_vien_ids = [vdv_id for vdv_id in van_dong_vien_ids if vdv_id and vdv_id not in registered_ids]

        if not van_dong_vien_ids:
            return redirect(f'/giai-dau/{giai_id}/admin')

        if so_nguoi_du_kien and len(registrations) >= so_nguoi_du_kien:
            DBLogger.log_warning(
                f"Registration rejected: tournament {giai_id} already full ({len(registrations)}/{so_nguoi_du_kien})",
                user.get('email'), f'/giai-dau/{giai_id}/dang-ky'
            )
            return redirect(f'/giai-dau/{giai_id}/admin?error=full')

        selected_count = len(van_dong_vien_ids)
        if so_nguoi_du_kien:
            slots_left = max(so_nguoi_du_kien - len(registrations), 0)
            van_dong_vien_ids = van_dong_vien_ids[:slots_left]

        if not van_dong_vien_ids:
            return redirect(f'/giai-dau/{giai_id}/admin?error=full')

        added_count = DangKyGiaiModel.register_many(van_dong_vien_ids, giai_id)

        DBLogger.log_success(f"{added_count} VĐV registered for tournament {giai_id}", user.get('email'), f'/giai-dau/{giai_id}/dang-ky')
        suffix = '?error=full' if added_count < selected_count else ''
        return redirect(f'/giai-dau/{giai_id}/admin{suffix}')
    except Exception as e:
        DBLogger.log_error(f"Error registering VĐV: {str(e)}", user.get('email'), f'/giai-dau/{giai_id}/dang-ky', context=traceback.format_exc())
        return f"❌ Error: {str(e)}", 500

@app.route('/dang-ky-giai/<int:dang_ky_id>/xoa')
@admin_required
def xoa_dang_ky(dang_ky_id):
    """Xóa đăng ký"""
    user = session.get('user', {})
    try:
        with db_cursor() as cursor:
            cursor.execute("SELECT giai_dau_id FROM dang_ky_giai WHERE id = %s;", (dang_ky_id,))
            result = cursor.fetchone()
        giai_id = result[0] if result else None
        if not giai_id or not _get_tournament_for_admin_or_403(giai_id, user):
            return "Khong co quyen cap nhat giai dau nay", 403
        
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
        
        with db_cursor() as cursor:
            cursor.execute("SELECT giai_dau_id FROM dang_ky_giai WHERE id = %s;", (dang_ky_id,))
            result = cursor.fetchone()
        giai_id = result[0] if result else None
        if not giai_id or not _get_tournament_for_admin_or_403(giai_id, user):
            return "Khong co quyen cap nhat giai dau nay", 403
        
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
        giai_raw = _get_tournament_for_admin_or_403(giai_id, user)
        if not giai_raw:
            return "Khong co quyen cap nhat giai dau nay", 403
        registrations = DangKyGiaiModel.get_by_tournament(giai_id)
        so_san = giai_raw[2] if giai_raw else 1
        
        loai_dau = giai_raw[15] if len(giai_raw) > 15 and giai_raw[15] else 'don'
        
        MatchModel.delete_by_tournament(giai_id)

        if loai_dau == 'doi':
            # Doubles: truyền (tên, trình độ) để smart pairing theo level
            players = [(r[2], r[3] or 'D') for r in registrations]
        else:
            # Singles: chỉ cần tên
            players = [r[2] for r in registrations]

        matches = MatchSchedulerService.generate_round_robin(players, so_san, loai_dau)
        MatchModel.save_matches(giai_id, matches)
        
        DBLogger.log_success(f"Schedule generated: {len(matches)} matches ({loai_dau})", user.get('email'), f'/giai-dau/{giai_id}/chia-lich')
        return redirect(f'/giai-dau/{giai_id}/admin')
    except Exception as e:
        DBLogger.log_error(f"Error generating schedule: {str(e)}", user.get('email'), f'/giai-dau/{giai_id}/chia-lich', context=traceback.format_exc())
        return f"❌ Error: {str(e)}", 500

@app.route('/giai-dau/<int:giai_id>/cap-nhat-tien-hang-loat', methods=['POST'])
@admin_required
def cap_nhat_tien_hang_loat(giai_id):
    """Cập nhật phí đóng cho toàn bộ VĐV trong 1 lần submit"""
    user = session.get('user', {})
    try:
        if not _get_tournament_for_admin_or_403(giai_id, user):
            return "Khong co quyen cap nhat giai dau nay", 403
        registrations = DangKyGiaiModel.get_by_tournament(giai_id)
        updates = []
        for reg in registrations:
            reg_id = reg[0]
            so_tien = request.form.get(f'tien_{reg_id}', 0)
            trang_thai = request.form.get(f'trang_thai_{reg_id}', 'Chưa đóng')
            try:
                so_tien = float(so_tien) if so_tien else 0
            except ValueError:
                so_tien = 0
            updates.append((reg_id, so_tien, trang_thai))
        updated = DangKyGiaiModel.update_payments(updates)
        DBLogger.log_success(f"Batch payment update: {updated} records for tournament {giai_id}", user.get('email'), f'/giai-dau/{giai_id}/cap-nhat-tien-hang-loat')
        return redirect(f'/giai-dau/{giai_id}/admin')
    except Exception as e:
        DBLogger.log_error(f"Batch payment error: {str(e)}", user.get('email'), f'/giai-dau/{giai_id}/cap-nhat-tien-hang-loat', context=traceback.format_exc())
        return f"❌ Error: {str(e)}", 500
@app.route('/giai-dau/<int:giai_id>/cap-nhat-giai-thuong', methods=['POST'])
@admin_required
def cap_nhat_giai_thuong(giai_id):
    user = session.get('user', {})
    try:
        giai_raw = _get_tournament_for_admin_or_403(giai_id, user)
        if not giai_raw:
            return "Khong co quyen cap nhat giai dau nay", 403
        registrations = DangKyGiaiModel.get_by_tournament(giai_id)
        giai_detail = prepare_tournament_detail(giai_raw, registrations)
        quy_toi_da = float(giai_detail.get('quy_giai_thuong_thuc_te') or 0)

        prizes = []
        for field in ('tien_giai_1', 'tien_giai_2', 'tien_giai_3'):
            raw_value = (request.form.get(field) or '').strip()
            if raw_value == '':
                prizes.append(None)
            else:
                prizes.append(max(0, float(raw_value)))

        if sum(value or 0 for value in prizes) > quy_toi_da:
            return redirect(f'/giai-dau/{giai_id}/admin?error=prize_over')

        TournamentModel.update_prizes(giai_id, prizes[0], prizes[1], prizes[2])
        DBLogger.log_success(f"Tournament prizes updated: {giai_id}", user.get('email'), f'/giai-dau/{giai_id}/cap-nhat-giai-thuong')
        return redirect(f'/giai-dau/{giai_id}/admin')
    except Exception as e:
        DBLogger.log_error(f"Prize update error: {str(e)}", user.get('email'), f'/giai-dau/{giai_id}/cap-nhat-giai-thuong', context=traceback.format_exc())
        return f"Error: {str(e)}", 500


@app.route('/giai-dau/<int:giai_id>/phan-quyen/them', methods=['POST'])
@admin_required
def them_quyen_giai_dau(giai_id):
    user = session.get('user', {})
    try:
        giai_raw = _get_tournament_for_admin_or_403(giai_id, user)
        if not giai_raw or (not _is_super_admin(user) and giai_raw[21] not in (None, user.get('id'))):
            return "Khong co quyen phan quyen giai dau nay", 403
        admin_id = request.form.get('admin_id')
        if admin_id:
            TournamentModel.add_permission(giai_id, admin_id)
        return redirect(f'/giai-dau/{giai_id}/admin')
    except Exception as e:
        DBLogger.log_error(f"Error adding tournament permission: {str(e)}", user.get('email'), f'/giai-dau/{giai_id}/phan-quyen/them', context=traceback.format_exc())
        return f"Error: {str(e)}", 500


@app.route('/giai-dau/<int:giai_id>/phan-quyen/<int:permission_id>/xoa')
@admin_required
def xoa_quyen_giai_dau(giai_id, permission_id):
    user = session.get('user', {})
    try:
        giai_raw = _get_tournament_for_admin_or_403(giai_id, user)
        if not giai_raw or (not _is_super_admin(user) and giai_raw[21] not in (None, user.get('id'))):
            return "Khong co quyen phan quyen giai dau nay", 403
        TournamentModel.remove_permission(giai_id, permission_id)
        return redirect(f'/giai-dau/{giai_id}/admin')
    except Exception as e:
        DBLogger.log_error(f"Error removing tournament permission: {str(e)}", user.get('email'), f'/giai-dau/{giai_id}/phan-quyen/{permission_id}/xoa', context=traceback.format_exc())
        return f"Error: {str(e)}", 500


@app.route('/tran-dau/<int:tran_id>/cap-nhat-ty-so', methods=['POST'])
@admin_required
def cap_nhat_ty_so(tran_id):
    """Cập nhật tỷ số"""
    user = session.get('user', {})
    is_fetch_score_update = request.is_json or request.headers.get('X-Requested-With') == 'fetch'
    try:
        data = request.get_json(silent=True) or request.form
        diem_a_raw = data.get('diem_a')
        diem_b_raw = data.get('diem_b')
        thu_tu_raw = data.get('thu_tu_danh', 2)
        doi_dang_giao = data.get('doi_dang_giao', 'A')

        diem_a = int(diem_a_raw) if str(diem_a_raw or '').strip() != '' else (0 if is_fetch_score_update else None)
        diem_b = int(diem_b_raw) if str(diem_b_raw or '').strip() != '' else (0 if is_fetch_score_update else None)
        thu_tu_danh = int(thu_tu_raw) if str(thu_tu_raw) in ('1', '2') else 2
        
        with db_cursor() as cursor:
            cursor.execute("SELECT giai_dau_id FROM tran_dau WHERE id = %s;", (tran_id,))
            giai_id = cursor.fetchone()[0]
        if not _get_tournament_for_admin_or_403(giai_id, user):
            return "Khong co quyen cap nhat giai dau nay", 403
        
        trang_thai, diem_a, diem_b = MatchModel.update_score(tran_id, diem_a, diem_b, thu_tu_danh, doi_dang_giao)
        DBLogger.log_success(f"Match {tran_id} score updated: {diem_a}-{diem_b}-{thu_tu_danh}-{doi_dang_giao}", user.get('email'), f'/tran-dau/{tran_id}/cap-nhat-ty-so')
        if is_fetch_score_update:
            matches = MatchModel.get_all_by_tournament(giai_id)
            return jsonify({
                'success': True,
                'tran_id': tran_id,
                'giai_id': giai_id,
                'diem_a': diem_a,
                'diem_b': diem_b,
                'thu_tu_danh': thu_tu_danh,
                'doi_dang_giao': doi_dang_giao,
                'trang_thai': trang_thai,
                'ranking': MatchModel.get_bang_xep_hang_by_matches(matches),
            })
        return redirect(f'/giai-dau/{giai_id}/admin')
    except Exception as e:
        DBLogger.log_error(f"Error updating match: {str(e)}", user.get('email'), f'/tran-dau/{tran_id}/cap-nhat-ty-so', context=traceback.format_exc())
        if is_fetch_score_update:
            return jsonify({'success': False, 'error': str(e)}), 500
        return f"❌ Error: {str(e)}", 500

@app.route('/giai-dau/<int:giai_id>/live-scores')
@admin_required
def live_scores_giai_dau(giai_id):
    user = session.get('user', {})
    try:
        if not _get_tournament_for_admin_or_403(giai_id, user):
            return jsonify({'success': False, 'error': 'Khong co quyen xem giai dau nay'}), 403

        matches = MatchModel.get_all_by_tournament(giai_id)
        return jsonify({
            'success': True,
            'giai_id': giai_id,
            'ranking': MatchModel.get_bang_xep_hang_by_matches(matches),
            'matches': [
                {
                    'tran_id': match[0],
                    'diem_a': match[3],
                    'diem_b': match[4],
                    'trang_thai': match[5],
                    'thu_tu_danh': match[8] if len(match) > 8 else 2,
                    'doi_dang_giao': match[9] if len(match) > 9 else 'A',
                }
                for match in matches
            ]
        })
    except Exception as e:
        DBLogger.log_error(f"Error loading live scores: {str(e)}", user.get('email'), f'/giai-dau/{giai_id}/live-scores', context=traceback.format_exc())
        return jsonify({'success': False, 'error': str(e)}), 500


# ============ AUTH ROUTES ============

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Đăng nhập"""
    try:
        if FLASK_SECRET_KEY_ERROR:
            DBLogger.log_error(
                FLASK_SECRET_KEY_ERROR,
                user_email=request.form.get('email'),
                route='/login',
                method=request.method,
                status_code=500,
            )
            return render_template('login.html', error=FLASK_SECRET_KEY_ERROR), 500

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
        DBLogger.log_exception(
            f"Login failed with system error: {str(e)}",
            e,
            user_email=request.form.get('email'),
            route='/login',
            method=request.method,
            status_code=500,
            context=traceback.format_exc(),
            request_path=request.path,
            ip_address=request.headers.get('X-Forwarded-For', request.remote_addr),
            user_agent=request.headers.get('User-Agent'),
        )
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
    forbidden = _require_super_admin()
    if forbidden:
        return forbidden
    success_key = request.args.get('success')
    success_messages = {
        'created': 'Tạo admin thành công',
        'updated': 'Cập nhật admin thành công',
        'deleted': 'Xóa admin thành công',
    }
    return render_template(
        'admin_settings.html',
        admins=AdminUserModel.get_all(),
        success=success_messages.get(success_key),
        super_admin_email='admin@pickleball',
    )

@app.route('/tao-admin', methods=['POST'])
@admin_required
def tao_admin():
    """Tạo admin"""
    user = session.get('user', {})
    try:
        forbidden = _require_super_admin()
        if forbidden:
            return forbidden
        email = request.form.get('email')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        
        if not email or not password:
            return render_template('admin_settings.html', admins=AdminUserModel.get_all(), error="Email & password required", super_admin_email='admin@pickleball')
        if password != confirm:
            return render_template('admin_settings.html', admins=AdminUserModel.get_all(), error="Passwords don't match", super_admin_email='admin@pickleball')
        if len(password) < 6:
            return render_template('admin_settings.html', admins=AdminUserModel.get_all(), error="Password min 6 chars", super_admin_email='admin@pickleball')
        
        success, msg = AuthService.register_admin(email, password)
        
        if success:
            DBLogger.log_success(f"Admin created: {email}", user.get('email'), '/tao-admin')
            return redirect('/admin-settings?success=created')
        else:
            DBLogger.log_warning(f"Failed to create admin: {email}", user.get('email'), '/tao-admin')
            return render_template('admin_settings.html', admins=AdminUserModel.get_all(), error=msg, super_admin_email='admin@pickleball')
    except Exception as e:
        DBLogger.log_error(f"Error creating admin: {str(e)}", user.get('email'), '/tao-admin', context=traceback.format_exc())
        return render_template('admin_settings.html', admins=AdminUserModel.get_all(), error=f"Error: {str(e)}", super_admin_email='admin@pickleball')


@app.route('/admin-settings/<int:admin_id>/sua', methods=['POST'])
@admin_required
def sua_admin(admin_id):
    user = session.get('user', {})
    try:
        forbidden = _require_super_admin()
        if forbidden:
            return forbidden

        admin = AdminUserModel.get_by_id(admin_id)
        if not admin:
            return "Khong tim thay admin", 404

        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''
        confirm = request.form.get('confirm_password') or ''

        if not email:
            return render_template('admin_settings.html', admins=AdminUserModel.get_all(), error="Email required", super_admin_email='admin@pickleball'), 400
        if (admin[1] or '').strip().lower() == 'admin@pickleball' and email != 'admin@pickleball':
            return render_template('admin_settings.html', admins=AdminUserModel.get_all(), error="Khong the doi email admin goc", super_admin_email='admin@pickleball'), 400
        if AdminUserModel.email_exists(email, exclude_id=admin_id):
            return render_template('admin_settings.html', admins=AdminUserModel.get_all(), error="Email da ton tai", super_admin_email='admin@pickleball'), 400
        if password or confirm:
            if password != confirm:
                return render_template('admin_settings.html', admins=AdminUserModel.get_all(), error="Passwords don't match", super_admin_email='admin@pickleball'), 400
            if len(password) < 6:
                return render_template('admin_settings.html', admins=AdminUserModel.get_all(), error="Password min 6 chars", super_admin_email='admin@pickleball'), 400
            AdminUserModel.update(admin_id, email, AuthService.hash_password(password))
        else:
            AdminUserModel.update(admin_id, email)

        if admin_id == user.get('id'):
            session['user']['email'] = email
        DBLogger.log_success(f"Admin updated: {email}", user.get('email'), f'/admin-settings/{admin_id}/sua')
        return redirect('/admin-settings?success=updated')
    except Exception as e:
        DBLogger.log_error(f"Error updating admin: {str(e)}", user.get('email'), f'/admin-settings/{admin_id}/sua', context=traceback.format_exc())
        return render_template('admin_settings.html', admins=AdminUserModel.get_all(), error=f"Error: {str(e)}", super_admin_email='admin@pickleball'), 500


@app.route('/admin-settings/<int:admin_id>/xoa', methods=['POST'])
@admin_required
def xoa_admin(admin_id):
    user = session.get('user', {})
    try:
        forbidden = _require_super_admin()
        if forbidden:
            return forbidden

        admin = AdminUserModel.get_by_id(admin_id)
        if not admin:
            return "Khong tim thay admin", 404
        if (admin[1] or '').strip().lower() == 'admin@pickleball':
            return render_template('admin_settings.html', admins=AdminUserModel.get_all(), error="Khong the xoa admin goc", super_admin_email='admin@pickleball'), 400

        fallback = next((item for item in AdminUserModel.get_all() if (item[1] or '').strip().lower() == 'admin@pickleball'), None)
        if not fallback:
            return render_template('admin_settings.html', admins=AdminUserModel.get_all(), error="Khong tim thay admin goc de chuyen quyen so huu", super_admin_email='admin@pickleball'), 400

        AdminUserModel.delete(admin_id, fallback[0])
        DBLogger.log_success(f"Admin deleted: {admin[1]}", user.get('email'), f'/admin-settings/{admin_id}/xoa')
        return redirect('/admin-settings?success=deleted')
    except Exception as e:
        DBLogger.log_error(f"Error deleting admin: {str(e)}", user.get('email'), f'/admin-settings/{admin_id}/xoa', context=traceback.format_exc())
        return render_template('admin_settings.html', admins=AdminUserModel.get_all(), error=f"Error: {str(e)}", super_admin_email='admin@pickleball'), 500

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
        registrations_by_tournament = DangKyGiaiModel.get_by_tournaments([row[1] for row in tournaments_raw])
        
        vdv_giai = []
        for row in tournaments_raw:
            try:
                giai_raw = tuple(row[1:16])
                registrations = registrations_by_tournament.get(row[1], [])
                giai_detail = prepare_tournament_detail(giai_raw, registrations)
                vdv_giai.append(giai_detail)
            except Exception as e:
                DBLogger.log_error(f"Error loading tournament for VĐV: {str(e)}", user.get('email'), '/vdv-dashboard', context=traceback.format_exc())
                continue
        
        vdv_doi_bong = DoiBongModel.get_by_vdv(vdv_id)
        return render_template('vdv_dashboard.html', vdv_giai=vdv_giai, vdv_doi_bong=vdv_doi_bong)
    except Exception as e:
        DBLogger.log_error(f"Error loading VĐV dashboard: {str(e)}", user.get('email'), '/vdv-dashboard', context=traceback.format_exc())
        return f"❌ Error: {str(e)}", 500


@app.route('/doi-bong/<int:doi_bong_id>/vdv')
@login_required
def chi_tiet_doi_bong_vdv(doi_bong_id):
    user = session.get('user', {})
    if user.get('role') != 'vdv':
        return redirect(url_for('login'))
    try:
        doi_bong = DoiBongModel.get_by_id_for_vdv(doi_bong_id, user['id'])
        if not doi_bong:
            return "Không có quyền xem đội bóng này", 403

        selected_month = request.args.get('thang') or _current_month()
        selected_month_date = DoiBongModel.normalize_month(selected_month)
        month_config = DoiBongModel.get_month_config(doi_bong_id, selected_month_date)
        members = DoiBongModel.get_members_with_payments(doi_bong_id, selected_month_date)
        expenses = DoiBongModel.get_expenses(doi_bong_id, selected_month_date)
        finance = FinanceService.tinh_toan_quy_doi_bong(month_config, members, expenses)
        available_months = DoiBongModel.get_available_months(doi_bong_id)
        if selected_month[:7] not in available_months:
            available_months.insert(0, selected_month[:7])

        DBLogger.log_request('GET', f'/doi-bong/{doi_bong_id}/vdv', user.get('email'))
        return render_template(
            'chi_tiet_doi_bong.html',
            doi_bong=doi_bong,
            finance=finance,
            selected_month=selected_month[:7],
            available_months=available_months,
            all_vdv=[],
            admins=[],
            permissions=[],
            can_edit=False,
            is_owner=False,
        )
    except Exception as e:
        DBLogger.log_error(f"Error loading team for VĐV: {str(e)}", user.get('email'), f'/doi-bong/{doi_bong_id}/vdv', context=traceback.format_exc())
        return f"Error: {str(e)}", 500

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
                "trang_thai": m[5], "san": m[6] or 1, "vong": vong,
                "thu_tu_danh": m[8] if len(m) > 8 and m[8] else 2,
                "doi_dang_giao": m[9] if len(m) > 9 and m[9] else 'A'
            })
        giai_detail['vong_dict'] = vong_dict

        giai_detail['loai_dau'] = giai_raw[15] if len(giai_raw) > 15 and giai_raw[15] else 'don'
        
        DBLogger.log_request('GET', f'/giai-dau/{giai_id}/vdv', user.get('email'))
        return render_template('chi_tiet_giai_vdv.html', giai=giai_detail, registrations=registrations, enumerate=enumerate)
    except Exception as e:
        DBLogger.log_error(f"Error loading tournament: {str(e)}", user.get('email'), f'/giai-dau/{giai_id}/vdv', context=traceback.format_exc())
        return f"❌ Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)
