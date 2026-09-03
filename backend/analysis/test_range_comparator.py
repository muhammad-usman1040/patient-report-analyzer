"""Tests for range_comparator.py."""
import pytest
import range_comparator
from range_comparator import compare_to_normal_ranges, normalize_unit
from confidence_engine import evaluate_possible_conditions


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


def test_t3_uses_ng_ml_range():
    result = compare_to_normal_ranges({"T3": {"value": 1.1, "unit": "ng/mL", "category": "Thyroid"}})
    assert result["T3"]["status"] == "normal"
    assert result["T3"]["normal_min"] == 0.8
    assert result["T3"]["normal_max"] == 2.0


def test_unit_mismatch_is_not_flagged_as_numeric_abnormality():
    result = compare_to_normal_ranges({"T3": {"value": 1.1, "unit": "pg/mL", "category": "Thyroid"}})
    assert result["T3"]["status"] == "unknown"


def test_qualitative_urine_value_is_compared():
    result = compare_to_normal_ranges({"Glucose_Urine": {"value": "Positive", "unit": "", "category": "Urinalysis"}})
    assert result["Glucose_Urine"]["status"] == "high"


def test_en_dash_range_string_computes_status(monkeypatch):
    monkeypatch.setitem(range_comparator._load_ranges()["Electrolytes"]["Potassium"], "general", "3.5 – 5.1")
    parsed = {"Potassium": {"value": 5.3, "unit": "mEq/L", "category": "Electrolytes"}}
    result = compare_to_normal_ranges(parsed)
    assert result["Potassium"]["status"] == "high"


def test_high_potassium_triggers_hyperkalemia():
    compared = compare_to_normal_ranges({"Potassium": {"value": 5.3, "unit": "mEq/L", "category": "Electrolytes"}})
    analysis = evaluate_possible_conditions(compared)
    assert compared["Potassium"]["status"] == "high"
    assert "Hyperkalemia" in {condition["name"] for condition in analysis["conditions"]}


def test_t3_ng_dl_uses_ng_dl_range():
    result = compare_to_normal_ranges({"T3": {"value": 110, "unit": "ng/dL", "category": "Thyroid"}})
    assert result["T3"]["status"] == "normal"
    assert result["T3"]["normal_min"] == 80
    assert result["T3"]["normal_max"] == 200


def test_t3_ng_ml_uses_ng_ml_range():
    result = compare_to_normal_ranges({"T3": {"value": 1.1, "unit": "ng/mL", "category": "Thyroid"}})
    assert result["T3"]["status"] == "normal"
    assert result["T3"]["normal_min"] == 0.8
    assert result["T3"]["normal_max"] == 2.0


def test_normalize_messy_units():
    assert normalize_unit(" x10⁶ / µL ") == "10^6/uL"
    assert normalize_unit("×10³/μL") == "10^3/uL"
    assert normalize_unit("uIU / mL") == "uIU/mL"
    assert normalize_unit("mL") != normalize_unit("ML")


def test_unknown_unit_uses_unverified_fallback():
    result = compare_to_normal_ranges({"WBC": {"value": 13.8, "unit": "garbled-count", "category": "CBC"}})
    assert result["WBC"]["status"] == "high"
    assert result["WBC"]["unit_unverified"] is True


def test_unit_conversion_groups_apply_without_value_scaling():
    assert compare_to_normal_ranges({"WBC": {"value": 13.8, "unit": "x10^3/uL", "category": "CBC"}})["WBC"]["status"] == "high"
    assert compare_to_normal_ranges({"TSH": {"value": 2.1, "unit": "uIU/mL", "category": "Thyroid"}})["TSH"]["status"] == "normal"
    assert compare_to_normal_ranges({"Potassium": {"value": 5.3, "unit": "mmol/L", "category": "Electrolytes"}})["Potassium"]["status"] == "high"


def test_corrupted_rbc_unit_uses_explicit_inference():
    result = compare_to_normal_ranges({"RBC": {"value": 5.0, "unit": "10■/µL", "category": "CBC"}})
    assert result["RBC"]["status"] == "normal"
    assert result["RBC"]["unit_unverified"] is False
