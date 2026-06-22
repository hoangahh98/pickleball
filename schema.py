from db import db_cursor


LOG_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS app_logs (
    id SERIAL PRIMARY KEY,
    log_level VARCHAR(20),
    message TEXT,
    context TEXT,
    user_email VARCHAR(255),
    route VARCHAR(255),
    method VARCHAR(20),
    status_code INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE app_logs
ADD COLUMN IF NOT EXISTS exception_type VARCHAR(255),
ADD COLUMN IF NOT EXISTS request_path TEXT,
ADD COLUMN IF NOT EXISTS request_method VARCHAR(20),
ADD COLUMN IF NOT EXISTS ip_address VARCHAR(100),
ADD COLUMN IF NOT EXISTS user_agent TEXT;

CREATE TABLE IF NOT EXISTS user_actions (
    id SERIAL PRIMARY KEY,
    user_email VARCHAR(255),
    user_role VARCHAR(50),
    action VARCHAR(255),
    route VARCHAR(255),
    endpoint VARCHAR(255),
    method VARCHAR(20),
    status_code INTEGER,
    ip_address VARCHAR(100),
    user_agent TEXT,
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


APP_SCHEMA_SQL = """
ALTER TABLE giai_dau
ADD COLUMN IF NOT EXISTS diem_cham INTEGER DEFAULT 11,
ADD COLUMN IF NOT EXISTS diem_toi_da INTEGER DEFAULT 15;

ALTER TABLE tran_dau
ADD COLUMN IF NOT EXISTS thu_tu_danh INTEGER DEFAULT 2;

ALTER TABLE tran_dau
ADD COLUMN IF NOT EXISTS doi_dang_giao VARCHAR(1) DEFAULT 'A';

CREATE INDEX IF NOT EXISTS idx_van_dong_vien_lower_email
ON van_dong_vien (lower(email));

CREATE INDEX IF NOT EXISTS idx_van_dong_vien_ten
ON van_dong_vien (ten_vdv);

CREATE INDEX IF NOT EXISTS idx_giai_dau_id_desc
ON giai_dau (id DESC);

CREATE INDEX IF NOT EXISTS idx_dang_ky_giai_giai
ON dang_ky_giai (giai_dau_id);

CREATE INDEX IF NOT EXISTS idx_dang_ky_giai_vdv
ON dang_ky_giai (van_dong_vien_id);

CREATE INDEX IF NOT EXISTS idx_dang_ky_giai_giai_vdv
ON dang_ky_giai (giai_dau_id, van_dong_vien_id);

CREATE INDEX IF NOT EXISTS idx_tran_dau_giai_order
ON tran_dau (giai_dau_id, vong_dau, san_so_may, id);

CREATE INDEX IF NOT EXISTS idx_app_logs_level_created
ON app_logs (log_level, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_app_logs_created
ON app_logs (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_user_actions_email_created
ON user_actions (user_email, created_at DESC);
"""


def ensure_log_schema():
    with db_cursor(commit=True) as cursor:
        cursor.execute(LOG_SCHEMA_SQL)


def ensure_app_schema():
    with db_cursor(commit=True) as cursor:
        cursor.execute(APP_SCHEMA_SQL)


def ensure_all_schema():
    ensure_log_schema()
    ensure_app_schema()
