"""SQLite connection and schema helpers for Campus Eco-Tracker."""
import sqlite3
from pathlib import Path

from flask import current_app, g


def get_db():
    """Return a request-scoped SQLite connection."""
    if "db" not in g:
        db_path = Path(current_app.config["DATABASE"])
        db_path.parent.mkdir(parents=True, exist_ok=True)
        g.db = sqlite3.connect(str(db_path), timeout=10)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        g.db.execute("PRAGMA busy_timeout = 10000")
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Create tables and seed the campus building registry if it's empty."""
    db = get_db()
    schema_path = Path(current_app.root_path) / "schema.sql"
    db.executescript(schema_path.read_text(encoding="utf-8"))
    building_count = db.execute("SELECT COUNT(*) FROM buildings").fetchone()[0]
    if building_count == 0:
        buildings = [
            ("CSE Block", "CSE", "Computer Science and Engineering", 42000),
            ("Mechanical Workshop", "MECH", "Mechanical Engineering", 36000),
            ("Admin Building", "ADMIN", "Administration", 28000),
            ("Central Library", "LIB", "Library Services", 24000),
            ("Biotechnology Center", "BIO", "Biotechnology", 31000),
            ("Student Hostel", "HOSTEL", "Student Welfare", 52000),
        ]
        db.executemany(
            "INSERT INTO buildings (name, code, department, total_area_sqft) VALUES (?, ?, ?, ?)",
            buildings,
        )
    db.commit()
