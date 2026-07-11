"""
db.py — SQLite database management for SpaceTrackOps
"""

import logging
import os
import sqlite3
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DB_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(DB_DIR, "spacetrackops.db")
_OLD_DB_PATH = os.path.join(DB_DIR, "aegis.db")


def _migrate_db_file() -> None:
    """Rename legacy aegis.db to spacetrackops.db if needed."""
    if os.path.exists(_OLD_DB_PATH) and not os.path.exists(DB_PATH):
        os.rename(_OLD_DB_PATH, DB_PATH)
        logger.info("Migrated database: aegis.db -> spacetrackops.db")


@contextmanager
def get_conn():
    """Context manager for SQLite connections with Row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    """Create tables, indexes, and run any pending migrations."""
    _migrate_db_file()

    with get_conn() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS satellites (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                norad_id    TEXT UNIQUE NOT NULL,
                name        TEXT NOT NULL,
                tle1        TEXT NOT NULL,
                tle2        TEXT NOT NULL,
                last_updated TEXT,
                category    TEXT
            )
        """)

        # Migration: add category column to existing DBs that predate this schema
        try:
            cursor.execute("ALTER TABLE satellites ADD COLUMN category TEXT")
            logger.info("Migration: added 'category' column to satellites table.")
        except Exception:
            # Column already exists — this is expected on any run after the first
            pass

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conjunctions (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                sat1     TEXT NOT NULL,
                sat2     TEXT NOT NULL,
                tca      TEXT NOT NULL,
                distance REAL NOT NULL,
                velocity REAL,
                risk     TEXT
            )
        """)

        # Indexes for frequently queried columns
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_satellites_category ON satellites(category)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_satellites_name ON satellites(name)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conjunctions_risk ON conjunctions(risk)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_conjunctions_distance ON conjunctions(distance)
        """)

        conn.commit()
    logger.info("Database initialised at %s", DB_PATH)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
