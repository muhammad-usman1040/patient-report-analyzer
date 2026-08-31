"""
Tests for Phase 5 Module 2 — Authentication and database persistence.

Covers:
  - POST /api/auth/register (success, duplicate email, weak password)
  - POST /api/auth/login (correct, incorrect password, unknown email)
  - GET  /api/auth/me (with/without token)
  - POST /api/analyze-report as anonymous (no DB save)
  - POST /api/analyze-report as authenticated (DB save verified)
  - GET  /api/history (authenticated, returns expected shape)
"""
import os
import sys
import tempfile
from pathlib import Path

# Isolate tests with a fresh temp database
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
os.unlink(_tmp_db.name)  # Delete so init_db creates a clean schema
os.environ["DATABASE_URL"] = _tmp_db.name

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "ocr"))
sys.path.insert(0, str(Path(__file__).parent / "analysis"))
sys.path.insert(0, str(Path(__file__).parent / "auth"))
sys.path.insert(0, str(Path(__file__).parent / "database"))

import pytest
from fastapi.testclient import TestClient
from main import app
from database.db import init_db

init_db()

client = TestClient(app)

SAMPLE_TEXT = b"Hemoglobin: 8.0 g/dL\nMCV: 72 fL\nTSH: 6.5 mIU/L\n"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def register(email: str, password: str = "securepassword123"):
    return client.post("/api/auth/register", json={"email": email, "password": password})


def login(email: str, password: str = "securepassword123"):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def auth_headers(token: str):
    return {"Authorization": f"Bearer {token}"}


def upload_report(token: str = None):
    headers = auth_headers(token) if token else {}
    return client.post(
        "/api/analyze-report",
        files={"file": ("report.txt", SAMPLE_TEXT, "text/plain")},
        data={"gender": "male", "age": "35"},
        headers=headers,
    )


# ---------------------------------------------------------------------------
# Register tests
# ---------------------------------------------------------------------------

def test_register_success():
    resp = register("test1@example.com")
    assert resp.status_code == 201
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_register_duplicate_email():
    register("dup@example.com")
    resp = register("dup@example.com")
    assert resp.status_code == 409


def test_register_weak_password():
    resp = register("weak@example.com", password="short")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Login tests
# ---------------------------------------------------------------------------

def test_login_correct_credentials():
    register("logintest@example.com")
    resp = login("logintest@example.com")
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password():
    register("wrongpw@example.com")
    resp = login("wrongpw@example.com", password="wrongpassword")
    assert resp.status_code == 401


def test_login_unknown_email():
    resp = login("nobody@example.com")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Protected route: /api/auth/me
# ---------------------------------------------------------------------------

def test_me_with_valid_token():
    register("me_test@example.com")
    token = login("me_test@example.com").json()["access_token"]
    resp = client.get("/api/auth/me", headers=auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "me_test@example.com"
    assert "id" in body


def test_me_without_token():
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401


def test_me_with_invalid_token():
    resp = client.get("/api/auth/me", headers=auth_headers("invalid.token.here"))
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# analyze-report: anonymous vs authenticated
# ---------------------------------------------------------------------------

def test_analyze_anonymous_succeeds():
    resp = upload_report(token=None)
    assert resp.status_code == 200
    body = resp.json()
    assert "result_state" in body
    # No report_id returned for anonymous
    assert "report_id" not in body


def test_analyze_authenticated_saves_report():
    register("savetest@example.com")
    token = login("savetest@example.com").json()["access_token"]
    resp = upload_report(token=token)
    assert resp.status_code == 200
    body = resp.json()
    assert "result_state" in body
    assert "report_id" in body
    assert isinstance(body["report_id"], int)


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

def test_history_requires_auth():
    resp = client.get("/api/history")
    assert resp.status_code == 401


def test_history_returns_expected_shape():
    register("history_user@example.com")
    token = login("history_user@example.com").json()["access_token"]
    # Upload a report so history is non-empty
    upload_report(token=token)
    resp = client.get("/api/history", headers=auth_headers(token))
    assert resp.status_code == 200
    body = resp.json()
    assert "reports" in body
    assert "trends" in body
    assert isinstance(body["reports"], list)
    assert isinstance(body["trends"], dict)
    assert len(body["reports"]) >= 1
    # Verify report shape matches sample_history.json
    r = body["reports"][0]
    assert "id" in r
    assert "report_date" in r
    assert "result_state" in r
    assert "conditions" in r
    assert "parameters" in r


def test_history_empty_for_new_user():
    register("fresh_user@example.com")
    token = login("fresh_user@example.com").json()["access_token"]
    resp = client.get("/api/history", headers=auth_headers(token))
    assert resp.status_code == 200
    assert resp.json()["reports"] == []
