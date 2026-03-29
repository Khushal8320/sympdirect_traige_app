"""
ui_helpers.py — Global CSS injection and every reusable UI helper.
All page modules import from here; keeps styling in one place.
"""

import math
import streamlit as st


# ─────────────────────────────────────────────────────────────────────────────
# TINY LAYOUT HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def sp(h: int = 8):
    """Invisible spacer block."""
    st.markdown(f'<div style="height:{h}px"></div>', unsafe_allow_html=True)


def divider_line():
    st.markdown(
        '<hr style="border:none;border-top:1px solid #D0E4F1;margin:.6rem 0;">',
        unsafe_allow_html=True,
    )


def alert(kind: str, text: str):
    """kind: 'error' | 'success' | 'warning'"""
    cfg = {
        "error":   ("#FEE2E2", "#FCA5A5", "#991B1B", "⚠"),
        "success": ("#D1FAE5", "#6EE7B7", "#065F46", "✓"),
        "warning": ("#FEF3C7", "#FCD34D", "#92400E", "⚠️"),
    }
    bg, bd, col, icon = cfg.get(kind, cfg["warning"])
    st.markdown(f"""
    <div style="background:{bg};border:1px solid {bd};border-radius:10px;
                padding:.62rem .95rem;font-size:.84rem;color:{col};
                display:flex;align-items:flex-start;gap:.5rem;
                line-height:1.5;font-family:'DM Sans',sans-serif;margin:.35rem 0;">
      <span style="flex-shrink:0;font-weight:700;">{icon}</span>{text}</div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL CSS
# ─────────────────────────────────────────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600;9..40,700;9..40,800&display=swap');

    /* ── Hide default Streamlit chrome ── */
    #MainMenu, footer, header { visibility: hidden !important; }
    [data-testid="stToolbar"],
    [data-testid="stDecoration"],
    .stDeployButton { display: none !important; }

    /* ── Base ── */
    html, body,
    [data-testid="stAppViewContainer"],
    [data-testid="stMain"],
    section.main {
        background: #EDF4FB !important;
        font-family: 'DM Sans', sans-serif !important;
        color: #0E1F35 !important;
    }

    .block-container {
        padding-top: 0 !important;
        padding-bottom: 5rem !important;
        max-width: 780px !important;
    }

    /* ── Scrollbar ── */
    ::-webkit-scrollbar { width: 5px; }
    ::-webkit-scrollbar-track { background: #EDF4FB; }
    ::-webkit-scrollbar-thumb { background: #BAD3E8; border-radius: 99px; }

    /* ── Sidebar hide ── */
    [data-testid="stSidebar"] { display: none !important; }

    /* ── Text inputs, number inputs, text areas ── */
    .stTextInput  > label,
    .stNumberInput > label,
    .stSelectbox  > label,
    .stTextArea   > label,
    .stRadio      > label {
        font-family: 'DM Sans', sans-serif !important;
        font-size: 0.68rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.85px !important;
        text-transform: uppercase !important;
        color: #6B90AA !important;
        margin-bottom: 0.3rem !important;
    }

    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stTextArea   > div > div > textarea {
        background:    #F8FBFE !important;
        border:        1.5px solid #D0E4F1 !important;
        border-radius: 10px !important;
        color:         #0E1F35 !important;
        font-family:   'DM Sans', sans-serif !important;
        font-size:     0.9rem !important;
        padding:       0.62rem 0.9rem !important;
        transition:    border-color .18s, box-shadow .18s, background .18s !important;
    }
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stTextArea   > div > div > textarea:focus {
        background:  #fff !important;
        border-color: #0EA5E9 !important;
        box-shadow:  0 0 0 3.5px rgba(14,165,233,0.13) !important;
        outline: none !important;
    }
    input:-webkit-autofill, input:-webkit-autofill:focus {
        -webkit-box-shadow: 0 0 0 1000px #fff inset !important;
        -webkit-text-fill-color: #0E1F35 !important;
    }

    /* ── Selectbox ── */
    .stSelectbox > div > div {
        background:    #F8FBFE !important;
        border:        1.5px solid #D0E4F1 !important;
        border-radius: 10px !important;
        color:         #0E1F35 !important;
        font-family:   'DM Sans', sans-serif !important;
        font-size:     0.9rem !important;
    }
    .stSelectbox > div > div:focus-within {
        border-color: #0EA5E9 !important;
        box-shadow: 0 0 0 3px rgba(14,165,233,0.12) !important;
    }
    [data-baseweb="select"] { background: #F8FBFE !important; }
    [data-baseweb="popover"] ul { background: #fff !important; }
    [data-baseweb="popover"] ul li:hover { background: #F0F9FF !important; }

    /* ── Number input steppers ── */
    .stNumberInput [data-testid="stNumberInputStepUp"],
    .stNumberInput [data-testid="stNumberInputStepDown"],
    .stNumberInput button {
        background: #EDF4FB !important;
        border-color: #D0E4F1 !important;
        color: #6B90AA !important;
        border-radius: 7px !important;
    }
    .stNumberInput button:hover { background: #E0F2FE !important; color: #0369A1 !important; }

    /* ── Radio buttons ── */
    .stRadio > div {
        flex-direction: row !important;
        gap: 8px !important;
        flex-wrap: wrap !important;
    }
    .stRadio > div > label {
        background: #fff !important;
        border: 1.5px solid #D0E4F1 !important;
        border-radius: 9px !important;
        padding: 6px 14px !important;
        cursor: pointer !important;
        font-size: 0.87rem !important;
        font-weight: 500 !important;
        color: #3D6080 !important;
        text-transform: none !important;
        letter-spacing: 0 !important;
        transition: all .18s !important;
    }
    .stRadio > div > label:hover {
        background: #F0F9FF !important;
        border-color: #7DD3FC !important;
        color: #0369A1 !important;
    }
    .stRadio > div > label[data-checked="true"],
    .stRadio > div > label:has(input:checked) {
        background: #E0F2FE !important;
        border-color: #38BDF8 !important;
        color: #0369A1 !important;
        font-weight: 700 !important;
    }
    .stRadio > div > label > div:first-child { display: none !important; }

    /* ── Primary button ── */
    [data-testid="baseButton-primary"],
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #0369A1, #0EA5E9) !important;
        color: #fff !important;
        border: none !important;
        border-radius: 12px !important;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 700 !important;
        font-size: 0.93rem !important;
        padding: 0.8rem 1.8rem !important;
        box-shadow: 0 4px 18px rgba(3,105,161,0.35) !important;
        transition: all .2s !important;
        letter-spacing: 0.2px !important;
    }
    [data-testid="baseButton-primary"]:hover,
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 10px 32px rgba(2,132,199,0.4) !important;
    }
    [data-testid="baseButton-primary"]:active,
    .stButton > button[kind="primary"]:active { transform: translateY(0) !important; }

    /* ── Secondary / ghost button ── */
    [data-testid="baseButton-secondary"],
    .stButton > button[kind="secondary"],
    .stButton > button {
        background: #fff !important;
        color: #0369A1 !important;
        border: 1.5px solid #BAE6FD !important;
        border-radius: 12px !important;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        transition: all .2s !important;
    }
    [data-testid="baseButton-secondary"]:hover,
    .stButton > button[kind="secondary"]:hover,
    .stButton > button:hover {
        background: #EDF4FB !important;
        border-color: #60A5D4 !important;
        color: #0369A1 !important;
    }

    /* ── Expander ── */
    .streamlit-expanderHeader {
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        color: #3D6080 !important;
        background: #fff !important;
        border: 1px solid #D0E4F1 !important;
        border-radius: 14px !important;
        padding: 0.9rem 1.3rem !important;
        transition: background .18s !important;
    }
    .streamlit-expanderHeader:hover { background: #F5F9FE !important; }
    [data-testid="stExpander"] > details > summary {
        background: #fff !important;
        border: 1px solid #D0E4F1 !important;
        border-radius: 14px !important;
        color: #3D6080 !important;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 600 !important;
        padding: 0.9rem 1.3rem !important;
    }
    [data-testid="stExpander"] > details[open] > summary {
        border-radius: 14px 14px 0 0 !important;
        border-bottom: 1px solid #D0E4F1 !important;
    }
    [data-testid="stExpander"] > details > div {
        background: #fff !important;
        border: 1px solid #D0E4F1 !important;
        border-top: none !important;
        border-radius: 0 0 14px 14px !important;
        padding: 1.1rem 1.3rem !important;
    }

    /* ── Spinner ── */
    .stSpinner > div { border-top-color: #0369A1 !important; }

    /* ── Column gap ── */
    [data-testid="column"] { padding-left: 5px !important; padding-right: 5px !important; }

    /* ── Divider ── */
    hr { border-color: #D0E4F1 !important; }

    /* ── Form submit button ── */
    [data-testid="stFormSubmitButton"] > button {
        background: linear-gradient(135deg, #0369A1, #0EA5E9) !important;
        color: #fff !important;
        border: none !important;
        border-radius: 12px !important;
        font-family: 'DM Sans', sans-serif !important;
        font-weight: 700 !important;
        font-size: 0.93rem !important;
        padding: 0.8rem 1.8rem !important;
        box-shadow: 0 4px 18px rgba(3,105,161,0.35) !important;
        width: 100% !important;
        transition: all .2s !important;
    }
    [data-testid="stFormSubmitButton"] > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 10px 32px rgba(2,132,199,0.4) !important;
    }

    /* ── Animations ── */
    @keyframes pulse    { 0%,100%{opacity:.6} 50%{opacity:1} }
    @keyframes fadeUp   { from{opacity:0;transform:translateY(12px)} to{opacity:1;transform:translateY(0)} }
    @keyframes spin     { to{transform:rotate(360deg)} }
    @keyframes heartbeat{ 0%,100%{transform:scale(1)} 14%{transform:scale(1.15)} 28%{transform:scale(1)} 42%{transform:scale(1.08)} 70%{transform:scale(1)} }
    .fade-up { animation: fadeUp .45s ease both; }

    /* ── Vital sign bordered containers ── */
    div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #F8FBFE !important;
        border: 1.5px solid #D0E4F1 !important;
        border-radius: 14px !important;
        padding: 0.25rem 0.6rem 0.5rem !important;
        transition: border-color .2s, box-shadow .2s !important;
    }
    div[data-testid="stVerticalBlockBorderWrapper"]:hover {
        border-color: #7DD3FC !important;
        box-shadow: 0 0 0 3px rgba(14,165,233,0.08) !important;
    }

    /* ── Sliders ── */
    .stSlider > label {
        font-size: .6rem !important;
        font-weight: 700 !important;
        letter-spacing: .85px !important;
        text-transform: uppercase !important;
        color: #6B90AA !important;
        margin-bottom: 0.1rem !important;
    }
    .stSlider [data-testid="stSliderThumb"] {
        background: #0369A1 !important;
        border: 2px solid #fff !important;
        box-shadow: 0 0 0 2px #0369A1, 0 2px 6px rgba(3,105,161,.3) !important;
        width: 18px !important;
        height: 18px !important;
    }
    .stSlider [data-testid="stSliderTrackFill"] {
        background: linear-gradient(90deg,#0369A1,#0EA5E9) !important;
    }
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SVG ICON LIBRARY  (platform-consistent, no emoji rendering drift)
# ─────────────────────────────────────────────────────────────────────────────
_SVG = {
    "vitals": """<svg width="18" height="18" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M1 10 L4 10 L6 5 L8 15 L10 8 L12 12 L14 10 L19 10" stroke="#0369A1" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>""",
    "patient": """<svg width="18" height="18" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
      <circle cx="10" cy="6" r="3.5" stroke="#0369A1" stroke-width="1.8"/>
      <path d="M3 18c0-3.866 3.134-7 7-7s7 3.134 7 7" stroke="#0369A1" stroke-width="1.8" stroke-linecap="round"/>
    </svg>""",
    "complaint": """<svg width="18" height="18" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M3 4h14a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H6l-4 3V5a1 1 0 0 1 1-1z" stroke="#0369A1" stroke-width="1.8" stroke-linejoin="round"/>
    </svg>""",
    "action": """<svg width="18" height="18" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M10 2a5 5 0 1 1 0 10A5 5 0 0 1 10 2z" stroke="#0369A1" stroke-width="1.8"/>
      <path d="M10 8v3" stroke="#0369A1" stroke-width="1.8" stroke-linecap="round"/>
      <path d="M6.5 17.5 L10 12 L13.5 17.5" stroke="#0369A1" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
    </svg>""",
    "chart": """<svg width="18" height="18" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="2" y="12" width="3" height="6" rx="1" stroke="#0369A1" stroke-width="1.8"/>
      <rect x="8.5" y="7" width="3" height="11" rx="1" stroke="#0369A1" stroke-width="1.8"/>
      <rect x="15" y="3" width="3" height="15" rx="1" stroke="#0369A1" stroke-width="1.8"/>
    </svg>""",
    "care": """<svg width="18" height="18" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="2" y="5" width="16" height="11" rx="2" stroke="#0369A1" stroke-width="1.8"/>
      <path d="M7 18h6M10 16v2" stroke="#0369A1" stroke-width="1.8" stroke-linecap="round"/>
      <path d="M8 10h4M10 8v4" stroke="#0369A1" stroke-width="1.8" stroke-linecap="round"/>
    </svg>""",
    "lock": """<svg width="18" height="18" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="4" y="9" width="12" height="9" rx="2" stroke="#0369A1" stroke-width="1.8"/>
      <path d="M7 9V6a3 3 0 1 1 6 0v3" stroke="#0369A1" stroke-width="1.8" stroke-linecap="round"/>
    </svg>""",
}

_ICON_MAP = {
    "📊": "vitals", "👤": "patient", "💬": "complaint",
    "📍": "action",  "📈": "chart",   "💻": "care",
    "🗺️": "care",   "⚕️": "lock",
}


def sec_label(icon: str, text: str):
    """Renders a section header with an SVG icon badge and a divider line."""
    svg_key = _ICON_MAP.get(icon)
    icon_html = (
        f'<span style="display:inline-flex;align-items:center;justify-content:center;'
        f'width:26px;height:26px;background:#E0F2FE;border:1.5px solid #BAE6FD;'
        f'border-radius:8px;flex-shrink:0;">{_SVG[svg_key]}</span>'
        if svg_key else
        f'<span style="font-size:1.1rem;font-family:\'Segoe UI Emoji\',\'Apple Color Emoji\','
        f'\'Noto Color Emoji\',sans-serif;flex-shrink:0;">{icon}</span>'
    )
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:1rem;">
      {icon_html}
      <span style="font-family:'DM Sans',sans-serif;font-size:.71rem;font-weight:700;
                   letter-spacing:1.1px;text-transform:uppercase;color:#0369A1;">{text}</span>
      <div style="flex:1;height:1px;background:#D0E4F1;"></div>
    </div>""", unsafe_allow_html=True)


def card_wrap(inner_html: str, extra_style: str = "") -> str:
    return f"""
    <div style="background:#fff;border:1px solid #D0E4F1;border-radius:16px;
                padding:1.4rem 1.6rem;margin-bottom:.75rem;
                box-shadow:0 1px 4px rgba(14,90,140,.06),0 4px 16px rgba(14,90,140,.06);
                {extra_style}">
      {inner_html}
    </div>"""


def top_bar():
    """3-px gradient rule pinned at the very top of every page."""
    st.markdown(
        '<div style="position:fixed;top:0;left:0;right:0;height:3px;''background:linear-gradient(90deg,#0369A1,#38BDF8,#0369A1);z-index:9999;"></div>',
        unsafe_allow_html=True,
    )
    sp(6)


def vital_card(label, value, unit, warn, pct, accent):
    dot_bg   = "#EF4444" if warn else "#10B981"
    dot_ring = "#FECACA" if warn else "#A7F3D0"
    card_bg  = "#FFF5F5" if warn else "#F8FBFE"
    card_bd  = "#FCA5A5" if warn else "#D0E4F1"
    lbl_col  = "#B91C1C" if warn else "#6B90AA"
    val_col  = "#DC2626" if warn else "#0E1F35"
    track_bg = "#FEE2E2" if warn else "#E0EEF8"
    bar_fill = "linear-gradient(90deg,#EF4444,#F87171)" if warn \
               else f"linear-gradient(90deg,{accent},{accent}bb)"
    pct = min(100, max(0, pct))
    return f"""
    <div style="background:{card_bg};border:1.5px solid {card_bd};border-radius:14px;
                padding:.85rem .95rem .75rem;transition:border-color .18s;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.28rem;">
        <span style="font-size:.6rem;font-weight:700;letter-spacing:.9px;
                     text-transform:uppercase;color:{lbl_col};">{label}</span>
        <div style="width:7px;height:7px;border-radius:50%;background:{dot_bg};
                    box-shadow:0 0 0 2px {dot_ring};"></div>
      </div>
      <div style="display:flex;align-items:baseline;gap:2px;margin-bottom:.45rem;">
        <span style="font-family:'DM Sans',sans-serif;font-size:1.65rem;font-weight:800;
                     color:{val_col};">{value}</span>
        <span style="font-size:.63rem;color:#6B90AA;font-weight:600;margin-left:2px;">{unit}</span>
      </div>
      <div style="height:4px;background:{track_bg};border-radius:99px;overflow:hidden;">
        <div style="height:100%;width:{pct:.0f}%;background:{bar_fill};border-radius:99px;"></div>
      </div>
    </div>"""


def ring_svg(pct: int, color: str, size: int = 116) -> str:
    r    = 42
    circ = 2 * math.pi * r
    off  = circ - (pct / 100) * circ
    return f"""
    <svg width="{size}" height="{size}" viewBox="0 0 100 100" style="display:block;">
      <circle cx="50" cy="50" r="{r}" fill="none" stroke="#E0EEF8" stroke-width="6.5"/>
      <circle cx="50" cy="50" r="{r}" fill="none" stroke="{color}" stroke-width="6.5"
              stroke-linecap="round" stroke-dasharray="{circ:.2f}" stroke-dashoffset="{off:.2f}"
              transform="rotate(-90 50 50)"
              style="filter:drop-shadow(0 0 5px {color}88);transition:stroke-dashoffset 1.2s;"/>
      <text x="50" y="44" text-anchor="middle" dominant-baseline="central"
            style="fill:{color};font-family:'DM Sans',sans-serif;font-size:18px;font-weight:800;">
        {pct}%</text>
      <text x="50" y="64" text-anchor="middle"
            style="fill:#6B90AA;font-family:'DM Sans',sans-serif;font-size:7.5px;
                   font-weight:700;letter-spacing:1px;">CONFIDENCE</text>
    </svg>"""


def nav_bar(subtitle: str | None = None, show_signout: bool = True):
    """Sticky top navigation bar shared by the Form and Result pages."""
    from config import T, DEFAULTS

    is_guest = st.session_state.is_guest
    user_email = st.session_state.email
    dot = T["amber"] if is_guest else T["green"]
    label = "Guest Session" if is_guest else (user_email or "")

    subtitle_html = (
        f'<div style="font-size:.62rem;color:#6B90AA;letter-spacing:.5px;'
        f'text-transform:uppercase;font-weight:600;">{subtitle}</div>'
        if subtitle else ""
    )

    html = (
        '<div style="position:sticky;top:0;z-index:200;'
        'background:rgba(255,255,255,0.96);'
        'backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);'
        'border-bottom:1px solid #D0E4F1;'
        'box-shadow:0 1px 8px rgba(14,90,140,.07);'
        'margin-left:-2rem;margin-right:-2rem;'
        'padding:.78rem 2rem;margin-bottom:1.6rem;">'

            '<div style="position:absolute;top:0;left:0;right:0;height:2px;'
            'background:linear-gradient(90deg,#0369A1,#38BDF8);"></div>'

            '<div style="display:flex;align-items:center;justify-content:space-between;'
            'max-width:780px;margin:0 auto;">'

                '<div style="display:flex;align-items:center;gap:.7rem;">'

                    '<div style="width:34px;height:34px;border-radius:10px;'
                    'background:linear-gradient(135deg,#0369A1,#0EA5E9);'
                    'display:flex;align-items:center;justify-content:center;'
                    'font-size:16px;box-shadow:0 4px 12px rgba(3,105,161,.28);">🏥</div>'

                    '<div>'
                        '<div style="font-family:\'DM Sans\',sans-serif;font-weight:800;'
                        'font-size:.95rem;color:#0F4C81;letter-spacing:-.3px;line-height:1.1;">'
                        'TriageAI</div>'
                        f'{subtitle_html}'
                    '</div>'

                '</div>'

                '<div style="display:flex;align-items:center;gap:.5rem;">'
                    '<div style="background:#F0F9FF;border:1px solid #BAE6FD;'
                    'border-radius:99px;padding:.22rem .8rem;font-size:.72rem;'
                    'color:#0369A1;display:flex;align-items:center;gap:.45rem;'
                    'font-weight:600;">'
                        f'<span style="width:6px;height:6px;border-radius:50%;'
                        f'background:{dot};display:inline-block;'
                        f'animation:pulse 2s infinite;"></span>'
                        f'{label}'
                    '</div>'
                '</div>'

            '</div>'
        '</div>'
    )

    st.markdown(html, unsafe_allow_html=True)

    if show_signout:
        _, right = st.columns([5, 1])
        with right:
            if st.button("Sign out", key="nav_signout"):
                for k in ["page", "is_guest", "email", "result", "features"]:
                    st.session_state[k] = DEFAULTS[k]
                st.rerun()
        sp(4)