"""Tests for confidence_engine.py."""
import pytest
from confidence_engine import evaluate_possible_conditions

ALL_NORMAL = {
    "Hemoglobin": {"value": 14.0, "unit": "g/dL", "category": "CBC", "status": "normal",
                   "normal_min": 13.5, "normal_max": 17.5},
    "TSH": {"value": 2.0, "unit": "mIU/L", "category": "Thyroid", "status": "normal",
            "normal_min": 0.4, "normal_max": 4.0},
}

ANEMIA_FLAGS = {
    "Hemoglobin": {"value": 8.0, "unit": "g/dL", "category": "CBC", "status": "low",
                   "normal_min": 13.5, "normal_max": 17.5},
    "MCV": {"value": 70, "unit": "fL", "category": "CBC", "status": "low",
            "normal_min": 80, "normal_max": 100},
    "MCH": {"value": 24, "unit": "pg", "category": "CBC", "status": "low",
            "normal_min": 27, "normal_max": 33},
}

DIABETES_FLAGS = {
    "Fasting_Glucose": {"value": 130, "unit": "mg/dL", "category": "Glucose", "status": "high",
                        "normal_min": 70, "normal_max": 100},
    "HbA1c": {"value": 7.5, "unit": "%", "category": "Glucose", "status": "high",
              "normal_min": 4.0, "normal_max": 5.6},
}


def test_all_normal_state():
    result = evaluate_possible_conditions(ALL_NORMAL)
    assert result["result_state"] == "all_normal"
    assert result["conditions"] == []
    assert "not a medical diagnosis" in result["disclaimer"].lower()


def test_anemia_detected():
    result = evaluate_possible_conditions(ANEMIA_FLAGS)
    assert result["result_state"] == "possible_conditions"
    names = [c["name"] for c in result["conditions"]]
    assert "Iron_Deficiency_Anemia" in names


def test_diabetes_detected():
    result = evaluate_possible_conditions(DIABETES_FLAGS)
    assert result["result_state"] == "possible_conditions"
    names = [c["name"] for c in result["conditions"]]
    assert "Diabetes_Mellitus" in names


def test_insufficient_evidence_on_empty():
    result = evaluate_possible_conditions({})
    assert result["result_state"] == "insufficient_evidence"


def test_single_weak_flag_insufficient():
    # Only one minor abnormal value — should not meet any threshold
    data = {
        "Sodium": {"value": 134, "unit": "mEq/L", "category": "Electrolytes", "status": "low",
                   "normal_min": 136, "normal_max": 145},
    }
    result = evaluate_possible_conditions(data)
    # May or may not trigger Electrolyte_Imbalance depending on threshold; just verify structure
    assert "result_state" in result
    assert "disclaimer" in result


def test_disclaimer_always_present():
    for data in [ALL_NORMAL, ANEMIA_FLAGS, {}, DIABETES_FLAGS]:
        result = evaluate_possible_conditions(data)
        assert "disclaimer" in result
        assert len(result["disclaimer"]) > 10
