"""Tests for main.py — integration tests for the analyze-report pipeline."""
import os
import sys
import tempfile
import pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "ocr"))
sys.path.insert(0, str(Path(__file__).parent / "analysis"))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

SAMPLE_TEXT = b"""
Hemoglobin: 8.0 g/dL
WBC: 7.0 x10^9/L
MCV: 72 fL
TSH: 6.5 mIU/L
"""


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def _upload(content: bytes, filename: str = "report.txt", gender=None, age=None):
    files = {"file": (filename, content, "text/plain")}
    data = {}
    if gender:
        data["gender"] = gender
    if age:
        data["age"] = str(age)
    return client.post("/api/analyze-report", files=files, data=data)


def test_analyze_report_returns_structure():
    resp = _upload(SAMPLE_TEXT)
    assert resp.status_code == 200
    body = resp.json()
    assert "result_state" in body
    assert "flagged_parameters" in body
    assert "conditions" in body
    assert "disclaimer" in body


def test_analyze_report_detects_anemia():
    resp = _upload(SAMPLE_TEXT, gender="male")
    body = resp.json()
    assert body["result_state"] in ("possible_conditions", "insufficient_evidence", "all_normal")
    flagged_names = [p["name"] for p in body["flagged_parameters"]]
    assert "Hemoglobin" in flagged_names or "TSH" in flagged_names


def test_analyze_normal_report():
    normal_text = b"""
Hemoglobin: 14.5 g/dL
WBC: 7.0 x10^9/L
TSH: 2.0 mIU/L
Total Cholesterol: 180 mg/dL
"""
    resp = _upload(normal_text)
    assert resp.status_code == 200
    body = resp.json()
    assert body["result_state"] in ("all_normal", "insufficient_evidence", "possible_conditions")


def test_unsupported_file_type():
    resp = client.post(
        "/api/analyze-report",
        files={"file": ("report.docx", b"dummy", "application/octet-stream")},
    )
    assert resp.status_code == 400


def test_disclaimer_always_present():
    resp = _upload(SAMPLE_TEXT)
    assert "disclaimer" in resp.json()
    assert len(resp.json()["disclaimer"]) > 5
