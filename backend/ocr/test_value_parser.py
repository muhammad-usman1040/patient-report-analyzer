"""Tests for value_parser.py."""
import pytest
from value_parser import parse_report_text


SAMPLE = """
Hemoglobin: 13.5 g/dL
WBC: 7.2 x10^9/L
Platelets: 220 x10^9/L
TSH: 2.10 mIU/L
ALT: 35 U/L
Creatinine: 0.9 mg/dL
Total Cholesterol: 195 mg/dL
HbA1c: 5.4 %
Vitamin D: 28 ng/mL
CRP: 3.0 mg/L
Sodium: 140 mEq/L
"""


def test_parses_hemoglobin():
    result = parse_report_text(SAMPLE)
    assert "Hemoglobin" in result
    assert result["Hemoglobin"]["value"] == 13.5
    assert result["Hemoglobin"]["category"] == "CBC"


def test_parses_tsh():
    result = parse_report_text(SAMPLE)
    assert "TSH" in result
    assert result["TSH"]["value"] == 2.10
    assert result["TSH"]["category"] == "Thyroid"


def test_parses_hba1c():
    result = parse_report_text(SAMPLE)
    assert "HbA1c" in result
    assert result["HbA1c"]["category"] == "Glucose"


def test_parses_vitamin_d():
    result = parse_report_text(SAMPLE)
    assert "Vitamin_D" in result
    assert result["Vitamin_D"]["value"] == 28.0


def test_empty_text_returns_empty():
    assert parse_report_text("") == {}
    assert parse_report_text("   \n   ") == {}


def test_gibberish_returns_empty():
    assert parse_report_text("foo bar baz qux") == {}
