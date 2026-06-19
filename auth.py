"""
Hệ thống xác thực cho Admin & VĐV
- Admin: email + password
- VĐV: email + password (123456789)
"""
import psycopg2
from config import DB_CONFIG
from functools import wraps
from flask import session, redirect, url_for, request

class AuthService:
    @staticmethod
    def hash_password(password):
        """Simple hash (trong production dùng werkzeug.security.generate_password_hash)"""
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def verify_password(plain, hashed):
        """Verify password"""
        return AuthService.hash_password(plain) == hashed

    @staticmethod
    def login_admin(email, password):
        """Login cho admin"""
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT id, email, password FROM users WHERE email = %s;", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if not user:
            return None, "Email không tồn tại"
        
        if not AuthService.verify_password(password, user[2]):
            return None, "Mật khẩu sai"
        
        return {"id": user[0], "email": user[1], "role": "admin"}, None

    @staticmethod
    def login_vdv(email, password):
        """Login cho VĐV"""
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, ten_nguoi_choi, email, giai_dau_id FROM nguoi_choi WHERE email = %s;
        """, (email,))
        vdv = cursor.fetchone()
        cursor.close()
        conn.close()

        if not vdv:
            return None, "Email không tồn tại trong danh sách VĐV"
        
        # Password mặc định: 123456789
        if password != "123456789":
            return None, "Mật khẩu sai (mặc định: 123456789)"
        
        return {
            "id": vdv[0],
            "ten": vdv[1],
            "email": vdv[2],
            "giai_id": vdv[3],
            "role": "vdv"
        }, None

    @staticmethod
    def register_admin(email, password):
        """Tạo tài khoản admin (chỉ cấu hình lần đầu)"""
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Kiểm tra email đã tồn tại
        cursor.execute("SELECT id FROM users WHERE email = %s;", (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return False, "Email đã tồn tại"
        
        # Thêm admin mới
        hashed = AuthService.hash_password(password)
        try:
            cursor.execute("""
                INSERT INTO users (email, password, role) VALUES (%s, %s, %s);
            """, (email, hashed, "admin"))
            conn.commit()
            cursor.close()
            conn.close()
            return True, "Tạo admin thành công"
        except Exception as e:
            cursor.close()
            conn.close()
            return False, str(e)


def login_required(f):
    """Decorator: chỉ cho phép user đã login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator: chỉ cho phép admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session or session['user'].get('role') != 'admin':
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def vdv_required(f):
    """Decorator: chỉ cho phép VĐV"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session or session['user'].get('role') != 'vdv':
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function