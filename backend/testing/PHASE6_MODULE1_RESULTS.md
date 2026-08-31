# Phase 6 Module 1 — End-to-End Accuracy Results

## Summary

| Metric | Score | Target | Result |
|---|---|---|---|
| Parameter extraction | 108 / 108 (100.0%) | >= 90% | PASS |
| Status flagging | 108 / 108 (100.0%) | >= 90% | PASS |
| Result state | 20 / 20 (100.0%) | — | PASS |

All 10 lab test categories meet the 90% accuracy target.

---

## Per-Category Breakdown

| Category | Extraction | Flagging | Result State |
|---|---|---|---|
| CBC | 24/24 (100%) | 24/24 (100%) | 2/2 |
| Electrolytes | 14/14 (100%) | 14/14 (100%) | 2/2 |
| Glucose | 6/6 (100%) | 6/6 (100%) | 2/2 |
| Inflammation | 4/4 (100%) | 4/4 (100%) | 2/2 |
| KFT | 8/8 (100%) | 8/8 (100%) | 2/2 |
| LFT | 14/14 (100%) | 14/14 (100%) | 2/2 |
| Lipid | 10/10 (100%) | 10/10 (100%) | 2/2 |
| Thyroid | 10/10 (100%) | 10/10 (100%) | 2/2 |
| Urinalysis | 12/12 (100%) | 12/12 (100%) | 2/2 |
| Vitamins | 6/6 (100%) | 6/6 (100%) | 2/2 |

---

## Conditions Detected

All 13 condition detections across the 20 samples matched ground truth:

- Iron_Deficiency_Anemia (cbc_sample1)
- Diabetes_Mellitus (glucose_sample1)
- Pre_Diabetes (glucose_sample2)
- Dyslipidemia (lipid_sample1)
- Liver_Disease (lft_sample1)
- Chronic_Kidney_Disease (kft_sample1)
- Hypothyroidism (thyroid_sample1)
- Hyperthyroidism (thyroid_sample2)
- Vitamin_D_Deficiency (vitamins_sample1)
- Electrolyte_Imbalance (electrolytes_sample1)
- Inflammation_Or_Infection (inflammation_sample1)

---

## Bugs Found and Fixed

### 1. Parenthetical label notation (root cause of most failures)

**Affected samples:** lft_sample1, kft_sample1, inflammation_sample1, vitamins_sample1  
**Affected parameters:** ALT, AST, ALP, BUN, CRP, ESR, Vitamin_D

Lab reports commonly annotate test names with parenthetical synonyms:
```
ALT (SGPT)                  98    U/L
BUN (Blood Urea Nitrogen)   28    mg/dL
C-Reactive Protein (CRP)    48    mg/L
```

The original `_LINE_PATTERN` regex used character class `[A-Za-z0-9 /\.\-]` which stops at `(`. This caused one of two failures:
- The label captured before `(` was too short to match any alias (e.g. "alt ")
- The parenthetical content was mistaken for part of the value

**Fix in `value_parser.py`:**

Added `_PAREN_BEFORE_NUM` — a pre-processing regex that strips parenthetical groups immediately before a number, replacing them with 2 spaces:
```python
_PAREN_BEFORE_NUM = re.compile(r"\s*\([^)]*\)(?=\s*[\d]|\s*[:\-]\s*\d)")
cleaned_line = _PAREN_BEFORE_NUM.sub("  ", line)
```

The 2-space replacement ensures the separator requirement (`\s{2,}`) in `_LINE_PATTERN` is preserved after stripping.

### 2. Labels containing digits (HbA1c, Free T3, Free T4, TSH 0.05)

The original lazy `+?` regex `([A-Za-z][A-Za-z0-9 /\.\-]+?)` stopped at the first digit it could use as the value group. For "HbA1c  8.2  %", the engine captured "HbA" as the label and "1" as the value.

**Fix in `value_parser.py`:**

Rewrote `_LINE_PATTERN` with:
- Non-greedy label that expands until a genuine separator is found
- Separator defined as `\s{2,}` (2+ spaces) OR `[:\-]` (colon/dash with optional spaces)
- `^` anchor so matching starts from the beginning of the (stripped) line

```python
_LINE_PATTERN = re.compile(
    r"^([A-Za-z][A-Za-z0-9 /\.\-]*?)"
    r"(?:\s{2,}|[ \t]*[:\-][ \t]*)"
    r"(\d+(?:\.\d+)?)"
    r"\s*([A-Za-z/%^0-9\.]*)",
    re.IGNORECASE,
)
```

With this pattern, "HbA1c   8.2   %" is correctly split: label="HbA1c", value=8.2, unit="%".

---

## Test Suite Status After Fixes

All 33 existing tests continue to pass:
- `test_auth.py`: 14/14
- `test_pdf_generation.py`: 19/19

No regressions introduced.

---

## Files

| File | Purpose |
|---|---|
| `testing/sample_reports/` | 20 realistic `.txt` lab reports (2 per category) |
| `testing/expected_results.json` | Ground truth: expected parsed values, statuses, conditions, result states |
| `testing/accuracy_report.py` | Runs full pipeline on all samples, reports per-category and overall accuracy |
| `ocr/value_parser.py` | Fixed: parenthetical stripping, digit-in-label regex, improved alias fallback |
