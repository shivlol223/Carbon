from pathlib import Path

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from database import get_db, init_db


@pytest.fixture()
def app(tmp_path: Path):
    test_app = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test-secret-key",
        "DATABASE": str(tmp_path / "test.db"),
    })
    with test_app.app_context():
        init_db()
        db = get_db()
        db.execute(
            "INSERT INTO users (full_name,username,email,password_hash,role,department) VALUES (?,?,?,?,?,?)",
            ("Test Admin", "admin", "admin@test.local", generate_password_hash("Password123!"), "admin", "Administration"),
        )
        db.execute(
            "INSERT INTO users (full_name,username,email,password_hash,role,department) VALUES (?,?,?,?,?,?)",
            ("Test Faculty", "faculty", "faculty@test.local", generate_password_hash("Password123!"), "faculty", "CSE"),
        )
        db.execute(
            "INSERT INTO users (full_name,username,email,password_hash,role,department) VALUES (?,?,?,?,?,?)",
            ("Test Student", "student", "student@test.local", generate_password_hash("Password123!"), "student", "CSE"),
        )
        db.commit()
    yield test_app


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, username, password="Password123!"):
    return client.post("/login", data={"username": username, "password": password}, follow_redirects=True)


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json["status"] == "ok"


def test_register_creates_student_account(client, app):
    response = client.post("/register", data={
        "full_name": "New Student", "username": "newstudent", "email": "newstudent@test.local",
        "department": "CSE", "password": "a-strong-password", "confirm_password": "a-strong-password",
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Account created" in response.data
    with app.app_context():
        row = get_db().execute("SELECT role FROM users WHERE username='newstudent'").fetchone()
        assert row["role"] == "student"


def test_login_dashboard_and_json_api(client):
    login(client, "admin")
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert b"Carbon footprint over time" in response.data
    api = client.get("/api/summary")
    assert api.status_code == 200
    assert "estimated_kg_co2e" in api.json


def test_student_cannot_manage_buildings(client):
    login(client, "student")
    response = client.get("/buildings")
    assert response.status_code == 403


def test_utility_entry_calculates_emissions(client, app):
    login(client, "faculty")
    with app.app_context():
        building_id = get_db().execute("SELECT id FROM buildings WHERE code='CSE'").fetchone()[0]
    response = client.post("/utilities/new", data={
        "utility_type": "Electricity", "building_id": str(building_id),
        "consumption_value": "100", "cost": "500", "recorded_date": "2026-10-20", "notes": "test meter",
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"85.000 kg CO" in response.data
    with app.app_context():
        row = get_db().execute("SELECT carbon_emission, unit FROM utility_logs WHERE notes='test meter'").fetchone()
        assert row["carbon_emission"] == 85.0
        assert row["unit"] == "kWh"


def test_student_can_log_eco_action(client, app):
    login(client, "student")
    response = client.post("/pledges", data={
        "action_name": "Walk or cycle to campus", "details": "Test action", "completed_on": "2026-10-20",
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"earned 10 green points" in response.data
    with app.app_context():
        points = get_db().execute("SELECT SUM(points) FROM eco_actions").fetchone()[0]
        assert points == 10


def test_admin_can_add_building(client, app):
    login(client, "admin")
    response = client.post("/buildings", data={
        "name": "Test Greenhouse", "code": "GREEN", "department": "Sustainability", "total_area_sqft": "5000",
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Test Greenhouse" in response.data


def test_analytics_and_csv_export(client):
    login(client, "faculty")
    assert client.get("/analytics").status_code == 200
    export = client.get("/export/utility-logs.csv")
    assert export.status_code == 200
    assert "text/csv" in export.content_type
    assert b"Recorded date" in export.data
