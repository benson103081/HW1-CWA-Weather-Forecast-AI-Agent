"""SQLite persistence with atomic upserts and parameterized queries."""
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "weather.db"


def init_db(db_path=DB_PATH):
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as connection, connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS forecast (
                region TEXT NOT NULL,
                date TEXT NOT NULL,
                min_temp REAL NOT NULL,
                max_temp REAL NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (region, date),
                CHECK (min_temp <= max_temp)
            )
        """)


def upsert_forecasts(rows, db_path=DB_PATH):
    timestamp = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    values = [(row["region"], row["date"], row["min_temp"], row["max_temp"], timestamp) for row in rows]
    with closing(sqlite3.connect(db_path)) as connection, connection:
        connection.executemany("""
            INSERT INTO forecast (region, date, min_temp, max_temp, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(region, date) DO UPDATE SET
                min_temp=excluded.min_temp,
                max_temp=excluded.max_temp,
                updated_at=excluded.updated_at
        """, values)
    return len(values)


def list_dates(db_path=DB_PATH):
    with closing(sqlite3.connect(db_path)) as connection:
        return [row[0] for row in connection.execute("SELECT DISTINCT date FROM forecast ORDER BY date")]


def get_forecasts(day, db_path=DB_PATH):
    with closing(sqlite3.connect(db_path)) as connection:
        connection.row_factory = sqlite3.Row
        return [dict(row) for row in connection.execute(
            "SELECT region, date, min_temp, max_temp, updated_at FROM forecast WHERE date = ? ORDER BY region", (day,)
        )]
