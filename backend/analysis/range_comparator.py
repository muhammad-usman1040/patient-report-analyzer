"""
Compare parsed lab values against normal ranges from normal_ranges.json.

compare_to_normal_ranges(parsed_data, user_gender=None, user_age=None) -> dict
"""
import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional

_RANGES_PATH = Path(__file__).parent.parent / "data" / "normal_ranges.json"
_ranges_cache: Optional[Dict] = None

logger = logging.getLogger(__name__)

_UNIT_GROUPS = {
    "cell_count_thousands": {
        "base": "10^9/l",
        "units": {"10^3/ul": 1, "10^9/l": 1, "k/ul": 1, "10^3/mm3": 1},
        "categories": {"CBC"},
    },
    "cell_count_millions": {
        "base": "10^12/l",
        "units": {"10^6/ul": 1, "10^12/l": 1, "m/ul": 1},
        "categories": {"CBC"},
    },
    "hormone_concentration": {
        "base": "miu/l",
        "units": {"uiu/ml": 1, "miu/l": 1, "miu/ml": 1000},
        "categories": {"Thyroid"},
    },
    "electrolyte_monovalent": {
        "base": "meq/l",
        "units": {"mmol/l": 1, "meq/l": 1},
        "categories": {"Electrolytes"},
        "parameters": {"Sodium", "Potassium", "Chloride"},
    },
}

_SUPERSCRIPTS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")


def normalize_unit(raw_unit: str) -> str:
    """Normalize common clinical unit notation without changing its magnitude."""
    normalized = re.sub(
        r"10([⁰¹²³⁴⁵⁶⁷⁸⁹]+)",
        lambda match: "10^" + match.group(1),
        str(raw_unit or "").strip(),
    ).translate(_SUPERSCRIPTS)
    normalized = normalized.replace("µ", "u").replace("μ", "u").replace("×", "x")
    normalized = re.sub(r"^x?\s*10\s*\^?\s*", "10^", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\s+", "", normalized)
    return normalized


def _unit_conversion(unit: str, expected: str, category: str, parameter: str):
    actual = normalize_unit(unit).lower()
    expected_normalized = normalize_unit(expected).lower()
    for group in _UNIT_GROUPS.values():
        if category not in group["categories"]:
            continue
        if "parameters" in group and parameter not in group["parameters"]:
            continue
        if actual in group["units"] and expected_normalized in group["units"]:
            return group["units"][actual] / group["units"][expected_normalized], True
    if category == "CBC" and re.match(r"^10\^?[^0-9^]?/ul$", actual):
        inferred = "10^6/ul" if parameter == "RBC" else "10^3/ul"
        for group in _UNIT_GROUPS.values():
            if inferred in group["units"] and expected_normalized in group["units"]:
                logger.warning("Inferring corrupted unit %r as %s for %s", unit, inferred, parameter)
                return group["units"][inferred] / group["units"][expected_normalized], True
    return 1, actual == expected_normalized or not expected_normalized


def _units_match(actual: str, expected: str) -> bool:
    _, matched = _unit_conversion(actual, expected, "", "")
    return matched


def _qualitative_status(value: Any, expected: Dict[str, Any]) -> str:
    normalized = str(value).strip().lower()
    for status, values in expected.get("qualitative", {}).items():
        if normalized in {str(item).lower() for item in values}:
            return status
    return "unknown"


def _load_ranges() -> Dict:
    """Load and cache normal_ranges.json on first call."""
    global _ranges_cache
    if _ranges_cache is None:
        with open(_RANGES_PATH) as f:
            _ranges_cache = json.load(f)
    return _ranges_cache


def _parse_limits(limits: Any):
    if isinstance(limits, dict):
        return limits.get("min"), limits.get("max")
    if isinstance(limits, str):
        match = re.search(r"([<>]?\s*\d+(?:\.\d+)?)\s*(?:-|–|—|to)\s*([<>]?\s*\d+(?:\.\d+)?)", limits, re.IGNORECASE)
        if match:
            return float(match.group(1).replace(" ", "").strip("<>")), float(match.group(2).replace(" ", "").strip("<>"))
    return None, None


def _get_range_info(ranges: Dict, category: str, param: str, unit: str = ""):
    info = ranges.get(category, {}).get(param, {})
    unit_ranges = info.get("ranges", {})
    if unit_ranges:
        normalized_unit = normalize_unit(unit)
        for expected_unit, selected in unit_ranges.items():
            if _unit_conversion(normalized_unit, expected_unit, category, param)[1]:
                return selected, expected_unit
        return {}, next(iter(unit_ranges))
    return info, info.get("unit", "")


def _get_limits(ranges: Dict, category: str, param: str, gender: Optional[str], unit: str = ""):
    """Return (min, max) for a parameter, using gender-specific limits when available."""
    info, _ = _get_range_info(ranges, category, param, unit)
    if not info:
        return None, None
    if "min" in info or "max" in info:
        return _parse_limits(info)

    gender_key = gender.lower() if gender and gender.lower() in ("male", "female") else None
    limits = info.get(gender_key) or info.get("general", {})
    return _parse_limits(limits)


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

        range_info, expected_unit = _get_range_info(ranges, category, param, unit)
        low, high = _get_limits(ranges, category, param, user_gender, unit)

        unit_unverified = False
        conversion, units_verified = _unit_conversion(unit, expected_unit, category, param)
        if value is None:
            status = "unknown"
        elif not isinstance(value, (int, float)):
            status = _qualitative_status(value, range_info)
        elif low is None or high is None:
            status = "unknown"
        elif value < low:
            status = "low"
        elif value > high:
            status = "high"
        else:
            status = "normal"
        if isinstance(value, (int, float)) and not units_verified:
            logger.warning("Unrecognized unit %r for %s", unit, param)
            unit_unverified = True
            plausible = 0 < value < 50 if category == "CBC" else value >= 0
            if not plausible:
                status = "unknown"
        elif isinstance(value, (int, float)) and units_verified:
            converted_value = value * conversion
            if low is not None and high is not None:
                status = "low" if converted_value < low else "high" if converted_value > high else "normal"

        result[param] = {
            "value": value,
            "unit": unit,
            "category": category,
            "status": status,
            "normal_min": low,
            "normal_max": high,
            "unit_unverified": unit_unverified,
        }

    return result
