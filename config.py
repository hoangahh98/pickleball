import os

# ============ DATABASE CONFIG ============
# Có thể override bằng biến môi trường trên Render (Settings -> Environment).
# Nếu không set biến môi trường, sẽ dùng giá trị mặc định bên dưới (giữ nguyên hành vi cũ).
DB_CONFIG = {
    "dbname": os.environ.get("DB_NAME", "postgres"),
    "user": os.environ.get("DB_USER", "postgres.tmtrbnobadglqgcrgirr"),
    "password": os.environ.get("DB_PASSWORD", "Baobeo@2023"),
    "host": os.environ.get("DB_HOST", "aws-1-ap-northeast-1.pooler.supabase.com"),
    "port": os.environ.get("DB_PORT", "5432"),
}

# ============ FLASK CONFIG ============
FLASK_SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "aK8mN@2kL9pQw3xRz5v7j#hF4tUyI6oP")
DEBUG = False  # Set True chỉ khi develop local

# ============ FILE UPLOAD CONFIG ============
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# ============ APP SETTINGS ============
APP_NAME = "Pickleball Tournament Manager"
APP_VERSION = "1.0.0"
BASE_URL = os.environ.get("BASE_URL", "https://pickleball-m7wn.onrender.com")

# Lưu ý: toàn bộ log của app (request/success/error/warning) đều được ghi vào
# bảng app_logs trong Postgres thông qua DBLogger (xem logging_service.py).
# Hệ thống log file cục bộ (logging module ghi ra thư mục logs/) đã được gỡ bỏ
# vì không được dùng ở đâu trong code, và trên Render đĩa là ephemeral nên ghi
# file log cục bộ vô nghĩa — chỉ tốn I/O mỗi lần cold start.
