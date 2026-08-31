-- Patient Report Analyzer — SQLite Schema

CREATE TABLE IF NOT EXISTS Users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS Reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES Users(id) ON DELETE CASCADE,
    report_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    patient_gender TEXT,
    patient_age INTEGER,
    output_format TEXT DEFAULT 'screen'
);

CREATE TABLE IF NOT EXISTS Test_Results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL REFERENCES Reports(id) ON DELETE CASCADE,
    test_category TEXT NOT NULL,
    parameter_name TEXT NOT NULL,
    value REAL,
    unit TEXT,
    status TEXT CHECK(status IN ('normal', 'high', 'low', 'unknown'))
);

CREATE TABLE IF NOT EXISTS Normal_Ranges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    parameter_name TEXT NOT NULL,
    gender TEXT DEFAULT 'general',
    min_value REAL,
    max_value REAL,
    unit TEXT
);

CREATE TABLE IF NOT EXISTS Condition_Indicators (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    condition_name TEXT NOT NULL,
    parameter_name TEXT NOT NULL,
    direction TEXT CHECK(direction IN ('high', 'low', 'present', 'absent')),
    weight REAL DEFAULT 1.0
);

CREATE TABLE IF NOT EXISTS Analysis_Results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL REFERENCES Reports(id) ON DELETE CASCADE,
    result_type TEXT CHECK(result_type IN ('possible_conditions', 'all_normal', 'insufficient_evidence')),
    condition_name TEXT,
    confidence_score REAL,
    supporting_indicators TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
