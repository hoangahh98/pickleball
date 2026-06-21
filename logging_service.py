from datetime import datetime
import psycopg2
from config import DB_CONFIG

class DBLogger:
    """Logs all events to database"""
    
    @staticmethod
    def log_error(message, user_email=None, route=None, method=None, status_code=None, context=None):
        """Log ERROR level"""
        DBLogger._insert_log('ERROR', message, user_email, route, method, status_code, context)
    
    @staticmethod
    def log_warning(message, user_email=None, route=None, context=None):
        """Log WARNING level"""
        DBLogger._insert_log('WARNING', message, user_email, route, context=context)
    
    @staticmethod
    def log_success(message, user_email=None, route=None, context=None):
        """Log SUCCESS level"""
        DBLogger._insert_log('SUCCESS', message, user_email, route, context=context)
    
    @staticmethod
    def log_info(message, user_email=None, route=None, context=None):
        """Log INFO level"""
        DBLogger._insert_log('INFO', message, user_email, route, context=context)
    
    @staticmethod
    def log_request(method, route, user_email=None):
        """Log HTTP REQUEST"""
        DBLogger._insert_log('REQUEST', f"{method} {route}", user_email, route, method)
    
    @staticmethod
    def _insert_log(level, message, user_email=None, route=None, method=None, status_code=None, context=None):
        """Insert log into database"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO app_logs (log_level, message, context, user_email, route, method, status_code)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
            """, (level, message, context, user_email, route, method, status_code))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            # Fallback - print to console if DB insert fails
            print(f"❌ DB Log Error: {str(e)}")
            print(f"   Original log: [{level}] {message}")

class DBLogViewer:
    """Query and view logs from database"""
    
    @staticmethod
    def get_recent_logs(limit=50, level=None, user_email=None, route=None):
        """Get recent logs with optional filters"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            
            query = "SELECT id, log_level, message, user_email, route, method, status_code, created_at FROM app_logs WHERE 1=1"
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
        except Exception as e:
            return []
    
    @staticmethod
    def get_errors_today():
        """Get all errors from today"""
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
        except Exception as e:
            return []
    
    @staticmethod
    def get_errors_last_hours(hours=24):
        """Get errors from last N hours"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, log_level, message, user_email, route, created_at 
                FROM app_logs 
                WHERE log_level = 'ERROR' AND created_at > NOW() - INTERVAL '%s hours'
                ORDER BY created_at DESC;
            """ % hours)
            errors = cursor.fetchall()
            cursor.close()
            conn.close()
            return errors
        except Exception as e:
            return []
    
    @staticmethod
    def get_user_actions(user_email):
        """Get all actions by specific user"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, log_level, message, route, created_at 
                FROM app_logs 
                WHERE user_email = %s
                ORDER BY created_at DESC
                LIMIT 100;
            """, (user_email,))
            actions = cursor.fetchall()
            cursor.close()
            conn.close()
            return actions
        except Exception as e:
            return []
    
    @staticmethod
    def get_log_stats():
        """Get statistics about logs"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    log_level,
                    COUNT(*) as count,
                    DATE(created_at) as date
                FROM app_logs
                WHERE created_at > NOW() - INTERVAL '7 days'
                GROUP BY log_level, DATE(created_at)
                ORDER BY date DESC, log_level;
            """)
            stats = cursor.fetchall()
            cursor.close()
            conn.close()
            return stats
        except Exception as e:
            return []