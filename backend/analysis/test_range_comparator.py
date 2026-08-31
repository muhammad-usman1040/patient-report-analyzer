"""Tests for range_comparator.py."""
import pytest
from range_comparator import compare_to_normal_ranges


PARSED = {
    "Hemoglobin": {"value": 8.0, "unit": "g/dL", "category": "CBC"},
    "WBC": {"value": 7.0, "unit": "x10^9/L", "category": "CBC"},
    "TSH": {"value": 6.5, "unit": "mIU/L", "category": "Thyroid"},
    "Total_Cholesterol": {"value": 180, "unit": "mg/dL", "category": "Lipid"},
}


def test_low_hemoglobin():
    result = compare_to_normal_ranges(PARSED, user_gender="male")
    assert result["Hemoglobin"]["status"] == "low"


def test_normal_wbc():
    result = compare_to_normal_ranges(PARSED)
    assert result["WBC"]["status"] == "normal"


def test_high_tsh():
    result = compare_to_normal_ranges(PARSED)
    assert result["TSH"]["status"] == "high"


def test_normal_cholesterol():
    result = compare_to_normal_ranges(PARSED)
    assert result["Total_Cholesterol"]["status"] == "normal"


def test_gender_aware_hemoglobin_female():
    parsed = {"Hemoglobin": {"value": 13.0, "unit": "g/dL", "category": "CBC"}}
    male_result = compare_to_normal_ranges(parsed, user_gender="male")
    female_result = compare_to_normal_ranges(parsed, user_gender="female")
    assert male_result["Hemoglobin"]["status"] == "low"
    assert female_result["Hemoglobin"]["status"] == "normal"


def test_empty_parsed_returns_empty():
    assert compare_to_normal_ranges({}) == {}
