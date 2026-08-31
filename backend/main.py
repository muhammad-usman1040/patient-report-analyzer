"""
FastAPI backend entry point — Phase 5 Modules 1 + 2 + 3.

Endpoints:
  GET  /api/health
  POST /api/analyze-report   (anonymous or authenticated)
  POST /api/generate-pdf     (accepts structured result JSON, returns PDF)
  GET  /api/history          (requires JWT token)
  POST /api/auth/register
  POST /api/auth/login
  GET  /api/auth/me
"""
import os
import sys
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Optional

from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE / "ocr"))
sys.path.insert(0, str(BASE / "analysis"))
sys.path.insert(0, str(BASE / "auth"))
sys.path.insert(0, str(BASE / "database"))
sys.path.insert(0, str(BASE / "reports"))

from ocr_engine import extract_text_from_report
from value_parser import parse_report_text
from range_comparator import compare_to_normal_ranges
from confidence_engine import evaluate_possible_conditions
from auth.auth_routes import router as auth_router, get_optional_current_user, get_required_current_user
from database.db import init_db, save_report, get_user_history
from reports.pdf_generator import generate_pdf_report

@asynccontextmanager
async def lifespan(app):
    init_db()
    yield


app = FastAPI(title="Patient Report Analyzer API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


# ---------------------------------------------------------------------------
# Analyze report
# ---------------------------------------------------------------------------

oauth2_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


@app.post("/api/analyze-report")
async def analyze_report(
    file: UploadFile = File(...),
    gender: Optional[str] = Form(None),
    age: Optional[int] = Form(None),
    output_format: Optional[str] = Form("screen"),
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user),
):
    allowed_suffixes = {".pdf", ".jpg", ".jpeg", ".png", ".txt"}
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in allowed_suffixes:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")

    MAX_UPLOAD_SIZE = 10 * 1024 * 1024

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10 MB)")

    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File handling error: {str(e)}")

    try:
        try:
            raw_text = extract_text_from_report(tmp_path)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"OCR failed: {str(e)}")

        try:
            parsed = parse_report_text(raw_text)
            flagged = compare_to_normal_ranges(parsed, user_gender=gender, user_age=age)
            analysis = evaluate_possible_conditions(flagged)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Analysis failed: {str(e)}")

        flagged_list = [
            {
                "name": param,
                "value": info["value"],
                "unit": info["unit"],
                "category": info["category"],
                "status": info["status"],
                "normal_min": info["normal_min"],
                "normal_max": info["normal_max"],
            }
            for param, info in flagged.items()
            if info["status"] != "normal"
        ]

        response: Dict[str, Any] = {
            "result_state": analysis["result_state"],
            "flagged_parameters": flagged_list,
            "conditions": analysis["conditions"],
            "disclaimer": analysis["disclaimer"],
            "output_format": output_format,
        }

        # Persist only when authenticated — never save raw file or OCR text
        if current_user:
            try:
                report_id = save_report(
                    user_id=current_user["id"],
                    gender=gender,
                    age=age,
                    output_format=output_format or "screen",
                    flagged=flagged,
                    analysis=analysis,
                )
                response["report_id"] = report_id
            except Exception:
                pass  # Persistence errors must never break analysis response

        return response

    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------

@app.get("/api/history")
def history(current_user: Dict[str, Any] = Depends(get_required_current_user)):
    return get_user_history(current_user["id"])


# ---------------------------------------------------------------------------
# PDF generation
# Design note: /api/generate-pdf is a separate endpoint (not a mode on
# /api/analyze-report) so the frontend can send back the already-computed
# result without re-running OCR — keeps the pipeline idempotent and fast.
# ---------------------------------------------------------------------------

class _FlaggedParameter(BaseModel):
    name: str
    value: float
    unit: str
    status: str
    normal_min: Optional[float] = None
    normal_max: Optional[float] = None
    category: Optional[str] = None


class _Condition(BaseModel):
    name: str
    confidence: float
    supporting_indicators: List[str] = []


class GeneratePdfRequest(BaseModel):
    result_state: str
    flagged_parameters: List[_FlaggedParameter] = []
    conditions: List[_Condition] = []
    disclaimer: Optional[str] = None
    language: Optional[str] = "en"


@app.post("/api/generate-pdf")
def generate_pdf(body: GeneratePdfRequest):
    """
    Accept the structured analysis result and return a PDF report.

    The PDF is generated entirely in memory (BytesIO) — never written to disk.
    """
    result_dict: Dict[str, Any] = {
        "result_state": body.result_state,
        "flagged_parameters": [p.model_dump() for p in body.flagged_parameters],
        "conditions": [c.model_dump() for c in body.conditions],
        "disclaimer": body.disclaimer or (
            "This is not a medical diagnosis. Please consult a qualified doctor."
        ),
    }

    try:
        pdf_bytes = generate_pdf_report(result_dict, language=body.language or "en")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {str(e)}")

    filename = f"report_{body.result_state}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
