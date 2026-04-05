import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.llm import get_provider_badge

def render():
    st.markdown("# 🎬 ContentAI Studio")
    st.markdown(f"**Active engine:** {get_provider_badge()}")
    st.markdown("---")

    # Metrics row
    c1, c2, c3, c4 = st.columns(4)
    metrics = [
        ("📝", "Scripts Made", "0"),
        ("🎣", "Hooks Generated", "0"),
        ("📅", "Calendar Days", "0"),
        ("🔥", "Avg Hook Score", "—"),
    ]
    for col, (icon, label, val) in zip([c1,c2,c3,c4], metrics):
        with col:
            count_key = label.lower().replace(" ", "_")
            actual = st.session_state.get(count_key, val)
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size:28px">{icon}</div>
                <div style="font-size:24px;font-weight:700;color:#a78bfa">{actual}</div>
                <div style="font-size:12px;color:#666;margin-top:4px">{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # Quick start guide
    col_l, col_r = st.columns([3, 2])
    with col_l:
        st.markdown("### 🚀 Quick Start")
        steps = [
            ("1", "Add your API key", "Groq is free — get one at console.groq.com", "⚡"),
            ("2", "Go to Script Generator", "Enter your topic, niche, and audience", "✍️"),
            ("3", "Build Viral Hooks", "Generate 5 scroll-stopping hooks instantly", "🎣"),
            ("4", "Plan your Calendar", "7-day content plan in one click", "📅"),
            ("5", "Set up Voice Clone", "Free ElevenLabs + Vidnoz workflow", "🗣️"),
        ]
        for num, title, desc, icon in steps:
            st.markdown(f"""
            <div class="content-card" style="display:flex;align-items:flex-start;gap:16px;padding:14px 18px">
                <div style="background:#1e1e3e;border:1px solid #3e3e6e;border-radius:50%;width:32px;height:32px;display:flex;align-items:center;justify-content:center;font-weight:700;color:#a78bfa;flex-shrink:0">{num}</div>
                <div>
                    <div style="font-weight:600;color:#e0e0f0;font-size:14px">{icon} {title}</div>
                    <div style="color:#666;font-size:12px;margin-top:2px">{desc}</div>
                </div>
            </div>""", unsafe_allow_html=True)

    with col_r:
        st.markdown("### 🛠️ Free Tool Stack")
        tools = [
            ("⚡", "Groq API", "Free LLM (llama-3.3-70b)", "#5c5cff"),
            ("🎙️", "ElevenLabs", "Free voice cloning (10k chars/mo)", "#8b5cf6"),
            ("🎬", "Vidnoz", "Free AI avatar (60 min/mo)", "#06b6d4"),
            ("✂️", "CapCut", "Free editing + captions", "#10b981"),
            ("☁️", "Streamlit Cloud", "Free deployment", "#f59e0b"),
            ("🖥️", "Ollama", "100% local, zero cost", "#ef4444"),
        ]
        for icon, name, desc, color in tools:
            st.markdown(f"""
            <div class="content-card" style="padding:10px 16px;margin-bottom:8px">
                <div style="display:flex;align-items:center;gap:10px">
                    <span style="font-size:18px">{icon}</span>
                    <div>
                        <div style="font-weight:600;color:{color};font-size:13px">{name}</div>
                        <div style="color:#555;font-size:11px">{desc}</div>
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 💡 Today's Content Idea")

    if st.button("✨ Generate a random content idea", use_container_width=True):
        import sys; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from core.llm import complete
        niche = st.session_state.get("niche", "AI and technology")
        with st.spinner("Thinking..."):
            idea = complete(
                "Generate one viral YouTube Shorts idea (1-2 sentences) for the given niche. Be specific.",
                f"Niche: {niche}",
                mode="script",
            )
        st.info(f"💡 **Idea:** {idea}")
