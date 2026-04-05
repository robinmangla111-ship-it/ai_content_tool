import streamlit as st

st.set_page_config(
    page_title="ContentAI Studio",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
}
code, pre, .stCode { font-family: 'JetBrains Mono', monospace !important; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f0f14 0%, #12121a 100%);
    border-right: 1px solid #1e1e2e;
}
[data-testid="stSidebar"] * { color: #e0e0f0 !important; }
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stRadio label { color: #888 !important; font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; }

/* Main background */
.main { background: #08080f; }
.block-container { padding-top: 2rem; max-width: 1200px; }

/* Cards */
.content-card {
    background: #0f0f1a;
    border: 1px solid #1e1e2e;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 16px;
}
.metric-card {
    background: #0f0f1a;
    border: 1px solid #1e1e2e;
    border-radius: 10px;
    padding: 16px 20px;
    text-align: center;
}
.tag {
    display: inline-block;
    background: #1a1a2e;
    color: #7c7cff;
    border: 1px solid #2e2e5e;
    border-radius: 6px;
    padding: 2px 10px;
    font-size: 12px;
    margin-right: 6px;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #5c5cff 0%, #8b5cf6 100%);
    color: white !important;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    font-family: 'Space Grotesk', sans-serif;
    padding: 10px 24px;
    transition: opacity 0.2s;
}
.stButton > button:hover { opacity: 0.85; }

/* Headings */
h1, h2, h3 { color: #f0f0ff !important; font-weight: 700 !important; }
h1 { font-size: 2rem !important; }
p, label, .stMarkdown { color: #a0a0c0 !important; }

/* Input fields */
.stTextInput input, .stTextArea textarea, .stSelectbox select {
    background: #0f0f1a !important;
    border: 1px solid #1e1e2e !important;
    color: #f0f0ff !important;
    border-radius: 8px !important;
    font-family: 'Space Grotesk', sans-serif !important;
}
.stTextArea textarea { font-family: 'JetBrains Mono', monospace !important; font-size: 13px !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: #0f0f1a;
    border-radius: 10px;
    padding: 4px;
    border: 1px solid #1e1e2e;
    gap: 4px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 8px !important;
    color: #666 !important;
    font-weight: 500 !important;
}
.stTabs [aria-selected="true"] {
    background: #1e1e3e !important;
    color: #a78bfa !important;
}

/* Expander */
.streamlit-expanderHeader {
    background: #0f0f1a !important;
    border: 1px solid #1e1e2e !important;
    border-radius: 8px !important;
    color: #c0c0e0 !important;
}

/* Divider */
hr { border-color: #1e1e2e !important; }

/* Success/Error/Info */
.stSuccess { background: #0f1e14 !important; border: 1px solid #1a3d28 !important; }
.stError   { background: #1e0f0f !important; border: 1px solid #3d1a1a !important; }
.stInfo    { background: #0f0f1e !important; border: 1px solid #1a1a3d !important; }

/* Spinner */
.stSpinner > div { border-top-color: #5c5cff !important; }

/* Copy area */
.copy-box {
    background: #0a0a12;
    border: 1px solid #1e1e2e;
    border-radius: 8px;
    padding: 16px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    color: #c0c0e0;
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 400px;
    overflow-y: auto;
}
</style>
""", unsafe_allow_html=True)

# ── Sidebar nav ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎬 ContentAI Studio")
    st.markdown("---")

    page = st.radio(
        "NAVIGATION",
        [
            "🏠  Dashboard",
            "✍️  Script Generator",
            "🎯  Hook Builder",
            "📅  Content Calendar",
            "🗣️  Voice Clone Setup",
            "🎥  Avatar Video Guide",
            "📊  Analytics Tracker",
            "⚙️  Settings",
        ],
        label_visibility="visible",
    )

    st.markdown("---")
    st.markdown("**API Keys**")
    api_key = st.text_input("OpenAI / Groq Key", type="password", placeholder="sk-...")
    if api_key:
        st.session_state["api_key"] = api_key
        st.success("Key saved ✓")

    st.markdown("---")
    st.caption("v1.0 · Free infra ready · Deploy on Streamlit Cloud")

# ── Route pages ─────────────────────────────────────────────────────────────
if   "Dashboard"        in page: from pages import dashboard;        dashboard.render()
elif "Script Generator" in page: from pages import script_gen;       script_gen.render()
elif "Hook Builder"     in page: from pages import hook_builder;     hook_builder.render()
elif "Content Calendar" in page: from pages import calendar_page;    calendar_page.render()
elif "Voice Clone"      in page: from pages import voice_clone;      voice_clone.render()
elif "Avatar Video"     in page: from pages import avatar_guide;     avatar_guide.render()
elif "Analytics"        in page: from pages import analytics;        analytics.render()
elif "Settings"         in page: from pages import settings_page;    settings_page.render()
