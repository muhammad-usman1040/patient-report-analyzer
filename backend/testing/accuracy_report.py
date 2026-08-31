"""
Phase 6 Module 1 -- End-to-End Accuracy Testing Script

Runs all sample reports through the full pipeline:
  extract_text_from_report -> parse_report_text -> compare_to_normal_ranges
                          -> evaluate_possible_conditions

Compares results against expected_results.json ground truth.
Outputs a per-category and overall accuracy summary.

Usage:
    cd backend
    python testing/accuracy_report.py
"""
import json
import sys
import os
from pathlib import Path
from typing import Dict, Any

# --- Path setup ---------------------------------------------------------------
BACKEND_DIR = Path(__file__).parent.parent
TESTING_DIR = Path(__file__).parent
SAMPLES_DIR = TESTING_DIR / "sample_reports"
EXPECTED_PATH = TESTING_DIR / "expected_results.json"

for p in (
    str(BACKEND_DIR / "ocr"),
    str(BACKEND_DIR / "analysis"),
):
    if p not in sys.path:
        sys.path.insert(0, p)

from ocr_engine import extract_text_from_report
from value_parser import parse_report_text
from range_comparator import compare_to_normal_ranges
from confidence_engine import evaluate_possible_conditions

# --- Helpers ------------------------------------------------------------------

SECTION_WIDTH = 72


def _divider(char="-"):
    return char * SECTION_WIDTH


def _header(text):
    pad = (SECTION_WIDTH - len(text) - 2) // 2
    return f"{'=' * SECTION_WIDTH}\n{'=' * pad} {text} {'=' * (SECTION_WIDTH - pad - len(text) - 2)}\n{'=' * SECTION_WIDTH}"


# --- Core evaluation ----------------------------------------------------------

def run_sample(sample_file: str, expected: Dict[str, Any], gender=None, age=None):
    """
    Run one sample through the pipeline and compare against expected results.

    Returns a dict with extraction, flagging, and state accuracy details.
    """
    path = SAMPLES_DIR / sample_file
    raw_text = extract_text_from_report(str(path))
    parsed = parse_report_text(raw_text)
    flagged = compare_to_normal_ranges(parsed, user_gender=gender, user_age=age)
    analysis = evaluate_possible_conditions(flagged)

    exp_params = expected["expected_parsed"]
    total_params = len(exp_params)

    # --- Extraction accuracy (was the parameter found at all?) ---------------
    found = sum(1 for p in exp_params if p in parsed)
    missed = [p for p in exp_params if p not in parsed]

    # --- Value accuracy (was the numeric value correct?) ---------------------
    value_correct = sum(
        1 for p, ev in exp_params.items()
        if p in parsed and abs(parsed[p]["value"] - ev["value"]) < 1e-6
    )

    # --- Status/flagging accuracy (High/Low/Normal correctly assigned?) ------
    status_correct = sum(
        1 for p, ev in exp_params.items()
        if p in flagged and flagged[p]["status"] == ev["status"]
    )
    wrong_status = [
        f"{p}: expected={ev['status']}, got={flagged[p]['status']}"
        for p, ev in exp_params.items()
        if p in flagged and flagged[p]["status"] != ev["status"]
    ]

    # --- Result state accuracy ------------------------------------------------
    expected_state = expected["expected_result_state"]
    actual_state = analysis["result_state"]
    state_ok = actual_state == expected_state

    # --- Expected condition check (best-effort -- not strict) -----------------
    exp_cond = expected.get("expected_condition")
    cond_found = False
    if exp_cond:
        cond_found = any(c["name"] == exp_cond for c in analysis.get("conditions", []))

    return {
        "sample": sample_file,
        "category": expected["category"],
        "patient": expected.get("patient", ""),
        "total_params": total_params,
        "found": found,
        "missed": missed,
        "value_correct": value_correct,
        "status_correct": status_correct,
        "wrong_status": wrong_status,
        "expected_state": expected_state,
        "actual_state": actual_state,
        "state_ok": state_ok,
        "expected_condition": exp_cond,
        "condition_found": cond_found,
        "raw_parsed": parsed,
        "raw_flagged": flagged,
        "raw_analysis": analysis,
    }


# --- Main report --------------------------------------------------------------

def main():
    with open(EXPECTED_PATH) as f:
        expected_all = json.load(f)

    results = []
    errors = []

    for sample_file, expected in expected_all.items():
        try:
            r = run_sample(sample_file, expected)
            results.append(r)
        except Exception as e:
            errors.append((sample_file, str(e)))

    # -- Per-sample detail -----------------------------------------------------
    print(_header("PHASE 6 MODULE 1 -- ACCURACY REPORT"))
    print(f"Samples evaluated : {len(results)}")
    print(f"Errors            : {len(errors)}")
    if errors:
        for ef, em in errors:
            print(f"  ERROR {ef}: {em}")
    print()

    # Group by category
    by_category: Dict[str, list] = {}
    for r in results:
        by_category.setdefault(r["category"], []).append(r)

    category_summary = []

    for cat, cat_results in sorted(by_category.items()):
        print(_divider("-"))
        print(f"  CATEGORY: {cat}")
        print(_divider("-"))

        total_p = sum(r["total_params"] for r in cat_results)
        total_found = sum(r["found"] for r in cat_results)
        total_value = sum(r["value_correct"] for r in cat_results)
        total_status = sum(r["status_correct"] for r in cat_results)
        states_ok = sum(1 for r in cat_results if r["state_ok"])

        for r in cat_results:
            ex_pct = r["found"] / r["total_params"] * 100 if r["total_params"] else 0
            st_pct = r["status_correct"] / r["total_params"] * 100 if r["total_params"] else 0
            state_mark = "OK" if r["state_ok"] else "XX"
            print(
                f"  [{state_mark}] {r['sample']:<35} "
                f"Extracted: {r['found']}/{r['total_params']} ({ex_pct:.0f}%)  "
                f"Status: {r['status_correct']}/{r['total_params']} ({st_pct:.0f}%)"
            )
            if r["missed"]:
                print(f"       MISSED: {', '.join(r['missed'])}")
            if r["wrong_status"]:
                for ws in r["wrong_status"]:
                    print(f"       WRONG STATUS: {ws}")
            if r["expected_condition"]:
                mark = "OK" if r["condition_found"] else "XX"
                print(f"       Condition [{mark}]: {r['expected_condition']}")
            if r["expected_state"] != r["actual_state"]:
                print(
                    f"       STATE MISMATCH: expected={r['expected_state']}, "
                    f"actual={r['actual_state']}"
                )

        cat_ex_pct = total_found / total_p * 100 if total_p else 0
        cat_st_pct = total_status / total_p * 100 if total_p else 0
        cat_state_pct = states_ok / len(cat_results) * 100

        print(
            f"\n  {cat} TOTAL: extraction {total_found}/{total_p} ({cat_ex_pct:.1f}%)  "
            f"flagging {total_status}/{total_p} ({cat_st_pct:.1f}%)  "
            f"result_state {states_ok}/{len(cat_results)} ({cat_state_pct:.0f}%)"
        )
        print()

        category_summary.append({
            "category": cat,
            "extraction_pct": cat_ex_pct,
            "flagging_pct": cat_st_pct,
            "state_pct": cat_state_pct,
            "total_params": total_p,
            "found": total_found,
            "status_correct": total_status,
            "states_ok": states_ok,
            "samples": len(cat_results),
        })

    # -- Overall summary table -------------------------------------------------
    print(_header("SUMMARY TABLE"))
    header = f"  {'Category':<18} {'Extraction':>12} {'Flagging':>10} {'State':>8}"
    print(header)
    print("  " + "-" * (len(header) - 2))

    all_total = all_found = all_status = all_states_ok = all_samples = 0

    for cs in category_summary:
        below = cs["extraction_pct"] < 90 or cs["flagging_pct"] < 90
        flag = " WARN" if below else ""
        print(
            f"  {cs['category']:<18} "
            f"{cs['found']}/{cs['total_params']} ({cs['extraction_pct']:5.1f}%)  "
            f"{cs['status_correct']}/{cs['total_params']} ({cs['flagging_pct']:5.1f}%)  "
            f"{cs['states_ok']}/{cs['samples']} ({cs['state_pct']:5.0f}%){flag}"
        )
        all_total += cs["total_params"]
        all_found += cs["found"]
        all_status += cs["status_correct"]
        all_states_ok += cs["states_ok"]
        all_samples += cs["samples"]

    print("  " + "-" * (len(header) - 2))
    ov_ex = all_found / all_total * 100 if all_total else 0
    ov_st = all_status / all_total * 100 if all_total else 0
    ov_state = all_states_ok / all_samples * 100 if all_samples else 0
    print(
        f"  {'OVERALL':<18} "
        f"{all_found}/{all_total} ({ov_ex:5.1f}%)  "
        f"{all_status}/{all_total} ({ov_st:5.1f}%)  "
        f"{all_states_ok}/{all_samples} ({ov_state:5.0f}%)"
    )
    print()

    # -- Pass/Fail verdict -----------------------------------------------------
    TARGET = 90.0
    ex_pass = ov_ex >= TARGET
    st_pass = ov_st >= TARGET

    print(_divider("="))
    print(f"  TARGET: {TARGET}% on extraction AND flagging accuracy")
    print(f"  Extraction accuracy : {ov_ex:.1f}%  {'PASS' if ex_pass else 'FAIL'}")
    print(f"  Flagging accuracy   : {ov_st:.1f}%  {'PASS' if st_pass else 'FAIL'}")
    print(f"  Result state accuracy: {ov_state:.1f}%")
    print(_divider("="))

    failing_cats = [
        cs["category"]
        for cs in category_summary
        if cs["extraction_pct"] < TARGET or cs["flagging_pct"] < TARGET
    ]
    if failing_cats:
        print(f"\n  WARNING - Categories below {TARGET}% target: {', '.join(failing_cats)}")
        print("  -> Fix value_parser.py aliases or normal_ranges.json for these categories.")
    else:
        print(f"\n  All categories meet the {TARGET}% accuracy target.")

    print()
    return 0 if (ex_pass and st_pass) else 1


if __name__ == "__main__":
    sys.exit(main())
