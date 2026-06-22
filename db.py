from contextlib import contextmanager
from threading import Lock

import psycopg2
from psycopg2.pool import ThreadedConnectionPool

from config import DB_CONFIG, DB_CONFIG_ERROR, DB_POOL_MAX, DB_POOL_MIN

_pool = None
_pool_lock = Lock()


def _get_pool():
    global _pool
    if DB_CONFIG_ERROR:
        raise RuntimeError(DB_CONFIG_ERROR)

    if _pool is None:
        with _pool_lock:
            if _pool is None:
                _pool = ThreadedConnectionPool(DB_POOL_MIN, DB_POOL_MAX, **DB_CONFIG)
    return _pool


def get_connection():
    """Get a PostgreSQL connection from the process-local pool."""
    return _get_pool().getconn()


def release_connection(conn):
    """Return a connection to the process-local pool."""
    if conn is not None:
        _get_pool().putconn(conn)


@contextmanager
def db_cursor(commit=False):
    """Yield a cursor and always return the connection to the pool."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        if commit:
            conn.commit()
        else:
            conn.rollback()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        release_connection(conn)
