from contextlib import contextmanager

import psycopg2

from config import DB_CONFIG, DB_CONFIG_ERROR


def get_connection():
    """Create a PostgreSQL connection with one central config check."""
    if DB_CONFIG_ERROR:
        raise RuntimeError(DB_CONFIG_ERROR)
    return psycopg2.connect(**DB_CONFIG)


@contextmanager
def db_cursor(commit=False):
    """Yield a cursor and always close the cursor/connection."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        if commit:
            conn.commit()
    except Exception:
        if commit:
            conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()
