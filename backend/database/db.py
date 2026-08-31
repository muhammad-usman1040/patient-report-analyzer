"""
Database layer — SQLite via raw sqlite3, matching schema.sql exactly.

Why sqlite3 over SQLAlchemy: schema.sql uses simple CREATE TABLE statements with
no ORM-specific features; sqlite3 keeps the dependency count minimal and maps
directly to the SQL schema already defined. Can be swapped for PostgreSQL later
by replacing the connection factory.

All sensitive data (passwords) is never stored in plain text.
Raw OCR text and raw file bytes are never persisted here.
"""
import os
import sqlite3
import json
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, Dict, Any, List

BASE = Path(__file__).parent.parent
DB_PATH: str = os.getenv("DATABASE_URL", str(BASE / "reports.db"))
SCHEMA_PATH = BASE / "database" / "schema.sql"


def _get_db_path() -> str:
    """Resolve the SQLite file path, stripping any sqlite:/// scheme prefix."""
    # Support sqlite:///path syntax if DATABASE_URL is set that way
    path = DB_PATH
    if path.startswith("sqlite:///"):
        path = path[len("sqlite:///"):]
    return path


@contextmanager
def get_connection():
    conn = sqlite3.connect(_get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create tables from schema.sql if they don't exist."""
    with open(SCHEMA_PATH) as f:
        schema = f.read()
    with get_connection() as conn:
        conn.executescript(schema)


# ---------------------------------------------------------------------------
# User operations
# ---------------------------------------------------------------------------

def create_user(email: str, password_hash: str) -> Optional[Dict[str, Any]]:
    """Insert a new user. Returns the created user row or None on duplicate."""
    try:
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO Users (email, password_hash) VALUES (?, ?)",
                (email.lower().strip(), password_hash),
            )
            user_id = cur.lastrowid
        return get_user_by_id(user_id)
    except sqlite3.IntegrityError:
        return None  # Duplicate email


def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Return user row (id, email, password_hash, created_at) or None if not found."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, email, password_hash, created_at FROM Users WHERE email = ?",
            (email.lower().strip(),),
        ).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Return user row (id, email, created_at) by primary key, or None."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id, email, created_at FROM Users WHERE id = ?",
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Report persistence
# ---------------------------------------------------------------------------

def save_report(
    user_id: int,
    gender: Optional[str],
    age: Optional[int],
    output_format: str,
    flagged: Dict[str, Any],
    analysis: Dict[str, Any],
) -> int:
    """
    Persist report metadata, test results, and analysis results.
    Returns the new report_id.
    Raw file content and raw OCR text are never passed here.
    """
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO Reports (user_id, patient_gender, patient_age, output_format) "
            "VALUES (?, ?, ?, ?)",
            (user_id, gender, age, output_format),
        )
        report_id = cur.lastrowid

        # Test_Results: one row per parameter
        test_rows = [
            (report_id, info["category"], param, info["value"], info["unit"], info["status"])
            for param, info in flagged.items()
        ]
        conn.executemany(
            "INSERT INTO Test_Results (report_id, test_category, parameter_name, value, unit, status) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            test_rows,
        )

        # Analysis_Results
        result_type = analysis["result_state"]
        if result_type == "possible_conditions" and analysis["conditions"]:
            analysis_rows = [
                (
                    report_id,
                    result_type,
                    c["name"],
                    c["confidence"],
                    json.dumps(c["supporting_indicators"]),
                )
                for c in analysis["conditions"]
            ]
        else:
            analysis_rows = [(report_id, result_type, None, None, None)]

        conn.executemany(
            "INSERT INTO Analysis_Results "
            "(report_id, result_type, condition_name, confidence_score, supporting_indicators) "
            "VALUES (?, ?, ?, ?, ?)",
            analysis_rows,
        )

    return report_id


# ---------------------------------------------------------------------------
# History retrieval
# ---------------------------------------------------------------------------

def get_user_history(user_id: int) -> Dict[str, Any]:
    """
    Return history in the shape expected by HistoryPage.jsx / sample_history.json:
    {
      "reports": [...],
      "trends": { "Hemoglobin": [{"date": ..., "value": ...}], ... }
    }
    """
    with get_connection() as conn:
        reports_rows = conn.execute(
            "SELECT id, report_date, patient_gender, patient_age "
            "FROM Reports WHERE user_id = ? ORDER BY report_date DESC",
            (user_id,),
        ).fetchall()

        reports = []
        for r in reports_rows:
            report_id = r["id"]

            params_rows = conn.execute(
                "SELECT parameter_name, value, unit, status, test_category "
                "FROM Test_Results WHERE report_id = ?",
                (report_id,),
            ).fetchall()

            analysis_rows = conn.execute(
                "SELECT result_type, condition_name "
                "FROM Analysis_Results WHERE report_id = ?",
                (report_id,),
            ).fetchall()

            result_type = analysis_rows[0]["result_type"] if analysis_rows else "insufficient_evidence"
            conditions = [
                row["condition_name"]
                for row in analysis_rows
                if row["condition_name"]
            ]

            reports.append({
                "id": report_id,
                "report_date": r["report_date"],
                "result_state": result_type,
                "conditions": conditions,
                "parameters": [
                    {
                        "name": p["parameter_name"],
                        "value": p["value"],
                        "unit": p["unit"],
                        "status": p["status"],
                    }
                    for p in params_rows
                ],
            })

        # Build trends: { param_name: [{date, value}, ...] } — oldest first
        all_params_rows = conn.execute(
            """
            SELECT tr.parameter_name, r.report_date, tr.value
            FROM Test_Results tr
            JOIN Reports r ON r.id = tr.report_id
            WHERE r.user_id = ?
            ORDER BY r.report_date ASC
            """,
            (user_id,),
        ).fetchall()

    trends: Dict[str, List] = {}
    for row in all_params_rows:
        name = row["parameter_name"]
        if name not in trends:
            trends[name] = []
        trends[name].append({"date": row["report_date"][:10], "value": row["value"]})

    return {"reports": reports, "trends": trends}
