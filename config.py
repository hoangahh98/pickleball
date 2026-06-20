import logging
import os
import sys
from datetime import datetime

# ============ DATABASE CONFIG ============
DB_CONFIG = {
    "dbname": "postgres",
    "user": "postgres.tmtrbnobadglqgcrgirr",
    "password": "Baobeo@2023",
    "host": "aws-1-ap-northeast-1.pooler.supabase.com",
    "port": "5432"
}

# ============ FLASK CONFIG ============
FLASK_SECRET_KEY = 'aK8mN@2kL9pQw3xRz5v7j#hF4tUyI6oP'
DEBUG = False  # Set True chỉ khi develop local

# ============ FILE UPLOAD CONFIG (TẠM, KO DÙNG) ============
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# ============ APP SETTINGS ============
APP_NAME = "Pickleball Tournament Manager"
APP_VERSION = "1.0.0"
BASE_URL = "https://pickleball-m7wn.onrender.com"

# ============ LOGGING CONFIG ============
class LogConfig:
    """Cấu hình logging chi tiết"""
    
    # Log folder
    LOG_DIR = "logs"
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    
    # Log file paths
    LOG_FILE = os.path.join(LOG_DIR, f"app_{datetime.now().strftime('%Y%m%d')}.log")
    ERROR_LOG_FILE = os.path.join(LOG_DIR, f"error_{datetime.now().strftime('%Y%m%d')}.log")
    SQL_LOG_FILE = os.path.join(LOG_DIR, f"sql_{datetime.now().strftime('%Y%m%d')}.log")
    
    # Log format - chi tiết, dễ trace
    LOG_FORMAT = """
[%(asctime)s] %(levelname)s [%(name)s:%(filename)s:%(lineno)d]
  Function: %(funcName)s
  Message: %(message)s
---
"""
    
    LOG_FORMAT_SHORT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"

def setup_logging():
    """Setup logging system"""
    
    # Main logger
    app_logger = logging.getLogger('pickleball')
    app_logger.setLevel(logging.DEBUG)
    
    # File handler - ALL logs (DEBUG level)
    file_handler = logging.FileHandler(LogConfig.LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(LogConfig.LOG_FORMAT_SHORT)
    file_handler.setFormatter(file_formatter)
    
    # File handler - ERROR logs only
    error_handler = logging.FileHandler(LogConfig.ERROR_LOG_FILE, encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    
    # Console handler - display in terminal/Render logs
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(LogConfig.LOG_FORMAT_SHORT)
    console_handler.setFormatter(console_formatter)
    
    # Add handlers
    app_logger.addHandler(file_handler)
    app_logger.addHandler(error_handler)
    app_logger.addHandler(console_handler)
    
    return app_logger

# ============ GET LOGGER ANYWHERE ============
def get_logger(name='pickleball'):
    """Get logger by name"""
    return logging.getLogger(name)

# ============ TRACE UTILITIES ============
class LogHelper:
    """Helper functions để log với context đầy đủ"""
    
    @staticmethod
    def log_request(method, path, user=None):
        """Log HTTP request"""
        logger = get_logger()
        logger.info(f"📡 {method} {path} | User: {user or 'Anonymous'}")
    
    @staticmethod
    def log_database(query, params=None):
        """Log database query"""
        logger = get_logger('pickleball.db')
        if params:
            logger.debug(f"🔍 SQL: {query[:100]}... | Params: {str(params)[:50]}...")
        else:
            logger.debug(f"🔍 SQL: {query[:100]}...")
    
    @staticmethod
    def log_error(error, context=None):
        """Log error with context"""
        logger = get_logger()
        if context:
            logger.error(f"❌ {error} | Context: {context}")
        else:
            logger.error(f"❌ {error}")
    
    @staticmethod
    def log_success(message):
        """Log success"""
        logger = get_logger()
        logger.info(f"✅ {message}")
    
    @staticmethod
    def log_warning(message):
        """Log warning"""
        logger = get_logger()
        logger.warning(f"⚠️ {message}")

# ============ INIT LOGGING KHI IMPORT ============
setup_logging()
logger = get_logger('pickleball')

logger.info("=" * 60)
logger.info(f"🚀 {APP_NAME} v{APP_VERSION} started")
logger.info(f"🌐 Base URL: {BASE_URL}")
logger.info(f"📁 Log files: {LogConfig.LOG_DIR}/")
logger.info("=" * 60)