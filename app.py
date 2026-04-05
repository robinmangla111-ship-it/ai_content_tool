import streamlit as st
import sys
import os

# ── Fix sys.path BEFORE any page imports ─────────────────────────────────────
# This must be at the very top, before any `from pages import ...`
# On Streamlit Cloud, __file__ = /mount/src/ai_content_tool/app.py
# We add that directory to sys.path so `from pages import x` and
# `from core import y` both resolve correctly.
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="ContentAI Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'Space Grotesk', sans-serif; }
code, pre, .stCode { font-family: 'JetBrains Mono', monospace !important; }

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f0f14 0%, #12121a 100%);
    border-right: 1px solid #1e1e2e;
}
[data-testid="stSidebar"] * { color: #e0e0f0 !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stRadio label {
    color: #888 !important; font-size: 11px;
    text-transform: uppercase; letter-spacing: 0.08em;
}

.main { background: #08080f; }
.block-container { padding-top: 2rem; max-width: 1200px; }

.content-card {
    background: #0f0f1a; border: 1px solid #1e1e2e;
    border-radius: 12px; padding: 20px 24px; margin-bottom: 16px;
}
.metric-card {
    background: #0f0f1a; border: 1px solid #1e1e2e;
    border-radius: 10px; padding: 16px 20px; text-align: center;
}

.stButton > button {
    background: linear-gradient(135deg, #5c5cff 0%, #8b5cf6 100%);
    color: white !important; border: none; border-radius: 8px;
    font-weight: 600; padding: 10px 24px; transition: opacity 0.2s;
}
.stButton > button:hover { opacity: 0.85; }

h1, h2, h3 { color: #f0f0ff !important; font-weight: 700 !important; }
h1 { font-size: 2rem !important; }
p, label, .stMarkdown { color: #a0a0c0 !important; }

.stTextInput input, .stTextArea textarea, .stSelectbox select {
    background: #0f0f1a !important; border: 1px solid #1e1e2e !important;
    color: #f0f0ff !important; border-radius: 8px !important;
}
.stTextArea textarea { font-family: 'JetBrains Mono', monospace !important; font-size: 13px !important; }

.stTabs [data-baseweb="tab-list"] {
    background: #0f0f1a; border-radius: 10px; padding: 4px;
    border: 1px solid #1e1e2e; gap: 4px;
}
.stTabs [data-baseweb="tab"] { border-radius: 8px !important; color: #666 !important; font-weight: 500 !important; }
.stTabs [aria-selected="true"] { background: #1e1e3e !important; color: #a78bfa !important; }

.streamlit-expanderHeader {
    background: #0f0f1a !important; border: 1px solid #1e1e2e !important;
    border-radius: 8px !important; color: #c0c0e0 !important;
}

hr { border-color: #1e1e2e !important; }
.stSuccess { background: #0f1e14 !important; border: 1px solid #1a3d28 !important; }
.stError   { background: #1e0f0f !important; border: 1px solid #3d1a1a !important; }
.stInfo    { background: #0f0f1e !important; border: 1px solid #1a1a3d !important; }
.stSpinner > div { border-top-color: #5c5cff !important; }

.copy-box {
    background: #0a0a12; border: 1px solid #1e1e2e; border-radius: 8px;
    padding: 16px; font-family: 'JetBrains Mono', monospace; font-size: 13px;
    color: #c0c0e0; white-space: pre-wrap; word-break: break-word;
    max-height: 400px; overflow-y: auto;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎬 ContentAI Studio")
    st.markdown("---")

    page = st.radio(
        "NAVIGATION",
        [
            "🏠 Dashboard",
            "✍️ Script Generator",
            "🎯 Hook Builder",
            "📅 Content Calendar",
            "🗣️ Voice Clone Setup",
            "🎥 Avatar Video Guide",
            "📊 Analytics Tracker",
            "⚙️ Settings",
        ],
        label_visibility="visible",
    )

    st.markdown("---")
    st.markdown("**API Keys**")
    api_key = st.text_input("Groq / OpenAI Key", type="password", placeholder="gsk_... or sk-...")
    if api_key:
        st.session_state["api_key"] = api_key
        st.success("Key saved ✓")

    st.markdown("---")
    st.caption("v1.0 · Free infra · Streamlit Cloud")


# ── Safe page loader ──────────────────────────────────────────────────────────
def load_page(module_name: str):
    """Import and render a page module, showing errors instead of blank screen."""
    try:
        import importlib
        mod = importlib.import_module(f"pages.{module_name}")
        mod.render()
    except ModuleNotFoundError as e:
        st.error(f"❌ Module not found: `{e}`")
        st.info(f"sys.path: `{sys.path}`")
        st.info(f"App dir: `{_APP_DIR}`")
        import traceback
        st.code(traceback.format_exc())
    except Exception as e:
        st.error(f"❌ Error in `{module_name}`: `{e}`")
        import traceback
        st.code(traceback.format_exc())


# ── Routing ───────────────────────────────────────────────────────────────────
if   "Dashboard"       in page: load_page("dashboard")
elif "Script Generator" in page: load_page("script_gen")
elif "Hook Builder"    in page: load_page("hook_builder")
elif "Content Calendar" in page: load_page("calendar_page")
elif "Voice Clone"     in page: load_page("voice_clone")
elif "Avatar Video"    in page: load_page("avatar_guide")
elif "Analytics"       in page: load_page("analytics")
elif "Settings"        in page: load_page("settings_page")
