"""
app.py — TriageAI · Main entry point.
Run:  streamlit run app.py

Responsibilities:
  1. st.set_page_config()  ← must be the very first Streamlit call
  2. Load the ML model once and store it in st.session_state
  3. Seed session-state defaults (first run only)
  4. Route to the correct page module based on st.session_state.page

Variable-sharing strategy
──────────────────────────
All cross-page data lives in st.session_state.
  • auth_page   writes: page, email, is_guest, users_db, auth_mode, auth_error, auth_success
  • form_page   reads:  is_guest, model, threshold_class_1, threshold_class_2
                writes: result, features, page
  • result_page reads:  result, features
                writes: result, features, page  (on reset / sign-out)
"""

import pickle
import streamlit as st
from database import create_tables
from db_helper import create_user, login_user, save_assessment
import bcrypt

# Ensure database tables exist (runs on every load, but create_tables() is idempotent)
create_tables()

if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False







# ── Page config (must come before any other st call) ─────────────────────────
st.set_page_config(
    page_title="TriageAI — Clinical Decision Support",
    page_icon="🏥",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Imports from our own modules ──────────────────────────────────────────────
from config import DEFAULTS          # shared constants + session defaults
from auth_page   import auth_page    # Page 1
from form_page   import form_page    # Page 2
from result_page import result_page  # Page 3

from dotenv import load_dotenv
load_dotenv()


# ─────────────────────────────────────────────────────────────────────────────
# ONE-TIME INITIALISATION  (runs on first load only)
# ─────────────────────────────────────────────────────────────────────────────
from triage_utils import (
    Word2VecTransformer, clean_text_func,
    predict_with_all_rules,
    obstetric_rule_override, clinical_rule_override, combined_rule_override
)
# Seed session state with defaults (skips keys that already exist)
for _k, _v in DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# Load ML model into session_state so every page can access it without
# re-loading the pickle on each rerun.
if st.session_state.model is None:
    try:
        with open("model_by_kp.pkl", "rb") as _f:
            _bundle = pickle.load(_f)

        # ✅ Store model artefacts as shared session-state variables
        st.session_state.model             = _bundle["model"]
        st.session_state.threshold_class_1 = _bundle["threshold_class_1"]
        st.session_state.threshold_class_2 = _bundle["threshold_class_2"]
        print("✅ Model loaded:", st.session_state.model)

    except FileNotFoundError:
        st.warning("⚠️  model_by_kp.pkl not found — using rule-based fallback predictor.")
    except Exception as _e:
        st.warning(f"⚠️  Could not load model ({_e}) — using rule-based fallback.")


# ─────────────────────────────────────────────────────────────────────────────
# ROUTER
# ─────────────────────────────────────────────────────────────────────────────
_page = st.session_state.page   # "auth" | "form" | "result"

if _page == "auth":
    auth_page()
elif _page == "form":
    form_page()
elif _page == "result":
    result_page()
else:
    # Safety fallback — should never happen
    st.session_state.page = "auth"
    st.rerun()
