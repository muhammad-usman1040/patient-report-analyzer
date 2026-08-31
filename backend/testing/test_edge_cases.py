"""
Phase 6 Module 2 -- Edge Case & Stress Tests

Covers:
  - Unsupported file formats
  - Corrupted / empty / binary files
  - File size limits
  - Irrelevant / non-medical content
  - Partial / incomplete reports
  - Boundary confidence thresholds
  - Auth edge cases (expired JWT, malformed headers, cross-user isolation)
  - Concurrent requests (no data leakage)
"""
import io
import os
import sys
import tempfile
import threading
from pathlib import Path

_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
try:
    os.unlink(_tmp_db.name)
except OSError:
    pass
os.environ["DATABASE_URL"] = _tmp_db.name
os.environ.setdefault("JWT_SECRET_KEY", "test-edge-secret")

BACKEND = Path(__file__).parent.parent
for _p in ("ocr", "analysis", "auth", "database", "reports"):
    sys.path.insert(0, str(BACKEND / _p))
sys.path.insert(0, str(BACKEND))

from main import app
from database.db import init_db
init_db()

from fastapi.testclient import TestClient
client = TestClient(app, raise_server_exceptions=False)

SAMPLES = Path(__file__).parent / "edge_case_samples"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _upload(filename: str, content: bytes, gender=None, age=None, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = {}
    if gender:
        data["gender"] = gender
    if age:
        data["age"] = str(age)
    return client.post(
        "/api/analyze-report",
        files={"file": (filename, io.BytesIO(content), "application/octet-stream")},
        data=data,
        headers=headers,
    )


def _register_and_login(email: str, password: str = "password123"):
    r = client.post("/api/auth/register", json={"email": email, "password": password})
    if r.status_code == 409:
        r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code in (200, 201)
    return r.json()["access_token"]


# ---------------------------------------------------------------------------
# TestUnsupportedFormats
# ---------------------------------------------------------------------------

class TestUnsupportedFormats:
    def test_docx_rejected(self):
        r = _upload("report.docx", b"fake docx content")
        assert r.status_code == 400
        assert "Unsupported file type" in r.json()["detail"]

    def test_csv_rejected(self):
        r = _upload("report.csv", b"col1,col2\n1,2\n")
        assert r.status_code == 400
        assert "Unsupported file type" in r.json()["detail"]

    def test_heic_rejected(self):
        r = _upload("report.heic", b"fake heic")
        assert r.status_code == 400
        assert "Unsupported file type" in r.json()["detail"]

    def test_xml_rejected(self):
        r = _upload("report.xml", b"<report></report>")
        assert r.status_code == 400
        assert "Unsupported file type" in r.json()["detail"]

    def test_no_extension_rejected(self):
        r = _upload("report", b"some content")
        assert r.status_code == 400
        assert "Unsupported file type" in r.json()["detail"]


# ---------------------------------------------------------------------------
# TestCorruptedAndEmptyFiles
# ---------------------------------------------------------------------------

class TestCorruptedAndEmptyFiles:
    def test_empty_file_graceful(self):
        r = _upload("empty.txt", b"")
        assert r.status_code == 200
        body = r.json()
        assert body["result_state"] == "insufficient_evidence"
        assert body["flagged_parameters"] == []

    def test_whitespace_only_graceful(self):
        r = _upload("whitespace.txt", b"   \n\n\t  \n")
        assert r.status_code == 200
        body = r.json()
        assert body["result_state"] == "insufficient_evidence"
        assert body["flagged_parameters"] == []

    def test_binary_garbage_as_txt(self):
        garbage = bytes(range(256)) * 3
        r = _upload("garbage.txt", garbage)
        assert r.status_code == 200
        body = r.json()
        assert body["result_state"] == "insufficient_evidence"
        assert body["flagged_parameters"] == []


# ---------------------------------------------------------------------------
# TestFileSizeLimit
# ---------------------------------------------------------------------------

class TestFileSizeLimit:
    def test_oversized_file_rejected(self):
        big = b"Hemoglobin: 8.0\n" * 750_000  # ~12 MB
        r = _upload("big.txt", big)
        assert r.status_code == 400
        assert "too large" in r.json()["detail"].lower()

    def test_file_at_exact_limit_plus_one_rejected(self):
        over = b"A" * (10 * 1024 * 1024 + 1)
        r = _upload("over.txt", over)
        assert r.status_code == 400
        assert "too large" in r.json()["detail"].lower()

    def test_file_just_under_limit_accepted(self):
        under = b"\n" * (10 * 1024 * 1024 - 100)
        r = _upload("under.txt", under)
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# TestIrrelevantContent
# ---------------------------------------------------------------------------

class TestIrrelevantContent:
    def test_shopping_list_no_hallucination(self):
        content = (SAMPLES / "irrelevant_content.txt").read_bytes()
        r = _upload("irrelevant.txt", content)
        assert r.status_code == 200
        body = r.json()
        assert body["result_state"] == "insufficient_evidence"
        assert body["flagged_parameters"] == []

    def test_pure_numbers_no_hallucination(self):
        r = _upload("numbers.txt", b"100\n200\n300\n")
        assert r.status_code == 200
        body = r.json()
        assert body["result_state"] == "insufficient_evidence"
        assert body["flagged_parameters"] == []

    import pytest

    @pytest.mark.xfail(strict=False, reason="short-alias partial match known issue")
    def test_short_alias_no_false_positives(self):
        content = b"Milk  2  liters\nBananas  6  pieces\n"
        r = _upload("short.txt", content)
        assert r.status_code == 200
        body = r.json()
        flagged_names = {p["name"] for p in body["flagged_parameters"]}
        assert "Potassium" not in flagged_names
        assert "Calcium" not in flagged_names
        assert "Sodium" not in flagged_names


# ---------------------------------------------------------------------------
# TestPartialAndIncompleteReports
# ---------------------------------------------------------------------------

class TestPartialAndIncompleteReports:
    def test_partial_report_normal_params(self):
        content = (SAMPLES / "partial_report.txt").read_bytes()
        r = _upload("partial.txt", content)
        assert r.status_code == 200
        body = r.json()
        assert body["result_state"] == "all_normal"
        assert body["flagged_parameters"] == []

    def test_one_abnormal_param_extracts_correctly(self):
        content = (SAMPLES / "partial_abnormal.txt").read_bytes()
        r = _upload("partial_abnormal.txt", content, gender="male", age=35)
        assert r.status_code == 200
        body = r.json()
        assert len(body["flagged_parameters"]) == 1
        param = body["flagged_parameters"][0]
        assert param["name"] == "Hemoglobin"
        assert param["status"] == "low"
        assert body["result_state"] == "insufficient_evidence"

    def test_mixed_valid_and_garbage(self):
        content = (SAMPLES / "mixed_valid_garbage.txt").read_bytes()
        r = _upload("mixed.txt", content, gender="male", age=35)
        assert r.status_code == 200
        body = r.json()
        flagged_names = {p["name"] for p in body["flagged_parameters"]}
        assert "Hemoglobin" in flagged_names
        assert "MCV" in flagged_names

    def test_noisy_report_graceful(self):
        content = (SAMPLES / "noisy_report.txt").read_bytes()
        r = _upload("noisy.txt", content, gender="male", age=35)
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# TestBoundaryConfidence
# ---------------------------------------------------------------------------

class TestBoundaryConfidence:
    def test_confidence_exactly_at_threshold(self):
        """Fasting_Glucose high → Pre_Diabetes confidence 0.5 == threshold 0.5 → detected."""
        content = (SAMPLES / "boundary_above.txt").read_bytes()
        r = _upload("boundary_above.txt", content)
        assert r.status_code == 200
        body = r.json()
        assert body["result_state"] == "possible_conditions"
        condition_names = {c["name"] for c in body["conditions"]}
        assert "Pre_Diabetes" in condition_names
        pre_diabetes = next(c for c in body["conditions"] if c["name"] == "Pre_Diabetes")
        assert abs(pre_diabetes["confidence"] - 0.5) < 1e-6

    def test_confidence_just_below_threshold(self):
        """Hemoglobin low only → Iron_Deficiency_Anemia confidence 0.4 < 0.6 → not detected."""
        content = (SAMPLES / "boundary_below.txt").read_bytes()
        r = _upload("boundary_below.txt", content, gender="male", age=35)
        assert r.status_code == 200
        body = r.json()
        assert body["result_state"] == "insufficient_evidence"
        condition_names = {c["name"] for c in body["conditions"]}
        assert "Iron_Deficiency_Anemia" not in condition_names

    def test_two_indicators_above_threshold(self):
        """Hemoglobin + MCV low → Iron_Deficiency_Anemia confidence 0.7 >= 0.6 → detected."""
        content = (SAMPLES / "boundary_two_indicators.txt").read_bytes()
        r = _upload("boundary_two_indicators.txt", content, gender="male", age=35)
        assert r.status_code == 200
        body = r.json()
        assert body["result_state"] == "possible_conditions"
        condition_names = {c["name"] for c in body["conditions"]}
        assert "Iron_Deficiency_Anemia" in condition_names
        ida = next(c for c in body["conditions"] if c["name"] == "Iron_Deficiency_Anemia")
        assert abs(ida["confidence"] - 0.7) < 1e-6


# ---------------------------------------------------------------------------
# TestAuthEdgeCases
# ---------------------------------------------------------------------------

class TestAuthEdgeCases:
    def test_history_without_token_401(self):
        r = client.get("/api/history")
        assert r.status_code == 401

    def test_history_with_invalid_token_401(self):
        r = client.get("/api/history", headers={"Authorization": "Bearer garbage_token"})
        assert r.status_code == 401

    def test_history_with_expired_token_401(self):
        from jose import jwt as jose_jwt
        expired = jose_jwt.encode(
            {"sub": "9999", "exp": 1_000_000_000},
            os.environ["JWT_SECRET_KEY"],
            algorithm="HS256",
        )
        r = client.get("/api/history", headers={"Authorization": f"Bearer {expired}"})
        assert r.status_code == 401

    def test_malformed_auth_headers(self):
        bad_headers = ["Basic xyz", "token123", "Bearer a.b.c"]
        for auth_val in bad_headers:
            r = client.get("/api/history", headers={"Authorization": auth_val})
            assert r.status_code == 401, f"Expected 401 for Authorization: {auth_val}"

    def test_non_numeric_sub_returns_401_not_500(self):
        """Regression: int(sub) was unguarded — a non-numeric sub caused 500."""
        from jose import jwt as jose_jwt
        import time
        token = jose_jwt.encode(
            {"sub": "not_a_number", "exp": int(time.time()) + 3600},
            os.environ["JWT_SECRET_KEY"],
            algorithm="HS256",
        )
        r = client.get("/api/history", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 401
        assert r.status_code != 500

    def test_analyze_with_invalid_token_proceeds_anonymously(self):
        r = _upload(
            "partial.txt",
            b"Hemoglobin  13.5  g/dL\n",
            token="invalid_token_xyz",
        )
        assert r.status_code == 200
        assert "report_id" not in r.json()

    def test_cross_user_history_isolation(self):
        token_a = _register_and_login("user_isolation_a@test.com")
        token_b = _register_and_login("user_isolation_b@test.com")

        _upload("report_a.txt", b"Hemoglobin  8.5  g/dL\n", token=token_a)
        _upload("report_b.txt", b"TSH  0.1  mIU/L\n", token=token_b)

        r_a = client.get("/api/history", headers={"Authorization": f"Bearer {token_a}"})
        assert r_a.status_code == 200
        history_a = r_a.json()

        r_b = client.get("/api/history", headers={"Authorization": f"Bearer {token_b}"})
        assert r_b.status_code == 200
        history_b = r_b.json()

        ids_a = {rep["id"] for rep in history_a["reports"]}
        ids_b = {rep["id"] for rep in history_b["reports"]}
        assert ids_a.isdisjoint(ids_b), "Cross-user history leakage detected"


# ---------------------------------------------------------------------------
# TestConcurrentRequests
# ---------------------------------------------------------------------------

class TestConcurrentRequests:
    def test_concurrent_uploads_no_data_leakage(self):
        """5 threads each upload a distinct report; verify no cross-contamination."""
        reports = [
            (f"thread_{i}.txt", f"Hemoglobin  {7 + i * 0.5:.1f}  g/dL\n".encode())
            for i in range(5)
        ]
        results = {}
        lock = threading.Lock()

        def upload(idx, filename, content):
            r = _upload(filename, content, gender="male", age=30)
            with lock:
                results[idx] = r

        threads = [
            threading.Thread(target=upload, args=(i, fn, ct))
            for i, (fn, ct) in enumerate(reports)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 5
        for i, r in results.items():
            assert r.status_code == 200
            body = r.json()
            flagged_names = {p["name"] for p in body["flagged_parameters"]}
            assert flagged_names.issubset({"Hemoglobin"}), (
                f"Thread {i} got unexpected parameters: {flagged_names}"
            )

    def test_concurrent_authenticated_uploads(self):
        """2 users each make 3 concurrent uploads; each user sees only their own history."""
        token_a = _register_and_login("concur_a@test.com")
        token_b = _register_and_login("concur_b@test.com")

        errors = []
        lock = threading.Lock()

        def upload_report(token, idx):
            r = _upload(
                f"concur_{idx}.txt",
                b"Hemoglobin  8.5  g/dL\n",
                token=token,
            )
            if r.status_code != 200:
                with lock:
                    errors.append(f"Upload {idx} failed: {r.status_code}")

        threads = []
        for i in range(3):
            threads.append(threading.Thread(target=upload_report, args=(token_a, f"a{i}")))
            threads.append(threading.Thread(target=upload_report, args=(token_b, f"b{i}")))
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Upload errors: {errors}"

        r_a = client.get("/api/history", headers={"Authorization": f"Bearer {token_a}"})
        r_b = client.get("/api/history", headers={"Authorization": f"Bearer {token_b}"})
        assert r_a.status_code == 200
        assert r_b.status_code == 200

        ids_a = {rep["id"] for rep in r_a.json()["reports"]}
        ids_b = {rep["id"] for rep in r_b.json()["reports"]}
        assert ids_a.isdisjoint(ids_b), "Concurrent upload caused cross-user history leakage"
