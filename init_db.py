"""Initialize the database and add sample records for the coursework demo.

Run: python init_db.py
This script is idempotent: it does not duplicate the demo users or sample logs.
"""
from datetime import date, timedelta

from werkzeug.security import generate_password_hash

from app import app
from database import get_db, init_db

DEMO_USERS = [
    ("Campus Administrator", "admin", "admin@campus.local", "admin", "Administration"),
    ("Faculty Demo", "faculty", "faculty@campus.local", "faculty", "Computer Science and Engineering"),
    ("Student Demo", "student", "student@campus.local", "student", "Computer Science and Engineering"),
]
DEMO_PASSWORD = "EcoTrack@2026"


def seed_demo_data():
    db = get_db()
    for full_name, username, email, role, department in DEMO_USERS:
        exists = db.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
        if not exists:
            db.execute(
                "INSERT INTO users (full_name,username,email,password_hash,role,department) VALUES (?,?,?,?,?,?)",
                (full_name, username, email, generate_password_hash(DEMO_PASSWORD), role, department),
            )
    db.commit()

    if db.execute("SELECT COUNT(*) FROM utility_logs").fetchone()[0] == 0:
        user_id = db.execute("SELECT id FROM users WHERE username='faculty'").fetchone()[0]
        buildings = {r["code"]: r["id"] for r in db.execute("SELECT id,code FROM buildings").fetchall()}
        samples = [
            ("CSE", "Electricity", 1280, "kWh", 10880, .85, 2),
            ("LIB", "Electricity", 960, "kWh", 8160, .85, 9),
            ("ADMIN", "Water", 6200, "litres", 1240, .001, 14),
            ("HOSTEL", "Water", 12500, "litres", 2500, .001, 19),
            ("MECH", "Waste", 95, "kg", 760, .57, 25),
            (None, "Transport", 36, "km", 0, .12, 28),
            ("CSE", "Electricity", 1175, "kWh", 9990, .85, 35),
            ("LIB", "Electricity", 885, "kWh", 7522.5, .85, 42),
            ("HOSTEL", "Waste", 122, "kg", 975, .57, 48),
            (None, "Transport", 24, "km", 0, .12, 53),
            ("ADMIN", "Water", 5700, "litres", 1140, .001, 60),
            ("BIO", "Electricity", 740, "kWh", 6290, .85, 67),
        ]
        today = date.today()
        for code, utility_type, value, unit, cost, factor, days_ago in samples:
            recorded = (today - timedelta(days=days_ago)).isoformat()
            building_id = buildings.get(code) if code else None
            db.execute(
                "INSERT INTO utility_logs (building_id,utility_type,consumption_value,unit,cost,carbon_emission,recorded_date,notes,logged_by) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (building_id, utility_type, value, unit, cost, round(value * factor, 3), recorded,
                 "Illustrative sample record", user_id),
            )
    if db.execute("SELECT COUNT(*) FROM eco_actions").fetchone()[0] == 0:
        users = {r["username"]: r["id"] for r in db.execute("SELECT id,username FROM users").fetchall()}
        sample_actions = [
            ("student", "Walk or cycle to campus", "Walked for the morning commute", 10, 3),
            ("student", "Carry a reusable bottle or cup", "Reusable bottle used all day", 5, 2),
            ("student", "Segregate waste responsibly", "Sorted dry and wet waste", 5, 1),
            ("faculty", "Save electricity or water", "Switched off unused classroom lights", 8, 2),
        ]
        today = date.today()
        for username, action, details, points, days_ago in sample_actions:
            db.execute(
                "INSERT INTO eco_actions (user_id,action_name,details,points,completed_on) VALUES (?,?,?,?,?)",
                (users[username], action, details, points, (today - timedelta(days=days_ago)).isoformat()),
            )
    db.commit()


if __name__ == "__main__":
    with app.app_context():
        init_db()
        seed_demo_data()
        print("Database initialized and sample campus data is ready.")
        print("Demo sign-in accounts (all use the same local demo password):")
        print("  admin   / EcoTrack@2026  (building + user administration)")
        print("  faculty / EcoTrack@2026  (utility entry and CSV export)")
        print("  student / EcoTrack@2026  (eco-pledges and leaderboard)")
        print("Change demo passwords before sharing or deploying this app.")
