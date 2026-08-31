"""
PDF Report Generator — Phase 5 Module 3.

generate_pdf_report(result: dict, language: str = "en") -> bytes

Generates a complete PDF analysis summary in memory (BytesIO) and returns
raw bytes. Never writes to disk.

Requires: reportlab (free, open-source — pip install reportlab)
"""
from io import BytesIO
from datetime import datetime
from typing import Any, Dict, List

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

# ---------------------------------------------------------------------------
# Colour palette — matches ResultsPage.jsx semantic colours
# ---------------------------------------------------------------------------
_RED = colors.HexColor("#DC2626")       # high
_AMBER = colors.HexColor("#D97706")     # low
_GREEN = colors.HexColor("#16A34A")     # normal
_ORANGE = colors.HexColor("#EA580C")    # condition card
_BLUE = colors.HexColor("#1D4ED8")
_LIGHT_BLUE = colors.HexColor("#EFF6FF")
_LIGHT_RED = colors.HexColor("#FEF2F2")
_LIGHT_AMBER = colors.HexColor("#FFFBEB")
_LIGHT_ORANGE = colors.HexColor("#FFF7ED")
_YELLOW_BG = colors.HexColor("#FEFCE8")
_YELLOW_BORDER = colors.HexColor("#CA8A04")
_GRAY = colors.HexColor("#6B7280")
_DARK = colors.HexColor("#111827")
_MID_GRAY = colors.HexColor("#D1D5DB")

# ---------------------------------------------------------------------------
# Bilingual strings
# ---------------------------------------------------------------------------
_STRINGS = {
    "en": {
        "title": "Patient Report Analysis Summary",
        "subtitle": "Computer-Generated Informational Summary",
        "date_label": "Date of Analysis:",
        "flagged_heading": "Parameter Results",
        "param_col": "Parameter",
        "value_col": "Value",
        "unit_col": "Unit",
        "range_col": "Normal Range",
        "flag_col": "Status",
        "conditions_heading": "Possible Conditions",
        "all_normal": "All values are within the normal range.",
        "insufficient": (
            "Insufficient evidence to identify a specific condition "
            "from the available report."
        ),
        "confidence_label": "Confidence",
        "indicators_label": "Supporting indicators",
        "disclaimer_heading": "Important Disclaimer",
        "disclaimer": (
            "This is NOT a medical diagnosis. The results above are "
            "generated automatically based on reported lab values and "
            "published reference ranges. Please consult a qualified "
            "doctor or healthcare professional before making any "
            "medical decisions."
        ),
        "footer": (
            "This document is a computer-generated informational summary. "
            "It is not a lab-certified or doctor-issued medical report."
        ),
        "status_high": "HIGH",
        "status_low": "LOW",
        "status_normal": "Normal",
        "status_unknown": "—",
        "page": "Page",
    },
    "ur": {
        "title": "مریض رپورٹ تجزیہ خلاصہ",
        "subtitle": "کمپیوٹر سے تیار کردہ معلوماتی خلاصہ",
        "date_label": "تجزیے کی تاریخ:",
        "flagged_heading": "پیرامیٹر نتائج",
        "param_col": "پیرامیٹر",
        "value_col": "قدر",
        "unit_col": "اکائی",
        "range_col": "معمول کی حد",
        "flag_col": "حیثیت",
        "conditions_heading": "ممکنہ حالات",
        "all_normal": "تمام اقدار معمول کی حد میں ہیں۔",
        "insufficient": (
            "دستیاب رپورٹ سے کوئی مخصوص حالت شناخت کرنے کے لیے "
            "ناکافی ثبوت۔"
        ),
        "confidence_label": "اعتماد",
        "indicators_label": "معاون اشارے",
        "disclaimer_heading": "اہم اعلانِ دستبرداری",
        "disclaimer": (
            "یہ طبی تشخیص نہیں ہے۔ اوپر کے نتائج لیب اقدار اور "
            "معیاری حوالہ جاتی حدود کی بنیاد پر خودکار طریقے سے "
            "تیار کیے گئے ہیں۔ براہ کرم کوئی بھی طبی فیصلہ کرنے "
            "سے پہلے کسی اہل ڈاکٹر یا صحت کی دیکھ بھال کے پیشہ ور "
            "سے مشورہ کریں۔"
        ),
        "footer": (
            "یہ دستاویز کمپیوٹر سے تیار کردہ معلوماتی خلاصہ ہے۔ "
            "یہ لیب سے تصدیق شدہ یا ڈاکٹر کا جاری کردہ طبی رپورٹ نہیں ہے۔"
        ),
        "status_high": "زیادہ",
        "status_low": "کم",
        "status_normal": "معمول",
        "status_unknown": "—",
        "page": "صفحہ",
    },
}


def _s(lang: str, key: str) -> str:
    """Look up a localised string by key, falling back to English."""
    return _STRINGS.get(lang, _STRINGS["en"]).get(key, _STRINGS["en"][key])


# ---------------------------------------------------------------------------
# Page-level header / footer callback
# ---------------------------------------------------------------------------

def _make_page_callback(title: str, footer: str):
    """Return a ReportLab onPage callback that draws a header bar and footer on every page."""
    def _draw(canvas, doc):
        canvas.saveState()
        w, h = A4
        # Top blue bar
        canvas.setFillColor(_BLUE)
        canvas.rect(0, h - 18 * mm, w, 18 * mm, fill=1, stroke=0)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawCentredString(w / 2, h - 12 * mm, title)

        # Footer line
        canvas.setStrokeColor(_MID_GRAY)
        canvas.line(15 * mm, 14 * mm, w - 15 * mm, 14 * mm)
        canvas.setFillColor(_GRAY)
        canvas.setFont("Helvetica", 7)
        canvas.drawString(15 * mm, 9 * mm, footer)
        canvas.drawRightString(
            w - 15 * mm, 9 * mm, f"{doc.page}"
        )
        canvas.restoreState()

    return _draw


# ---------------------------------------------------------------------------
# Status helpers
# ---------------------------------------------------------------------------

def _status_label(status: str, lang: str) -> str:
    """Return the localised display label for a parameter status."""
    mapping = {
        "high": _s(lang, "status_high"),
        "low": _s(lang, "status_low"),
        "normal": _s(lang, "status_normal"),
    }
    return mapping.get(status, _s(lang, "status_unknown"))


def _status_color(status: str):
    """Return the ReportLab colour for a status badge."""
    return {"high": _RED, "low": _AMBER, "normal": _GREEN}.get(status, _GRAY)


def _status_bg(status: str):
    """Return the row background colour for high/low rows; white for normal."""
    return {"high": _LIGHT_RED, "low": _LIGHT_AMBER}.get(status, colors.white)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_pdf_report(result: Dict[str, Any], language: str = "en") -> bytes:
    """
    Convert a structured analysis result into a PDF report.

    Args:
        result: dict with keys result_state, flagged_parameters, conditions, disclaimer
        language: "en" (default) or "ur"

    Returns:
        PDF file as raw bytes — never written to disk.
    """
    lang = language if language in _STRINGS else "en"
    buf = BytesIO()

    # Build document
    margin = 15 * mm
    doc = BaseDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=22 * mm,
        bottomMargin=20 * mm,
    )

    page_cb = _make_page_callback(
        title=_s(lang, "title"),
        footer=_s(lang, "footer"),
    )
    frame = Frame(
        margin, 20 * mm,
        A4[0] - 2 * margin, A4[1] - 42 * mm,
        id="body",
    )
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=page_cb)])

    styles = getSampleStyleSheet()
    normal = styles["Normal"]

    def style(name, **kw) -> ParagraphStyle:
        base = kw.pop("parent", normal)
        return ParagraphStyle(name, parent=base, **kw)

    heading2 = style("H2", fontSize=11, textColor=_BLUE,
                     fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=4)
    body_text = style("Body", fontSize=9, leading=13, textColor=_DARK)
    small_gray = style("SmGray", fontSize=7.5, textColor=_GRAY, leading=11)
    disclaimer_style = style(
        "Disc", fontSize=8.5, leading=13, textColor=colors.HexColor("#92400E"),
        fontName="Helvetica",
    )
    condition_name_style = style(
        "CndName", fontSize=10, fontName="Helvetica-Bold",
        textColor=_ORANGE, spaceAfter=2,
    )
    condition_detail_style = style(
        "CndDet", fontSize=8.5, leading=12, textColor=_DARK,
    )

    story: list = []

    # --- Subtitle + date ---
    story.append(Paragraph(_s(lang, "subtitle"), style("Sub", fontSize=9, textColor=_GRAY, alignment=TA_CENTER)))
    story.append(Spacer(1, 4 * mm))

    date_str = datetime.now().strftime("%d %B %Y, %H:%M")
    story.append(Paragraph(f"<b>{_s(lang, 'date_label')}</b> {date_str}", body_text))
    story.append(Spacer(1, 5 * mm))

    # --- Parameter results table ---
    flagged: List[Dict] = result.get("flagged_parameters", [])
    story.append(Paragraph(_s(lang, "flagged_heading"), heading2))

    if flagged:
        col_widths = [52 * mm, 22 * mm, 18 * mm, 42 * mm, 22 * mm]
        header_row = [
            Paragraph(f"<b>{_s(lang, c)}</b>", style("TH", fontSize=8.5, textColor=colors.white, fontName="Helvetica-Bold"))
            for c in ("param_col", "value_col", "unit_col", "range_col", "flag_col")
        ]
        table_data = [header_row]
        row_styles: list = []

        for i, p in enumerate(flagged):
            row_idx = i + 1
            status = p.get("status", "normal")
            lo = p.get("normal_min")
            hi = p.get("normal_max")
            range_str = (
                f"{lo} – {hi}" if lo is not None and hi is not None else "—"
            )
            # Replace 9999 sentinel for "no upper bound" ranges (e.g. HDL)
            range_str = range_str.replace("9999", "∞").replace("– ∞", "∞ →").replace("∞ →", "+ ∞")

            label = _status_label(status, lang)
            label_color = _status_color(status)

            cell_style = style(f"Cell{i}", fontSize=8.5, leading=12, textColor=_DARK)
            status_style = style(
                f"Stat{i}", fontSize=8.5, fontName="Helvetica-Bold",
                textColor=label_color, leading=12,
            )

            table_data.append([
                Paragraph(p.get("name", "").replace("_", " "), cell_style),
                Paragraph(str(p.get("value", "—")), cell_style),
                Paragraph(p.get("unit", "—"), cell_style),
                Paragraph(range_str, cell_style),
                Paragraph(label, status_style),
            ])

            bg = _status_bg(status)
            if bg != colors.white:
                row_styles.append(("BACKGROUND", (0, row_idx), (-1, row_idx), bg))

        tbl = Table(table_data, colWidths=col_widths, repeatRows=1)
        tbl.setStyle(TableStyle([
            # Header
            ("BACKGROUND", (0, 0), (-1, 0), _BLUE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
            ("GRID", (0, 0), (-1, -1), 0.4, _MID_GRAY),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            *row_styles,
        ]))
        story.append(tbl)
    else:
        story.append(Paragraph(_s(lang, "all_normal"), style("OK", fontSize=9, textColor=_GREEN)))

    story.append(Spacer(1, 6 * mm))

    # --- Conditions section ---
    result_state = result.get("result_state", "insufficient_evidence")
    conditions: List[Dict] = result.get("conditions", [])

    story.append(Paragraph(_s(lang, "conditions_heading"), heading2))

    if result_state == "all_normal":
        story.append(Paragraph(_s(lang, "all_normal"), style("AllOK", fontSize=9, textColor=_GREEN)))

    elif result_state == "insufficient_evidence" or not conditions:
        story.append(Paragraph(_s(lang, "insufficient"), style("Insuf", fontSize=9, textColor=_GRAY, fontName="Helvetica-Oblique")))

    else:
        for cond in conditions:
            pct = round(cond.get("confidence", 0) * 100)
            indicators = cond.get("supporting_indicators", [])
            ind_str = ", ".join(indicators) if indicators else "—"
            block = [
                Paragraph(cond["name"].replace("_", " "), condition_name_style),
                Paragraph(
                    f"<b>{_s(lang, 'confidence_label')}:</b> {pct}% &nbsp;&nbsp; "
                    f"<b>{_s(lang, 'indicators_label')}:</b> {ind_str}",
                    condition_detail_style,
                ),
                Spacer(1, 3 * mm),
            ]
            inner_tbl = Table(
                [[block]],
                colWidths=[A4[0] - 2 * margin - 8 * mm],
            )
            inner_tbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), _LIGHT_ORANGE),
                ("BOX", (0, 0), (-1, -1), 0.8, _ORANGE),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]))
            story.append(KeepTogether([inner_tbl, Spacer(1, 3 * mm)]))

    story.append(Spacer(1, 6 * mm))

    # --- Disclaimer box ---
    disc_tbl = Table(
        [[
            Paragraph(f"<b>⚕ {_s(lang, 'disclaimer_heading')}</b>", style("DH", fontSize=9, fontName="Helvetica-Bold", textColor=colors.HexColor("#92400E"))),
            Paragraph(_s(lang, "disclaimer"), disclaimer_style),
        ]],
        colWidths=[A4[0] - 2 * margin],
        rowHeights=None,
    )
    # Use single-cell layout for the disclaimer block
    disc_content = [
        Paragraph(f"<b>⚕ {_s(lang, 'disclaimer_heading')}</b>",
                  style("DH2", fontSize=9, fontName="Helvetica-Bold",
                        textColor=colors.HexColor("#92400E"), spaceAfter=3)),
        Paragraph(_s(lang, "disclaimer"), disclaimer_style),
    ]
    disc_wrapper = Table(
        [[disc_content]],
        colWidths=[A4[0] - 2 * margin],
    )
    disc_wrapper.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _YELLOW_BG),
        ("BOX", (0, 0), (-1, -1), 1.0, _YELLOW_BORDER),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(KeepTogether([disc_wrapper]))

    doc.build(story)
    return buf.getvalue()
