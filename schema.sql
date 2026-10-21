PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('student', 'faculty', 'admin')),
    department TEXT NOT NULL DEFAULT 'General',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS buildings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    code TEXT NOT NULL UNIQUE,
    department TEXT NOT NULL,
    total_area_sqft REAL NOT NULL CHECK (total_area_sqft > 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS utility_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    building_id INTEGER,
    utility_type TEXT NOT NULL CHECK (utility_type IN ('Electricity', 'Water', 'Waste', 'Transport')),
    consumption_value REAL NOT NULL CHECK (consumption_value > 0),
    unit TEXT NOT NULL,
    cost REAL NOT NULL DEFAULT 0 CHECK (cost >= 0),
    carbon_emission REAL NOT NULL CHECK (carbon_emission >= 0),
    recorded_date TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    logged_by INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (building_id) REFERENCES buildings (id) ON DELETE RESTRICT,
    FOREIGN KEY (logged_by) REFERENCES users (id) ON DELETE RESTRICT,
    CHECK (utility_type = 'Transport' OR building_id IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS eco_actions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    action_name TEXT NOT NULL,
    details TEXT NOT NULL DEFAULT '',
    points INTEGER NOT NULL CHECK (points > 0),
    completed_on TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_utility_logs_date ON utility_logs(recorded_date);
CREATE INDEX IF NOT EXISTS idx_utility_logs_type ON utility_logs(utility_type);
CREATE INDEX IF NOT EXISTS idx_utility_logs_user ON utility_logs(logged_by);
CREATE INDEX IF NOT EXISTS idx_utility_logs_building ON utility_logs(building_id);
CREATE INDEX IF NOT EXISTS idx_eco_actions_user ON eco_actions(user_id);
CREATE INDEX IF NOT EXISTS idx_eco_actions_date ON eco_actions(completed_on);
