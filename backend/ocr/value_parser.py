"""
Parse raw OCR text into a structured dict keyed by parameter name.

Recognises the 10 lab test categories defined in normal_ranges.json.
Returns: {parameter_name: {"value": float, "unit": str, "category": str}}
"""
import re
from typing import Dict, Any

# Aliases: maps common OCR label variants → canonical parameter name
ALIASES: Dict[str, str] = {
    # CBC
    "hb": "Hemoglobin", "haemoglobin": "Hemoglobin", "hemoglobin": "Hemoglobin",
    "wbc": "WBC", "white blood cell": "WBC", "white blood cells": "WBC", "white blood count": "WBC",
    "rbc": "RBC", "red blood cell": "RBC", "red blood cells": "RBC",
    "plt": "Platelets", "platelets": "Platelets", "platelet count": "Platelets",
    "hct": "Hematocrit", "hematocrit": "Hematocrit", "haematocrit": "Hematocrit",
    "mcv": "MCV", "mch": "MCH", "mchc": "MCHC",
    "neutrophils": "Neutrophils", "neutrophil": "Neutrophils",
    "lymphocytes": "Lymphocytes", "lymphocyte": "Lymphocytes",
    "monocytes": "Monocytes", "monocyte": "Monocytes",
    "eosinophils": "Eosinophils", "eosinophil": "Eosinophils",
    "basophils": "Basophils", "basophil": "Basophils",
    # Glucose
    "fasting glucose": "Fasting_Glucose", "fasting blood sugar": "Fasting_Glucose",
    "fbs": "Fasting_Glucose", "fasting sugar": "Fasting_Glucose",
    "random glucose": "Random_Glucose", "random blood sugar": "Random_Glucose",
    "rbs": "Random_Glucose",
    "hba1c": "HbA1c", "hb a1c": "HbA1c", "glycated hemoglobin": "HbA1c",
    "a1c": "HbA1c",
    # Lipid
    "total cholesterol": "Total_Cholesterol", "cholesterol": "Total_Cholesterol",
    "ldl": "LDL", "ldl cholesterol": "LDL", "ldl-c": "LDL",
    "hdl": "HDL", "hdl cholesterol": "HDL", "hdl-c": "HDL",
    "triglycerides": "Triglycerides", "tg": "Triglycerides",
    "vldl": "VLDL",
    # LFT
    "alt": "ALT", "alanine aminotransferase": "ALT", "sgpt": "ALT",
    "ast": "AST", "aspartate aminotransferase": "AST", "sgot": "AST",
    "alp": "ALP", "alkaline phosphatase": "ALP",
    "total bilirubin": "Total_Bilirubin", "t. bilirubin": "Total_Bilirubin",
    "direct bilirubin": "Direct_Bilirubin", "d. bilirubin": "Direct_Bilirubin",
    "albumin": "Albumin",
    "ggt": "GGT", "gamma gt": "GGT",
    # KFT
    "creatinine": "Creatinine", "serum creatinine": "Creatinine",
    "bun": "BUN", "blood urea nitrogen": "BUN", "urea": "BUN",
    "uric acid": "Uric_Acid",
    "egfr": "eGFR", "gfr": "eGFR",
    # Thyroid
    "tsh": "TSH", "thyroid stimulating hormone": "TSH",
    "t3": "T3", "triiodothyronine": "T3",
    "t4": "T4", "thyroxine": "T4",
    "free t3": "Free_T3", "ft3": "Free_T3",
    "free t4": "Free_T4", "ft4": "Free_T4",
    # Urinalysis
    "ph": "pH",
    "specific gravity": "Specific_Gravity", "sp. gr": "Specific_Gravity", "sp gr": "Specific_Gravity",
    "urine protein": "Protein", "protein": "Protein",
    "urine glucose": "Glucose_Urine", "glucose urine": "Glucose_Urine",
    "rbc urine": "RBC_Urine", "rbc/hpf": "RBC_Urine",
    "wbc urine": "WBC_Urine", "wbc/hpf": "WBC_Urine", "pus cells": "WBC_Urine",
    # Vitamins
    "vitamin d": "Vitamin_D", "vit d": "Vitamin_D", "25-oh vitamin d": "Vitamin_D",
    "vitamin b12": "Vitamin_B12", "vit b12": "Vitamin_B12", "b12": "Vitamin_B12",
    "folate": "Folate", "folic acid": "Folate",
    # Electrolytes
    "sodium": "Sodium", "na": "Sodium",
    "potassium": "Potassium", "k": "Potassium",
    "chloride": "Chloride", "cl": "Chloride",
    "bicarbonate": "Bicarbonate", "hco3": "Bicarbonate",
    "calcium": "Calcium", "ca": "Calcium",
    "magnesium": "Magnesium", "mg": "Magnesium",
    "phosphorus": "Phosphorus", "phosphate": "Phosphorus",
    # Inflammation
    "crp": "CRP", "c-reactive protein": "CRP", "c reactive protein": "CRP",
    "esr": "ESR", "erythrocyte sedimentation rate": "ESR",
}

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
# e.g. "ALT (SGPT)  98  U/L" -> "ALT   98  U/L"
# e.g. "C-Reactive Protein (CRP)  48  mg/L" -> "C-Reactive Protein   48  mg/L"
_PAREN_BEFORE_NUM = re.compile(r"\s*\([^)]*\)(?=\s*[\d]|\s*[:\-]\s*\d)")

# Matches lines like:  "Hemoglobin   13.5   g/dL"  or  "TSH: 2.10 mIU/L"  or  "HbA1c   8.2  %"
# Label: starts with a letter, contains letters/digits/spaces/dots/hyphens/slashes
# Separator: colon, dash, or 2+ whitespace chars
# Value: decimal number
# Unit: optional trailing alphanumeric+symbol string
_LINE_PATTERN = re.compile(
    r"^([A-Za-z][A-Za-z0-9 /\.\-]*?)"       # label (non-greedy, starts with letter)
    r"(?:\s{2,}|[ \t]*[:\-][ \t]*)"          # separator: 2+ spaces OR colon/dash
    r"(\d+(?:\.\d+)?)"                        # numeric value
    r"\s*([A-Za-z/%^0-9\.]*)",               # optional unit
    re.IGNORECASE,
)


def _clean_label(raw: str) -> str:
    """Strip parenthetical suffixes and normalise whitespace for alias lookup."""
    # Remove trailing parenthetical: "alt (sgpt)" -> "alt"
    cleaned = re.sub(r"\s*\([^)]*\)\s*$", "", raw).strip()
    # Collapse internal whitespace
    return re.sub(r"\s+", " ", cleaned)


def parse_report_text(raw_text: str) -> Dict[str, Any]:
    """
    Parse raw OCR text into structured dict.

    Returns:
        {
          "Hemoglobin": {"value": 13.5, "unit": "g/dL", "category": "CBC"},
          ...
        }
    """
    results: Dict[str, Any] = {}
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue

        # Strip parenthetical groups that appear immediately before a number/colon,
        # replacing with 2 spaces so the separator check (\s{2,}) still fires.
        # "ALT (SGPT) 98" -> "ALT  98"
        # "ESR (Erythrocyte...) 65" -> "ESR  65"
        cleaned_line = _PAREN_BEFORE_NUM.sub("  ", line)

        match = _LINE_PATTERN.search(cleaned_line)
        if not match:
            continue
        raw_label = match.group(1).strip().lower()
        try:
            value = float(match.group(2))
        except ValueError:
            continue
        unit = match.group(3).strip() if match.group(3) else ""

        # Try exact alias lookup, then lookup after stripping parentheticals
        canonical = ALIASES.get(raw_label)
        if not canonical:
            stripped_label = _clean_label(raw_label)
            canonical = ALIASES.get(stripped_label)
        if not canonical:
            # Try partial match for multi-word labels
            check_labels = [raw_label]
            stripped = _clean_label(raw_label)
            if stripped != raw_label:
                check_labels.append(stripped)
            for check in check_labels:
                for alias, canon in ALIASES.items():
                    if alias in check or check in alias:
                        canonical = canon
                        break
                if canonical:
                    break

        if canonical and canonical in PARAM_CATEGORY:
            results[canonical] = {
                "value": value,
                "unit": unit,
                "category": PARAM_CATEGORY[canonical],
            }

    return results
