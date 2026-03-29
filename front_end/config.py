"""
config.py — Shared design tokens, CTAS level definitions, and session-state defaults.
Imported by every page module; never import streamlit here.
"""

# ── Design Tokens ────────────────────────────────────────────────────────────
T = {
    "bg":          "#EDF4FB",
    "white":       "#FFFFFF",
    "border":      "#D0E4F1",
    "blue700":     "#0F4C81",
    "blue600":     "#0369A1",
    "blue500":     "#0284C7",
    "blue400":     "#0EA5E9",
    "blue200":     "#7DD3FC",
    "blue100":     "#BAE6FD",
    "blue50":      "#E0F2FE",
    "blue25":      "#F0F9FF",
    "textPri":     "#0E1F35",
    "textSec":     "#3D6080",
    "textMid":     "#6B90AA",
    "textMute":    "#94B3C6",
    "red":         "#DC2626",
    "redLight":    "#FEE2E2",
    "redBorder":   "#FCA5A5",
    "green":       "#059669",
    "greenLight":  "#D1FAE5",
    "greenBorder": "#6EE7B7",
    "amber":       "#D97706",
    "amberLight":  "#FEF3C7",
    "amberBorder": "#FCD34D",
}

# ── CTAS Level Config ─────────────────────────────────────────────────────────
CI = {
    1: {
        "name": "Resuscitation", "color": "#7C3AED",
        "colorLight": "#EDE9FE", "colorBorder": "#C4B5FD",
        "time": "Immediate", "icon": "🚨",
        "at":  "Call Emergency Services NOW",
        "ad":  "This assessment indicates a potentially life-threatening condition. "
               "Call 911 immediately and proceed to the nearest hospital Emergency "
               "Department with full resuscitation and critical-care facilities.",
        "un":  "⚡ Call 911 immediately — do not drive yourself.",
        "mq":  "emergency hospital near me",
        "ml":  "Find Nearest Emergency Hospital", "iv": False,
    },
    2: {
        "name": "Emergent", "color": "#DC2626",
        "colorLight": "#FEE2E2", "colorBorder": "#FCA5A5",
        "time": "Within 15 min", "icon": "🏥",
        "at":  "Go to Nearest High-Care Hospital",
        "ad":  "This assessment indicates an emergent condition requiring care within "
               "15 minutes. Proceed immediately to the nearest Emergency Department "
               "with high-care / critical-care capabilities.",
        "un":  "🚗 Have someone drive you or call an ambulance. Do not wait.",
        "mq":  "hospital emergency department high care near me",
        "ml":  "Find High-Care Hospital", "iv": False,
    },
    3: {
        "name": "Urgent", "color": "#D97706",
        "colorLight": "#FEF3C7", "colorBorder": "#FCD34D",
        "time": "Within 30 min", "icon": "🏨",
        "at":  "Visit Nearest Healthcare Centre",
        "ad":  "This assessment indicates an urgent condition — you should be seen "
               "within 30 minutes. Head to the nearest urgent care centre or "
               "walk-in clinic as soon as possible.",
        "un":  "🚶 Head to urgent care — do not wait more than 30 minutes.",
        "mq":  "urgent care centre healthcare near me",
        "ml":  "Find Nearest Healthcare Centre", "iv": False,
    },
    4: {
        "name": "Less Urgent", "color": "#059669",
        "colorLight": "#D1FAE5", "colorBorder": "#6EE7B7",
        "time": "Within 60 min", "icon": "🏪",
        "at":  "Visit a Healthcare Facility",
        "ad":  "This assessment indicates a less-urgent condition. You can safely "
               "wait up to 1 hour. Visit a walk-in clinic, family health centre, "
               "or GP at your earliest convenience.",
        "un":  "📅 Book a same-day or next-available appointment.",
        "mq":  "walk-in clinic family health centre near me",
        "ml":  "Find Nearest Walk-In Clinic", "iv": False,
    },
    5: {
        "name": "Non-Urgent", "color": "#0369A1",
        "colorLight": "#E0F2FE", "colorBorder": "#7DD3FC",
        "time": "Within 120 min", "icon": "💻",
        "at":  "Meet Virtually with a Doctor",
        "ad":  "This assessment indicates a non-urgent condition. Your situation can "
               "be safely managed through a telehealth consultation. Book an online "
               "appointment from the comfort of home.",
        "un":  "🏠 No need to travel — connect with a doctor online.",
        "mq":  None, "ml": None, "iv": True,
    },
}

# ── Telehealth Links ──────────────────────────────────────────────────────────
TELEHEALTH = [
    {"name": "Teladoc Health",  "url": "https://www.teladochealth.com", "icon": "🩺", "desc": "24/7 doctors online"},
    {"name": "Maple (Canada)",  "url": "https://www.getmaple.ca",       "icon": "🍁", "desc": "Canadian telehealth"},
    {"name": "Dialogue Health", "url": "https://www.dialogue.co",       "icon": "💬", "desc": "Virtual care platform"},
    {"name": "Rocket Doctor",   "url": "https://rocketdoctor.ca",       "icon": "🚀", "desc": "Same-day online visits"},
]

# ── Session-state defaults ────────────────────────────────────────────────────
# Shared across all pages; app.py seeds these on startup.
DEFAULTS = {
    "page":         "auth",   # auth | form | result
    "is_guest":     False,
    "email":        None,
    "result":       None,
    "features":     None,
    "users_db":     {},
    "auth_mode":    "login",  # login | register
    "auth_error":   "",
    "auth_success": "",
    # model bundle — populated by app.py after pickle load
    "model":              None,
    "threshold_class_1":  None,
    "threshold_class_2":  None,
}
