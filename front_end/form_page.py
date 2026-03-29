"""
form_page.py — Patient assessment form (Page 2).

Shared variables read from st.session_state:
  is_guest, model, threshold_class_1, threshold_class_2

Shared variables written to st.session_state:
  result, features, page
"""

import time
from dotenv import load_dotenv
load_dotenv()

from streamlit_webrtc import webrtc_streamer
from xml.parsers.expat import model
import streamlit as st
import pandas as pd
from config import DEFAULTS
from triage_utils import predict_with_all_rules
from triage_utils import predict_with_all_rules
from logic import get_warnings, predict, predict_with_model
from ui_helpers import inject_css, top_bar, nav_bar, sp, sec_label, alert
import numpy as np
from db_helper import save_assessment

import os
import os
import queue
import time
import threading
import azure.cognitiveservices.speech as speechsdk
from streamlit_webrtc import webrtc_streamer, WebRtcMode, AudioProcessorBase




# ---------------- LIVE AZURE SPEECH HELPERS ----------------

import os
import tempfile
import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv

load_dotenv()

def transcribe_audio_with_azure(audio_bytes: bytes) -> str:
    speech_key = os.getenv("AZURE_SPEECH_KEY")
    speech_region = os.getenv("AZURE_SPEECH_REGION")

    if not speech_key or not speech_region:
        return ""

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_bytes)
            temp_path = tmp_file.name

        speech_config = speechsdk.SpeechConfig(
            subscription=speech_key,
            region=speech_region
        )
        speech_config.speech_recognition_language = "en-CA"

        # Improve punctuation/readability
        speech_config.set_property(
            speechsdk.PropertyId.SpeechServiceResponse_PostProcessingOption,
            "TrueText"
        )

        audio_config = speechsdk.audio.AudioConfig(filename=temp_path)
        recognizer = speechsdk.SpeechRecognizer(
            speech_config=speech_config,
            audio_config=audio_config
        )

        result = recognizer.recognize_once()

        if result.reason == speechsdk.ResultReason.RecognizedSpeech:
            return result.text.strip()

        return ""

    except Exception:
        return ""

    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
import streamlit as st
from spellchecker import SpellChecker

spell = SpellChecker()

def correct_text(text):
    words = text.split()
    corrected = []
    for w in words:
        corr = spell.correction(w)
        corrected.append(corr if corr else w)
    return " ".join(corrected)
def form_page():
    inject_css()
    top_bar()
    nav_bar()

    # ── Guest banner ─────────────────────────────────────────────────────────
    if st.session_state.is_guest:
        alert("warning",
              "⚠️ <strong>Guest mode</strong> — session data will not be saved between visits.")
        sp(6)

    # ── Page title ───────────────────────────────────────────────────────────
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
        sex = st.selectbox("Biological Sex",
                           ["Male", "Female"], key="f_sex")
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

    preg_map = {
    "No": 0,
    "Yes": 1
    #  # or np.nan if your model was trained that way
}           
    preg_num = preg_map.get(preg, 0) if sex == "Female" else 0
    print(f"Pregnancy status (numeric): {preg_num}")
    # ── CARD: Chief Complaint ─────────────────────────────────────────────────

# ── CARD: Chief Complaint ─────────────────────────────────────────────────
    st.markdown("""
    <div style="background:rgba(255,255,255,0.92);border:1px solid #D0E4F1;border-radius:16px;
                padding:1.4rem 1.6rem 1rem;margin-bottom:.2rem;
                box-shadow:0 1px 4px rgba(14,90,140,.06),0 4px 16px rgba(14,90,140,.06);
                animation:fadeUp .45s .07s ease both;opacity:0;">""",
                unsafe_allow_html=True)

    sec_label("💬", "Chief Complaint")
    

    if "final_text" in st.session_state:
     st.success(f"Final text: {st.session_state['final_text']}")
    if "pending_transcript" not in st.session_state:
        st.session_state["pending_transcript"] = ""

    if "f_comp" not in st.session_state:
        st.session_state["f_comp"] = ""

    if st.session_state["pending_transcript"]:
        current_text = st.session_state.get("f_comp", "").strip()
        new_text = st.session_state["pending_transcript"].strip()

        if current_text:
            st.session_state["f_comp"] = f"{current_text} {new_text}".strip()
        else:
            st.session_state["f_comp"] = new_text

        st.session_state["pending_transcript"] = ""

    st.caption("Type the complaint or use the microphone to auto-fill the text.")

    comp = st.text_area(
        "Describe the Patient's Main Complaint",
        height=112,
        placeholder="Speak or type the complaint...",
        key="f_comp",
    )

    audio_value = st.audio_input("🎤 Record Chief Complaint")

    if audio_value is not None:
        st.audio(audio_value)

        current_audio_id = getattr(audio_value, "file_id", None)
        last_audio_id = st.session_state.get("last_audio_id")

        if current_audio_id != last_audio_id:
            st.session_state["last_audio_id"] = current_audio_id

            with st.spinner("Converting speech to text..."):
                transcript = transcribe_audio_with_azure(audio_value.read())

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
    # text = st.session_state["f_comp"]
    # if text:
    #     suggestion = correct_text(text)
    #     st.write("Original:", text)
    #     st.write("Suggested:", suggestion)

    #     if st.button("Use suggested text"):
    #         st.session_state["final_text"] = suggestion

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

    # Row 1: SBP · DBP · HR
    v1, v2, v3 = st.columns(3)
    with v1:
        with st.container(border=True):
            _s = _vital_val("f_sbp", 120); _w = _s < 90 or _s > 180
            hdr1, hdr2 = st.columns([3, 2])
            with hdr1: st.markdown('<div style="font-size:.6rem;font-weight:700;letter-spacing:.85px;text-transform:uppercase;color:#6B90AA;">🩸 SBP</div>', unsafe_allow_html=True)
            with hdr2: st.markdown(_badge(_w, "✓ OK", "⚠ Abnormal"), unsafe_allow_html=True)
            st.markdown(_big_val(_s, "mmHg", _w), unsafe_allow_html=True)
            sbp = st.slider("SBP (mmHg)", 60, 200, 120, 1, key="f_sbp", label_visibility="collapsed")
            st.markdown(_ref_bar(90, 140, "60", "200"), unsafe_allow_html=True)
    with v2:
        with st.container(border=True):
            _s = _vital_val("f_dbp", 80); _w = _s > 90 or _s < 60
            hdr1, hdr2 = st.columns([3, 2])
            with hdr1: st.markdown('<div style="font-size:.6rem;font-weight:700;letter-spacing:.85px;text-transform:uppercase;color:#6B90AA;">💜 DBP</div>', unsafe_allow_html=True)
            with hdr2: st.markdown(_badge(_w, "✓ OK", "⚠ Abnormal"), unsafe_allow_html=True)
            st.markdown(_big_val(_s, "mmHg", _w), unsafe_allow_html=True)
            dbp = st.slider("DBP (mmHg)", 40, 130, 80, 1, key="f_dbp", label_visibility="collapsed")
            st.markdown(_ref_bar(60, 90, "40", "130"), unsafe_allow_html=True)
    with v3:
        with st.container(border=True):
            _s = _vital_val("f_hr", 80); _w = _s > 120 or _s < 50
            hdr1, hdr2 = st.columns([3, 2])
            with hdr1: st.markdown('<div style="font-size:.6rem;font-weight:700;letter-spacing:.85px;text-transform:uppercase;color:#6B90AA;">❤️ Heart Rate</div>', unsafe_allow_html=True)
            with hdr2: st.markdown(_badge(_w, "✓ OK", "⚠ Abnormal"), unsafe_allow_html=True)
            st.markdown(_big_val(_s, "bpm", _w), unsafe_allow_html=True)
            hr = st.slider("HR (bpm)", 30, 200, 80, 1, key="f_hr", label_visibility="collapsed")
            st.markdown(_ref_bar(50, 100, "30", "200"), unsafe_allow_html=True)

    sp(6)

    # Row 2: RR · Temp · Pain
    v4, v5, v6 = st.columns(3)
    with v4:
        with st.container(border=True):
            _s = _vital_val("f_rr", 18); _w = _s > 25 or _s < 8
            hdr1, hdr2 = st.columns([3, 2])
            with hdr1: st.markdown('<div style="font-size:.6rem;font-weight:700;letter-spacing:.85px;text-transform:uppercase;color:#6B90AA;">🌬️ Resp. Rate</div>', unsafe_allow_html=True)
            with hdr2: st.markdown(_badge(_w, "✓ OK", "⚠ Abnormal"), unsafe_allow_html=True)
            st.markdown(_big_val(_s, "/min", _w), unsafe_allow_html=True)
            rr = st.slider("RR (/min)", 4, 60, 18, 1, key="f_rr", label_visibility="collapsed")
            st.markdown(_ref_bar(12, 20, "4", "60"), unsafe_allow_html=True)
    with v5:
        with st.container(border=True):
            _s = round(_vital_val("f_bt", 37.0), 1); _w = _s > 38.5 or _s < 36.0
            hdr1, hdr2 = st.columns([3, 2])
            with hdr1: st.markdown('<div style="font-size:.6rem;font-weight:700;letter-spacing:.85px;text-transform:uppercase;color:#6B90AA;">🌡️ Temperature</div>', unsafe_allow_html=True)
            with hdr2: st.markdown(_badge(_w, "✓ OK", "⚠ Abnormal"), unsafe_allow_html=True)
            st.markdown(_big_val(f"{_s:.1f}", "°C", _w), unsafe_allow_html=True)
            bt = st.slider("Temp (°C)", 30.0, 45.0, 37.0, 0.1, key="f_bt", label_visibility="collapsed", format="%.1f")
            st.markdown(_ref_bar("36.0", "37.5", "30°C", "45°C"), unsafe_allow_html=True)
    with v6:
        with st.container(border=True):
            _s = _vital_val("f_nrs", 0); _w = _s >= 8
            hdr1, hdr2 = st.columns([3, 2])
            with hdr1: st.markdown('<div style="font-size:.6rem;font-weight:700;letter-spacing:.85px;text-transform:uppercase;color:#6B90AA;">😣 NRS Pain</div>', unsafe_allow_html=True)
            with hdr2: st.markdown(_badge(_w, "✓ Mild", "⚠ Severe"), unsafe_allow_html=True)
            st.markdown(_big_val(f"{_s}/10", "", _w), unsafe_allow_html=True)
            nrs = st.slider("Pain (NRS)", 0, 10, 0, 1, key="f_nrs", label_visibility="collapsed")
            st.markdown(_ref_bar(0, 3, "0", "10"), unsafe_allow_html=True)

    sp(8)

    # ── Vital-sign warnings ───────────────────────────────────────────────────
    warns = get_warnings(sbp, hr, rr, bt, nrs)
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
    else:
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
        if not comp.strip():
            alert("error",
                  "Please describe the chief complaint before running the assessment.")
        else:
            with st.spinner("Analysing clinical data…"):
                time.sleep(1.3)

            f =  {
            "Chief_complain_clean": comp,
            "SBP": int(sbp),
            "DBP": int(dbp),
            "HR": int(hr),
            "RR": int(rr),
            "BT": float(bt),
            "NRS_pain": int(nrs),
            "Age": int(age),
            "Sex": sex,
            "KTAS_RN": np.nan,
            "pregnant": int(preg_num)}
            print("features before prediction:", f)
            
            assessment_id = None

            if not st.session_state.get("is_guest", False):
                user_id = st.session_state.get("user_id")

                if user_id is not None:
                    assessment_id = save_assessment(
                        user_id=user_id,
                        sex=sex,
                        age=int(age),
                        chief_complaint=comp,
                        sbp=int(sbp),
                        dbp=int(dbp),
                        rr=int(rr),
                        temp=float(bt),
                        nrs_pain=int(nrs),
                        heart_rate=int(hr)
        )



            final_data = pd.DataFrame([f])  # Convert to DataFrame  model expects that
            # ✅ Use ML model from session_state if available, else fallback
            mdl  = st.session_state.get("model")
            thr1 = st.session_state.get("threshold_class_1")
            thr2 = st.session_state.get("threshold_class_2")
            print("results of the thresholds:", mdl, thr1, thr2)
            if mdl is not None:
                result = predict_with_model(f, mdl, thr1, thr2)
                print("Model result_final:")
                result_final = predict_with_all_rules(
                                mdl,
                                final_data,
                                threshold_class_1=thr1,
                                threshold_class_2=thr2
                            )
                print("Result after applying rules:", print(result_final.head(1).T))
                
            else:
                result 

            # ✅ Write shared variables for result_page to consume
            st.session_state.result   = result_final
            st.session_state.features = f
            st.session_state.page     = "result"
            st.rerun()
