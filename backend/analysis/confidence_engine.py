"""
Confidence engine — evaluates possible conditions from flagged lab parameters.

evaluate_possible_conditions(flagged_data) -> dict
"""
import json
from pathlib import Path
from typing import Dict, Any

_INDICATORS_PATH = Path(__file__).parent / "condition_indicators.json"
_indicators_cache = None


def _load_indicators() -> Dict:
    global _indicators_cache
    if _indicators_cache is None:
        with open(_INDICATORS_PATH) as f:
            _indicators_cache = json.load(f)
    return _indicators_cache


def evaluate_possible_conditions(flagged_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Score each condition against the flagged parameters.

    Args:
        flagged_data: output of compare_to_normal_ranges()

    Returns:
        {
          "result_state": "possible_conditions" | "all_normal" | "insufficient_evidence",
          "conditions": [
              {
                "name": "Iron_Deficiency_Anemia",
                "confidence": 0.82,
                "supporting_indicators": ["Hemoglobin (low)", "MCV (low)"]
              }
          ],
          "disclaimer": "This is not a medical diagnosis. ..."
        }
    """
    DISCLAIMER = (
        "This is not a medical diagnosis. Please consult a qualified doctor."
    )

    indicators = _load_indicators()

    # Check if all values are normal
    non_normal = {
        p: d for p, d in flagged_data.items()
        if d.get("status") in ("high", "low")
    }

    if not flagged_data:
        return {
            "result_state": "insufficient_evidence",
            "conditions": [],
            "disclaimer": DISCLAIMER,
        }

    if not non_normal:
        return {
            "result_state": "all_normal",
            "conditions": [],
            "disclaimer": DISCLAIMER,
        }

    matched_conditions = []

    for condition_name, config in indicators.items():
        threshold = config["threshold"]
        possible_score = 0.0
        actual_score = 0.0
        supporting: list = []

        for ind in config["indicators"]:
            param = ind["parameter"]
            direction = ind["direction"]
            weight = ind["weight"]

            param_data = flagged_data.get(param)
            if param_data is None:
                continue

            possible_score += weight
            status = param_data.get("status")

            if status == direction:
                actual_score += weight
                supporting.append(f"{param} ({status})")

        if possible_score == 0:
            continue

        # Normalise: confidence = actual / total_possible_weight_of_condition
        total_weight = sum(i["weight"] for i in config["indicators"])
        confidence = actual_score / total_weight

        if confidence >= threshold:
            matched_conditions.append({
                "name": condition_name,
                "confidence": round(confidence, 3),
                "supporting_indicators": supporting,
            })

    matched_conditions.sort(key=lambda x: x["confidence"], reverse=True)

    if matched_conditions:
        return {
            "result_state": "possible_conditions",
            "conditions": matched_conditions,
            "disclaimer": DISCLAIMER,
        }

    return {
        "result_state": "insufficient_evidence",
        "conditions": [],
        "disclaimer": DISCLAIMER,
    }
