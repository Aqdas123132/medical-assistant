"""
report.py - Build the downloadable report (.txt always, .pdf when possible).

The PDF uses the 'reportlab' library and the built-in Helvetica font, which
only supports Latin letters. For Urdu/Arabic/Hindi etc. we skip the PDF and
the user can use the .txt report instead.
"""

import io
import re
from datetime import datetime

from src.config import DISCLAIMER_LONG

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    REPORTLAB_OK = True
except Exception:  # reportlab not installed
    REPORTLAB_OK = False


def _parsed(a: dict) -> dict:
    return a.get("parsed") or {}


def build_report_text(a: dict, user: dict) -> str:
    """Plain text report, works for every language."""
    p = _parsed(a)
    lines = [
        "MEDIGUIDE AI - GUIDANCE REPORT",
        "=" * 40,
        f"Prepared for : {user.get('full_name', '')}",
        f"Created      : {str(a.get('created_at', ''))[:19].replace('T', ' ')}",
        f"Generated on : {datetime.now():%Y-%m-%d %H:%M}",
        "",
        "DISCLAIMER",
        DISCLAIMER_LONG,
        "",
        "PATIENT SUMMARY",
        f"Age: {a.get('age')} | Gender: {a.get('gender')} | Duration: {a.get('duration')}",
        f"Symptoms: {a.get('symptoms')}",
        f"Severity reported: {a.get('severity')}/10",
        "",
        f"URGENCY LEVEL: {p.get('urgency_level') or a.get('urgency') or 'n/a'}",
        "",
        "GENERAL INFORMATION",
        p.get("summary") or "-",
        "",
        "POSSIBLE CONDITIONS (education only, NOT a diagnosis)",
    ]
    for c in p.get("possible_conditions") or []:
        lines.append(f"- {c.get('name', '')}: {c.get('reason', '')}")
    lines += ["", "RECOMMENDED NEXT STEPS"]
    lines += [f"- {s}" for s in p.get("recommended_next_steps") or []]
    lines += ["", "QUESTIONS FOR YOUR DOCTOR"]
    lines += [f"- {q}" for q in p.get("questions_for_doctor") or []]
    lines += ["", "WARNING SIGNS - seek urgent help if these happen"]
    lines += [f"- {w}" for w in p.get("warning_signs") or []]
    if a.get("narrative"):
        lines += ["", "GUIDANCE IN PLAIN WORDS", a["narrative"]]
    lines += ["", "-" * 40, "Educational project, not a medical device. See a qualified professional."]
    return "\n".join(lines)


def _is_latin(text: str) -> bool:
    """True when the text can be written with the standard PDF font."""
    try:
        text.encode("latin-1")
        return True
    except UnicodeEncodeError:
        return False


def pdf_supported(a: dict, user: dict) -> bool:
    return REPORTLAB_OK and _is_latin(build_report_text(a, user))


def _clean(text: str) -> str:
    """Escape characters that reportlab's mini-HTML would misread."""
    text = str(text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return re.sub(r"\s+\n", "\n", text).replace("\n", "<br/>")


def build_pdf(a: dict, user: dict) -> bytes:
    p = _parsed(a)
    styles = getSampleStyleSheet()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm, title="MediGuide AI Report")
    story = []

    def heading(text):
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"<b>{_clean(text)}</b>", styles["Heading3"]))

    def para(text):
        story.append(Paragraph(_clean(text), styles["BodyText"]))

    def bullets(items):
        for item in items or ["-"]:
            story.append(Paragraph("&bull; " + _clean(item), styles["BodyText"]))

    story.append(Paragraph("MediGuide AI - Guidance Report", styles["Title"]))
    para(f"Prepared for {user.get('full_name', '')} on {datetime.now():%Y-%m-%d %H:%M}")
    story.append(Spacer(1, 8))
    para(DISCLAIMER_LONG)

    heading("Patient summary")
    para(f"Age: {a.get('age')} | Gender: {a.get('gender')} | Duration: {a.get('duration')}")
    para(f"Symptoms: {a.get('symptoms')}")
    para(f"Severity reported: {a.get('severity')}/10")

    heading(f"Urgency level: {p.get('urgency_level') or a.get('urgency') or 'n/a'}")
    heading("General information")
    para(p.get("summary") or "-")

    heading("Possible conditions (education only, not a diagnosis)")
    bullets([f"{c.get('name', '')}: {c.get('reason', '')}" for c in p.get("possible_conditions") or []])
    heading("Recommended next steps")
    bullets(p.get("recommended_next_steps"))
    heading("Questions for your doctor")
    bullets(p.get("questions_for_doctor"))
    heading("Warning signs - seek urgent help")
    bullets(p.get("warning_signs"))

    if a.get("narrative"):
        heading("Guidance in plain words")
        para(a["narrative"])

    doc.build(story)
    return buffer.getvalue()