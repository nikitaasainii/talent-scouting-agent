import sys
import os
import streamlit as st

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

st.set_page_config(page_title="Talent Scout Agent", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,700&family=Space+Grotesk:wght@300;400;500;600;700&display=swap');
    html, body, [class*="st-"], .main { background-color: #ffffff !important; color: #000000 !important; font-family: 'Space Grotesk', sans-serif; }
    header[data-testid="stHeader"] { visibility: hidden; height: 0px; }
    .block-container { padding-top: 1rem; max-width: 1100px; }
    .hero-container { text-align: center; margin-top: 1rem; margin-bottom: 3rem; }
    .hero-line-1 { font-family: 'Space Grotesk', sans-serif; font-size: 5rem; font-weight: 700; letter-spacing: -4px; color: #000; line-height: 0.9; }
    .hero-line-2 { font-family: 'Playfair Display', serif; font-style: italic; font-size: 6rem; font-weight: 700; color: #000; background-color: #FFDE59; display: inline-block; padding: 0 1.5rem; line-height: 1; margin-top: 5px; }
    .hero-sub { margin-top: 1.5rem; font-size: 0.9rem; color: #000; letter-spacing: 1px; }
    .dashed-underline { border-bottom: 2px dashed #000; padding-bottom: 2px; }
    div[data-testid="column"] .stButton > button { background-color: transparent !important; color: #000 !important; border: 1.5px solid #000 !important; border-radius: 50px !important; padding: 0.2rem 1rem !important; font-weight: 600 !important; width: 100% !important; }
    div[data-testid="column"] .stButton > button:hover { background-color: #000 !important; color: #fff !important; }
    .stTextArea textarea { background: #fff !important; border: 2px solid #000 !important; border-radius: 4px !important; }
    .cand-card { border-top: 1px solid #000; padding: 2.5rem 0; margin-bottom: 1rem; }
    .chat-bubble { border: 1px solid #000; padding: 1.5rem; margin-bottom: 1rem; background: #fff; }
    .chat-label { font-size: 0.7rem; font-weight: 700; text-transform: uppercase; margin-bottom: 8px; color: #666; }
</style>
""", unsafe_allow_html=True)

if 'current_view' not in st.session_state: st.session_state.current_view = 'home'
if 'shortlist' not in st.session_state: st.session_state.shortlist = None

def set_view(v): st.session_state.current_view = v

_, c1, c2, c3, c4, _ = st.columns([2, 1, 1, 1, 1, 2])
with c1: st.button("home", on_click=set_view, args=("home",))
with c2: st.button("shortlist", on_click=set_view, args=("candidates",))
with c3: st.button("chat", on_click=set_view, args=("conversations",))
with c4: st.button("trace", on_click=set_view, args=("trace",))

st.markdown("""
<div class="hero-container">
    <div class="hero-line-1">talent scouting</div>
    <div class="hero-line-2">agent</div>
    <div class="hero-sub">going from raw descriptions to <span class="dashed-underline">verified hires</span></div>
</div>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------ #
#  VIEW: HOME                                                         #
# ------------------------------------------------------------------ #
if st.session_state.current_view == 'home':
    st.markdown("<h3 style='text-align: center; font-family: \"Playfair Display\"; font-style: italic; font-weight: 400; margin-bottom: 2rem;'>drop the formula</h3>", unsafe_allow_html=True)
    _, col_center, _ = st.columns([1, 3, 1])
    with col_center:
        jd_input = st.text_area("jd", label_visibility="collapsed", placeholder="Paste your JD here to begin the scouting...", height=220)
        st.write("")
        _, b_center, _ = st.columns([1, 2, 1])
        with b_center:
            if st.button("commence search", use_container_width=True):
                if jd_input.strip():
                    with st.spinner("scouting multi-source networks..."):
                        from agents.orchestrator import run_pipeline
                        try:
                            st.session_state.shortlist = run_pipeline(jd_input)
                            st.session_state.current_view = 'candidates'
                            st.rerun()
                        except Exception as e:
                            st.error(f"Search failed: {e}")

# ------------------------------------------------------------------ #
#  VIEW: SHORTLIST                                                    #
# ------------------------------------------------------------------ #
elif st.session_state.current_view == 'candidates':
    st.markdown("<h3 style='font-family: \"Playfair Display\"; font-style: italic; margin-bottom: 3rem;'>the curated list</h3>", unsafe_allow_html=True)
    if st.session_state.shortlist:
        for c in st.session_state.shortlist.shortlisted:
            c_name = getattr(c, 'candidate_name', 'Unknown')
            c_score = getattr(c, 'match_score', 0)
            c_url = getattr(c, 'github_url', '')

            # Detect platform
            is_linkedin = "linkedin.com" in c_url.lower()
            is_wellfound = "wellfound.com" in c_url.lower()

            if is_linkedin:
                platform_name = "LINKEDIN"
                platform_color = "#0077B5"
                platform_icon = "🔗"
                # Build LinkedIn people search — direct profile URLs always redirect
                search_name = c_name.replace(" ", "%20")
                display_url = f"https://www.linkedin.com/search/results/people/?keywords={search_name}"
                button_label = f"SEARCH {c_name.split()[0].upper()} ON LINKEDIN"
            elif is_wellfound:
                platform_name = "WELLFOUND"
                platform_color = "#000000"
                platform_icon = "🚀"
                display_url = c_url
                button_label = "VIEW WELLFOUND PROFILE"
            else:
                platform_name = "GITHUB"
                platform_color = "#000000"
                platform_icon = "📁"
                display_url = c_url
                button_label = "VIEW GITHUB PROFILE"

            st.markdown(f"""
            <div class="cand-card">
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <span style="font-family: 'Playfair Display'; font-size: 3.5rem; font-weight: 700;">0{c.rank}</span>
                        <span style="font-size: 2.2rem; font-weight: 700; margin-left: 1rem; letter-spacing: -1px;">{c_name.upper()}</span>
                        <div style="margin-left: 5rem; margin-top: 10px;">
                            <p style="font-size: 0.8rem; color: #888; margin: 0; letter-spacing: 1px;"><b>{platform_icon} VERIFIED {platform_name} PROFILE</b></p>
                        </div>
                    </div>
                    <div style="background: #FFDE59; padding: 15px 25px; text-align: center; border: 1.5px solid #000;">
                        <div style="font-size: 0.7rem; font-weight: 700;">MATCH SCORE</div>
                        <div style="font-family: 'Playfair Display'; font-size: 2.5rem; font-weight: 700;">{int(c_score)}</div>
                    </div>
                </div>
                <div style="margin-left: 5rem; margin-top: 2rem;">
                    <p style="font-size: 1rem; line-height: 1.6; color: #111;">
                        <b>Scouting Analysis:</b> {c.match_reasons[0] if c.match_reasons else "Strong technical match."}
                    </p>
                </div>
            </div>
            """, unsafe_allow_html=True)

            act1, act2, _ = st.columns([2, 2, 4])
            with act1:
                st.markdown(f'''
                    <a href="{display_url}" target="_blank" style="text-decoration: none;">
                        <div style="background-color: {platform_color}; color: white; text-align: center;
                                    padding: 12px; font-weight: 600; font-size: 0.75rem; border-radius: 2px;">
                            {button_label}
                        </div>
                    </a>
                ''', unsafe_allow_html=True)
            with act2:
                if st.button("VIEW CONTACT DETAILS", key=f"btn_{c.rank}", use_container_width=True):
                    st.session_state[f"view_{c.rank}"] = not st.session_state.get(f"view_{c.rank}", False)

            if st.session_state.get(f"view_{c.rank}"):
                enthusiasm = c.interest_signals.enthusiasm_level if hasattr(c, 'interest_signals') else 'medium'
                st.markdown(f"""
                <div style="border: 1.5px dashed #000; padding: 1.5rem; background: #fff; margin-top: 10px;">
                    <p style="font-size: 0.9rem; margin-bottom: 0.5rem;"><b>Verified Channel:</b> {platform_name}</p>
                    <p style="font-size: 0.9rem; margin-bottom: 1rem;"><b>Interest Signal:</b> {enthusiasm.capitalize()}</p>
                    <hr style="border: 0.5px solid #eee;">
                    <p style="font-size: 0.8rem; color: #555;"><b>AI Outreach Draft:</b></p>
                    <p style="font-style: italic; font-size: 0.9rem;">"Hi {c_name.split()[0]}, I noticed your background while scouting for our {st.session_state.shortlist.job_title} role. Your technical fit is a standout match. Would love to sync!"</p>
                    <p style="font-size: 0.8rem; color: #888; margin-top: 1rem;">Profile Source: {c_url}</p>
                </div>
                """, unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------------------------------ #
#  VIEW: CHAT                                                         #
# ------------------------------------------------------------------ #
elif st.session_state.current_view == 'conversations':
    st.markdown("<h3 style='font-family: \"Playfair Display\"; font-style: italic; margin-bottom: 2rem;'>simulated outreach</h3>", unsafe_allow_html=True)
    if st.session_state.shortlist:
        for c in st.session_state.shortlist.shortlisted:
            with st.expander(f"{c.candidate_name.upper()} — INTEREST: {int(c.interest_score)}%"):
                if not c.conversation:
                    st.markdown("<p style='color:#888;font-size:0.9rem;'>No conversation data available.</p>", unsafe_allow_html=True)
                for turn in c.conversation:
                    is_rec = turn.speaker == "recruiter"
                    st.markdown(f"""
                        <div class="chat-bubble" style="background: {'#f9f9f9' if is_rec else '#ffffff'};">
                            <div class="chat-label">{'AI RECRUITER' if is_rec else c.candidate_name.upper()}</div>
                            <div style="font-size: 1rem;">{turn.message}</div>
                        </div>
                    """, unsafe_allow_html=True)
    else:
        st.markdown("<p style='color:#888;'>Run a search first.</p>", unsafe_allow_html=True)

# ------------------------------------------------------------------ #
#  VIEW: TRACE                                                        #
# ------------------------------------------------------------------ #
elif st.session_state.current_view == 'trace':
    st.markdown("<h3 style='font-family: \"Playfair Display\"; font-style: italic; margin-bottom: 1rem;'>system logs</h3>", unsafe_allow_html=True)
    if st.session_state.shortlist:
        trace_html = "".join([
            f'<div style="font-family: monospace; font-size: 0.8rem; padding: 8px 0; border-bottom: 1px solid #eee;">> {line}</div>'
            for line in st.session_state.shortlist.agent_trace
        ])
        st.markdown(f'<div style="border: 1.5px solid #000; padding: 1.5rem; background: #fff; height: 550px; overflow-y: auto;">{trace_html}</div>', unsafe_allow_html=True)
    else:
        st.markdown("<p style='color:#888;'>Run a search first.</p>", unsafe_allow_html=True)