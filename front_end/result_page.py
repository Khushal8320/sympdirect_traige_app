"""
result_page.py — Assessment Result page (Page 3).

Shared variables READ from st.session_state:
  result, features, is_guest, user_id, email

Shared variables WRITTEN to st.session_state:
  result, features, page  (on reset / sign-out)
"""

# ── Standard library ──────────────────────────────────────────────────────────
import io
import math
import re
from datetime import datetime
from urllib.parse import quote

# ── Third-party ───────────────────────────────────────────────────────────────
import streamlit as st

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table,
        TableStyle, HRFlowable,
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    _REPORTLAB_OK = True
except ImportError:
    _REPORTLAB_OK = False

# ── Standard-library email helpers ───────────────────────────────────────────
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders as _email_encoders

# ── Internal modules ──────────────────────────────────────────────────────────
from config import CI, TELEHEALTH, DEFAULTS
from ui_helpers import inject_css, top_bar, nav_bar, sp, sec_label, ring_svg


# =============================================================================
# NULL-SAFE HELPERS
# =============================================================================

def is_missing_value(v):
    if v is None:
        return True
    try:
        if isinstance(v, float) and math.isnan(v):
            return True
    except Exception:
        pass
    if isinstance(v, str) and v.strip().lower() in ("", "none", "nan", "null"):
        return True
    return False


def safe_text(v, default="N/A"):
    return default if is_missing_value(v) else str(v)


def safe_ctas_text(v):
    if is_missing_value(v):
        return "N/A"
    try:
        return str(int(float(v)))
    except Exception:
        return str(v)


def rule_explain_text(v):
    if is_missing_value(v):
        return "Rule not escalated"
    return f"Rule escalated → CTAS {safe_ctas_text(v)}"


# =============================================================================
# CLINICIAN IDENTITY HELPERS  (initials & display name from email)
# =============================================================================

def get_initials(email: str) -> str:
    """
    Derive short initials from a clinician's email address.

    Examples
    --------
    john.doe@hospital.org   → J.D.
    alice_smith@clinic.ca   → A.S.
    drwilliams@example.com  → D.
    """
    if not email or "@" not in email:
        return "G"
    local = email.split("@")[0]
    parts = [p for p in re.split(r"[._\-]", local) if p]
    if len(parts) >= 2:
        return ".".join(p[0].upper() for p in parts) + "."
    return local[:2].upper() + "."


def get_display_name(email: str) -> str:
    """
    Derive a human-readable name from a clinician's email address.

    Examples
    --------
    john.doe@hospital.org   → John Doe
    alice_smith@clinic.ca   → Alice Smith
    drwilliams@example.com  → Drwilliams
    """
    if not email or "@" not in email:
        return "Guest"
    local = email.split("@")[0]
    parts = [p for p in re.split(r"[._\-]", local) if p]
    return " ".join(p.capitalize() for p in parts) if parts else local.capitalize()


# =============================================================================
# EXPLAINABLE-AI  — narrative generators
# =============================================================================

_CTAS_NAMES = {
    1: "Resuscitation", 2: "Emergent", 3: "Urgent",
    4: "Less Urgent",   5: "Non-Urgent",
}


def _ctas_label(v):
    """Return 'CTAS N (Name)' or None if missing."""
    if is_missing_value(v):
        return None
    try:
        n = int(float(v))
        return f"CTAS {n} ({_CTAS_NAMES.get(n, 'Unknown')})"
    except Exception:
        return str(v)


def build_xai_narrative(res: dict) -> str:
    """
    Return an HTML string explaining, in plain clinical English,
    how the final CTAS level was reached.
    """
    final_ctas_raw = res.get("Final_CTAS", 3)
    final_ctas     = safe_ctas_text(final_ctas_raw)
    final_name     = _CTAS_NAMES.get(int(final_ctas), "") if final_ctas != "N/A" else ""
    final_source   = str(res.get("Final_Source", "")).strip().lower()

    preg_rule  = _ctas_label(res.get("Pregnancy_Rule_CTAS"))
    clin_rule  = _ctas_label(res.get("Clinical_Rule_CTAS"))
    comb_rule  = _ctas_label(res.get("Combined_Rule_CTAS"))
    model_def  = _ctas_label(res.get("Model_Default_CTAS"))
    model_tune = _ctas_label(res.get("Model_Tuned_CTAS"))

    # ── Step 1 — Rule evaluation ──────────────────────────────────────────────
    rule_items = []

    if preg_rule:
        rule_items.append(
            f"<li><strong>Pregnancy / Obstetric Rule — triggered.</strong> The patient's "
            f"obstetric status combined with the presenting complaint met the escalation "
            f"threshold, raising the triage level to <strong>{preg_rule}</strong>.</li>"
        )
    else:
        rule_items.append(
            "<li><strong>Pregnancy / Obstetric Rule — not triggered.</strong> "
            "The patient is either not pregnant, or the presentation did not meet "
            "obstetric escalation criteria.</li>"
        )

    if clin_rule:
        rule_items.append(
            f"<li><strong>Clinical Rule — triggered.</strong> One or more vital signs "
            f"crossed a critical safety threshold (e.g., severely abnormal blood pressure, "
            f"heart rate, respiratory rate, or temperature), forcing escalation to "
            f"<strong>{clin_rule}</strong> regardless of the model output.</li>"
        )
    else:
        rule_items.append(
            "<li><strong>Clinical Rule — not triggered.</strong> "
            "All vital signs remained within the bounds that would mandate automatic "
            "rule-based escalation.</li>"
        )

    if comb_rule:
        rule_items.append(
            f"<li><strong>Combined Rule — triggered.</strong> The simultaneous combination "
            f"of multiple abnormal parameters (e.g., elevated pain score alongside haemodynamic "
            f"instability) met the composite escalation threshold, escalating to "
            f"<strong>{comb_rule}</strong>.</li>"
        )
    else:
        rule_items.append(
            "<li><strong>Combined Rule — not triggered.</strong> "
            "The overall combination of findings did not meet the multi-parameter "
            "composite escalation criteria.</li>"
        )

    step1_html = (
        "<ul style='margin:.3rem 0 .3rem 1.2rem;padding:0;line-height:1.8;'>"
        + "".join(rule_items)
        + "</ul>"
    )

    # ── Step 2 — ML model ─────────────────────────────────────────────────────
    if model_def and model_tune:
        if model_def == model_tune:
            step2_html = (
                f"The machine-learning model produced consistent predictions under both the "
                f"<em>default</em> and <em>sensitivity-tuned</em> probability thresholds: "
                f"<strong>{model_tune}</strong>. Agreement across thresholds strengthens "
                f"confidence in this prediction."
            )
        else:
            step2_html = (
                f"Under the <em>default</em> probability threshold the model initially predicted "
                f"<strong>{model_def}</strong>. After applying sensitivity-tuned thresholds "
                f"— calibrated to reduce under-triaging of high-acuity CTAS&nbsp;1 and 2 cases "
                f"— the prediction shifted to <strong>{model_tune}</strong>. "
                f"The tuned value takes precedence."
            )
    elif model_tune:
        step2_html = (
            f"The machine-learning model predicted <strong>{model_tune}</strong> "
            f"using sensitivity-tuned probability thresholds."
        )
    else:
        step2_html = "The ML model output was unavailable or could not be interpreted for this assessment."

    # ── Step 3 — Final decision ───────────────────────────────────────────────
    if "rule" in final_source:
        step3_html = (
            f"Because one or more <strong>clinical rules were triggered</strong>, the rule-based "
            f"escalation overrides the model output. This design ensures hard clinical safety "
            f"boundaries are never superseded by a probabilistic model. "
            f"The final triage level is <strong>CTAS {final_ctas} — {final_name}</strong> "
            f"<em>(Rule Override)</em>."
        )
    else:
        step3_html = (
            f"No clinical or obstetric rule was triggered. The system therefore uses the "
            f"ML model's tuned prediction as the final result. "
            f"The final triage level is <strong>CTAS {final_ctas} — {final_name}</strong> "
            f"<em>(ML Model)</em>."
        )

    return f"""
    <div style="font-size:.855rem;color:#1E3A52;line-height:1.75;">

      <p style="margin:0 0 .7rem;">
        TriageAI uses a <strong>layered decision pipeline</strong>: deterministic clinical
        rules are evaluated first; if none fire, the machine-learning model provides the
        final triage level. Below is a step-by-step account of how
        <strong>CTAS {final_ctas} — {final_name}</strong> was determined.
      </p>

      <p style="font-weight:700;color:#0369A1;margin:.7rem 0 .25rem;font-size:.88rem;">
        Step 1 &mdash; Rule Evaluation
      </p>
      <p style="margin:0 0 .1rem;">
        Three independent rule sets were evaluated against the patient's data:
      </p>
      {step1_html}

      <p style="font-weight:700;color:#0369A1;margin:.7rem 0 .25rem;font-size:.88rem;">
        Step 2 &mdash; Machine-Learning Model Prediction
      </p>
      <p style="margin:0 0 .65rem;">{step2_html}</p>

      <p style="font-weight:700;color:#0369A1;margin:.7rem 0 .25rem;font-size:.88rem;">
        Step 3 &mdash; Final Decision
      </p>
      <p style="margin:0 0 .5rem;">{step3_html}</p>

      <div style="background:#EFF6FF;border-left:3px solid #3B82F6;border-radius:6px;
                  padding:.55rem .9rem;margin-top:.6rem;font-size:.79rem;color:#1E3A52;">
        <strong>Note:</strong> This narrative reflects the system's internal logic at the
        time of assessment and is intended to support — not replace — clinical judgement.
        The attending clinician remains responsible for the final triage decision.
      </div>
    </div>
    """


def build_xai_pdf_sections(res: dict) -> list:
    """
    Return a list of (heading, body_text) tuples for the PDF report.
    """
    final_ctas  = safe_ctas_text(res.get("Final_CTAS", 3))
    final_name  = _CTAS_NAMES.get(int(final_ctas), "") if final_ctas != "N/A" else ""
    final_src   = str(res.get("Final_Source", "")).strip().lower()

    preg_rule   = _ctas_label(res.get("Pregnancy_Rule_CTAS"))
    clin_rule   = _ctas_label(res.get("Clinical_Rule_CTAS"))
    comb_rule   = _ctas_label(res.get("Combined_Rule_CTAS"))
    model_def   = _ctas_label(res.get("Model_Default_CTAS"))
    model_tune  = _ctas_label(res.get("Model_Tuned_CTAS"))

    r1 = f"Pregnancy/Obstetric Rule: {'Triggered → ' + preg_rule if preg_rule else 'Not triggered.'}"
    r2 = f"Clinical Rule: {'Triggered → ' + clin_rule if clin_rule else 'Not triggered — no vital-sign threshold breached.'}"
    r3 = f"Combined Rule: {'Triggered → ' + comb_rule if comb_rule else 'Not triggered — composite criteria not met.'}"
    step1_body = f"{r1}\n{r2}\n{r3}"

    if model_def and model_tune and model_def != model_tune:
        step2_body = (
            f"Default threshold: {model_def}. "
            f"Sensitivity-tuned threshold: {model_tune}. "
            f"The tuned prediction is used as it reduces under-triaging risk."
        )
    elif model_tune:
        step2_body = f"Model prediction (tuned): {model_tune}."
    else:
        step2_body = "Model output unavailable."

    if "rule" in final_src:
        step3_body = (
            f"A clinical rule override was applied. "
            f"Final triage level: CTAS {final_ctas} — {final_name} (Rule Override)."
        )
    else:
        step3_body = (
            f"No rule triggered; ML model used. "
            f"Final triage level: CTAS {final_ctas} — {final_name} (ML Model)."
        )

    return [
        ("Step 1 — Rule Evaluation",          step1_body),
        ("Step 2 — ML Model Prediction",       step2_body),
        ("Step 3 — Final Decision",            step3_body),
    ]


# =============================================================================
# PDF REPORT GENERATOR
# =============================================================================

def generate_pdf_report(res: dict, feat: dict, email: str = None) -> bytes:
    """
    Build a professional A4 clinical PDF report and return raw bytes.
    Requires reportlab. Raises RuntimeError if reportlab is not installed.
    """
    if not _REPORTLAB_OK:
        raise RuntimeError(
            "reportlab is not installed. Run:  pip install reportlab"
        )

    CTAS_COLORS = {
        1: ("#7C3AED", "#EDE9FE"),
        2: ("#DC2626", "#FEE2E2"),
        3: ("#D97706", "#FEF3C7"),
        4: ("#059669", "#D1FAE5"),
        5: ("#0369A1", "#E0F2FE"),
    }
    CTAS_TIMES = {
        1: "Immediate",      2: "Within 20 min", 3: "Within 40 min",
        4: "Within 120 min",  5: "Within 420 min",
    }

    ctas       = int(res.get("Final_CTAS", 3))
    clr, light = CTAS_COLORS.get(ctas, ("#0369A1", "#E0F2FE"))
    clr_obj    = colors.HexColor(clr)
    light_obj  = colors.HexColor(light)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        topMargin=12*mm, bottomMargin=15*mm,
        leftMargin=18*mm, rightMargin=18*mm,
    )

    styles = getSampleStyleSheet()

    def S(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    h2_s   = S("h2",  fontSize=11, fontName="Helvetica-Bold",
               textColor=colors.HexColor("#0E1F35"), spaceBefore=8, spaceAfter=3)
    lbl_s  = S("lbl", fontSize=8,  fontName="Helvetica-Bold",
               textColor=colors.HexColor("#6B90AA"))
    val_s  = S("val", fontSize=10, fontName="Helvetica-Bold",
               textColor=colors.HexColor("#0E1F35"))
    bod_s  = S("bod", fontSize=9,  textColor=colors.HexColor("#1E3A52"), leading=13)
    disc_s = S("dsc", fontSize=8,  textColor=colors.HexColor("#92400E"),
               backColor=colors.HexColor("#FEF3C7"), borderPadding=5, spaceBefore=6)

    story = []

    # ── Header ────────────────────────────────────────────────────────────────
    ts             = datetime.now().strftime("%Y-%m-%d  %H:%M")
    display_name   = get_display_name(email) if email else "Guest"
    assessor_line  = f"Assessor: {display_name}  |  {email}" if email else "Assessor: Guest session"

    hdr = Table([[
        Paragraph(
            "<font color='white'><b>TriageAI — Clinical Decision Support</b></font>",
            S("hb", fontSize=13, fontName="Helvetica-Bold",
              textColor=colors.white, alignment=TA_LEFT)),
        Paragraph(
            f"<font color='white'>Generated: {ts}<br/>{assessor_line}</font>",
            S("ht", fontSize=8, textColor=colors.white, alignment=TA_RIGHT, leading=12)),
    ]], colWidths=["58%", "42%"])
    hdr.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), clr_obj),
        ("TOPPADDING",    (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("LEFTPADDING",   (0,0), (0,-1),  12),
        ("RIGHTPADDING",  (-1,0),(-1,-1), 12),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 6*mm))

    # ── CTAS Hero ─────────────────────────────────────────────────────────────
    prob_cols = [k for k in res if str(k).startswith("Prob_Class_")]
    max_prob  = max((float(res.get(k, 0)) for k in prob_cols), default=0)
    conf_pct  = round(max_prob * 100)

    hero = Table([[
        Paragraph(
            f"<font color='{clr}'><b>CTAS&nbsp;{ctas}&nbsp;Level</b></font>",
            S("hl", fontSize=27, fontName="Helvetica-Bold",
              textColor=clr_obj, alignment=TA_CENTER)),
        Paragraph(
            f"<b>{_CTAS_NAMES[ctas]}</b><br/>"
            f"<font color='#6B90AA' size='9'>Response Target: {CTAS_TIMES[ctas]}</font><br/>"
            f"<font color='#6B90AA' size='9'>Confidence Score: {conf_pct}%</font>",
            S("hd", fontSize=12, textColor=colors.HexColor("#0E1F35"),
              alignment=TA_LEFT, leading=20)),
    ]], colWidths=["42%", "58%"])
    hero.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), light_obj),
        ("BOX",           (0,0), (-1,-1), 1.5, clr_obj),
        ("TOPPADDING",    (0,0), (-1,-1), 14),
        ("BOTTOMPADDING", (0,0), (-1,-1), 14),
        ("LEFTPADDING",   (0,0), (-1,-1), 14),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    story.append(hero)
    story.append(Spacer(1, 5*mm))

    # ── Patient Information ───────────────────────────────────────────────────
    story.append(Paragraph("Patient Information", h2_s))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#D0E4F1")))
    story.append(Spacer(1, 2*mm))

    preg_raw = feat.get("pregnant", feat.get("Pregnant", 0))
    preg_txt = "Yes" if preg_raw == 1 else ("Unknown" if preg_raw not in (0, 1) else "No")
    chief    = feat.get("Chief_complain_clean") or feat.get("Chief_complain") or "N/A"

    def kv(label, value):
        return [Paragraph(label, lbl_s), Paragraph(str(value), val_s)]

    pt_tbl = Table([
        kv("AGE",              f"{feat.get('Age', 'N/A')} years"),
        kv("BIOLOGICAL SEX",   feat.get("Sex", "N/A")),
        kv("PREGNANCY STATUS", preg_txt),
    ], colWidths=["35%", "65%"])
    pt_tbl.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.HexColor("#F7FBFF"), colors.white]),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("BOX",           (0,0), (-1,-1), 0.5, colors.HexColor("#D0E4F1")),
        ("INNERGRID",     (0,0), (-1,-1), 0.3, colors.HexColor("#D0E4F1")),
    ]))
    story.append(pt_tbl)
    story.append(Spacer(1, 2*mm))

    story.append(Paragraph("CHIEF COMPLAINT", lbl_s))
    cc = Table([[Paragraph(chief, val_s)]], colWidths=["100%"])
    cc.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), colors.HexColor("#F0F9FF")),
        ("BOX",           (0,0), (-1,-1), 1,   colors.HexColor("#BAE6FD")),
        ("TOPPADDING",    (0,0), (-1,-1), 7),
        ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
    ]))
    story.append(cc)
    story.append(Spacer(1, 5*mm))

    # ── Vital Signs ───────────────────────────────────────────────────────────
    story.append(Paragraph("Vital Signs", h2_s))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#D0E4F1")))
    story.append(Spacer(1, 2*mm))

    sbp = feat.get("SBP", 0);  dbp = feat.get("DBP", 0)
    hr  = feat.get("HR",  0);  rr  = feat.get("RR",  0)
    bt  = float(feat.get("BT", 0)); nrs = feat.get("NRS_pain", 0)

    vital_defs = [
        ("SBP",         sbp,           "mmHg", "90–140",    sbp < 90  or sbp > 180),
        ("DBP",         dbp,           "mmHg", "60–90",     dbp < 60  or dbp > 90),
        ("Heart Rate",  hr,            "bpm",  "50–100",    hr  < 50  or hr  > 120),
        ("Resp. Rate",  rr,            "/min", "12–20",     rr  < 8   or rr  > 25),
        ("Temperature", f"{bt:.1f}",   "°C",   "36.0–37.5", bt < 36   or bt  > 38.5),
        ("NRS Pain",    f"{nrs}/10",   "",     "0–3",       nrs >= 8),
    ]

    def vital_row_data(name, val, unit, normal, is_warn):
        sc = "#DC2626" if is_warn else "#059669"
        st_ = "ABNORMAL" if is_warn else "NORMAL"
        return [
            Paragraph(name,               S(f"vn{name}", fontSize=9, fontName="Helvetica-Bold", textColor=colors.HexColor("#0E1F35"))),
            Paragraph(f"<b>{val}</b> {unit}", S(f"vv{name}", fontSize=10, fontName="Helvetica-Bold", textColor=colors.HexColor("#0E1F35"))),
            Paragraph(f"Normal: {normal}", S(f"vr{name}", fontSize=8, textColor=colors.HexColor("#6B90AA"))),
            Paragraph(f"<b><font color='{sc}'>{st_}</font></b>", S(f"vs{name}", fontSize=8, fontName="Helvetica-Bold")),
        ]

    v_rows = [["Vital Sign", "Value", "Reference Range", "Status"]]
    for item in vital_defs:
        v_rows.append(vital_row_data(*item))

    v_style = [
        ("BACKGROUND",    (0,0), (-1,0), colors.HexColor("#0369A1")),
        ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,0), 8),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("BOX",           (0,0), (-1,-1), 0.5, colors.HexColor("#D0E4F1")),
        ("INNERGRID",     (0,0), (-1,-1), 0.3, colors.HexColor("#D0E4F1")),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]
    for i, (*_, is_warn) in enumerate(vital_defs):
        bg = colors.HexColor("#FFF5F5") if is_warn else (
             colors.HexColor("#F7FBFF") if i % 2 == 0 else colors.white)
        v_style.append(("BACKGROUND", (0, i+1), (-1, i+1), bg))

    v_tbl = Table(v_rows, colWidths=["28%", "22%", "28%", "22%"])
    v_tbl.setStyle(TableStyle(v_style))
    story.append(v_tbl)
    story.append(Spacer(1, 5*mm))

    # ── Probability Breakdown ─────────────────────────────────────────────────
    story.append(Paragraph("CTAS Probability Breakdown", h2_s))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#D0E4F1")))
    story.append(Spacer(1, 2*mm))

    LVL_CLR = {1:"#7C3AED", 2:"#DC2626", 3:"#D97706", 4:"#059669", 5:"#0369A1"}
    p_rows = [["CTAS Level", "Name", "Probability", "Selected"]]
    for lvl in range(1, 6):
        p    = float(res.get(f"Prob_Class_{lvl}", 0))
        pct2 = round(p * 100)
        mark = "YES" if lvl == ctas else ""
        p_rows.append([
            Paragraph(f"Level {lvl}", S(f"pl{lvl}", fontSize=9, fontName="Helvetica-Bold",
                                        textColor=colors.HexColor(LVL_CLR[lvl]))),
            Paragraph(_CTAS_NAMES[lvl], S(f"pn{lvl}", fontSize=9)),
            Paragraph(f"<b>{pct2}%</b>", S(f"pp{lvl}", fontSize=9,
                       fontName="Helvetica-Bold" if lvl == ctas else "Helvetica",
                       textColor=colors.HexColor(LVL_CLR[lvl]) if lvl == ctas
                                 else colors.HexColor("#94B3C6"))),
            Paragraph(f"<b>{mark}</b>", S(f"ps{lvl}", fontSize=9,
                       fontName="Helvetica-Bold", textColor=clr_obj)),
        ])

    p_tbl = Table(p_rows, colWidths=["20%", "38%", "22%", "20%"])
    p_style = [
        ("BACKGROUND",    (0,0), (-1,0), colors.HexColor("#0369A1")),
        ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
        ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",      (0,0), (-1,0), 8),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("BOX",           (0,0), (-1,-1), 0.5, colors.HexColor("#D0E4F1")),
        ("INNERGRID",     (0,0), (-1,-1), 0.3, colors.HexColor("#D0E4F1")),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.white, colors.HexColor("#F7FBFF")]),
    ]
    p_style.append(("BACKGROUND", (0, ctas), (-1, ctas), light_obj))
    p_tbl.setStyle(TableStyle(p_style))
    story.append(p_tbl)
    story.append(Spacer(1, 5*mm))

    # ── Explainable AI — Decision Pathway ────────────────────────────────────
    story.append(Paragraph("Explainable AI — Decision Pathway", h2_s))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#D0E4F1")))
    story.append(Spacer(1, 2*mm))

    for heading, body_text in build_xai_pdf_sections(res):
        story.append(Paragraph(
            heading,
            S(f"xh{heading[:6].replace(' ','_')}",
              fontSize=9, fontName="Helvetica-Bold",
              textColor=colors.HexColor("#0369A1"), spaceBefore=4),
        ))
        for line in body_text.split("\n"):
            if line.strip():
                story.append(Paragraph(line.strip(), bod_s))
        story.append(Spacer(1, 2*mm))

    note_tbl = Table([[Paragraph(
        "<b>Note:</b> This narrative reflects the system's internal logic. "
        "It supports — not replaces — clinical judgement. "
        "The attending clinician is responsible for the final triage decision.",
        S("note", fontSize=8, textColor=colors.HexColor("#1E3A52")),
    )]], colWidths=["100%"])
    note_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), colors.HexColor("#EFF6FF")),
        ("BOX",           (0,0), (-1,-1), 1, colors.HexColor("#93C5FD")),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(note_tbl)
    story.append(Spacer(1, 5*mm))

    # ── Clinical Disclaimer ───────────────────────────────────────────────────
    story.append(Paragraph(
        "<b>Clinical Disclaimer:</b>  This report is generated by an AI decision-support "
        "system and does <b>not</b> replace the clinical judgment of a qualified healthcare "
        "professional. Always verify the care pathway with an on-site clinician.",
        disc_s,
    ))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 4*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#D0E4F1")))
    story.append(Spacer(1, 2*mm))
    footer = "Generated by TriageAI · Clinical Decision Support System"
    if email:
        footer += f"  ·  {display_name} ({email})"
    story.append(Paragraph(
        footer,
        S("ft", fontSize=7, textColor=colors.HexColor("#94B3C6"), alignment=TA_CENTER),
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()


# =============================================================================
# EMAIL REPORT SENDER
# =============================================================================

def send_email_report(
    to_email: str,
    pdf_bytes: bytes,
    ctas: int,
    clinician_name: str,
) -> tuple[bool, str]:
    """
    Send the PDF report to the clinician's email via SMTP.
    Reads SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASS from environment.
    Returns (success: bool, message: str).
    """
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER", "")
    smtp_pass = os.getenv("SMTP_PASS", "")

    if not smtp_user or not smtp_pass:
        return False, (
            "Email sending is not configured. "
            "Set SMTP_HOST, SMTP_PORT, SMTP_USER, and SMTP_PASS in your .env file."
        )

    try:
        msg = MIMEMultipart()
        msg["From"]    = smtp_user
        msg["To"]      = to_email
        msg["Subject"] = f"TriageAI Assessment Report — CTAS Level {ctas}"

        body = (
            f"Dear {clinician_name},\n\n"
            f"Please find attached your TriageAI triage assessment report "
            f"(CTAS Level {ctas}).\n\n"
            f"This report is generated for clinical reference only and does not "
            f"replace the judgment of a qualified healthcare professional.\n\n"
            f"TriageAI — Clinical Decision Support System"
        )
        msg.attach(MIMEText(body, "plain"))

        attachment = MIMEBase("application", "octet-stream")
        attachment.set_payload(pdf_bytes)
        _email_encoders.encode_base64(attachment)
        attachment.add_header(
            "Content-Disposition",
            f'attachment; filename="TriageAI_Report_CTAS{ctas}.pdf"',
        )
        msg.attach(attachment)

        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_email, msg.as_string())

        return True, f"Report sent to {to_email}"

    except smtplib.SMTPAuthenticationError:
        return False, "SMTP authentication failed — check SMTP_USER and SMTP_PASS."
    except smtplib.SMTPException as e:
        return False, f"SMTP error: {e}"
    except Exception as e:
        return False, f"Could not send email: {e}"


# =============================================================================
# RESULT PAGE
# =============================================================================

def result_page():
    inject_css()
    top_bar()
    nav_bar(subtitle="Assessment Result")

    # ── Pull shared state ─────────────────────────────────────────────────────
    res  = st.session_state.result    # DataFrame (single row)
    feat = st.session_state.features  # plain dict

    # Normalise to a plain dict — works whether res is a DataFrame or dict
    if hasattr(res, "iloc"):
        res_dict = res.iloc[0].to_dict()
    elif hasattr(res, "to_dict"):
        res_dict = res.to_dict()
    else:
        res_dict = dict(res)

    ctas = int(res_dict.get("Final_CTAS", 3))
    probs = {lvl: float(res_dict.get(f"Prob_Class_{lvl}", 0)) for lvl in range(1, 6)}

    predicted_class = max(probs, key=probs.get)
    max_probability = probs[predicted_class]
    conf = float(res_dict.get("confidence", max_probability))
    ci   = CI[ctas]
    pct  = round(conf * 100)

    # ── Clinician identity ────────────────────────────────────────────────────
    clinician_email    = st.session_state.get("email") or ""
    clinician_name     = get_display_name(clinician_email) if clinician_email else "Guest"
    clinician_initials = get_initials(clinician_email) if clinician_email else "G"

    # ── Hero result card ──────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:#fff;border:1.5px solid {ci['colorBorder']};border-radius:20px;
                padding:2rem 2.2rem 1.8rem;margin-bottom:1rem;
                box-shadow:0 4px 24px {ci['color']}22,0 1px 4px rgba(14,90,140,.06);
                position:relative;overflow:hidden;animation:fadeUp .45s ease both;">
      <div style="position:absolute;left:0;top:0;bottom:0;width:5px;
                  background:{ci['color']};border-radius:16px 0 0 16px;"></div>
      <div style="position:absolute;inset:0;
                  background:linear-gradient(135deg,{ci['colorLight']}55,#fff);
                  pointer-events:none;"></div>
      <div style="position:relative;display:flex;align-items:center;
                  justify-content:space-between;flex-wrap:wrap;gap:1.5rem;">
        <div>
          <div style="display:inline-flex;align-items:center;gap:.4rem;
                      background:{ci['colorLight']};border:1.5px solid {ci['colorBorder']};
                      border-radius:99px;padding:.22rem .85rem;margin-bottom:.75rem;">
            <span style="width:7px;height:7px;border-radius:50%;background:{ci['color']};
                         display:inline-block;animation:pulse 2s infinite;"></span>
            <span style="font-size:.68rem;font-weight:700;letter-spacing:.9px;
                         text-transform:uppercase;color:{ci['color']};">CTAS Assessment Result</span>
          </div>
          <div style="font-family:'DM Sans',sans-serif;font-size:3.5rem;font-weight:800;
                      line-height:1;color:{ci['color']};letter-spacing:-2px;margin-bottom:.2rem;">
            Level {ctas}</div>
          <div style="font-family:'DM Sans',sans-serif;font-size:1.3rem;font-weight:700;
                      color:#0E1F35;letter-spacing:-.4px;margin-bottom:.9rem;">
            {ci['name']}</div>
          <div style="display:inline-flex;align-items:center;gap:.5rem;background:#fff;
                      border:1.5px solid {ci['colorBorder']};border-radius:99px;
                      padding:.3rem 1rem;box-shadow:0 1px 4px rgba(0,0,0,.06);">
            <span>⏱</span>
            <span style="font-size:.78rem;font-weight:700;color:{ci['color']};">
              Response Target: {ci['time']}</span>
          </div>
        </div>
        <div style="flex-shrink:0;">{ring_svg(pct, ci['color'], 120)}</div>
      </div>
      <!-- Assessor identity chip -->
      <div style="position:relative;margin-top:1rem;display:flex;
                  align-items:center;gap:.55rem;">
        <div style="width:30px;height:30px;border-radius:50%;flex-shrink:0;
                    background:{ci['color']};color:#fff;font-size:.7rem;font-weight:800;
                    display:flex;align-items:center;justify-content:center;">
          {clinician_initials}</div>
        <div>
          <div style="font-size:.73rem;font-weight:700;color:#0E1F35;">{clinician_name}</div>
          <div style="font-size:.65rem;color:#6B90AA;">
            {clinician_email if clinician_email else "Guest session — results not saved"}</div>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── Two-column: Action + Probability Breakdown ────────────────────────────
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown(f"""
        <div style="background:#fff;border:1px solid #D0E4F1;border-radius:16px;
                    padding:1.4rem 1.5rem;
                    box-shadow:0 1px 4px rgba(14,90,140,.06),0 4px 16px rgba(14,90,140,.06);
                    animation:fadeUp .45s .08s ease both;opacity:0;">""",
                    unsafe_allow_html=True)
        sec_label("📍", "Recommended Action")
        st.markdown(f"""
          <div style="background:{ci['color']};border-radius:12px;padding:1.1rem 1.3rem;
                      margin-bottom:.75rem;">
            <div style="font-family:'DM Sans',sans-serif;font-size:.95rem;font-weight:800;
                        color:#fff;margin-bottom:.35rem;">{ci['icon']}  {ci['at']}</div>
            <div style="font-size:.82rem;color:rgba(255,255,255,.9);line-height:1.65;">
              {ci['ad']}</div>
          </div>
          <div style="background:{ci['colorLight']};border:1px solid {ci['colorBorder']};
                      border-radius:10px;padding:.62rem .95rem;font-size:.83rem;
                      color:{ci['color']};display:flex;align-items:flex-start;gap:.45rem;
                      line-height:1.5;font-weight:500;">
            <span style="flex-shrink:0;">ℹ</span>{ci['un']}
          </div>
        </div>""", unsafe_allow_html=True)

    with col_b:
        st.markdown("""
        <div style="background:#fff;border:1px solid #D0E4F1;border-radius:16px;
                    padding:1.4rem 1.5rem;
                    box-shadow:0 1px 4px rgba(14,90,140,.06),0 4px 16px rgba(14,90,140,.06);
                    animation:fadeUp .45s .16s ease both;opacity:0;">""",
                    unsafe_allow_html=True)
        sec_label("📈", "Probability Breakdown")

        bars = ""
        for lvl in range(1, 6):
            p   = round(probs.get(lvl, 0) * 100)
            a   = (lvl == ctas)
            lc  = CI[lvl]["color"]
            ll  = CI[lvl]["colorLight"]
            lb  = CI[lvl]["colorBorder"]
            dot = (f'<span style="width:6px;height:6px;border-radius:50%;'
                   f'background:{lc};display:inline-block;margin-right:4px;"></span>') if a else ""
            bars += f"""
            <div style="margin-bottom:.6rem;">
              <div style="display:flex;justify-content:space-between;align-items:center;
                          margin-bottom:.22rem;">
                <span style="font-size:.72rem;font-weight:{'700' if a else '500'};
                             color:{lc if a else '#6B90AA'};display:flex;align-items:center;">
                  {dot}Level {lvl} — {CI[lvl]['name']}</span>
                <span style="font-size:.72rem;font-weight:700;
                             color:{lc if a else '#94B3C6'};">{p}%</span>
              </div>
              <div style="height:5px;background:{ll if a else '#EDF4FB'};border-radius:99px;
                          overflow:hidden;{'border:1px solid ' + lb + ';' if a else ''}">
                <div style="height:100%;width:{p}%;
                            background:{lc if a else lc + '55'};border-radius:99px;"></div>
              </div>
            </div>"""
        st.markdown(bars + '</div>', unsafe_allow_html=True)

    sp(8)

    # ── Find Care ─────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="background:#fff;border:1px solid #D0E4F1;border-radius:16px;
                padding:1.4rem 1.6rem;margin-bottom:.75rem;
                box-shadow:0 1px 4px rgba(14,90,140,.06),0 4px 16px rgba(14,90,140,.06);
                animation:fadeUp .45s .24s ease both;opacity:0;">""",
                unsafe_allow_html=True)
    sec_label("💻" if ci["iv"] else "🗺️", "Find Care")

    if ci["iv"]:
        st.markdown("""
        <div style="font-size:.68rem;font-weight:700;letter-spacing:.8px;
                    text-transform:uppercase;color:#6B90AA;margin-bottom:.85rem;">
          Connect with a Telehealth Provider</div>""", unsafe_allow_html=True)
        tl_html = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:.5rem;">'
        for lnk in TELEHEALTH:
            tl_html += f"""
            <a href="{lnk['url']}" target="_blank" rel="noopener noreferrer"
               style="display:flex;align-items:center;gap:.7rem;background:#F0F9FF;
                      border:1.5px solid #BAE6FD;border-radius:12px;padding:.8rem 1rem;
                      text-decoration:none;">
              <span style="font-size:1.3rem;">{lnk['icon']}</span>
              <div>
                <div style="font-weight:700;font-size:.87rem;color:#0E1F35;">{lnk['name']}</div>
                <div style="font-size:.72rem;color:#3D6080;">{lnk['desc']}</div>
              </div>
            </a>"""
        st.markdown(tl_html + "</div>", unsafe_allow_html=True)
    else:
        maps_url = f"https://www.google.com/maps/search/{quote(ci['mq'])}"
        st.markdown(f"""
        <a href="{maps_url}" target="_blank" rel="noopener noreferrer"
           style="display:flex;align-items:center;justify-content:center;gap:.6rem;
                  background:{ci['color']};color:#fff;border-radius:12px;
                  padding:1rem 1.5rem;text-decoration:none;font-family:'DM Sans',sans-serif;
                  font-size:.95rem;font-weight:700;
                  box-shadow:0 4px 18px {ci['color']}44;margin-bottom:.5rem;">
          📍  {ci['ml']}  ↗
        </a>
        <div style="text-align:center;font-size:.72rem;color:#94B3C6;margin-top:.35rem;">
          Opens Google Maps · finds nearby facilities based on your location</div>
        """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Input Summary ─────────────────────────────────────────────────────────
    with st.expander("📋  View Input Summary"):
        chief_text   = feat.get("Chief_complain_clean") or feat.get("Chief_complain") or "Not provided"
        pregnant_val = feat.get("pregnant", feat.get("Pregnant", 0))
        summary_rows = [
            ("Chief Complaint", chief_text),
            ("Age",             f"{safe_text(feat.get('Age'))} yrs"),
            ("Sex",             safe_text(feat.get("Sex"))),
            ("SBP",             f"{safe_text(feat.get('SBP'))} mmHg"),
            ("DBP",             f"{safe_text(feat.get('DBP'))} mmHg"),
            ("Heart Rate",      f"{safe_text(feat.get('HR'))} bpm"),
            ("Resp. Rate",      f"{safe_text(feat.get('RR'))} /min"),
            ("Body Temp.",      f"{safe_text(feat.get('BT'))} °C"),
            ("NRS Pain",        f"{safe_text(feat.get('NRS_pain'))} / 10"),
            ("Pregnant",        safe_text(pregnant_val)),
        ]
        cells = ""
        for i, (lbl, val) in enumerate(summary_rows):
            bg = "#F7FBFF" if i % 2 == 0 else "#fff"
            br = "border-right:1px solid #D0E4F1;" if (i + 1) % 3 != 0 else ""
            cells += f"""
            <div style="background:{bg};padding:.6rem .85rem;
                        {br}border-bottom:1px solid #D0E4F1;">
              <div style="font-size:.63rem;font-weight:700;letter-spacing:.7px;
                          text-transform:uppercase;color:#94B3C6;margin-bottom:.14rem;">{lbl}</div>
              <div style="font-size:.9rem;font-weight:700;color:#0E1F35;word-break:break-word;">{val}</div>
            </div>"""
        st.markdown(f"""
        <div style="border:1px solid #D0E4F1;border-radius:12px;overflow:hidden;margin-bottom:.8rem;">
          <div style="display:grid;grid-template-columns:1fr 1fr 1fr;">{cells}</div>
        </div>""", unsafe_allow_html=True)

    # ── Explainable AI — narrative + raw reference table ─────────────────────
    with st.expander("🧠  Explainable AI — How was this result determined?"):
        st.markdown(
            f"""<div style="background:#fff;border:1px solid #D0E4F1;border-radius:12px;
                           padding:1.1rem 1.3rem;margin-bottom:.6rem;">
                  {build_xai_narrative(res_dict)}</div>""",
            unsafe_allow_html=True,
        )

        # Quick-reference raw values
        st.markdown("""
        <div style="font-size:.65rem;font-weight:700;letter-spacing:.7px;
                    text-transform:uppercase;color:#94B3C6;margin:.5rem 0 .4rem;">
          Quick Reference — Raw Decision Values</div>""", unsafe_allow_html=True)

        quick_rows = [
            ("Pregnancy Rule",     rule_explain_text(res_dict.get("Pregnancy_Rule_CTAS"))),
            ("Clinical Rule",      rule_explain_text(res_dict.get("Clinical_Rule_CTAS"))),
            ("Combined Rule",      rule_explain_text(res_dict.get("Combined_Rule_CTAS"))),
            ("Model Default CTAS", safe_ctas_text(res_dict.get("Model_Default_CTAS"))),
            ("Model Tuned CTAS",   safe_ctas_text(res_dict.get("Model_Tuned_CTAS"))),
            ("Final CTAS",         safe_ctas_text(res_dict.get("Final_CTAS"))),
            ("Final Source",       safe_text(res_dict.get("Final_Source"))),
        ]
        qcells = ""
        for i, (lbl, val) in enumerate(quick_rows):
            bg = "#F7FBFF" if i % 2 == 0 else "#fff"
            br = "border-right:1px solid #D0E4F1;" if (i + 1) % 2 != 0 else ""
            qcells += f"""
            <div style="background:{bg};padding:.5rem .8rem;
                        {br}border-bottom:1px solid #D0E4F1;">
              <div style="font-size:.6rem;font-weight:700;letter-spacing:.6px;
                          text-transform:uppercase;color:#94B3C6;margin-bottom:.1rem;">{lbl}</div>
              <div style="font-size:.85rem;font-weight:700;color:#0E1F35;">{val}</div>
            </div>"""
        st.markdown(f"""
        <div style="border:1px solid #D0E4F1;border-radius:10px;overflow:hidden;">
          <div style="display:grid;grid-template-columns:1fr 1fr;">{qcells}</div>
        </div>""", unsafe_allow_html=True)

    # ── Disclaimer ────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="background:#FEF3C7;border:1px solid #FCD34D;border-radius:14px;
                padding:1rem 1.2rem;margin:.5rem 0 .85rem;">
      <div style="font-weight:700;color:#92400E;font-size:.8rem;margin-bottom:.25rem;">
        ⚕️  Clinical Disclaimer</div>
      <div style="color:#78350F;font-size:.8rem;line-height:1.6;">
        This tool provides <strong>decision support only</strong> and does not replace
        the clinical judgment of a qualified healthcare professional. Always verify
        the care pathway with an on-site clinician.</div></div>""", unsafe_allow_html=True)

    # ── Action buttons ────────────────────────────────────────────────────────
    # Generate PDF once — shared by download AND email buttons
    _pdf_bytes = None
    try:
        _pdf_bytes = generate_pdf_report(
            res_dict,
            feat,
            email=clinician_email or None,
        )
    except Exception as _pdf_err:
        st.warning(f"PDF generation failed: {_pdf_err}")

    act1, act2, act3, act4 = st.columns([3, 2, 2, 2])

    with act1:
        if st.button("🔄  New Assessment", use_container_width=True,
                     type="primary", key="new_btn"):
            st.session_state.update(result=None, features=None, page="form")
            st.rerun()

    with act2:
        if _pdf_bytes:
            ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            st.download_button(
                label="📄  Download PDF",
                data=_pdf_bytes,
                file_name=f"TriageAI_Report_CTAS{ctas}_{ts_str}.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="pdf_btn",
            )

    with act3:
        # Email report button — only shown for logged-in users
        _can_email = (
            _pdf_bytes is not None
            and clinician_email
            and not st.session_state.get("is_guest", False)
        )
        if _can_email:
            if st.button("📧  Email Report", use_container_width=True, key="email_btn"):
                with st.spinner("Sending report to your email..."):
                    _ok, _msg = send_email_report(
                        to_email=clinician_email,
                        pdf_bytes=_pdf_bytes,
                        ctas=ctas,
                        clinician_name=clinician_name,
                    )
                if _ok:
                    st.success(f"✅ {_msg}")
                else:
                    st.error(f"❌ {_msg}")
        else:
            st.button(
                "📧  Email Report",
                use_container_width=True,
                disabled=True,
                help="Sign in to receive the report by email.",
                key="email_btn_disabled",
            )

    with act4:
        if st.button("← Sign Out", use_container_width=True, key="res_signout"):
            for k in ["page", "is_guest", "email", "result", "features"]:
                st.session_state[k] = DEFAULTS[k]
            st.rerun()