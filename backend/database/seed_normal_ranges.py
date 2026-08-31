"""Seed Normal_Ranges table from normal_ranges.json."""
import json
import sqlite3
from pathlib import Path

BASE = Path(__file__).parent.parent
RANGES_FILE = BASE / "data" / "normal_ranges.json"
DB_FILE = BASE / "reports.db"


def seed():
    with open(RANGES_FILE) as f:
        data = json.load(f)

    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    with open(BASE / "database" / "schema.sql") as f:
        conn.executescript(f.read())

    cur.execute("DELETE FROM Normal_Ranges")

    rows = []
    for category, params in data.items():
        for param, info in params.items():
            unit = info.get("unit", "")
            for gender, limits in info.items():
                if gender in ("male", "female", "general"):
                    rows.append((
                        category, param, gender,
                        limits.get("min"), limits.get("max"), unit
                    ))

    cur.executemany(
        "INSERT INTO Normal_Ranges (category, parameter_name, gender, min_value, max_value, unit) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        rows
    )
    conn.commit()
    conn.close()
    print(f"Seeded {len(rows)} normal range rows.")


if __name__ == "__main__":
    seed()
