import streamlit as st, sys, os
_D = os.path.dirname(os.path.abspath(__file__))
if _D not in sys.path: sys.path.insert(0, _D)
st.set_page_config(page_title="ContentAI Studio", page_icon="🎬", layout="wide", initial_sidebar_state="expanded")
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=JetBrains+Mono:wght@400&display=swap');
html,body,[class*="css"]{font-family:'Space Grotesk',sans-serif}
code,pre,.stCode{font-family:'JetBrains Mono',monospace!important}
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0f0f14,#12121a);border-right:1px solid #1e1e2e}
[data-testid="stSidebar"] *{color:#e0e0f0!important}
.main{background:#08080f}.block-container{padding-top:2rem;max-width:1200px}
.content-card{background:#0f0f1a;border:1px solid #1e1e2e;border-radius:12px;padding:20px 24px;margin-bottom:16px}
.stButton>button{background:linear-gradient(135deg,#5c5cff,#8b5cf6);color:white!important;border:none;border-radius:8px;font-weight:600;padding:10px 24px}
h1,h2,h3{color:#f0f0ff!important;font-weight:700!important} h1{font-size:2rem!important}
p,label,.stMarkdown{color:#a0a0c0!important}
.stTextInput input,.stTextArea textarea{background:#0f0f1a!important;border:1px solid #1e1e2e!important;color:#f0f0ff!important;border-radius:8px!important}
.stTabs [data-baseweb="tab-list"]{background:#0f0f1a;border-radius:10px;padding:4px;border:1px solid #1e1e2e}
.stTabs [aria-selected="true"]{background:#1e1e3e!important;color:#a78bfa!important}
hr{border-color:#1e1e2e!important}
.copy-box{background:#0a0a12;border:1px solid #1e1e2e;border-radius:8px;padding:16px;font-family:'JetBrains Mono',monospace;font-size:13px;color:#c0c0e0;white-space:pre-wrap;max-height:400px;overflow-y:auto}
</style>""", unsafe_allow_html=True)
with st.sidebar:
    st.markdown("## 🎬 ContentAI Studio")
    st.markdown("---")
    page = st.radio("NAVIGATION", [
        "🏠 Dashboard","✍️ Script Generator","🎯 Hook Builder",
        "📅 Content Calendar","🎙️ Voice Studio","🏖️ Travel Content Creator","Slider Content Creator"
        "🗣️ Voice Clone Setup","🎥 Avatar Video Guide",
        "📊 Analytics Tracker","⚙️ Settings",
    ], label_visibility="visible")
    st.markdown("---")
    st.markdown("**API Keys**")
    gk = st.text_input("Groq / OpenAI Key", type="password", placeholder="gsk_...")
    if gk: st.session_state["api_key"] = gk; st.success("LLM key ✓")
    hk = st.text_input("Hugging Face Token", type="password", placeholder="hf_...")
    if hk: st.session_state["hf_token"] = hk; st.success("HF token ✓")
    st.markdown("---")
    st.caption("v1.3 · Free infra · Streamlit Cloud")
def load_page(m):
    try:
        import importlib
        importlib.import_module(f"pages.{m}").render()
    except Exception as e:
        st.error(f"❌ {m}: {e}")
        import traceback; st.code(traceback.format_exc())
if   "Dashboard"              in page: load_page("dashboard")
elif "Script Generator"       in page: load_page("script_gen")
elif "Hook Builder"           in page: load_page("hook_builder")
elif "Content Calendar"       in page: load_page("calendar_page")
elif "Voice Studio"           in page: load_page("voice_studio")
elif "Travel Content Creator" in page: load_page("travel_content")
elif "Slider Content Creator" in page: load_page("slider_content")
elif "Voice Clone"            in page: load_page("voice_clone")
elif "Avatar Video"           in page: load_page("avatar_guide")
elif "Analytics"              in page: load_page("analytics")
elif "Settings"               in page: load_page("settings_page")
