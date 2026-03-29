"""
auth_page.py — Login / Register / Guest-access page.

Shared variables read from st.session_state:
  auth_mode, auth_error, auth_success, users_db

Shared variables written to st.session_state:
  page, email, is_guest, auth_mode, auth_error, auth_success, users_db
"""

import streamlit as st
from config import DEFAULTS
from logic import hash_pw
from ui_helpers import inject_css, top_bar, sp, alert, card_wrap
from db_helper import create_user, login_user
from database import create_tables

create_tables()

def auth_page():
    inject_css()
    top_bar()

    # ── Brand strip ──────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:#fff;border-bottom:1px solid #D0E4F1;
                box-shadow:0 1px 6px rgba(14,90,140,.06);
                padding:1rem 1.5rem;margin:-1rem -2rem 0;position:relative;">
      <div style="position:absolute;top:0;left:0;right:0;height:3px;
                  background:linear-gradient(90deg,#0369A1,#38BDF8,#0369A1);"></div>
      <div style="max-width:680px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;">
        <div style="display:flex;align-items:center;gap:.65rem;">
          <div style="width:34px;height:34px;border-radius:10px;
                      background:linear-gradient(135deg,#0369A1,#0EA5E9);
                      display:flex;align-items:center;justify-content:center;
                      font-size:16px;box-shadow:0 4px 12px rgba(3,105,161,.28);">🏥</div>
          <div>
            <div style="font-family:'DM Sans',sans-serif;font-weight:800;
                        font-size:.95rem;color:#0F4C81;">TriageAI</div>
            <div style="font-size:.62rem;color:#6B90AA;letter-spacing:.5px;
                        text-transform:uppercase;font-weight:600;">Clinical Decision Support</div>
          </div>
        </div>
        <div style="display:flex;align-items:center;gap:5px;background:#F0F9FF;
                    border:1px solid #BAE6FD;border-radius:99px;padding:.22rem .75rem;">
          <span style="width:6px;height:6px;border-radius:50%;background:#059669;
                       display:inline-block;margin-right:4px;
                       animation:pulse 2s infinite;"></span>
          <span style="font-size:.7rem;color:#0369A1;font-weight:600;">System Active</span>
        </div>
      </div>
    </div>""", unsafe_allow_html=True)

    sp(32)

    # ── Hero section ─────────────────────────────────────────────────────────
    chips = "".join([
        f'<span style="background:#E0F2FE;border:1px solid #BAE6FD;border-radius:99px;'
        f'padding:.22rem .75rem;font-size:.69rem;font-weight:600;letter-spacing:.3px;'
        f'color:#0369A1;display:inline-block;margin:.12rem;">{ic} {t}</span>'
        for ic, t in [("⚡","CTAS 1–5 Protocol"),("📊","Real-time Vitals"),
                      ("🗺️","Care Pathways"),("💻","Telehealth")]
    ])
    st.markdown(f"""
    <div style="text-align:center;padding:1.8rem 0 2rem;animation:fadeUp .45s ease both;">
      <div style="position:relative;display:inline-flex;align-items:center;
                  justify-content:center;margin-bottom:1.4rem;">
        <div style="position:absolute;inset:-14px;border-radius:36px;
                    background:linear-gradient(135deg,rgba(3,105,161,.1),rgba(14,165,233,.07));
                    border:2px solid #BAE6FD;"></div>
        <div style="position:relative;width:76px;height:76px;border-radius:24px;
                    background:linear-gradient(145deg,#0369A1,#0EA5E9);
                    display:flex;align-items:center;justify-content:center;font-size:32px;
                    box-shadow:0 12px 40px rgba(3,105,161,.3);
                    animation:heartbeat 2.4s ease-in-out infinite;">🏥</div>
      </div>
      <div style="font-family:'DM Sans',sans-serif;font-size:2.4rem;font-weight:800;
                  color:#0E1F35;letter-spacing:-1.5px;line-height:1.1;margin-bottom:.4rem;">
        Welcome to <span style="color:#0369A1;">TriageAI</span>
      </div>
      <div style="font-size:.9rem;color:#3D6080;margin-bottom:1.4rem;line-height:1.6;">
        Emergency Department · Clinical Decision Support System
      </div>
      <div style="display:flex;justify-content:center;flex-wrap:wrap;">{chips}</div>
    </div>""", unsafe_allow_html=True)

    # ── Mode toggle ──────────────────────────────────────────────────────────
    m = st.session_state.auth_mode
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔑  Sign In", use_container_width=True,
                     type="primary" if m == "login" else "secondary",
                     key="btn_login_tab"):
            st.session_state.auth_mode  = "login"
            st.session_state.auth_error = ""
            st.rerun()
    with c2:
        if st.button("📝  Create Account", use_container_width=True,
                     type="primary" if m == "register" else "secondary",
                     key="btn_reg_tab"):
            st.session_state.auth_mode  = "register"
            st.session_state.auth_error = ""
            st.rerun()

    sp(14)

    # ── Login form ───────────────────────────────────────────────────────────
    if m == "login":
        st.markdown(card_wrap(
            '<div style="font-family:\'DM Sans\',sans-serif;font-size:1.22rem;'
            'font-weight:800;color:#0E1F35;margin-bottom:1.2rem;letter-spacing:-.4px;">'
            'Sign in to your account</div>', "padding-bottom:.8rem;"), unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            email_in = st.text_input("Email Address", placeholder="doctor@hospital.org",
                                     key="li_email")
            pw_in    = st.text_input("Password", type="password",
                                     placeholder="Enter your password", key="li_pw")
            submitted = st.form_submit_button("Sign In  →", use_container_width=True)

        if submitted:
            if not email_in or not pw_in:
                st.session_state.auth_error = "Please enter both email and password."
            elif "@" not in email_in:
                st.session_state.auth_error = "Please enter a valid email address."
            else:
                user = login_user(email_in, pw_in)

                if user is None:
                    existing_user = login_user(email_in)

                    if existing_user is None:
                        st.session_state.auth_error = "No account found with this email."
                    else:
                        st.session_state.auth_error = "Incorrect password."
                else:
                    st.session_state.update(
                        page="form",
                        email=email_in,
                        is_guest=False,
                        auth_error="",
                         # Debugging line
                    )
                    st.rerun()

        if st.session_state.auth_error:
            alert("error", st.session_state.auth_error)
        if st.session_state.auth_success:
            alert("success", st.session_state.auth_success)
            alert(f"Logged in user:user_id={st.session_state.user_id}")

    # ── Register form ────────────────────────────────────────────────────────
    else:
        st.markdown(card_wrap(
            '<div style="font-family:\'DM Sans\',sans-serif;font-size:1.22rem;'
            'font-weight:800;color:#0E1F35;margin-bottom:1.2rem;letter-spacing:-.4px;">'
            'Create your account</div>', "padding-bottom:.8rem;"), unsafe_allow_html=True)

        with st.form("register_form", clear_on_submit=False):
            reg_email = st.text_input("Email Address", placeholder="doctor@hospital.org",
                                      key="re_email")
            rc1, rc2 = st.columns(2)
            with rc1:
                reg_pw  = st.text_input("Password", type="password",
                                        placeholder="Min. 6 characters", key="re_pw")
            with rc2:
                reg_pw2 = st.text_input("Confirm Password", type="password",
                                        placeholder="Repeat password", key="re_pw2")
            submitted_r = st.form_submit_button("Create Account  →", use_container_width=True)
            
              

        if submitted_r:
            err = ""
            if not reg_email or not reg_pw or not reg_pw2:
                err = "All fields are required."
            elif "@" not in reg_email:
                err = "Please enter a valid email address."
            elif len(reg_pw) < 6:
                err = "Password must be at least 6 characters."
            elif reg_pw != reg_pw2:
                err = "Passwords do not match."
            elif reg_email in st.session_state.users_db:
                err = "Email already registered."
            if err:
                st.session_state.auth_error = err
            else:
                # ✅ Persist new user in shared users_db
                st.session_state.users_db[reg_email] = hash_pw(reg_pw)
                create_user(reg_email, reg_pw)
                st.session_state.update(
                    auth_mode="login",
                    auth_success="Account created — you can now sign in.",
                    auth_error="",
                )
                st.rerun()
           

        if st.session_state.auth_error:
            alert("error", st.session_state.auth_error)

    # ── OR divider ───────────────────────────────────────────────────────────
    sp(16)
    st.markdown("""
    <div style="display:flex;align-items:center;gap:.9rem;color:#94B3C6;
                font-size:.73rem;font-weight:600;letter-spacing:.5px;margin:.3rem 0;">
      <div style="flex:1;height:1px;background:#D0E4F1;"></div>
      OR
      <div style="flex:1;height:1px;background:#D0E4F1;"></div>
    </div>""", unsafe_allow_html=True)
    sp(10)

    # ── Guest access ─────────────────────────────────────────────────────────
    st.markdown("""
    <div style="background:#F8FBFE;border:1px solid #BAE6FD;border-radius:16px;
                padding:1.1rem 1.4rem;margin-bottom:.5rem;
                box-shadow:0 1px 4px rgba(14,90,140,.06);">
      <div style="font-family:'DM Sans',sans-serif;font-weight:700;font-size:.97rem;
                  color:#0E1F35;margin-bottom:.15rem;">Continue as Guest</div>
      <div style="font-size:.82rem;color:#3D6080;">
        No account needed — assessment results won't be saved.</div>
    </div>""", unsafe_allow_html=True)

    if st.button("👤  Enter as Guest", use_container_width=True, key="guest_btn"):
        # ✅ Share is_guest=True so form_page shows the guest banner
        st.session_state.update(page="form", is_guest=True,
                                email=None, auth_error="")
        st.rerun()

    # ── Privacy badge ────────────────────────────────────────────────────────
    sp(16)
    st.markdown("""
    <div style="text-align:center;">
      <span style="display:inline-flex;align-items:center;gap:6px;background:#E0F2FE;
                   border:1px solid #BAE6FD;color:#0369A1;border-radius:99px;
                   padding:.26rem 1rem;font-size:.72rem;font-weight:600;">
        🔒 &nbsp;Data processed locally — nothing stored externally
      </span>
    </div>""", unsafe_allow_html=True)
