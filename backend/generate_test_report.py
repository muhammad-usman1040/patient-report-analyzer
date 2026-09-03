"""Generate a realistic multi-section test lab report PDF."""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import re

doc = SimpleDocTemplate(
    "test_lab_report.pdf",
    pagesize=A4,
    leftMargin=20*mm, rightMargin=20*mm,
    topMargin=20*mm, bottomMargin=20*mm,
)

styles = getSampleStyleSheet()
story = []

header_style = ParagraphStyle("H", fontName="Helvetica-Bold", fontSize=16, spaceAfter=2)
sub_style = ParagraphStyle("S", fontName="Helvetica", fontSize=9, textColor=colors.grey, spaceAfter=4)
sep_style = ParagraphStyle("Sep", fontName="Helvetica", fontSize=9, spaceAfter=6)
section_style = ParagraphStyle(
    "Sec", fontName="Helvetica-Bold", fontSize=11,
    spaceBefore=10, spaceAfter=4, textColor=colors.HexColor("#1D4ED8"),
)
footer_style = ParagraphStyle(
    "F", fontName="Helvetica-Oblique", fontSize=7.5,
    textColor=colors.grey, spaceAfter=2,
)

BLUE = colors.HexColor("#1D4ED8")
RED = colors.HexColor("#DC2626")
AMBER = colors.HexColor("#D97706")
LOW_BG = colors.HexColor("#FEF2F2")
HIGH_BG = colors.HexColor("#FFFBEB")
ALT_ROW = colors.HexColor("#F9FAFB")
GRID = colors.HexColor("#D1D5DB")

# ---- Header ----
story.append(Paragraph("CITY DIAGNOSTICS LABORATORY", header_style))
story.append(Paragraph("123 Medical Plaza, Lahore, Pakistan  |  Tel: 042-1234567  |  lab@citydiag.pk", sub_style))
story.append(Paragraph("-" * 95, sep_style))
story.append(Spacer(1, 4*mm))

# ---- Patient info ----
patient_data = [
    ["Patient Name:", "Ahmed Khan", "Report No:", "CDL-2026-08831"],
    ["Age / Gender:", "45 Years / Male", "Sample Date:", "31-Aug-2026"],
    ["Ref. Doctor:", "Dr. Fatima Malik", "Report Date:", "31-Aug-2026"],
]
pt = Table(patient_data, colWidths=[38*mm, 55*mm, 38*mm, 45*mm])
pt.setStyle(TableStyle([
    ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
    ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ("TOPPADDING", (0, 0), (-1, -1), 3),
    ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
    ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
]))
story.append(pt)
story.append(Spacer(1, 6*mm))


def calculate_status(value, reference):
    value_text = str(value).strip().lower()
    reference_text = str(reference).strip().lower()
    if not re.search(r"\d", value_text):
        return "Normal" if value_text == reference_text or value_text in {"negative", "nil", "none", "absent", "clear", "few", "pale yellow"} else "HIGH"
    numeric_value = float(value_text.replace(",", ""))
    range_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(?:-|–|—|to)\s*([0-9]+(?:\.[0-9]+)?)", reference)
    if range_match:
        low, high = map(float, range_match.groups())
        if numeric_value < low:
            return "LOW"
        if numeric_value > high:
            return "HIGH"
        return "Normal"
    upper_match = re.search(r"(?:<|≤)\s*([0-9]+(?:\.[0-9]+)?)", reference)
    lower_match = re.search(r"(?:>|≥)\s*([0-9]+(?:\.[0-9]+)?)", reference)
    if upper_match:
        return "HIGH" if numeric_value > float(upper_match.group(1)) else "Normal"
    if lower_match:
        return "LOW" if numeric_value < float(lower_match.group(1)) else "Normal"
    return "—"


def make_table(data, flag_rows_high=None, flag_rows_low=None):
    for row in data[1:]:
        row[4] = calculate_status(row[1], row[3])
    flag_rows_high = [index for index, row in enumerate(data[1:], start=1) if row[4] == "HIGH"]
    flag_rows_low = [index for index, row in enumerate(data[1:], start=1) if row[4] == "LOW"]
    col_widths = [60*mm, 25*mm, 22*mm, 45*mm, 18*mm]
    tbl = Table(data, colWidths=col_widths)
    style_cmds = [
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (-1, 1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("GRID", (0, 0), (-1, -1), 0.3, GRID),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ALT_ROW]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    for r in flag_rows_high:
        style_cmds.append(("BACKGROUND", (0, r), (-1, r), HIGH_BG))
        style_cmds.append(("TEXTCOLOR", (-1, r), (-1, r), AMBER))
    for r in flag_rows_low:
        style_cmds.append(("BACKGROUND", (0, r), (-1, r), LOW_BG))
        style_cmds.append(("TEXTCOLOR", (-1, r), (-1, r), RED))
    tbl.setStyle(TableStyle(style_cmds))
    return tbl


# ---- CBC ----
story.append(Paragraph("COMPLETE BLOOD COUNT (CBC)", section_style))
cbc = [
    ["TEST", "RESULT", "UNIT", "REFERENCE RANGE", "FLAG"],
    ["Hemoglobin",       "7.8",  "g/dL",       "13.5 - 17.5",  "LOW"],
    ["RBC Count",        "3.2",  "x10^12/L",   "4.5 - 5.9",    "LOW"],
    ["Hematocrit (PCV)", "26.0", "%",           "41 - 53",      "LOW"],
    ["MCV",              "68",   "fL",          "80 - 100",     "LOW"],
    ["MCH",              "21",   "pg",          "27 - 33",      "LOW"],
    ["MCHC",             "30",   "g/dL",        "31.5 - 36.0",  "LOW"],
    ["Platelets",        "420",  "x10^9/L",     "150 - 400",    "HIGH"],
    ["WBC",              "6.8",  "x10^9/L",     "4.0 - 11.0",   ""],
    ["Neutrophils",      "62",   "%",           "40 - 75",      ""],
    ["Lymphocytes",      "28",   "%",           "20 - 45",      ""],
    ["Monocytes",        "7",    "%",           "2 - 10",       ""],
    ["Eosinophils",      "3",    "%",           "1 - 6",        ""],
]
story.append(make_table(cbc, flag_rows_high=[7], flag_rows_low=[1, 2, 3, 4, 5, 6]))
story.append(Spacer(1, 6*mm))

# ---- Lipid Profile ----
story.append(Paragraph("LIPID PROFILE", section_style))
lipid = [
    ["TEST", "RESULT", "UNIT", "REFERENCE RANGE", "FLAG"],
    ["Total Cholesterol", "245", "mg/dL", "< 200",  "HIGH"],
    ["Triglycerides",     "310", "mg/dL", "< 150",  "HIGH"],
    ["HDL Cholesterol",   "32",  "mg/dL", "> 40",   "LOW"],
    ["LDL Cholesterol",   "168", "mg/dL", "< 100",  "HIGH"],
    ["VLDL",              "45",  "mg/dL", "< 30",   "HIGH"],
]
story.append(make_table(lipid, flag_rows_high=[1, 2, 4, 5], flag_rows_low=[3]))
story.append(Spacer(1, 6*mm))

# ---- Blood Glucose ----
story.append(Paragraph("BLOOD GLUCOSE", section_style))
glucose = [
    ["TEST", "RESULT", "UNIT", "REFERENCE RANGE", "FLAG"],
    ["Fasting Blood Sugar (FBS)", "138", "mg/dL", "70 - 100", "HIGH"],
    ["HbA1c",                     "7.2", "%",     "< 5.7",    "HIGH"],
]
story.append(make_table(glucose, flag_rows_high=[1, 2], flag_rows_low=[]))
story.append(Spacer(1, 8*mm))

# ---- Urinalysis ----
story.append(Paragraph("URINALYSIS (URINE R/E)", section_style))
urinalysis = [
    ["TEST", "RESULT", "UNIT", "REFERENCE RANGE", "FLAG"],
    ["Color", "Pale Yellow", "", "Pale Yellow", "Normal"],
    ["Appearance", "Clear", "", "Clear", "Normal"],
    ["Specific Gravity", "1.015", "", "1.005 - 1.030", "Normal"],
    ["Protein", "Negative", "", "Negative", "Normal"],
    ["Glucose", "Negative", "", "Negative", "Normal"],
    ["Ketones", "Negative", "", "Negative", "Normal"],
    ["Blood", "Negative", "", "Negative", "Normal"],
    ["Leukocyte Esterase", "Negative", "", "Negative", "Normal"],
    ["Nitrites", "Negative", "", "Negative", "Normal"],
    ["Epithelial Cells", "Few", "", "Few", "Normal"],
    ["Pus Cells", "2", "/hpf", "0 - 5", "Normal"],
    ["RBC", "1", "/hpf", "0 - 2", "Normal"],
    ["Casts", "None", "", "None", "Normal"],
    ["Crystals", "None", "", "None", "Normal"],
]
story.append(make_table(urinalysis))
story.append(Spacer(1, 6*mm))

# ---- Footer ----
story.append(Paragraph("-" * 95, sep_style))
story.append(Paragraph("* Results outside normal reference range are flagged HIGH or LOW.", footer_style))
story.append(Paragraph("* This report is for informational purposes only. Please consult your physician for interpretation.", footer_style))
story.append(Paragraph("* Authorized Signatory: Dr. Zara Hussain (MBBS, Pathologist) — City Diagnostics Laboratory", footer_style))

doc.build(story)
print("PDF created: test_lab_report.pdf")
