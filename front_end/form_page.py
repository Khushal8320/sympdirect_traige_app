"""
form_page.py — Patient assessment form (Page 2).

Shared variables read from st.session_state:
  is_guest, model, threshold_class_1, threshold_class_2, user_id

Shared variables written to st.session_state:
  result, features, page
"""

import time
import os
import tempfile
import numpy as np
import pandas as pd
import streamlit as st

from dotenv import load_dotenv
load_dotenv()

import azure.cognitiveservices.speech as speechsdk
from spellchecker import SpellChecker

from config import DEFAULTS
from triage_utils import predict_with_all_rules
from logic import get_warnings, predict, predict_with_model
from ui_helpers import inject_css, top_bar, nav_bar, sp, sec_label, alert
from db_helper import save_assessment

spell = SpellChecker()


# ── Azure Speech helper ───────────────────────────────────────────────────────
def transcribe_audio_with_azure(audio_bytes: bytes) -> str:
    speech_key    = os.getenv("AZURE_SPEECH_KEY")
    speech_region = os.getenv("AZURE_SPEECH_REGION")

    if not speech_key or not speech_region:
        return ""

    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(audio_bytes)
            temp_path = tmp.name

        speech_config = speechsdk.SpeechConfig(
            subscription=speech_key, region=speech_region
        )
        speech_config.speech_recognition_language = "en-CA"
        speech_config.set_property(
            speechsdk.PropertyId.SpeechServiceResponse_PostProcessingOption,
            "TrueText",
        )

        audio_config = speechsdk.audio.AudioConfig(filename=temp_path)
        recognizer   = speechsdk.SpeechRecognizer(
            speech_config=speech_config, audio_config=audio_config
        )
        result = recognizer.recognize_once()
        return result.text.strip() if result.reason == speechsdk.ResultReason.RecognizedSpeech else ""

    except Exception:
        return ""
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


# ── Main page ─────────────────────────────────────────────────────────────────
def form_page():
    inject_css()
    top_bar()
    nav_bar()

    # ── Guest banner ──────────────────────────────────────────────────────────
    if st.session_state.is_guest:
        alert("warning",
              "⚠️ <strong>Guest mode</strong> — session data will not be saved between visits.")
        sp(6)

    # ── Page title ────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="margin-bottom:1.4rem;animation:fadeUp .45s ease both;">
      <div style="display:flex;align-items:center;gap:.75rem;margin-bottom:.3rem;">
        <div style="width:3px;height:26px;border-radius:99px;
                    background:linear-gradient(180deg,#0369A1,#38BDF8);"></div>
        <div style="font-family:'DM Sans',sans-serif;font-size:1.5rem;font-weight:800;
                    color:#0E1F35;letter-spacing:-.7px;">New Assessment</div></div>
      <div style="font-size:.85rem;color:#3D6080;padding-left:1.1rem;">
        Enter patient data below to receive a CTAS triage recommendation.</div>
    </div>""", unsafe_allow_html=True)

    # ── CARD: Patient Information ─────────────────────────────────────────────
    st.markdown("""
    <div style="background:#fff;border:1px solid #D0E4F1;border-radius:16px;
                padding:1.4rem 1.6rem 1rem;margin-bottom:.2rem;
                box-shadow:0 1px 4px rgba(14,90,140,.06),0 4px 16px rgba(14,90,140,.06);
                animation:fadeUp .45s .07s ease both;opacity:0;">""",
                unsafe_allow_html=True)
    sec_label("👤", "Patient Information")

    pc1, pc2 = st.columns(2)
    with pc1:
        age = st.number_input("Age (Years)", 0, 120, 40, 1, key="f_age")
    with pc2:
        sex = st.selectbox("Biological Sex", ["Male", "Female"], key="f_sex")

    preg = "No"
    if sex == "Female":
        sp(6)
        st.markdown("""
        <div style="background:#FFF5FB;border:1px solid #FBCFE8;border-radius:12px;
                    padding:.75rem 1.1rem .5rem;">
          <div style="font-size:.67rem;font-weight:700;letter-spacing:.9px;
                      text-transform:uppercase;color:#9D174D;margin-bottom:.5rem;">
            🤰  Pregnancy Status</div>
        </div>""", unsafe_allow_html=True)
        preg = st.radio("Pregnancy Status", ["No", "Yes", "Unknown"],
                        horizontal=True, key="f_preg", label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)
    sp(8)

    preg_map = {"No": 0, "Yes": 1}
    preg_num = preg_map.get(preg, 0) if sex == "Female" else 0

    # ── CARD: Chief Complaint ─────────────────────────────────────────────────
    st.markdown("""
    <div style="background:rgba(255,255,255,0.92);border:1px solid #D0E4F1;border-radius:16px;
                padding:1.4rem 1.6rem 1rem;margin-bottom:.2rem;
                box-shadow:0 1px 4px rgba(14,90,140,.06),0 4px 16px rgba(14,90,140,.06);
                animation:fadeUp .45s .07s ease both;opacity:0;">""",
                unsafe_allow_html=True)
    sec_label("💬", "Chief Complaint")

    if "pending_transcript" not in st.session_state:
        st.session_state["pending_transcript"] = ""
    if "f_comp" not in st.session_state:
        st.session_state["f_comp"] = ""

    if st.session_state["pending_transcript"]:
        current_text = st.session_state.get("f_comp", "").strip()
        new_text     = st.session_state["pending_transcript"].strip()
        st.session_state["f_comp"] = (
            f"{current_text} {new_text}".strip() if current_text else new_text
        )
        st.session_state["pending_transcript"] = ""

    # ── No-symptoms shortcut ──────────────────────────────────────────────
    no_symptoms = st.checkbox(
        "Patient unable to communicate / No specific symptoms",
        key="f_no_symptoms",
        help="Check this if the patient cannot describe symptoms. "
             "Assessment will rely on vital signs only.",
    )
    if no_symptoms:
        st.info(
            "\u2139\ufe0f Chief complaint set to 'No specific symptoms'. "
            "Assessment will rely entirely on vital signs."
        )

    st.caption("Type the complaint or use the microphone to auto-fill the text.")

    comp = st.text_area(
        "Describe the Patient's Main Complaint",
        height=112,
        placeholder="Speak or type the complaint...",
        key="f_comp",
        disabled=no_symptoms,
    )

    # Override comp when no-symptoms is checked
    if no_symptoms:
        comp = "No specific symptoms - patient unable to communicate"

    audio_value = st.audio_input("🎤 Record Chief Complaint")
    if audio_value is not None:
        st.audio(audio_value)
        current_audio_id = getattr(audio_value, "file_id", None)
        last_audio_id    = st.session_state.get("last_audio_id")

        if current_audio_id != last_audio_id:
            st.session_state["last_audio_id"] = current_audio_id
            try:
                audio_bytes = audio_value.read()
                if not audio_bytes:
                    st.warning("⚠️ Empty audio recording — please try again.")
                    transcript = ""
                else:
                    with st.spinner("Converting speech to text..."):
                        transcript = transcribe_audio_with_azure(audio_bytes)
            except Exception as _audio_err:
                st.warning(f"⚠️ Could not read audio ({_audio_err}) — please type manually.")
                transcript = ""

            if transcript:
                current_text = st.session_state.get("f_comp", "").strip()
                if current_text:
                    st.session_state["f_comp"] = f"{current_text} {transcript}".strip()
                else:
                    st.session_state["pending_transcript"] = transcript
                    st.rerun()
                st.success("Chief complaint updated from voice input.")
                st.rerun()
            else:
                st.warning("Could not transcribe the audio clearly. Please try again or type manually.")

    st.markdown('</div>', unsafe_allow_html=True)
    sp(8)

    # ── CARD: Vital Signs ─────────────────────────────────────────────────────
    st.markdown("""
    <div style="background:#fff;border:1px solid #D0E4F1;border-radius:16px;
                padding:1.4rem 1.6rem 1rem;margin-bottom:.2rem;
                box-shadow:0 1px 4px rgba(14,90,140,.06),0 4px 16px rgba(14,90,140,.06);
                animation:fadeUp .45s .21s ease both;opacity:0;">""",
                unsafe_allow_html=True)
    sec_label("📊", "Vital Signs")

    def _vital_val(key, default):
        return st.session_state.get(key, default)

    def _badge(warn: bool, ok_text: str, warn_text: str) -> str:
        bg  = "#FEE2E2" if warn else "#D1FAE5"
        col = "#991B1B" if warn else "#065F46"
        txt = warn_text if warn else ok_text
        return (f'<span style="background:{bg};color:{col};border-radius:99px;'
                f'padding:.12rem .55rem;font-size:.65rem;font-weight:700;">{txt}</span>')

    def _big_val(val, unit, warn: bool) -> str:
        col = "#DC2626" if warn else "#0E1F35"
        return (f'<div style="font-size:1.9rem;font-weight:800;color:{col};'
                f'line-height:1.1;margin:.05rem 0 .15rem;">{val}'
                f'<span style="font-size:.72rem;font-weight:600;color:#6B90AA;'
                f'margin-left:3px;">{unit}</span></div>')

    def _ref_bar(lo, hi, lo_label, hi_label) -> str:
        return (f'<div style="display:flex;justify-content:space-between;'
                f'font-size:.59rem;color:#94B3C6;margin-top:.05rem;">'
                f'<span>{lo_label}</span>'
                f'<span style="color:#059669;font-weight:600;">Normal: {lo}–{hi}</span>'
                f'<span>{hi_label}</span></div>')

    # ── N/A helper: renders a vital-sign container with an optional skip toggle ─
    def _na_badge() -> str:
        return ('<span style="background:#F3F4F6;color:#6B7280;border-radius:99px;'
                'padding:.12rem .55rem;font-size:.65rem;font-weight:700;">— N/A</span>')

    def _na_box() -> str:
        return ('<div style="font-size:1.9rem;font-weight:800;color:#D1D5DB;'
                'line-height:1.1;margin:.05rem 0 .15rem;">—'
                '<span style="font-size:.72rem;font-weight:600;color:#D1D5DB;'
                'margin-left:3px;">not measured</span></div>')

    # Row 1: SBP · DBP · HR
    v1, v2, v3 = st.columns(3)
    with v1:
        with st.container(border=True):
            hdr1, hdr2, hdr3 = st.columns([3, 2, 2])
            with hdr1: st.markdown('<div style="font-size:.6rem;font-weight:700;letter-spacing:.85px;text-transform:uppercase;color:#6B90AA;">🩸 SBP</div>', unsafe_allow_html=True)
            skip_sbp = st.checkbox("N/A", key="skip_sbp", help="Mark SBP as not available")
            if skip_sbp:
                with hdr2: st.markdown(_na_badge(), unsafe_allow_html=True)
                st.markdown(_na_box(), unsafe_allow_html=True)
                st.slider("SBP (mmHg)", 60, 200, 120, 1, key="f_sbp", label_visibility="collapsed", disabled=True)
                sbp = np.nan
            else:
                _s = _vital_val("f_sbp", 120); _w = _s < 90 or _s > 180
                with hdr2: st.markdown(_badge(_w, "✓ OK", "⚠ Abnormal"), unsafe_allow_html=True)
                st.markdown(_big_val(_s, "mmHg", _w), unsafe_allow_html=True)
                sbp = st.slider("SBP (mmHg)", 60, 200, 120, 1, key="f_sbp", label_visibility="collapsed")
                st.markdown(_ref_bar(90, 140, "60", "200"), unsafe_allow_html=True)
    with v2:
        with st.container(border=True):
            hdr1, hdr2, hdr3 = st.columns([3, 2, 2])
            with hdr1: st.markdown('<div style="font-size:.6rem;font-weight:700;letter-spacing:.85px;text-transform:uppercase;color:#6B90AA;">💜 DBP</div>', unsafe_allow_html=True)
            skip_dbp = st.checkbox("N/A", key="skip_dbp", help="Mark DBP as not available")
            if skip_dbp:
                with hdr2: st.markdown(_na_badge(), unsafe_allow_html=True)
                st.markdown(_na_box(), unsafe_allow_html=True)
                st.slider("DBP (mmHg)", 40, 130, 80, 1, key="f_dbp", label_visibility="collapsed", disabled=True)
                dbp = np.nan
            else:
                _s = _vital_val("f_dbp", 80); _w = _s > 90 or _s < 60
                with hdr2: st.markdown(_badge(_w, "✓ OK", "⚠ Abnormal"), unsafe_allow_html=True)
                st.markdown(_big_val(_s, "mmHg", _w), unsafe_allow_html=True)
                dbp = st.slider("DBP (mmHg)", 40, 130, 80, 1, key="f_dbp", label_visibility="collapsed")
                st.markdown(_ref_bar(60, 90, "40", "130"), unsafe_allow_html=True)
    with v3:
        with st.container(border=True):
            hdr1, hdr2, hdr3 = st.columns([3, 2, 2])
            with hdr1: st.markdown('<div style="font-size:.6rem;font-weight:700;letter-spacing:.85px;text-transform:uppercase;color:#6B90AA;">❤️ Heart Rate</div>', unsafe_allow_html=True)
            skip_hr = st.checkbox("N/A", key="skip_hr", help="Mark Heart Rate as not available")
            if skip_hr:
                with hdr2: st.markdown(_na_badge(), unsafe_allow_html=True)
                st.markdown(_na_box(), unsafe_allow_html=True)
                st.slider("HR (bpm)", 30, 200, 80, 1, key="f_hr", label_visibility="collapsed", disabled=True)
                hr = np.nan
            else:
                _s = _vital_val("f_hr", 80); _w = _s > 120 or _s < 50
                with hdr2: st.markdown(_badge(_w, "✓ OK", "⚠ Abnormal"), unsafe_allow_html=True)
                st.markdown(_big_val(_s, "bpm", _w), unsafe_allow_html=True)
                hr = st.slider("HR (bpm)", 30, 200, 80, 1, key="f_hr", label_visibility="collapsed")
                st.markdown(_ref_bar(50, 100, "30", "200"), unsafe_allow_html=True)

    sp(6)

    # Row 2: RR · Temp · Pain
    v4, v5, v6 = st.columns(3)
    with v4:
        with st.container(border=True):
            hdr1, hdr2, hdr3 = st.columns([3, 2, 2])
            with hdr1: st.markdown('<div style="font-size:.6rem;font-weight:700;letter-spacing:.85px;text-transform:uppercase;color:#6B90AA;">🌬️ Resp. Rate</div>', unsafe_allow_html=True)
            skip_rr = st.checkbox("N/A", key="skip_rr", help="Mark Respiratory Rate as not available")
            if skip_rr:
                with hdr2: st.markdown(_na_badge(), unsafe_allow_html=True)
                st.markdown(_na_box(), unsafe_allow_html=True)
                st.slider("RR (/min)", 4, 60, 18, 1, key="f_rr", label_visibility="collapsed", disabled=True)
                rr = np.nan
            else:
                _s = _vital_val("f_rr", 18); _w = _s > 25 or _s < 8
                with hdr2: st.markdown(_badge(_w, "✓ OK", "⚠ Abnormal"), unsafe_allow_html=True)
                st.markdown(_big_val(_s, "/min", _w), unsafe_allow_html=True)
                rr = st.slider("RR (/min)", 4, 60, 18, 1, key="f_rr", label_visibility="collapsed")
                st.markdown(_ref_bar(12, 20, "4", "60"), unsafe_allow_html=True)
    with v5:
        with st.container(border=True):
            hdr1, hdr2, hdr3 = st.columns([3, 2, 2])
            with hdr1: st.markdown('<div style="font-size:.6rem;font-weight:700;letter-spacing:.85px;text-transform:uppercase;color:#6B90AA;">🌡️ Temperature</div>', unsafe_allow_html=True)
            skip_bt = st.checkbox("N/A", key="skip_bt", help="Mark Temperature as not available")
            if skip_bt:
                with hdr2: st.markdown(_na_badge(), unsafe_allow_html=True)
                st.markdown(_na_box(), unsafe_allow_html=True)
                st.slider("Temp (°C)", 30.0, 45.0, 37.0, 0.1, key="f_bt", label_visibility="collapsed", disabled=True, format="%.1f")
                bt = np.nan
            else:
                _s = round(_vital_val("f_bt", 37.0), 1); _w = _s > 38.5 or _s < 36.0
                with hdr2: st.markdown(_badge(_w, "✓ OK", "⚠ Abnormal"), unsafe_allow_html=True)
                st.markdown(_big_val(f"{_s:.1f}", "°C", _w), unsafe_allow_html=True)
                bt = st.slider("Temp (°C)", 30.0, 45.0, 37.0, 0.1, key="f_bt", label_visibility="collapsed", format="%.1f")
                st.markdown(_ref_bar("36.0", "37.5", "30°C", "45°C"), unsafe_allow_html=True)
    with v6:
        with st.container(border=True):
            hdr1, hdr2, hdr3 = st.columns([3, 2, 2])
            with hdr1: st.markdown('<div style="font-size:.6rem;font-weight:700;letter-spacing:.85px;text-transform:uppercase;color:#6B90AA;">😣 NRS Pain</div>', unsafe_allow_html=True)
            skip_nrs = st.checkbox("N/A", key="skip_nrs", help="Mark NRS Pain as not available")
            if skip_nrs:
                with hdr2: st.markdown(_na_badge(), unsafe_allow_html=True)
                st.markdown(_na_box(), unsafe_allow_html=True)
                st.slider("Pain (NRS)", 0, 10, 0, 1, key="f_nrs", label_visibility="collapsed", disabled=True)
                nrs = np.nan
            else:
                _s = _vital_val("f_nrs", 0); _w = _s >= 8
                with hdr2: st.markdown(_badge(_w, "✓ Mild", "⚠ Severe"), unsafe_allow_html=True)
                st.markdown(_big_val(f"{_s}/10", "", _w), unsafe_allow_html=True)
                nrs = st.slider("Pain (NRS)", 0, 10, 0, 1, key="f_nrs", label_visibility="collapsed")
                st.markdown(_ref_bar(0, 3, "0", "10"), unsafe_allow_html=True)

    sp(8)

    # ── Vital-sign warnings (skip NaN values) ─────────────────────────────────
    _sbp_w = sbp if not (isinstance(sbp, float) and np.isnan(sbp)) else None
    _hr_w  = hr  if not (isinstance(hr,  float) and np.isnan(hr))  else None
    _rr_w  = rr  if not (isinstance(rr,  float) and np.isnan(rr))  else None
    _bt_w  = bt  if not (isinstance(bt,  float) and np.isnan(bt))  else None
    _nrs_w = nrs if not (isinstance(nrs, float) and np.isnan(nrs)) else None
    warns = get_warnings(
        _sbp_w if _sbp_w is not None else 120,
        _hr_w  if _hr_w  is not None else 80,
        _rr_w  if _rr_w  is not None else 18,
        _bt_w  if _bt_w  is not None else 37.0,
        _nrs_w if _nrs_w is not None else 0,
    )
    # Remove warnings for vitals that were explicitly skipped
    _skipped_labels = []
    if _sbp_w is None: _skipped_labels += ["Hypotension", "Hypertension"]
    if _hr_w  is None: _skipped_labels += ["Tachycardia", "Bradycardia"]
    if _rr_w  is None: _skipped_labels += ["Tachypnea"]
    if _bt_w  is None: _skipped_labels += ["Fever", "Hypothermia"]
    if _nrs_w is None: _skipped_labels += ["Severe pain"]
    warns = [w for w in warns if not any(skip in w for skip in _skipped_labels)]

    _skipped_count = sum([skip_sbp, skip_dbp, skip_hr, skip_rr, skip_bt, skip_nrs])
    if _skipped_count:
        st.markdown(
            f'<div style="background:#F0F9FF;border:1px solid #BAE6FD;border-radius:10px;'            f'padding:.5rem 1rem;font-size:.8rem;color:#0369A1;margin-top:.2rem;">'            f'ℹ️ <strong>{_skipped_count} vital sign{"s" if _skipped_count>1 else ""} '            f'marked as N/A</strong> — model will use available data only.</div>',
            unsafe_allow_html=True,
        )
    if warns:
        chips = "".join([
            f'<span style="background:#FEE2E2;border:1px solid #FCA5A5;border-radius:99px;'
            f'padding:.18rem .65rem;font-size:.76rem;color:#B91C1C;font-weight:600;'
            f'display:inline-block;margin:.12rem;">'
            f'<span style="width:5px;height:5px;border-radius:50%;background:#EF4444;'
            f'display:inline-block;margin-right:4px;vertical-align:middle;"></span>{w}</span>'
            for w in warns
        ])
        st.markdown(f"""
        <div style="background:#FEE2E2;border:1.5px solid #FCA5A5;border-radius:12px;
                    padding:.8rem 1rem;margin-top:.2rem;">
          <div style="font-size:.67rem;font-weight:700;letter-spacing:.8px;
                      text-transform:uppercase;color:#991B1B;margin-bottom:.45rem;">
            ⚠ {len(warns)} Abnormal Reading{"s" if len(warns) > 1 else ""} Detected
          </div>
          <div>{chips}</div>
        </div>""", unsafe_allow_html=True)
    elif not _skipped_count:
        st.markdown("""
        <div style="background:#D1FAE5;border:1px solid #6EE7B7;border-radius:11px;
                    padding:.6rem 1rem;font-size:.83rem;color:#065F46;margin-top:.2rem;">
          ✓ <strong>All vital signs</strong> within normal reference range
        </div>""", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
    sp(12)

    # ── Submit ────────────────────────────────────────────────────────────────
    if st.button("🔍  Run CTAS Assessment", use_container_width=True,
                 type="primary", key="submit_btn"):
        _comp_missing = not comp.strip() and not st.session_state.get("f_no_symptoms", False)
        if _comp_missing:
            alert("error",
                  "Please describe the chief complaint, or check "
                  "'No specific symptoms' to proceed on vital signs only.")
        else:
            with st.spinner("Analysing clinical data…"):
                time.sleep(1.3)

            # ── Build feature dict (NaN for skipped vitals) ──────────────
            def _v_int(v):
                return np.nan if (isinstance(v, float) and np.isnan(v)) else int(v)
            def _v_float(v):
                return np.nan if (isinstance(v, float) and np.isnan(v)) else float(v)

            f = {
                "Chief_complain_clean": comp,
                "SBP":      _v_int(sbp),
                "DBP":      _v_int(dbp),
                "HR":       _v_int(hr),
                "RR":       _v_int(rr),
                "BT":       _v_float(bt),
                "NRS_pain": _v_int(nrs),
                "Age":      int(age),
                "Sex":      sex,
                "KTAS_RN":  np.nan,
                "pregnant": int(preg_num),
            }

            final_data = pd.DataFrame([f])

            # ── Run ML prediction ─────────────────────────────────────────────
            mdl  = st.session_state.get("model")
            thr1 = st.session_state.get("threshold_class_1")
            thr2 = st.session_state.get("threshold_class_2")

            if mdl is not None:
                result_final = predict_with_all_rules(
                    mdl,
                    final_data,
                    threshold_class_1=thr1,
                    threshold_class_2=thr2,
                )
            else:
                st.error("⚠️ Model not loaded — cannot run assessment.")
                st.stop()

            # ── Save assessment to DB (logged-in users only) ──────────────────
            if not st.session_state.get("is_guest", False):
                user_id = st.session_state.get("user_id")

                if user_id:
                    try:
                        final_ctas     = int(result_final["Final_CTAS"].iloc[0])
                        predicted_ctas = int(result_final["Model_Tuned_CTAS"].iloc[0])
                        prob_cols      = [c for c in result_final.columns
                                          if c.startswith("Prob_Class_")]
                        confidence     = float(
                            result_final[prob_cols].max(axis=1).iloc[0]
                        )

                        def _db_int(v):
                            """Convert NaN → None for SQLite INTEGER columns."""
                            if isinstance(v, float) and np.isnan(v):
                                return None
                            return int(v)
                        def _db_float(v):
                            """Convert NaN → None for SQLite REAL columns."""
                            if isinstance(v, float) and np.isnan(v):
                                return None
                            return float(v)

                        assessment_id = save_assessment(
                            user_id          = user_id,
                            sex              = sex,
                            age              = int(age),
                            chief_complaint  = comp,
                            sbp              = _db_int(sbp),
                            dbp              = _db_int(dbp),
                            rr               = _db_int(rr),
                            temp             = _db_float(bt),
                            nrs_pain         = _db_int(nrs),
                            heart_rate       = _db_int(hr),
                            predicted_ctas   = predicted_ctas,
                            final_ctas       = final_ctas,
                            confidence_score = round(confidence, 4),
                        )

                    except Exception as _e:
                        st.warning(f"⚠️ Assessment could not be saved: {_e}")
                else:
                    # Means auth_page didn't store user_id in session on login
                    print("WARNING: user_id missing from session_state — "
                          "check auth_page stores user_id=user_id on login.")

            # ── Pass results to result_page ───────────────────────────────────
            st.session_state.result   = result_final
            st.session_state.features = f
            st.session_state.page     = "result"
            st.rerun()