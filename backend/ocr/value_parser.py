"""
Parse raw OCR text into a structured dict keyed by parameter name.

Recognises the 10 lab test categories defined in normal_ranges.json.
Returns: {parameter_name: {"value": float, "unit": str, "category": str}}
"""
import re
from typing import Dict, Any, Optional

# Aliases: maps common OCR label variants → canonical parameter name.
# Keys must be lowercase. Exact match is always tried first.
# Short/ambiguous keys (2-3 chars: hb, wbc, rbc, etc.) are EXACT-MATCH ONLY —
# they are listed in _EXACT_ONLY_ALIASES and never used in word-boundary fallback.
ALIASES: Dict[str, str] = {
    # CBC
    "hb": "Hemoglobin",
    "haemoglobin": "Hemoglobin", "hemoglobin": "Hemoglobin",
    "wbc": "WBC",
    "white blood cell": "WBC", "white blood cells": "WBC",
    "white blood count": "WBC", "white blood cell count": "WBC",
    "rbc": "RBC",
    "red blood cell": "RBC", "red blood cells": "RBC",
    "red blood cell count": "RBC", "rbc count": "RBC",
    "plt": "Platelets", "platelets": "Platelets", "platelet count": "Platelets",
    "hct": "Hematocrit", "hematocrit": "Hematocrit", "haematocrit": "Hematocrit",
    "mcv": "MCV", "mean corpuscular volume": "MCV",
    "mch": "MCH", "mean corpuscular hemoglobin": "MCH",
    "mchc": "MCHC", "mean corpuscular hemoglobin concentration": "MCHC",
    "neutrophils": "Neutrophils", "neutrophil": "Neutrophils",
    "lymphocytes": "Lymphocytes", "lymphocyte": "Lymphocytes",
    "monocytes": "Monocytes", "monocyte": "Monocytes",
    "eosinophils": "Eosinophils", "eosinophil": "Eosinophils",
    "basophils": "Basophils", "basophil": "Basophils",
    # Glucose
    "fasting glucose": "Fasting_Glucose",
    "fasting blood sugar": "Fasting_Glucose",
    "fasting blood glucose": "Fasting_Glucose",
    "fasting plasma glucose": "Fasting_Glucose",
    "fasting sugar": "Fasting_Glucose",
    "blood sugar fasting": "Fasting_Glucose",
    "fbs": "Fasting_Glucose",
    "random glucose": "Random_Glucose",
    "random blood sugar": "Random_Glucose",
    "random blood glucose": "Random_Glucose",
    "random sugar": "Random_Glucose",
    "blood sugar random": "Random_Glucose",
    "blood glucose": "Random_Glucose",
    "plasma glucose": "Random_Glucose",
    "serum glucose": "Random_Glucose",
    "blood sugar": "Random_Glucose",
    "sugar": "Random_Glucose",
    "rbs": "Random_Glucose",
    "hba1c": "HbA1c", "hb a1c": "HbA1c",
    "glycated hemoglobin": "HbA1c", "glycosylated hemoglobin": "HbA1c",
    "a1c": "HbA1c",
    # Lipid
    "total cholesterol": "Total_Cholesterol",
    "cholesterol total": "Total_Cholesterol",
    "cholesterol": "Total_Cholesterol",
    "ldl": "LDL", "ldl cholesterol": "LDL", "ldl-c": "LDL",
    "low density lipoprotein": "LDL",
    "hdl": "HDL", "hdl cholesterol": "HDL", "hdl-c": "HDL",
    "high density lipoprotein": "HDL",
    "triglycerides": "Triglycerides", "triglyceride": "Triglycerides",
    "tg": "Triglycerides",
    "vldl": "VLDL", "vldl cholesterol": "VLDL",
    # LFT
    "alt": "ALT",
    "alanine aminotransferase": "ALT", "alanine transaminase": "ALT",
    "sgpt": "ALT",
    "ast": "AST",
    "aspartate aminotransferase": "AST", "aspartate transaminase": "AST",
    "sgot": "AST",
    "alp": "ALP", "alkaline phosphatase": "ALP",
    "total bilirubin": "Total_Bilirubin",
    "t. bilirubin": "Total_Bilirubin", "t bilirubin": "Total_Bilirubin",
    "serum bilirubin": "Total_Bilirubin",
    "direct bilirubin": "Direct_Bilirubin",
    "d. bilirubin": "Direct_Bilirubin", "d bilirubin": "Direct_Bilirubin",
    "albumin": "Albumin",
    "ggt": "GGT", "gamma-gt": "GGT", "gamma gt": "GGT",
    "gamma glutamyl transferase": "GGT",
    # KFT
    "creatinine": "Creatinine", "serum creatinine": "Creatinine",
    "bun": "BUN", "blood urea nitrogen": "BUN", "urea": "BUN",
    "serum urea": "BUN", "blood urea": "BUN",
    "uric acid": "Uric_Acid", "serum uric acid": "Uric_Acid",
    "egfr": "eGFR", "gfr": "eGFR", "estimated gfr": "eGFR",
    # Thyroid
    "tsh": "TSH", "thyroid stimulating hormone": "TSH",
    "thyroid-stimulating hormone": "TSH",
    "t3": "T3", "triiodothyronine": "T3",
    "t4": "T4", "thyroxine": "T4",
    "free t3": "Free_T3", "ft3": "Free_T3",
    "free t4": "Free_T4", "ft4": "Free_T4",
    # Urinalysis
    "ph": "pH", "urine ph": "pH",
    "specific gravity": "Specific_Gravity",
    "sp. gr": "Specific_Gravity", "sp gr": "Specific_Gravity",
    "sp.gr": "Specific_Gravity",
    "urine protein": "Protein", "protein": "Protein",
    "urine glucose": "Glucose_Urine", "glucose urine": "Glucose_Urine",
    "rbc urine": "RBC_Urine", "rbc/hpf": "RBC_Urine", "rbc urine/hpf": "RBC_Urine",
    "wbc urine": "WBC_Urine", "wbc/hpf": "WBC_Urine",
    "wbc urine/hpf": "WBC_Urine", "pus cells": "WBC_Urine",
    # Vitamins
    "vitamin d": "Vitamin_D", "vit d": "Vitamin_D",
    "25-oh vitamin d": "Vitamin_D", "25-hydroxyvitamin d": "Vitamin_D",
    "vitamin d3": "Vitamin_D",
    "vitamin b12": "Vitamin_B12", "vitamin b-12": "Vitamin_B12",
    "vit b12": "Vitamin_B12", "vit b-12": "Vitamin_B12",
    "b12": "Vitamin_B12", "cobalamin": "Vitamin_B12",
    "folate": "Folate", "folic acid": "Folate", "serum folate": "Folate",
    # Electrolytes
    "sodium": "Sodium", "serum sodium": "Sodium",
    "na": "Sodium",
    "potassium": "Potassium", "serum potassium": "Potassium",
    "k": "Potassium",
    "chloride": "Chloride", "serum chloride": "Chloride",
    "cl": "Chloride",
    "bicarbonate": "Bicarbonate", "serum bicarbonate": "Bicarbonate",
    "hco3": "Bicarbonate",
    "calcium": "Calcium", "serum calcium": "Calcium",
    "ca": "Calcium",
    "magnesium": "Magnesium", "serum magnesium": "Magnesium",
    "mg": "Magnesium",
    "phosphorus": "Phosphorus", "serum phosphorus": "Phosphorus",
    "phosphate": "Phosphorus",
    # Inflammation
    "crp": "CRP", "c-reactive protein": "CRP", "c reactive protein": "CRP",
    "esr": "ESR", "erythrocyte sedimentation rate": "ESR",
}

# Short aliases that must ONLY match when the entire cleaned label equals the alias.
# These are dangerous in substring/word-boundary matching because they appear
# inside unrelated words or unit strings (e.g. "ast" in "fasting", "mg" in "mg/dL").
_EXACT_ONLY_ALIASES = frozenset({
    "hb", "wbc", "rbc", "plt", "hct", "mcv", "mch", "mchc",
    "fbs", "rbs", "tg", "ldl", "hdl", "vldl",
    "alt", "ast", "alp", "ggt", "bun",
    "tsh", "t3", "t4", "ft3", "ft4",
    "ph", "crp", "esr",
    "na", "k", "cl", "ca", "mg",
    "hco3", "egfr", "gfr",
    "a1c", "b12",
})

# Unit strings that must never be treated as parameter labels.
_UNIT_TOKENS = frozenset({
    "g/dl", "mg/dl", "mmol/l", "umol/l", "nmol/l", "pmol/l",
    "u/l", "iu/l", "miu/l", "ng/ml", "pg/ml", "ug/dl", "ng/dl",
    "meq/l", "mm/hr", "x10^9/l", "x10^3/ul", "x10^6/ul",
    "k/ul", "m/ul", "fl", "pg", "%", "g/l", "mg/l",
    "/hpf", "ml/min", "ml/min/1.73m2",
})

# Header / status words that look like labels but aren't parameters.
_SKIP_LABELS = frozenset({
    "low", "high", "normal", "flag", "result", "unit", "range", "test",
    "reference", "value", "parameter", "name", "status", "level",
    "positive", "negative", "trace", "absent", "present",
    "within normal limits", "wnl",
})

# Map canonical parameter → category
PARAM_CATEGORY: Dict[str, str] = {
    "Hemoglobin": "CBC", "WBC": "CBC", "RBC": "CBC", "Platelets": "CBC",
    "Hematocrit": "CBC", "MCV": "CBC", "MCH": "CBC", "MCHC": "CBC",
    "Neutrophils": "CBC", "Lymphocytes": "CBC", "Monocytes": "CBC",
    "Eosinophils": "CBC", "Basophils": "CBC",
    "Fasting_Glucose": "Glucose", "Random_Glucose": "Glucose", "HbA1c": "Glucose",
    "Total_Cholesterol": "Lipid", "LDL": "Lipid", "HDL": "Lipid",
    "Triglycerides": "Lipid", "VLDL": "Lipid",
    "ALT": "LFT", "AST": "LFT", "ALP": "LFT", "Total_Bilirubin": "LFT",
    "Direct_Bilirubin": "LFT", "Albumin": "LFT", "GGT": "LFT",
    "Creatinine": "KFT", "BUN": "KFT", "Uric_Acid": "KFT", "eGFR": "KFT",
    "TSH": "Thyroid", "T3": "Thyroid", "T4": "Thyroid",
    "Free_T3": "Thyroid", "Free_T4": "Thyroid",
    "pH": "Urinalysis", "Specific_Gravity": "Urinalysis", "Protein": "Urinalysis",
    "Glucose_Urine": "Urinalysis", "RBC_Urine": "Urinalysis", "WBC_Urine": "Urinalysis",
    "Vitamin_D": "Vitamins", "Vitamin_B12": "Vitamins", "Folate": "Vitamins",
    "Sodium": "Electrolytes", "Potassium": "Electrolytes", "Chloride": "Electrolytes",
    "Bicarbonate": "Electrolytes", "Calcium": "Electrolytes",
    "Magnesium": "Electrolytes", "Phosphorus": "Electrolytes",
    "CRP": "Inflammation", "ESR": "Inflammation",
}

# Strips parenthetical groups from a line segment before the first standalone number.
_PAREN_BEFORE_NUM = re.compile(r"\s*\([^)]*\)(?=\s*[\d]|\s*[:\-]\s*\d)")

# Matches: "Hemoglobin   13.5   g/dL"  or  "TSH: 2.10 mIU/L"  or  "HbA1c   8.2  %"
_LINE_PATTERN = re.compile(
    r"^([A-Za-z][A-Za-z0-9 /\.\-]*?)"       # label (non-greedy, starts with letter)
    r"(?:\s{2,}|[ \t]*[:\-][ \t]*)"          # separator: 2+ spaces OR colon/dash
    r"(\d+(?:\.\d+)?)"                        # numeric value
    r"\s*([A-Za-z/%^0-9\.]*)",               # optional unit
    re.IGNORECASE,
)

_IS_NUMBER = re.compile(r"^\d+(?:\.\d+)?$")
_IS_UNIT = re.compile(r"^[A-Za-z/%^][A-Za-z0-9/%^\.\-]*$")
_NOT_UNIT = {"low", "high", "normal", "flag", "result", "unit", "range", "test"}

# Pre-build a sorted list of multi-word aliases (longest first) for word-boundary matching.
# Single-word aliases that are in _EXACT_ONLY_ALIASES are excluded here.
_MULTIWORD_ALIASES = sorted(
    [(alias, canon) for alias, canon in ALIASES.items()
     if " " in alias or alias not in _EXACT_ONLY_ALIASES],
    key=lambda x: len(x[0]),
    reverse=True,
)


def _resolve_alias(raw_label: str) -> Optional[str]:
    """Return canonical parameter name for a raw label string, or None.

    Strategy (in order):
    1. Exact match after normalisation — always tried first.
    2. Word-boundary regex match against multi-word aliases and safe single-word aliases.
       Short/ambiguous aliases (_EXACT_ONLY_ALIASES) are skipped in this step.
    3. Returns None if no match — never falls back to unbounded substring.
    """
    # Reject unit strings and header words immediately.
    raw_lower = raw_label.strip().lower()
    if raw_lower in _UNIT_TOKENS or raw_lower in _SKIP_LABELS:
        return None
    # Reject strings that look like "mg/dL", "x10^9/L" etc.
    if re.match(r"^[\d\.]+[a-z%/\^]+", raw_lower):
        return None

    # Normalise: strip trailing parens, collapse whitespace.
    label = re.sub(r"\s*\([^)]*\)\s*$", "", raw_lower).strip()
    label = re.sub(r"\s+", " ", label)

    if not label:
        return None

    # 1. Exact match.
    canonical = ALIASES.get(label)
    if canonical:
        return canonical

    # 2. Word-boundary match — longest alias first, exact-only aliases excluded.
    for alias, canon in _MULTIWORD_ALIASES:
        if alias in _EXACT_ONLY_ALIASES:
            continue
        # Require word boundaries so "ast" doesn't fire inside "fasting".
        pattern = r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])"
        if re.search(pattern, label):
            return canon

    return None


def parse_report_text(raw_text: str) -> Dict[str, Any]:
    """
    Parse raw OCR/PDF text into a structured dict.

    Handles two layouts:
      - Single-line: "Hemoglobin   7.8   g/dL"
      - Multi-line table (PyMuPDF cell-per-line): label on one line,
        value on the next, optional unit on the line after that.

    Both passes always run; Pass 1 results take precedence over Pass 2.

    Returns:
        {
          "Hemoglobin": {"value": 13.5, "unit": "g/dL", "category": "CBC"},
          ...
        }
    """
    results: Dict[str, Any] = {}
    lines = [ln.strip() for ln in raw_text.splitlines()]

    # --- Pass 1: single-line format ---
    for line in lines:
        if not line:
            continue
        cleaned_line = _PAREN_BEFORE_NUM.sub("  ", line)
        match = _LINE_PATTERN.search(cleaned_line)
        if not match:
            continue
        raw_label = match.group(1).strip()
        try:
            value = float(match.group(2))
        except ValueError:
            continue
        unit = match.group(3).strip() if match.group(3) else ""
        # Reject if the "unit" field looks like a parameter name (mis-parse).
        if unit.lower() in _SKIP_LABELS:
            unit = ""
        canonical = _resolve_alias(raw_label)
        if canonical and canonical in PARAM_CATEGORY:
            results[canonical] = {
                "value": value,
                "unit": unit,
                "category": PARAM_CATEGORY[canonical],
            }

    # --- Pass 2: multi-line table format (label / value / unit on separate lines) ---
    # Runs always; does not overwrite entries already found in Pass 1.
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line:
            i += 1
            continue

        canonical = _resolve_alias(line)
        if canonical and canonical in PARAM_CATEGORY and canonical not in results:
            # Look ahead up to 3 lines for a bare number.
            value = None
            unit = ""
            found_at = i
            for j in range(i + 1, min(i + 4, len(lines))):
                candidate = lines[j].strip()
                if _IS_NUMBER.match(candidate):
                    value = float(candidate)
                    # Check the next non-empty line for a unit token.
                    for k in range(j + 1, min(j + 3, len(lines))):
                        next_tok = lines[k].strip()
                        if not next_tok:
                            continue
                        if _IS_UNIT.match(next_tok) and next_tok.lower() not in _NOT_UNIT:
                            unit = next_tok
                        break
                    found_at = j
                    break
                # Stop if we hit another known parameter label before a number.
                elif _resolve_alias(candidate) and _resolve_alias(candidate) in PARAM_CATEGORY:
                    break

            if value is not None:
                results[canonical] = {
                    "value": value,
                    "unit": unit,
                    "category": PARAM_CATEGORY[canonical],
                }
                i = found_at + 1
                continue

        i += 1

    return results
