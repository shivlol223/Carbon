"""Campus Eco-Tracker: a student-friendly Flask + SQLite sustainability app."""
from __future__ import annotations

import csv
import io
import json
import os
import re
from datetime import date, datetime, timedelta
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from flask import (
    Flask, Response, abort, flash, g, jsonify, redirect, render_template,
    request, session, url_for,
)
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import check_password_hash, generate_password_hash

from database import close_db, get_db, init_db
from emissions import EMISSION_FACTORS, calculate_emissions

load_dotenv()
csrf = CSRFProtect()


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "local-dev-key-change-before-deployment"),
        DATABASE=os.environ.get("ECO_DATABASE", str(Path(app.instance_path) / "eco_tracker.db")),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
    )
    if test_config:
        app.config.update(test_config)
    csrf.init_app(app)
    app.teardown_appcontext(close_db)

    @app.context_processor
    def inject_globals():
        return {
            "current_user": g.get("user"),
            "utility_types": list(EMISSION_FACTORS.keys()),
            "today": date.today().isoformat(),
        }

    @app.before_request
    def load_logged_in_user():
        user_id = session.get("user_id")
        g.user = None
        if user_id is not None:
            g.user = get_db().execute(
                "SELECT id, full_name, username, email, role, department, created_at FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            if g.user is None:
                session.clear()

    def login_required(view):
        @wraps(view)
        def wrapped_view(**kwargs):
            if g.user is None:
                flash("Please sign in to access that page.", "info")
                return redirect(url_for("login", next=request.path))
            return view(**kwargs)
        return wrapped_view

    def roles_required(*roles):
        def decorator(view):
            @wraps(view)
            def wrapped_view(**kwargs):
                if g.user is None:
                    flash("Please sign in to continue.", "info")
                    return redirect(url_for("login", next=request.path))
                if g.user["role"] not in roles:
                    abort(403)
                return view(**kwargs)
            return wrapped_view
        return decorator

    # Make access decorators available to route functions and tests.
    app.login_required = login_required
    app.roles_required = roles_required

    @app.route("/")
    def index():
        if g.user:
            return redirect(url_for("dashboard"))
        db = get_db()
        try:
            totals = db.execute(
                "SELECT COUNT(*) AS logs, COALESCE(SUM(carbon_emission), 0) AS emissions FROM utility_logs"
            ).fetchone()
            building_count = db.execute("SELECT COUNT(*) FROM buildings").fetchone()[0]
            action_count = db.execute("SELECT COUNT(*) FROM eco_actions").fetchone()[0]
            leaders = db.execute(
                "SELECT u.full_name, u.department, COALESCE(SUM(a.points),0) AS points "
                "FROM users u LEFT JOIN eco_actions a ON a.user_id=u.id "
                "GROUP BY u.id ORDER BY points DESC, u.full_name LIMIT 5"
            ).fetchall()
        except Exception:
            totals = {"logs": 0, "emissions": 0}
            building_count, action_count, leaders = 0, 0, []
        return render_template("landing.html", totals=totals, building_count=building_count,
                               action_count=action_count, leaders=leaders)

    @app.route("/register", methods=("GET", "POST"))
    def register():
        if g.user:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            full_name = request.form.get("full_name", "").strip()
            username = request.form.get("username", "").strip().lower()
            email = request.form.get("email", "").strip().lower()
            department = request.form.get("department", "General").strip() or "General"
            password = request.form.get("password", "")
            confirm = request.form.get("confirm_password", "")
            error = None
            if len(full_name) < 2 or len(full_name) > 80:
                error = "Enter your full name (2–80 characters)."
            elif not re.fullmatch(r"[a-z0-9_.-]{3,30}", username):
                error = "Username must be 3–30 characters using letters, numbers, dots, underscores or hyphens."
            elif not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
                error = "Enter a valid email address."
            elif len(password) < 8:
                error = "Use a password with at least 8 characters."
            elif password != confirm:
                error = "The passwords do not match."
            elif len(department) > 80:
                error = "Department must be 80 characters or fewer."
            if error is None:
                db = get_db()
                try:
                    db.execute(
                        "INSERT INTO users (full_name, username, email, password_hash, role, department) "
                        "VALUES (?, ?, ?, ?, 'student', ?)",
                        (full_name, username, email, generate_password_hash(password), department),
                    )
                    db.commit()
                except Exception as exc:
                    if "UNIQUE constraint failed" in str(exc):
                        error = "That username or email is already registered."
                    else:
                        raise
                if error is None:
                    flash("Account created. Sign in to start tracking your eco-actions.", "success")
                    return redirect(url_for("login"))
            flash(error, "danger")
        return render_template("register.html")

    @app.route("/login", methods=("GET", "POST"))
    def login():
        if g.user:
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            username = request.form.get("username", "").strip().lower()
            password = request.form.get("password", "")
            user = get_db().execute(
                "SELECT * FROM users WHERE username = ? OR email = ?", (username, username)
            ).fetchone()
            if user is None or not check_password_hash(user["password_hash"], password):
                flash("Incorrect username/email or password.", "danger")
            else:
                session.clear()
                session["user_id"] = user["id"]
                flash(f"Welcome back, {user['full_name'].split()[0]}!", "success")
                next_url = request.args.get("next", "")
                # Prevent open redirects: only allow local relative paths.
                if next_url.startswith("/") and not next_url.startswith("//"):
                    return redirect(next_url)
                return redirect(url_for("dashboard"))
        return render_template("login.html")

    @app.post("/logout")
    @login_required
    def logout():
        session.clear()
        flash("You have been signed out.", "info")
        return redirect(url_for("index"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        db = get_db()
        summary = db.execute(
            "SELECT COUNT(*) AS log_count, COALESCE(SUM(carbon_emission),0) AS total_emissions, "
            "COALESCE(SUM(cost),0) AS total_cost, COUNT(DISTINCT building_id) AS buildings "
            "FROM utility_logs"
        ).fetchone()
        user_points = db.execute(
            "SELECT COALESCE(SUM(points),0) FROM eco_actions WHERE user_id = ?", (g.user["id"],)
        ).fetchone()[0]
        actions_total = db.execute("SELECT COUNT(*) FROM eco_actions").fetchone()[0]
        month_start = date.today().replace(day=1).isoformat()
        month_emissions = db.execute(
            "SELECT COALESCE(SUM(carbon_emission),0) FROM utility_logs WHERE recorded_date >= ?",
            (month_start,),
        ).fetchone()[0]
        type_rows = db.execute(
            "SELECT utility_type, ROUND(SUM(carbon_emission),2) AS emissions "
            "FROM utility_logs GROUP BY utility_type ORDER BY emissions DESC"
        ).fetchall()
        trend_rows = db.execute(
            "SELECT substr(recorded_date,1,7) AS month, ROUND(SUM(carbon_emission),2) AS emissions "
            "FROM utility_logs WHERE recorded_date >= date('now','-5 months','start of month') "
            "GROUP BY month ORDER BY month"
        ).fetchall()
        recent_logs = db.execute(
            "SELECT ul.*, b.name AS building_name, u.full_name AS logged_by_name "
            "FROM utility_logs ul LEFT JOIN buildings b ON b.id=ul.building_id "
            "JOIN users u ON u.id=ul.logged_by ORDER BY ul.recorded_date DESC, ul.id DESC LIMIT 6"
        ).fetchall()
        top_users = db.execute(
            "SELECT u.full_name, u.department, COALESCE(SUM(a.points),0) AS points "
            "FROM users u LEFT JOIN eco_actions a ON a.user_id=u.id "
            "GROUP BY u.id ORDER BY points DESC, u.full_name LIMIT 5"
        ).fetchall()
        return render_template(
            "dashboard.html", summary=summary, user_points=user_points,
            actions_total=actions_total, month_emissions=round(month_emissions, 2),
            type_labels=[r["utility_type"] for r in type_rows],
            type_values=[r["emissions"] for r in type_rows],
            trend_labels=[r["month"] for r in trend_rows],
            trend_values=[r["emissions"] for r in trend_rows],
            recent_logs=recent_logs, top_users=top_users,
        )

    @app.route("/buildings", methods=("GET", "POST"))
    @roles_required("admin")
    def buildings():
        db = get_db()
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            code = request.form.get("code", "").strip().upper()
            department = request.form.get("department", "").strip()
            try:
                area = float(request.form.get("total_area_sqft", "0"))
            except ValueError:
                area = 0
            if not name or not code or not department or area <= 0 or area > 100_000_000:
                flash("Enter a building name, code, department and a positive area.", "danger")
            else:
                try:
                    db.execute(
                        "INSERT INTO buildings (name, code, department, total_area_sqft) VALUES (?,?,?,?)",
                        (name, code, department, area),
                    )
                    db.commit()
                    flash("Building added successfully.", "success")
                    return redirect(url_for("buildings"))
                except Exception as exc:
                    if "UNIQUE constraint failed" in str(exc):
                        flash("Building name and code must be unique.", "danger")
                    else:
                        raise
        rows = db.execute(
            "SELECT b.*, COUNT(ul.id) AS log_count, COALESCE(SUM(ul.carbon_emission),0) AS emissions "
            "FROM buildings b LEFT JOIN utility_logs ul ON ul.building_id=b.id "
            "GROUP BY b.id ORDER BY b.name"
        ).fetchall()
        return render_template("buildings.html", buildings=rows)

    @app.route("/buildings/<int:building_id>/edit", methods=("GET", "POST"))
    @roles_required("admin")
    def edit_building(building_id: int):
        db = get_db()
        building = db.execute("SELECT * FROM buildings WHERE id=?", (building_id,)).fetchone()
        if building is None:
            abort(404)
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            code = request.form.get("code", "").strip().upper()
            department = request.form.get("department", "").strip()
            try:
                area = float(request.form.get("total_area_sqft", "0"))
            except ValueError:
                area = 0
            if not name or not code or not department or not (0 < area <= 100_000_000):
                flash("Complete every field and enter a positive area.", "danger")
            else:
                try:
                    db.execute(
                        "UPDATE buildings SET name=?, code=?, department=?, total_area_sqft=? WHERE id=?",
                        (name, code, department, area, building_id),
                    )
                    db.commit()
                    flash("Building details updated.", "success")
                    return redirect(url_for("buildings"))
                except Exception as exc:
                    if "UNIQUE constraint failed" in str(exc):
                        flash("Building name and code must be unique.", "danger")
                    else:
                        raise
        return render_template("building_edit.html", building=building)

    @app.post("/buildings/<int:building_id>/delete")
    @roles_required("admin")
    def delete_building(building_id: int):
        db = get_db()
        try:
            cursor = db.execute("DELETE FROM buildings WHERE id=?", (building_id,))
            db.commit()
            if cursor.rowcount:
                flash("Building deleted.", "success")
            else:
                flash("Building not found.", "warning")
        except Exception as exc:
            if "FOREIGN KEY constraint failed" in str(exc):
                flash("This building has utility logs. Delete or reassign those logs first.", "warning")
            else:
                raise
        return redirect(url_for("buildings"))

    @app.route("/utilities")
    @login_required
    def utilities():
        db = get_db()
        utility_type = request.args.get("type", "").strip()
        building_id = request.args.get("building_id", "").strip()
        start = request.args.get("start", "").strip()
        end = request.args.get("end", "").strip()
        clauses, params = [], []
        if utility_type in EMISSION_FACTORS:
            clauses.append("ul.utility_type=?")
            params.append(utility_type)
        if building_id.isdigit():
            clauses.append("ul.building_id=?")
            params.append(int(building_id))
        if start and re.fullmatch(r"\d{4}-\d{2}-\d{2}", start):
            clauses.append("ul.recorded_date>=?")
            params.append(start)
        if end and re.fullmatch(r"\d{4}-\d{2}-\d{2}", end):
            clauses.append("ul.recorded_date<=?")
            params.append(end)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        rows = db.execute(
            "SELECT ul.*, b.name AS building_name, u.full_name AS logged_by_name "
            "FROM utility_logs ul LEFT JOIN buildings b ON b.id=ul.building_id "
            "JOIN users u ON u.id=ul.logged_by " + where +
            " ORDER BY ul.recorded_date DESC, ul.id DESC LIMIT 500", params
        ).fetchall()
        buildings_list = db.execute("SELECT id,name FROM buildings ORDER BY name").fetchall()
        return render_template("utilities.html", logs=rows, buildings=buildings_list,
                               filters={"type": utility_type, "building_id": building_id,
                                        "start": start, "end": end})

    @app.route("/utilities/new", methods=("GET", "POST"))
    @roles_required("admin", "faculty")
    def new_utility():
        db = get_db()
        buildings_list = db.execute("SELECT id,name FROM buildings ORDER BY name").fetchall()
        if request.method == "POST":
            utility_type = request.form.get("utility_type", "")
            building_raw = request.form.get("building_id", "").strip()
            recorded_date = request.form.get("recorded_date", "").strip()
            notes = request.form.get("notes", "").strip()[:500]
            try:
                value = float(request.form.get("consumption_value", "0"))
                cost = float(request.form.get("cost", "0"))
            except ValueError:
                value, cost = 0, -1
            building_id = int(building_raw) if building_raw.isdigit() else None
            error = None
            if utility_type not in EMISSION_FACTORS:
                error = "Choose a valid utility type."
            elif value <= 0 or value > 1_000_000_000:
                error = "Consumption must be greater than zero and within a reasonable range."
            elif cost < 0 or cost > 1_000_000_000:
                error = "Cost cannot be negative or exceed the supported range."
            elif utility_type != "Transport" and building_id is None:
                error = "Select a building for this utility log."
            elif building_id is not None and db.execute("SELECT 1 FROM buildings WHERE id=?", (building_id,)).fetchone() is None:
                error = "Select a valid building."
            elif not re.fullmatch(r"\d{4}-\d{2}-\d{2}", recorded_date):
                error = "Choose a valid recorded date."
            elif recorded_date > date.today().isoformat():
                error = "Recorded date cannot be in the future."
            else:
                try:
                    datetime.strptime(recorded_date, "%Y-%m-%d")
                except ValueError:
                    error = "Choose a valid recorded date."
            if error:
                flash(error, "danger")
            else:
                emissions = calculate_emissions(utility_type, value)
                unit = EMISSION_FACTORS[utility_type]["unit"]
                db.execute(
                    "INSERT INTO utility_logs (building_id, utility_type, consumption_value, unit, cost, "
                    "carbon_emission, recorded_date, notes, logged_by) VALUES (?,?,?,?,?,?,?,?,?)",
                    (building_id, utility_type, value, unit, cost, emissions, recorded_date, notes, g.user["id"]),
                )
                db.commit()
                flash(f"Utility entry saved. Estimated footprint: {emissions:,.3f} kg CO₂e.", "success")
                return redirect(url_for("utilities"))
        return render_template("utility_form.html", buildings=buildings_list,
                               factors=EMISSION_FACTORS)

    @app.post("/utilities/<int:log_id>/delete")
    @roles_required("admin", "faculty")
    def delete_utility(log_id: int):
        db = get_db()
        log = db.execute("SELECT id, logged_by FROM utility_logs WHERE id=?", (log_id,)).fetchone()
        if log is None:
            flash("Utility log not found.", "warning")
        elif g.user["role"] != "admin" and log["logged_by"] != g.user["id"]:
            abort(403)
        else:
            db.execute("DELETE FROM utility_logs WHERE id=?", (log_id,))
            db.commit()
            flash("Utility log deleted.", "success")
        return redirect(url_for("utilities"))

    @app.route("/pledges", methods=("GET", "POST"))
    @login_required
    def pledges():
        db = get_db()
        action_points = {
            "Walk or cycle to campus": 10,
            "Use public transport": 8,
            "Carpool with others": 8,
            "Carry a reusable bottle or cup": 5,
            "Segregate waste responsibly": 5,
            "Join a campus clean-up": 15,
            "Plant or care for a tree": 15,
            "Save electricity or water": 8,
            "Bring reusable lunch containers": 5,
        }
        if request.method == "POST":
            action_name = request.form.get("action_name", "")
            details = request.form.get("details", "").strip()[:300]
            completed_on = request.form.get("completed_on", "").strip()
            error = None
            if action_name not in action_points:
                error = "Choose one of the available eco-actions."
            elif not re.fullmatch(r"\d{4}-\d{2}-\d{2}", completed_on):
                error = "Choose a valid completion date."
            elif completed_on > date.today().isoformat():
                error = "Completion date cannot be in the future."
            else:
                try:
                    datetime.strptime(completed_on, "%Y-%m-%d")
                except ValueError:
                    error = "Choose a valid completion date."
            if error:
                flash(error, "danger")
            else:
                db.execute(
                    "INSERT INTO eco_actions (user_id, action_name, details, points, completed_on) VALUES (?,?,?,?,?)",
                    (g.user["id"], action_name, details, action_points[action_name], completed_on),
                )
                db.commit()
                flash(f"Eco-action recorded. You earned {action_points[action_name]} green points!", "success")
                return redirect(url_for("pledges"))
        own_actions = db.execute(
            "SELECT * FROM eco_actions WHERE user_id=? ORDER BY completed_on DESC, id DESC LIMIT 25",
            (g.user["id"],),
        ).fetchall()
        total_points = db.execute("SELECT COALESCE(SUM(points),0) FROM eco_actions WHERE user_id=?", (g.user["id"],)).fetchone()[0]
        return render_template("pledges.html", actions=own_actions, action_points=action_points,
                               total_points=total_points)

    @app.post("/pledges/<int:action_id>/delete")
    @login_required
    def delete_pledge(action_id: int):
        db = get_db()
        action = db.execute("SELECT user_id FROM eco_actions WHERE id=?", (action_id,)).fetchone()
        if action is None:
            flash("Eco-action not found.", "warning")
        elif action["user_id"] != g.user["id"] and g.user["role"] != "admin":
            abort(403)
        else:
            db.execute("DELETE FROM eco_actions WHERE id=?", (action_id,))
            db.commit()
            flash("Eco-action removed.", "success")
        return redirect(url_for("pledges"))

    @app.route("/leaderboard")
    @login_required
    def leaderboard():
        rows = get_db().execute(
            "SELECT u.id, u.full_name, u.department, COALESCE(SUM(a.points),0) AS points, "
            "COUNT(a.id) AS actions FROM users u LEFT JOIN eco_actions a ON a.user_id=u.id "
            "GROUP BY u.id ORDER BY points DESC, actions DESC, u.full_name"
        ).fetchall()
        return render_template("leaderboard.html", leaders=rows)

    @app.route("/analytics")
    @login_required
    def analytics():
        db = get_db()
        start = request.args.get("start", "").strip()
        end = request.args.get("end", "").strip()
        utility_type = request.args.get("type", "").strip()
        building_id = request.args.get("building_id", "").strip()
        clauses, params = [], []
        if start and re.fullmatch(r"\d{4}-\d{2}-\d{2}", start):
            clauses.append("ul.recorded_date>=?"); params.append(start)
        if end and re.fullmatch(r"\d{4}-\d{2}-\d{2}", end):
            clauses.append("ul.recorded_date<=?"); params.append(end)
        if utility_type in EMISSION_FACTORS:
            clauses.append("ul.utility_type=?"); params.append(utility_type)
        if building_id.isdigit():
            clauses.append("ul.building_id=?"); params.append(int(building_id))
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        summary = db.execute(
            "SELECT COUNT(*) AS log_count, COALESCE(SUM(ul.consumption_value),0) AS consumption, "
            "COALESCE(SUM(ul.carbon_emission),0) AS emissions, COALESCE(SUM(ul.cost),0) AS cost "
            "FROM utility_logs ul " + where, params
        ).fetchone()
        by_type = db.execute(
            "SELECT ul.utility_type, ROUND(SUM(ul.carbon_emission),2) AS emissions, "
            "ROUND(SUM(ul.consumption_value),2) AS consumption, ROUND(SUM(ul.cost),2) AS cost "
            "FROM utility_logs ul " + where + " GROUP BY ul.utility_type ORDER BY emissions DESC", params
        ).fetchall()
        by_building = db.execute(
            "SELECT COALESCE(b.name,'Commute / no building') AS building_name, "
            "ROUND(SUM(ul.carbon_emission),2) AS emissions, COUNT(ul.id) AS entries "
            "FROM utility_logs ul LEFT JOIN buildings b ON b.id=ul.building_id " + where +
            " GROUP BY b.id ORDER BY emissions DESC", params
        ).fetchall()
        trend = db.execute(
            "SELECT substr(ul.recorded_date,1,7) AS month, ROUND(SUM(ul.carbon_emission),2) AS emissions "
            "FROM utility_logs ul " + where + " GROUP BY month ORDER BY month", params
        ).fetchall()
        buildings_list = db.execute("SELECT id,name FROM buildings ORDER BY name").fetchall()
        return render_template("analytics.html", summary=summary, by_type=by_type,
                               by_building=by_building, trend_labels=[r["month"] for r in trend],
                               trend_values=[r["emissions"] for r in trend], buildings=buildings_list,
                               filters={"start": start, "end": end, "type": utility_type,
                                        "building_id": building_id})

    @app.get("/export/utility-logs.csv")
    @roles_required("admin", "faculty")
    def export_utility_logs():
        db = get_db()
        rows = db.execute(
            "SELECT ul.id, ul.recorded_date, b.name AS building, ul.utility_type, "
            "ul.consumption_value, ul.unit, ul.cost, ul.carbon_emission, ul.notes, u.full_name AS logged_by "
            "FROM utility_logs ul LEFT JOIN buildings b ON b.id=ul.building_id "
            "JOIN users u ON u.id=ul.logged_by ORDER BY ul.recorded_date DESC, ul.id DESC"
        ).fetchall()
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(["ID", "Recorded date", "Building", "Utility type", "Consumption", "Unit", "Cost (INR)", "Estimated kg CO2e", "Notes", "Logged by"])
        for row in rows:
            writer.writerow([row[k] for k in row.keys()])
        return Response(output.getvalue(), mimetype="text/csv",
                        headers={"Content-Disposition": "attachment; filename=campus-utility-logs.csv"})

    @app.route("/admin/users", methods=("GET", "POST"))
    @roles_required("admin")
    def manage_users():
        db = get_db()
        if request.method == "POST":
            user_id = request.form.get("user_id", "")
            role = request.form.get("role", "")
            if not user_id.isdigit() or role not in ("student", "faculty", "admin"):
                flash("Choose a valid user and role.", "danger")
            elif int(user_id) == g.user["id"]:
                flash("You cannot change your own role while signed in.", "warning")
            else:
                db.execute("UPDATE users SET role=? WHERE id=?", (role, int(user_id)))
                db.commit()
                flash("User role updated.", "success")
                return redirect(url_for("manage_users"))
        rows = db.execute(
            "SELECT u.id, u.full_name, u.username, u.email, u.role, u.department, u.created_at, "
            "COALESCE(SUM(a.points),0) AS points FROM users u LEFT JOIN eco_actions a ON a.user_id=u.id "
            "GROUP BY u.id ORDER BY u.created_at DESC"
        ).fetchall()
        return render_template("users.html", users=rows)

    @app.route("/profile/password", methods=("GET", "POST"))
    @login_required
    def change_password():
        if request.method == "POST":
            current = request.form.get("current_password", "")
            new = request.form.get("new_password", "")
            confirm = request.form.get("confirm_password", "")
            user = get_db().execute("SELECT password_hash FROM users WHERE id=?", (g.user["id"],)).fetchone()
            error = None
            if not check_password_hash(user["password_hash"], current):
                error = "Your current password is incorrect."
            elif len(new) < 8:
                error = "Your new password must contain at least 8 characters."
            elif new != confirm:
                error = "The new passwords do not match."
            if error:
                flash(error, "danger")
            else:
                db = get_db()
                db.execute("UPDATE users SET password_hash=? WHERE id=?", (generate_password_hash(new), g.user["id"]))
                db.commit()
                flash("Password changed successfully.", "success")
                return redirect(url_for("dashboard"))
        return render_template("change_password.html")

    @app.get("/api/summary")
    @login_required
    def api_summary():
        db = get_db()
        row = db.execute(
            "SELECT COUNT(*) AS utility_logs, ROUND(COALESCE(SUM(carbon_emission),0),2) AS estimated_kg_co2e, "
            "ROUND(COALESCE(SUM(cost),0),2) AS recorded_cost_inr FROM utility_logs"
        ).fetchone()
        return jsonify(dict(row))

    @app.get("/api/analytics")
    @login_required
    def api_analytics():
        db = get_db()
        rows = db.execute(
            "SELECT utility_type, ROUND(SUM(carbon_emission),2) AS kg_co2e "
            "FROM utility_logs GROUP BY utility_type ORDER BY kg_co2e DESC"
        ).fetchall()
        return jsonify({"emissions_by_utility": [dict(r) for r in rows],
                        "factors_note": "Illustrative educational factors; not official inventory values."})

    @app.route("/health")
    def health():
        return jsonify({"status": "ok", "application": "Campus Eco-Tracker"})

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("error.html", code=403,
                               message="You do not have permission to access this page."), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", code=404, message="The page or record could not be found."), 404

    @app.cli.command("init-db")
    def init_db_command():
        init_db()
        print("Database tables initialized. Run `python init_db.py` to seed demo data.")

    return app


app = create_app()

if __name__ == "__main__":
    # For local coursework only. Do not use Flask's development server in production.
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", "5000")), debug=os.environ.get("FLASK_DEBUG", "1") == "1")
