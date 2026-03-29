from urllib.parse import quote
import streamlit as st

from config import CI, TELEHEALTH, DEFAULTS
from ui_helpers import inject_css, top_bar, nav_bar, sp, sec_label, ring_svg


def is_missing_value(v):
    if v is None:
        return True

    try:
        if isinstance(v, float) and v != v:   # NaN check
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


def result_page():
    inject_css()
    top_bar()
    nav_bar(subtitle="Assessment Result")

    # ── Pull shared state set by form_page ────────────────────────────────────
    res = st.session_state.result
    feat = st.session_state.features

    ctas = int(res["Final_CTAS"])
    probs = {
        1: float(res.get("Prob_Class_1", 0)),
        2: float(res.get("Prob_Class_2", 0)),
        3: float(res.get("Prob_Class_3", 0)),
        4: float(res.get("Prob_Class_4", 0)),
        5: float(res.get("Prob_Class_5", 0)),
    }

    predicted_class = max(probs, key=probs.get)
    max_probability = probs[predicted_class]

    conf = float(res.get("confidence", max_probability))
    ci = CI[ctas]
    pct = round(conf * 100)

    # ── Hero result card ──────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:#fff;border:1.5px solid {ci['colorBorder']};border-radius:20px;
                padding:2rem 2.2rem 1.8rem;margin-bottom:1rem;
                box-shadow:0 4px 24px {ci['color']}22,0 1px 4px rgba(14,90,140,06);
                position:relative;overflow:hidden;
                animation:fadeUp .45s ease both;">
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
          <div style="display:inline-flex;align-items:center;gap:.5rem;
                      background:#fff;
                      border:1.5px solid {ci['colorBorder']};border-radius:99px;
                      padding:.3rem 1rem;box-shadow:0 1px 4px rgba(0,0,0,06);">
            <span>⏱</span>
            <span style="font-size:.78rem;font-weight:700;color:{ci['color']};">
              Response Target: {ci['time']}</span>
          </div>
        </div>
        <div style="flex-shrink:0;">{ring_svg(pct, ci['color'], 120)}</div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── Two-column: Action + Probability Breakdown ────────────────────────────
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown(f"""
        <div style="background:#fff;border:1px solid #D0E4F1;border-radius:16px;
                    padding:1.4rem 1.5rem;
                    box-shadow:0 1px 4px rgba(14,90,140,06),0 4px 16px rgba(14,90,140,06);
                    animation:fadeUp .45s .08s ease both;opacity:0;">""",
                    unsafe_allow_html=True)
        sec_label("📍", "Recommended Action")
        st.markdown(f"""
          <div style="background:{ci['color']};border-radius:12px;padding:1.1rem 1.3rem;
                      margin-bottom:.75rem;">
            <div style="font-family:'DM Sans',sans-serif;font-size:.95rem;font-weight:800;
                        color:#fff;margin-bottom:.35rem;">{ci['icon']}  {ci['at']}</div>
            <div style="font-size:.82rem;color:rgba(255,255,255,9);line-height:1.65;">
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
                    box-shadow:0 1px 4px rgba(14,90,140,06),0 4px 16px rgba(14,90,140,06);
                    animation:fadeUp .45s .16s ease both;opacity:0;">""",
                    unsafe_allow_html=True)
        sec_label("📈", "Probability Breakdown")

        bars = ""
        for lvl in range(1, 6):
            p = round(probs.get(lvl, 0) * 100)
            a = lvl == ctas
            col = CI[lvl]["color"]
            cl = CI[lvl]["colorLight"]
            cb = CI[lvl]["colorBorder"]
            dot = (f'<span style="width:6px;height:6px;border-radius:50%;'
                   f'background:{col};display:inline-block;margin-right:4px;"></span>') if a else ""
            bars += f"""
            <div style="margin-bottom:.6rem;">
              <div style="display:flex;justify-content:space-between;align-items:center;
                          margin-bottom:.22rem;">
                <span style="font-size:.72rem;font-weight:{'700' if a else '500'};
                             color:{col if a else '#6B90AA'};display:flex;align-items:center;">
                  {dot}Level {lvl} — {CI[lvl]['name']}</span>
                <span style="font-size:.72rem;font-weight:700;
                             color:{col if a else '#94B3C6'};">{p}%</span>
              </div>
              <div style="height:5px;background:{cl if a else '#EDF4FB'};border-radius:99px;
                          overflow:hidden;{'border:1px solid ' + cb + ';' if a else ''}">
                <div style="height:100%;width:{p}%;
                            background:{col if a else col + '55'};border-radius:99px;"></div>
              </div>
            </div>"""
        st.markdown(bars + '</div>', unsafe_allow_html=True)

    sp(8)

    # ── Find Care ─────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="background:#fff;border:1px solid #D0E4F1;border-radius:16px;
                padding:1.4rem 1.6rem;margin-bottom:.75rem;
                box-shadow:0 1px 4px rgba(14,90,140,06),0 4px 16px rgba(14,90,140,06);
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
                      text-decoration:none;transition:all .2s;">
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

    # ── Input Summary (same design) ───────────────────────────────────────────
    with st.expander("📋  View Input Summary"):
        chief_text = feat.get("Chief_complain_clean") or feat.get("Chief_complain") or "Not provided"
        pregnant_val = feat.get("pregnant", feat.get("Pregnant", 0))

        summary_rows = [
            ("Chief Complaint", chief_text),
            ("Age", f"{safe_text(feat.get('Age'))} yrs"),
            ("Sex", safe_text(feat.get("Sex"))),
            ("SBP", f"{safe_text(feat.get('SBP'))} mmHg"),
            ("DBP", f"{safe_text(feat.get('DBP'))} mmHg"),
            ("Heart Rate", f"{safe_text(feat.get('HR'))} bpm"),
            ("Resp. Rate", f"{safe_text(feat.get('RR'))} /min"),
            ("Body Temp.", f"{safe_text(feat.get('BT'))} °C"),
            ("NRS Pain", f"{safe_text(feat.get('NRS_pain'))} / 10"),
            #("KTAS_RN", safe_text(feat.get("KTAS_RN"), "Not provided")),
            ("Pregnant", safe_text(pregnant_val)),
        ]

        cells = ""
        for i, (lbl, val) in enumerate(summary_rows):
            bg = "#F7FBFF" if i % 2 == 0 else "#fff"
            br = "border-right:1px solid #D0E4F1;" if (i + 1) % 3 != 0 else ""
            cells += f"""
            <div style="background:{bg};padding:.6rem .85rem;
                        {br}border-bottom:1px solid #D0E4F1;">
              <div style="font-size:.63rem;font-weight:700;letter-spacing:.7px;
                          text-transform:uppercase;color:#94B3C6;margin-bottom:.14rem;">
                {lbl}</div>
              <div style="font-size:.9rem;font-weight:700;color:#0E1F35;word-break:break-word;">
                {val}</div>
            </div>"""
        st.markdown(f"""
        <div style="border:1px solid #D0E4F1;border-radius:12px;overflow:hidden;margin-bottom:.8rem;">
          <div style="display:grid;grid-template-columns:1fr 1fr 1fr;">{cells}</div>
        </div>""", unsafe_allow_html=True)

    # ── Explainable AI (same design style, null-aware text) ──────────────────
    with st.expander("🧠  Explainable AI"):
        explain_rows = [
            ("Pregnancy Rule", rule_explain_text(res.get("Pregnancy_Rule_CTAS"))),
            ("Clinical Rule", rule_explain_text(res.get("Clinical_Rule_CTAS"))),
            ("Combined Rule", rule_explain_text(res.get("Combined_Rule_CTAS"))),
            ("Model Default CTAS", safe_ctas_text(res.get("Model_Default_CTAS"))),
            ("Model Tuned CTAS", safe_ctas_text(res.get("Model_Tuned_CTAS"))),
            ("Final CTAS", safe_ctas_text(res.get("Final_CTAS"))),
            ("Final Source", safe_text(res.get("Final_Source"))),
        ]

        explain_cells = ""
        for i, (lbl, val) in enumerate(explain_rows):
            bg = "#F7FBFF" if i % 2 == 0 else "#fff"
            br = "border-right:1px solid #D0E4F1;" if (i + 1) % 2 != 0 else ""
            explain_cells += f"""
            <div style="background:{bg};padding:.75rem .9rem;
                        {br}border-bottom:1px solid #D0E4F1;">
              <div style="font-size:.63rem;font-weight:700;letter-spacing:.7px;
                          text-transform:uppercase;color:#94B3C6;margin-bottom:.16rem;">
                {lbl}</div>
              <div style="font-size:.92rem;font-weight:700;color:#0E1F35;word-break:break-word;">
                {val}</div>
            </div>"""

        st.markdown(f"""
        <div style="border:1px solid #D0E4F1;border-radius:12px;overflow:hidden;margin-bottom:.8rem;">
          <div style="display:grid;grid-template-columns:1fr 1fr;">{explain_cells}</div>
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
        the care pathway with an on-site clinician.</div>
    </div>""", unsafe_allow_html=True)

    # ── Action buttons ────────────────────────────────────────────────────────
    act1, act2 = st.columns([3, 2])
    with act1:
        if st.button("🔄  New Assessment", use_container_width=True,
                     type="primary", key="new_btn"):
            st.session_state.update(result=None, features=None, page="form")
            st.rerun()

    with act2:
        if st.button("← Sign Out", use_container_width=True, key="res_signout"):
            for k in ["page", "is_guest", "email", "result", "features"]:
                st.session_state[k] = DEFAULTS[k]
            st.rerun()