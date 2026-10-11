"""Database connection helper (PostgreSQL + pgvector)."""
import psycopg

from app.config import get_settings


def connect() -> psycopg.Connection:
    """Open a connection to the database described by DATABASE_URL.

    autocommit=True: every statement is committed right away, unless we group several of
    them explicitly with `with conn.transaction():` (we do that when saving chunks).
    """
    url = get_settings().database_url.get_secret_value()
    if not url:
        raise RuntimeError("DATABASE_URL is empty. Set it in your .env file.")
    return psycopg.connect(url, autocommit=True)