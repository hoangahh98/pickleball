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
ADD COLUMN IF NOT EXISTS user_agent TEXT,
ADD COLUMN IF NOT EXISTS cf_ray VARCHAR(100);

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
    cf_ray VARCHAR(100),
    details JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE user_actions
ADD COLUMN IF NOT EXISTS cf_ray VARCHAR(100);
"""


APP_SCHEMA_SQL = """
ALTER TABLE giai_dau
ADD COLUMN IF NOT EXISTS diem_cham INTEGER DEFAULT 11,
ADD COLUMN IF NOT EXISTS diem_toi_da INTEGER DEFAULT 15;

ALTER TABLE giai_dau
ADD COLUMN IF NOT EXISTS tien_giai_1 NUMERIC(12, 2),
ADD COLUMN IF NOT EXISTS tien_giai_2 NUMERIC(12, 2),
ADD COLUMN IF NOT EXISTS tien_giai_3 NUMERIC(12, 2);

ALTER TABLE giai_dau
ADD COLUMN IF NOT EXISTS owner_admin_id INTEGER REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE giai_dau
ADD COLUMN IF NOT EXISTS the_thuc VARCHAR(20) DEFAULT 'vong_tron',
ADD COLUMN IF NOT EXISTS so_doi_moi_bang INTEGER DEFAULT 4,
ADD COLUMN IF NOT EXISTS so_bang INTEGER DEFAULT 2,
ADD COLUMN IF NOT EXISTS so_doi_vao_vong_trong INTEGER DEFAULT 2;

ALTER TABLE giai_dau
ALTER COLUMN so_doi_vao_vong_trong SET DEFAULT 2;

UPDATE giai_dau
SET owner_admin_id = COALESCE(
    (SELECT id FROM users WHERE lower(email) = lower('admin@pickleball') LIMIT 1),
    (SELECT id FROM users WHERE role = 'admin' ORDER BY id ASC LIMIT 1)
)
WHERE owner_admin_id IS NULL;

CREATE TABLE IF NOT EXISTS giai_dau_admin_quyen (
    id SERIAL PRIMARY KEY,
    giai_dau_id INTEGER NOT NULL REFERENCES giai_dau(id) ON DELETE CASCADE,
    admin_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (giai_dau_id, admin_id)
);

ALTER TABLE tran_dau
ADD COLUMN IF NOT EXISTS thu_tu_danh INTEGER DEFAULT 2;

ALTER TABLE tran_dau
ADD COLUMN IF NOT EXISTS doi_dang_giao VARCHAR(1) DEFAULT 'A';

ALTER TABLE tran_dau
ADD COLUMN IF NOT EXISTS giai_doan VARCHAR(20) DEFAULT 'vong_tron',
ADD COLUMN IF NOT EXISTS bang_dau VARCHAR(20);

CREATE TABLE IF NOT EXISTS tran_dau_edit_lock (
    tran_id INTEGER PRIMARY KEY REFERENCES tran_dau(id) ON DELETE CASCADE,
    locked_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    locked_by_email VARCHAR(255),
    lock_token VARCHAR(100) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tran_dau_edit_lock_expires
ON tran_dau_edit_lock (expires_at);

CREATE INDEX IF NOT EXISTS idx_van_dong_vien_lower_email
ON van_dong_vien (lower(email));

CREATE INDEX IF NOT EXISTS idx_van_dong_vien_ten
ON van_dong_vien (ten_vdv);

CREATE INDEX IF NOT EXISTS idx_users_role_email
ON users (role, lower(email));

CREATE INDEX IF NOT EXISTS idx_giai_dau_id_desc
ON giai_dau (id DESC);

CREATE INDEX IF NOT EXISTS idx_giai_dau_owner
ON giai_dau (owner_admin_id);

CREATE INDEX IF NOT EXISTS idx_giai_dau_admin_quyen_admin
ON giai_dau_admin_quyen (admin_id, giai_dau_id);

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

CREATE TABLE IF NOT EXISTS doi_bong (
    id SERIAL PRIMARY KEY,
    ten_doi VARCHAR(255) NOT NULL,
    mo_ta TEXT,
    owner_admin_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE doi_bong
ADD COLUMN IF NOT EXISTS owner_admin_id INTEGER REFERENCES users(id) ON DELETE SET NULL;

UPDATE doi_bong
SET owner_admin_id = COALESCE(
    (SELECT id FROM users WHERE lower(email) = lower('admin@pickleball') LIMIT 1),
    (SELECT id FROM users WHERE role = 'admin' ORDER BY id ASC LIMIT 1)
)
WHERE owner_admin_id IS NULL;

CREATE TABLE IF NOT EXISTS doi_bong_thanh_vien (
    id SERIAL PRIMARY KEY,
    doi_bong_id INTEGER NOT NULL REFERENCES doi_bong(id) ON DELETE CASCADE,
    van_dong_vien_id INTEGER REFERENCES van_dong_vien(id) ON DELETE CASCADE,
    ten_thanh_vien VARCHAR(255) NOT NULL,
    trinh_do VARCHAR(10) DEFAULT 'C',
    loai_thanh_vien VARCHAR(20) DEFAULT 'co_dinh',
    ghi_chu TEXT,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE doi_bong_thanh_vien
ADD COLUMN IF NOT EXISTS van_dong_vien_id INTEGER REFERENCES van_dong_vien(id) ON DELETE CASCADE;

CREATE TABLE IF NOT EXISTS doi_bong_quy_thang (
    id SERIAL PRIMARY KEY,
    doi_bong_id INTEGER NOT NULL REFERENCES doi_bong(id) ON DELETE CASCADE,
    thang DATE NOT NULL,
    muc_phi_thang NUMERIC(12, 2) DEFAULT 0,
    chi_phi_san_bai NUMERIC(12, 2) DEFAULT 0,
    chi_phi_nuoc_noi NUMERIC(12, 2) DEFAULT 0,
    chi_phi_khac NUMERIC(12, 2) DEFAULT 0,
    tien_san_con_lai_thang_truoc NUMERIC(12, 2) DEFAULT 0,
    ghi_chu TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (doi_bong_id, thang)
);

ALTER TABLE doi_bong_quy_thang
ADD COLUMN IF NOT EXISTS tien_san_con_lai_thang_truoc NUMERIC(12, 2) DEFAULT 0;

CREATE TABLE IF NOT EXISTS doi_bong_khoan_chi (
    id SERIAL PRIMARY KEY,
    doi_bong_id INTEGER NOT NULL REFERENCES doi_bong(id) ON DELETE CASCADE,
    thang DATE NOT NULL,
    ngay_chi DATE NOT NULL,
    noi_dung VARCHAR(255) NOT NULL,
    so_tien NUMERIC(12, 2) DEFAULT 0,
    ghi_chu TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS doi_bong_admin_quyen (
    id SERIAL PRIMARY KEY,
    doi_bong_id INTEGER NOT NULL REFERENCES doi_bong(id) ON DELETE CASCADE,
    admin_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (doi_bong_id, admin_id)
);

CREATE TABLE IF NOT EXISTS doi_bong_dong_phi (
    id SERIAL PRIMARY KEY,
    thanh_vien_id INTEGER NOT NULL REFERENCES doi_bong_thanh_vien(id) ON DELETE CASCADE,
    thang DATE NOT NULL,
    so_tien_da_dong NUMERIC(12, 2) DEFAULT 0,
    trang_thai_dong_tien VARCHAR(50) DEFAULT 'Chưa đóng',
    ghi_chu TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (thanh_vien_id, thang)
);

CREATE INDEX IF NOT EXISTS idx_doi_bong_ten
ON doi_bong (ten_doi);

CREATE INDEX IF NOT EXISTS idx_doi_bong_thanh_vien_doi
ON doi_bong_thanh_vien (doi_bong_id, active, ten_thanh_vien);

CREATE INDEX IF NOT EXISTS idx_doi_bong_thanh_vien_doi_vdv_active
ON doi_bong_thanh_vien (doi_bong_id, van_dong_vien_id, active);

CREATE UNIQUE INDEX IF NOT EXISTS idx_doi_bong_thanh_vien_doi_vdv
ON doi_bong_thanh_vien (doi_bong_id, van_dong_vien_id)
WHERE active = TRUE AND van_dong_vien_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_doi_bong_quy_thang
ON doi_bong_quy_thang (doi_bong_id, thang);

CREATE INDEX IF NOT EXISTS idx_doi_bong_dong_phi_thang
ON doi_bong_dong_phi (thang, thanh_vien_id);

CREATE INDEX IF NOT EXISTS idx_doi_bong_owner
ON doi_bong (owner_admin_id);

CREATE INDEX IF NOT EXISTS idx_doi_bong_khoan_chi_thang
ON doi_bong_khoan_chi (doi_bong_id, thang, ngay_chi);

CREATE INDEX IF NOT EXISTS idx_doi_bong_admin_quyen_admin
ON doi_bong_admin_quyen (admin_id, doi_bong_id);
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
