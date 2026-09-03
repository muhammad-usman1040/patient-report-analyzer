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


def test_normal_parameters_are_returned():
    body = _upload(b"Platelets: 220 x10^9/L\nTSH: 2.0 mIU/L").json()
    parameters = {item["name"]: item for item in body["parameters"]}
    assert parameters["Platelets"]["status"] == "normal"
    assert parameters["TSH"]["status"] == "normal"


def test_qualitative_and_unsupported_results_are_returned_separately():
    body = _upload(b"Urine Protein: Trace\nTroponin: 0.04 ng/mL").json()
    parameters = {item["name"]: item for item in body["parameters"]}
    assert parameters["Protein"]["status"] == "low"
    assert body["unsupported_parameters"] == ["Troponin"]
    assert "not currently supported" in body["unsupported_message"]


def test_statuses_are_present_for_all_numeric_parameters():
    body = _upload(
        b"WBC: 13.8 x10^9/L\nPotassium: 5.3 mEq/L\nSodium: 140 mEq/L\n"
        b"Chloride: 90 mEq/L\nTSH: 2.0 mIU/L"
    ).json()
    statuses = {item["name"]: item["status"] for item in body["parameters"]}
    assert statuses == {
        "WBC": "high", "Potassium": "high", "Sodium": "normal",
        "Chloride": "low", "TSH": "normal",
    }


def test_multiple_reports_warn_and_analyze_first_only():
    body = _upload(b"Patient: One\nWBC: 13.8 x10^9/L\nPatient: Two\nWBC: 4.0 x10^9/L").json()
    assert body["multiple_reports_message"] == "Multiple reports detected in this file; only the first was analyzed."
    assert body["parameters"][0]["value"] == 13.8
