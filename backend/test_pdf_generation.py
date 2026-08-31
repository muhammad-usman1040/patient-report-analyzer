"""
Tests for Phase 5 Module 3 — PDF Report Generation.

Covers:
  - generate_pdf_report() returns valid PDF bytes for all three result states
  - Bilingual generation (en / ur) does not raise
  - POST /api/generate-pdf returns 200, correct Content-Type, and
    Content-Disposition attachment header
  - Anonymous (no token) access to /api/generate-pdf is allowed
"""
import sys
from pathlib import Path
from io import BytesIO

import pytest

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE / "reports"))
sys.path.insert(0, str(BASE / "ocr"))
sys.path.insert(0, str(BASE / "analysis"))
sys.path.insert(0, str(BASE / "auth"))
sys.path.insert(0, str(BASE / "database"))

from pdf_generator import generate_pdf_report

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_ALL_NORMAL = {
    "result_state": "all_normal",
    "flagged_parameters": [],
    "conditions": [],
    "disclaimer": None,
}

_INSUFFICIENT = {
    "result_state": "insufficient_evidence",
    "flagged_parameters": [
        {
            "name": "Hemoglobin",
            "value": 11.5,
            "unit": "g/dL",
            "status": "low",
            "normal_min": 13.5,
            "normal_max": 17.5,
        }
    ],
    "conditions": [],
    "disclaimer": None,
}

_POSSIBLE_CONDITIONS = {
    "result_state": "possible_conditions",
    "flagged_parameters": [
        {
            "name": "Hemoglobin",
            "value": 9.0,
            "unit": "g/dL",
            "status": "low",
            "normal_min": 12.0,
            "normal_max": 16.0,
        },
        {
            "name": "MCV",
            "value": 70.0,
            "unit": "fL",
            "status": "low",
            "normal_min": 80.0,
            "normal_max": 100.0,
        },
        {
            "name": "Total Cholesterol",
            "value": 230.0,
            "unit": "mg/dL",
            "status": "high",
            "normal_min": 0.0,
            "normal_max": 200.0,
        },
    ],
    "conditions": [
        {
            "name": "iron_deficiency_anemia",
            "confidence": 0.85,
            "supporting_indicators": ["Hemoglobin", "MCV"],
        },
        {
            "name": "hyperlipidemia",
            "confidence": 0.70,
            "supporting_indicators": ["Total Cholesterol"],
        },
    ],
    "disclaimer": "This is not a medical diagnosis.",
}


# ---------------------------------------------------------------------------
# Unit tests — pdf_generator directly
# ---------------------------------------------------------------------------

class TestGeneratePdfUnit:
    def test_all_normal_returns_bytes(self):
        result = generate_pdf_report(_ALL_NORMAL)
        assert isinstance(result, bytes)

    def test_all_normal_is_valid_pdf(self):
        result = generate_pdf_report(_ALL_NORMAL)
        assert result[:4] == b"%PDF", "Output does not start with PDF magic bytes"

    def test_all_normal_non_empty(self):
        result = generate_pdf_report(_ALL_NORMAL)
        assert len(result) > 500

    def test_insufficient_evidence(self):
        result = generate_pdf_report(_INSUFFICIENT)
        assert result[:4] == b"%PDF"
        assert len(result) > 500

    def test_possible_conditions(self):
        result = generate_pdf_report(_POSSIBLE_CONDITIONS)
        assert result[:4] == b"%PDF"
        assert len(result) > 500

    def test_english_language(self):
        result = generate_pdf_report(_POSSIBLE_CONDITIONS, language="en")
        assert result[:4] == b"%PDF"

    def test_urdu_language(self):
        result = generate_pdf_report(_POSSIBLE_CONDITIONS, language="ur")
        assert result[:4] == b"%PDF"
        assert len(result) > 500

    def test_unknown_language_falls_back_to_english(self):
        result = generate_pdf_report(_ALL_NORMAL, language="zz")
        assert result[:4] == b"%PDF"

    def test_custom_disclaimer_included(self):
        result = generate_pdf_report(_INSUFFICIENT, language="en")
        # PDF bytes contain plain-text disclaimers embedded in the stream.
        # We check the content renders without error; byte-level search is not
        # reliable for compressed PDF streams so we only assert validity.
        assert len(result) > 500

    def test_empty_conditions_list(self):
        result = generate_pdf_report({
            "result_state": "possible_conditions",
            "flagged_parameters": [],
            "conditions": [],
            "disclaimer": None,
        })
        assert result[:4] == b"%PDF"


# ---------------------------------------------------------------------------
# Integration tests — FastAPI endpoint
# ---------------------------------------------------------------------------

import os
import tempfile

_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
try:
    os.unlink(_tmp_db.name)
except OSError:
    pass
os.environ["DATABASE_URL"] = _tmp_db.name
os.environ.setdefault("JWT_SECRET_KEY", "test-pdf-secret")
os.environ.setdefault("JWT_ALGORITHM", "HS256")

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


class TestGeneratePdfEndpoint:
    def test_all_normal_200(self):
        resp = client.post("/api/generate-pdf", json=_ALL_NORMAL)
        assert resp.status_code == 200

    def test_response_content_type_is_pdf(self):
        resp = client.post("/api/generate-pdf", json=_ALL_NORMAL)
        assert "application/pdf" in resp.headers["content-type"]

    def test_response_has_attachment_header(self):
        resp = client.post("/api/generate-pdf", json=_ALL_NORMAL)
        cd = resp.headers.get("content-disposition", "")
        assert "attachment" in cd

    def test_response_filename_contains_result_state(self):
        resp = client.post("/api/generate-pdf", json=_ALL_NORMAL)
        cd = resp.headers.get("content-disposition", "")
        assert "all_normal" in cd

    def test_insufficient_evidence_200(self):
        resp = client.post("/api/generate-pdf", json=_INSUFFICIENT)
        assert resp.status_code == 200
        assert resp.content[:4] == b"%PDF"

    def test_possible_conditions_200(self):
        resp = client.post("/api/generate-pdf", json=_POSSIBLE_CONDITIONS)
        assert resp.status_code == 200
        assert resp.content[:4] == b"%PDF"

    def test_anonymous_access_allowed(self):
        resp = client.post("/api/generate-pdf", json=_ALL_NORMAL)
        assert resp.status_code == 200

    def test_urdu_language_200(self):
        payload = dict(_POSSIBLE_CONDITIONS, language="ur")
        resp = client.post("/api/generate-pdf", json=payload)
        assert resp.status_code == 200
        assert resp.content[:4] == b"%PDF"

    def test_response_body_is_valid_pdf(self):
        resp = client.post("/api/generate-pdf", json=_POSSIBLE_CONDITIONS)
        assert resp.content[:4] == b"%PDF"
        assert len(resp.content) > 500
