# Campus Eco-Tracker & Carbon Footprint Monitor

A full-stack coursework project for **Full Stack Technologies (22CSE71), AAT-1**. Campus Eco-Tracker is a responsive web application for recording campus electricity, water, waste and commute data; estimating carbon-equivalent emissions; viewing sustainability analytics; managing campus buildings and users; and rewarding student eco-actions.

> **Academic demonstration note:** The project uses sample data and simplified emission factors to demonstrate full-stack development. The factors are not official, location-specific or independently verified greenhouse-gas inventory values. Do not use the figures as official institutional disclosures.

## Features

- **Authentication and roles:** login, student registration, password hashing, session cookies, password changes, and `student`, `faculty`, and `admin` permissions.
- **Campus dashboard:** total estimated emissions, utility entries, entered utility costs, individual green points, recent activity, and leaderboard previews.
- **Utility entry and tracking:** add Electricity, Water, Waste and Transport records, validate inputs, automatically compute an estimated CO₂e value, filter the list and delete permitted records.
- **Building directory:** admin-only add, edit and delete operations, unique building codes, department ownership, area and linked utility totals.
- **Eco-actions and gamification:** log actions from a controlled list, earn fixed demonstration points, and view the campus leaderboard.
- **Analytics:** filters for date range, utility type and building; monthly trend and utility-source charts; utility/building breakdown tables.
- **CSV export:** faculty and admin users can export utility records for report preparation.
- **JSON endpoints:** `/api/summary` and `/api/analytics` for a small REST-style interface; `/health` for a health check.
- **Version-control hygiene:** local SQLite databases, environment secrets, virtual environments and Python cache files are excluded by `.gitignore`.

## Technology stack

- Frontend: HTML5, CSS3, Bootstrap 5, JavaScript (ES6+), Chart.js
- Backend: Python 3.10+ and Flask
- Database: SQLite with foreign keys, indexes and parameterized SQL
- Security basics: Werkzeug password hashing, Flask-WTF CSRF protection, role checks, and safe redirects after login

## Project structure

```text
campus-eco-tracker/
├── app.py                 # Routes, session auth, role checks and JSON API
├── database.py            # Request-scoped SQLite connections and schema init
├── emissions.py           # Emission factors and carbon calculation helper
├── init_db.py             # Database initialization plus optional sample data
├── schema.sql              # Relational schema, constraints and indexes
├── requirements.txt       # Python dependencies
├── .env.example           # Example local environment settings
├── .gitignore
├── instance/              # Local database is created here; database is ignored by Git
├── templates/              # Jinja pages and shared base layout
├── static/
│   ├── css/style.css       # Responsive UI styles
│   └── js/app.js           # Chart rendering and live estimate preview
└── tests/test_app.py       # Basic smoke / integration tests
```

## Run locally (Windows, VS Code or terminal)

Install **Python 3.10 or newer** and Git. Open a terminal in the project folder.

### 1. Create and activate a virtual environment

**Windows PowerShell**

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, you can use Command Prompt instead:

```bat
.venv\Scripts\activate.bat
```

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure a local secret (recommended)

Make a local copy of `.env.example` named `.env` and replace `SECRET_KEY` with a long random value. Keep `.env` private; it is excluded from Git.

PowerShell example to generate a key:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Paste the generated value into `.env`, for example:

```env
SECRET_KEY=paste-your-generated-value-here
FLASK_DEBUG=1
```

### 4. Create the database and sample records

```bash
python init_db.py
```

This creates `instance/eco_tracker.db`, the initial campus buildings, demo accounts, sample utility records and sample eco-actions. It is safe to run again: it will not duplicate demo users or sample rows when records already exist.

### 5. Start the application

```bash
python app.py
```

Open **http://127.0.0.1:5000** in your browser. Stop the server with `Ctrl+C`.

### Local demonstration accounts

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `EcoTrack@2026` |
| Faculty | `faculty` | `EcoTrack@2026` |
| Student | `student` | `EcoTrack@2026` |

These are **demo-only credentials** created by `init_db.py`. Sign in and use **Change password** before showing/sharing your local demo. Do not reuse the demo passwords in a production deployment. Public registration creates student accounts; an admin assigns faculty/admin roles in **Manage → Users & roles**.

## How to demonstrate the project

1. Sign in as `admin` and show the dashboard, building directory, and user-role management.
2. Sign in as `faculty`, open **Utility logs → Add utility entry**, and record a test reading. The form previews the estimated CO₂e result before saving.
3. Open **Analytics** and filter by dates, utility type or building. Show the monthly chart and breakdown tables.
4. Download the CSV export using a faculty or admin account.
5. Sign in as `student`, record an eco-action, and open **Leaderboard** to see the points.
6. Show the JSON endpoints at `/api/summary` and `/api/analytics` while signed in, and `/health` for a simple health response.

## Carbon calculation used

For each record, the app multiplies the consumption value by the illustrative factor below:

| Category | Unit | Factor used by the demo |
|---|---|---:|
| Electricity | kWh | 0.85 kg CO₂e per kWh |
| Water | litre | 0.001 kg CO₂e per litre |
| Waste | kg | 0.57 kg CO₂e per kg |
| Transport | km | 0.12 kg CO₂e per km |

The Electricity, Water and Transport factors follow the values stated in the supplied AAT report. The Waste factor is an additional illustrative assumption to let the project track waste as described in the report. Replace all factors with properly sourced and suitable factors before using real institutional data. Each record stores the calculated value at the time of entry; changing factors later does not automatically recalculate historical rows.

## Run tests

```bash
python -m pytest -q
```

The included tests cover account registration, dashboard access, permissions, utility emission calculation, eco-action logging, building creation, analytics and CSV output.

## GitHub: push this project

The report lists the target repository as `https://github.com/shivamkapoor/campus-eco-tracker.git`. First make sure that repository exists under your GitHub account. From the project root, run:

```bash
git init -b main
git add .
git status
git commit -m "Build Campus Eco-Tracker full-stack application"
git remote add origin https://github.com/shivamkapoor/campus-eco-tracker.git
git push -u origin main
```

If Git reports that `origin` already exists, check it instead of adding it again:

```bash
git remote -v
# If the URL is incorrect, update it:
git remote set-url origin https://github.com/shivamkapoor/campus-eco-tracker.git
git push -u origin main
```

If you created the GitHub repository with a README, license or `.gitignore`, GitHub may have an initial commit that your local folder does not have. The simplest coursework workflow is to create the GitHub repository as **empty** (do not pre-add a README), then push using the commands above. If the repository is not empty, integrate its initial commit before pushing rather than force-pushing over it.

### Important Git checks

```bash
git status
git remote -v
git log --oneline -5
```

Confirm that `.env`, `.venv/`, `instance/eco_tracker.db` and `__pycache__/` are not listed by `git status` before committing. The `.gitignore` already excludes them.

## Known scope / future improvements

- Utility readings are entered manually. This version does not connect to live meters, campus sensors or external utility providers.
- Charts show records stored in the application, not sensor-driven real-time data.
- Emission factors and eco-points are simplified for academic demonstration and require verified sources for real use.
- Possible extensions: monthly report PDF generation, approval workflow, verified factor configuration, department-level targets, and meter / IoT integration.

## AAT alignment

This implementation supports the report's requested full-stack sustainability dashboard, SQLite relational storage, user roles, building and utility management, carbon estimation, analytics, eco-action leaderboard, GitHub documentation and version control. Review the report's stated factors and screenshots against the running application before final submission.
