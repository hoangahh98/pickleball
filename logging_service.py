import json
import psycopg2
from flask import has_request_context, request
from config import DB_CONFIG, DB_CONFIG_ERROR


class DBLogger:
    """Database logger. Logging failures must never crash the app."""

    _schema_ready = False

    @staticmethod
    def ensure_log_schema():
        if DBLogger._schema_ready:
            return
        if DB_CONFIG_ERROR:
            raise RuntimeError(DB_CONFIG_ERROR)

        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        try:
            cursor.execute("""
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
            """)
            conn.commit()
            DBLogger._schema_ready = True
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def log_error(message, user_email=None, route=None, method=None, status_code=None, context=None):
        DBLogger._insert_log("ERROR", message, user_email, route, method, status_code, context)

    @staticmethod
    def log_warning(message, user_email=None, route=None, context=None):
        DBLogger._insert_log("WARNING", message, user_email, route, context=context)

    @staticmethod
    def log_success(message, user_email=None, route=None, context=None):
        DBLogger._insert_log("SUCCESS", message, user_email, route, context=context)

    @staticmethod
    def log_info(message, user_email=None, route=None, context=None):
        DBLogger._insert_log("INFO", message, user_email, route, context=context)

    @staticmethod
    def log_request(method, route, user_email=None):
        DBLogger._insert_log("REQUEST", f"{method} {route}", user_email, route, method)

    @staticmethod
    def _insert_log(level, message, user_email=None, route=None, method=None, status_code=None, context=None):
        try:
            if DB_CONFIG_ERROR:
                DBLogger._safe_console_log(RuntimeError(DB_CONFIG_ERROR), level, message)
                return

            request_path = route
            request_method = method
            ip_address = None
            user_agent = None
            if has_request_context():
                request_path = request.path
                request_method = request.method
                ip_address = request.headers.get("X-Forwarded-For", request.remote_addr)
                user_agent = request.headers.get("User-Agent")

            DBLogger.ensure_log_schema()
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO app_logs (
                    log_level, message, context, user_email, route, method, status_code,
                    exception_type, request_path, request_method, ip_address, user_agent
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                level, message, context, user_email, route, method, status_code,
                None, request_path, request_method, ip_address, user_agent
            ))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            DBLogger._safe_console_log(e, level, message)

    @staticmethod
    def log_exception(message, exc, user_email=None, route=None, method=None, status_code=500, context=None,
                      request_path=None, ip_address=None, user_agent=None):
        try:
            if DB_CONFIG_ERROR:
                DBLogger._safe_console_log(RuntimeError(DB_CONFIG_ERROR), "ERROR", message)
                return

            DBLogger.ensure_log_schema()
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO app_logs (
                    log_level, message, context, user_email, route, method, status_code,
                    exception_type, request_path, request_method, ip_address, user_agent
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """, (
                "ERROR", message, context, user_email, route, method, status_code,
                exc.__class__.__name__ if exc else None,
                request_path, method, ip_address, user_agent
            ))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            DBLogger._safe_console_log(e, "ERROR", message)

    @staticmethod
    def log_user_action(user_email=None, user_role=None, action=None, route=None, endpoint=None, method=None,
                        status_code=None, ip_address=None, user_agent=None, details=None):
        try:
            if DB_CONFIG_ERROR:
                DBLogger._safe_console_log(RuntimeError(DB_CONFIG_ERROR), "ACTION", action or route or "unknown")
                return

            DBLogger.ensure_log_schema()
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_actions (
                    user_email, user_role, action, route, endpoint, method, status_code,
                    ip_address, user_agent, details
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb);
            """, (
                user_email, user_role, action, route, endpoint, method, status_code,
                ip_address, user_agent, json.dumps(details or {}, ensure_ascii=False)
            ))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            DBLogger._safe_console_log(e, "ACTION", action or route or "unknown")

    @staticmethod
    def _safe_console_log(error, level, message):
        try:
            if DB_CONFIG_ERROR:
                print(f"DB Config Error: {ascii(DB_CONFIG_ERROR)}")
            print(f"DB Log Error: {ascii(str(error))}")
            print(f"Original log: [{level}] {ascii(str(message))}")
        except Exception:
            pass


class DBLogViewer:
    """Query and view logs from database."""

    @staticmethod
    def get_recent_logs(limit=50, level=None, user_email=None, route=None):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            query = """
                SELECT id, log_level, message, user_email, route, method, status_code, created_at
                FROM app_logs
                WHERE 1=1
            """
            params = []
            if level:
                query += " AND log_level = %s"
                params.append(level)
            if user_email:
                query += " AND user_email = %s"
                params.append(user_email)
            if route:
                query += " AND route = %s"
                params.append(route)
            query += " ORDER BY created_at DESC LIMIT %s;"
            params.append(limit)
            cursor.execute(query, params)
            logs = cursor.fetchall()
            cursor.close()
            conn.close()
            return logs
        except Exception:
            return []

    @staticmethod
    def get_errors_today():
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, message, user_email, route, created_at
                FROM app_logs
                WHERE log_level = 'ERROR' AND DATE(created_at) = CURRENT_DATE
                ORDER BY created_at DESC;
            """)
            errors = cursor.fetchall()
            cursor.close()
            conn.close()
            return errors
        except Exception:
            return []

    @staticmethod
    def get_errors_last_hours(hours=24):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, log_level, message, user_email, route, created_at
                FROM app_logs
                WHERE log_level = 'ERROR' AND created_at > NOW() - (%s * INTERVAL '1 hour')
                ORDER BY created_at DESC;
            """, (hours,))
            errors = cursor.fetchall()
            cursor.close()
            conn.close()
            return errors
        except Exception:
            return []

    @staticmethod
    def get_user_actions(user_email):
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, action, route, method, status_code, created_at
                FROM user_actions
                WHERE user_email = %s
                ORDER BY created_at DESC
                LIMIT 100;
            """, (user_email,))
            actions = cursor.fetchall()
            cursor.close()
            conn.close()
            return actions
        except Exception:
            return []

    @staticmethod
    def get_log_stats():
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT log_level, COUNT(*) as count, DATE(created_at) as date
                FROM app_logs
                WHERE created_at > NOW() - INTERVAL '7 days'
                GROUP BY log_level, DATE(created_at)
                ORDER BY date DESC, log_level;
            """)
            stats = cursor.fetchall()
            cursor.close()
            conn.close()
            return stats
        except Exception:
            return []
