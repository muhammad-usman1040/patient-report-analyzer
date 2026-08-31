"""
Compare parsed lab values against normal ranges from normal_ranges.json.

compare_to_normal_ranges(parsed_data, user_gender=None, user_age=None) -> dict
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional

_RANGES_PATH = Path(__file__).parent.parent / "data" / "normal_ranges.json"
_ranges_cache: Optional[Dict] = None


def _load_ranges() -> Dict:
    """Load and cache normal_ranges.json on first call."""
    global _ranges_cache
    if _ranges_cache is None:
        with open(_RANGES_PATH) as f:
            _ranges_cache = json.load(f)
    return _ranges_cache


def _get_limits(ranges: Dict, category: str, param: str, gender: Optional[str]):
    """Return (min, max) for a parameter, using gender-specific limits when available."""
    cat = ranges.get(category, {})
    info = cat.get(param)
    if not info:
        return None, None

    gender_key = gender.lower() if gender and gender.lower() in ("male", "female") else None
    limits = info.get(gender_key) or info.get("general", {})
    return limits.get("min"), limits.get("max")


def compare_to_normal_ranges(
    parsed_data: Dict[str, Any],
    user_gender: Optional[str] = None,
    user_age: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Compare each parsed parameter against its normal range.

    Returns:
        {
          "Hemoglobin": {
              "value": 8.5,
              "unit": "g/dL",
              "category": "CBC",
              "status": "low",      # "normal" | "high" | "low" | "unknown"
              "normal_min": 13.5,
              "normal_max": 17.5,
          },
          ...
        }
    """
    ranges = _load_ranges()
    result: Dict[str, Any] = {}

    for param, info in parsed_data.items():
        value = info.get("value")
        category = info.get("category", "")
        unit = info.get("unit", "")

        low, high = _get_limits(ranges, category, param, user_gender)

        if value is None or low is None or high is None:
            status = "unknown"
        elif value < low:
            status = "low"
        elif value > high:
            status = "high"
        else:
            status = "normal"

        result[param] = {
            "value": value,
            "unit": unit,
            "category": category,
            "status": status,
            "normal_min": low,
            "normal_max": high,
        }

    return result
