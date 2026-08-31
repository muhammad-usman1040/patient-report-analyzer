"""Tests for ocr_engine.py — uses a plain .txt file to avoid Tesseract dependency in CI."""
import os
import tempfile
import pytest
from ocr_engine import extract_text_from_report


def test_extract_from_txt_file():
    content = "Hemoglobin: 13.5 g/dL\nWBC: 7.2 x10^9/L\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(content)
        tmp = f.name
    try:
        result = extract_text_from_report(tmp)
        assert "Hemoglobin" in result
        assert "WBC" in result
    finally:
        os.unlink(tmp)


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        extract_text_from_report("/nonexistent/report.txt")


def test_unsupported_format_raises():
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        tmp = f.name
    try:
        with pytest.raises(ValueError):
            extract_text_from_report(tmp)
    finally:
        os.unlink(tmp)
