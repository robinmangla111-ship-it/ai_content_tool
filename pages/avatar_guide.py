import streamlit as st

def render():
    st.markdown("# 🎥 AI Avatar Video Guide")
    st.markdown("The exact workflow to create Vaibhav Sisinty-style AI clone videos — for free.")
    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["🗺️ Full Workflow", "🆓 Free Tools", "🔧 Advanced (Self-host)"])

    with tab1:
        st.markdown("### The Complete Pipeline")
        st.markdown("""
        <div class="content-card" style="padding:24px">
        <div style="display:flex;flex-direction:column;gap:0">
        """, unsafe_allow_html=True)

        flow = [
            ("✍️", "Script", "Use ContentAI Studio → Script Generator", "#5c5cff"),
            ("🗣️", "Voice Audio", "ElevenLabs (free) → paste script → download MP3", "#8b5cf6"),
            ("🎭", "Avatar Video", "Vidnoz or D-ID → upload audio → generate talking head video", "#06b6d4"),
            ("✂️", "Edit + Captions", "CapCut → import video → auto-captions → add music + B-roll", "#10b981"),
            ("📤", "Export & Post", "Export 9:16 → upload to YouTube Shorts / Instagram Reels / TikTok", "#f59e0b"),
        ]

        for i, (icon, title, desc, color) in enumerate(flow):
            arrow = '<div style="text-align:center;color:#333;font-size:20px;margin:4px 0">↓</div>' if i < len(flow)-1 else ""
            st.markdown(f"""
            <div style="background:#0f0f1a;border:1px solid {color}40;border-radius:10px;padding:14px 18px;display:flex;align-items:center;gap:14px">
                <div style="background:{color}20;border:1px solid {color}60;border-radius:8px;width:40px;height:40px;display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0">{icon}</div>
                <div>
                    <div style="font-weight:700;color:{color};font-size:13px">{title}</div>
                    <div style="color:#777;font-size:12px;margin-top:2px">{desc}</div>
                </div>
            </div>
            {arrow}
            """, unsafe_allow_html=True)

        st.markdown("</div></div>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### ⏱️ Time breakdown (per video)")
        c1,c2,c3,c4,c5 = st.columns(5)
        times = [("Script", "2 min"), ("Voice", "1 min"), ("Avatar", "5 min"), ("Edit", "10 min"), ("Post", "2 min")]
        for col, (step, t) in zip([c1,c2,c3,c4,c5], times):
            with col:
                st.markdown(f"""<div class="metric-card">
                <div style="font-size:18px;font-weight:700;color:#a78bfa">{t}</div>
                <div style="font-size:11px;color:#555;margin-top:4px">{step}</div>
                </div>""", unsafe_allow_html=True)

        st.success("**Total: ~20 minutes per video** · Vaibhav's workflow at scale")

    with tab2:
        st.markdown("### 🆓 Free Tool Comparison")
        tools = [
            {
                "name": "Vidnoz", "icon": "🎬", "category": "Avatar",
                "free": "2 min/day = 60 min/month", "quality": 82,
                "pros": "Huge template library, easy UI", "cons": "Watermark on free",
                "link": "https://vidnoz.com", "color": "#5c5cff"
            },
            {
                "name": "D-ID", "icon": "🤖", "category": "Avatar",
                "free": "14-day free trial, $5.9/mo after", "quality": 88,
                "pros": "Very realistic, V4 expressive model", "cons": "Short free period",
                "link": "https://d-id.com", "color": "#8b5cf6"
            },
            {
                "name": "ElevenLabs", "icon": "🗣️", "category": "Voice",
                "free": "10,000 chars/month", "quality": 95,
                "pros": "Best voice clone quality, very natural", "cons": "Limited chars free",
                "link": "https://elevenlabs.io", "color": "#06b6d4"
            },
            {
                "name": "CapCut", "icon": "✂️", "category": "Editor",
                "free": "Fully free, all features", "quality": 90,
                "pros": "Auto-captions, templates, free B-roll", "cons": "Slight watermark option",
                "link": "https://capcut.com", "color": "#10b981"
            },
            {
                "name": "Groq", "icon": "⚡", "category": "LLM (Scripts)",
                "free": "Free tier — very fast llama-3.3-70b", "quality": 92,
                "pros": "Free, fastest inference available", "cons": "Rate limits on free",
                "link": "https://console.groq.com", "color": "#f59e0b"
            },
        ]

        for tool in tools:
            col_info, col_bar = st.columns([3, 1])
            with col_info:
                st.markdown(f"""
                <div class="content-card" style="border-color:{tool['color']}30">
                    <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
                        <span style="font-size:24px">{tool['icon']}</span>
                        <div>
                            <span style="font-weight:700;color:{tool['color']};font-size:15px">{tool['name']}</span>
                            <span style="margin-left:8px;font-size:10px;color:#555;background:#1a1a2e;padding:2px 8px;border-radius:10px">{tool['category']}</span>
                        </div>
                        <a href="{tool['link']}" target="_blank" style="margin-left:auto;color:#5c5cff;font-size:12px">Visit →</a>
                    </div>
                    <div style="color:#10b981;font-size:12px;margin-bottom:4px">✓ Free: {tool['free']}</div>
                    <div style="color:#888;font-size:12px">✓ {tool['pros']} &nbsp;·&nbsp; ✗ {tool['cons']}</div>
                    <div style="margin-top:10px">
                        <div style="background:#1a1a2e;border-radius:3px;height:4px">
                            <div style="background:{tool['color']};width:{tool['quality']}%;height:4px;border-radius:3px"></div>
                        </div>
                        <div style="text-align:right;font-size:10px;color:#555;margin-top:2px">Quality: {tool['quality']}/100</div>
                    </div>
                </div>""", unsafe_allow_html=True)

    with tab3:
        st.markdown("### 🔧 Self-hosted / Advanced Stack")
        st.markdown("Zero ongoing cost — runs on your own machine.")

        st.code("""
# 1. Install Ollama (free local LLM)
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama3.3        # or mistral, phi4

# 2. Install SadTalker (free local avatar)
git clone https://github.com/OpenTalker/SadTalker
cd SadTalker && pip install -r requirements.txt
# Download checkpoints (see their README)

# 3. Install Coqui TTS (free local voice clone)
pip install TTS
tts --list_models           # see available models

# 4. Run this app locally
cd ai_content_tool
pip install -r requirements.txt
streamlit run app.py
""", language="bash")

        st.markdown("---")
        st.markdown("### 📦 Self-hosted voice clone (Coqui)")
        st.code("""
from TTS.api import TTS

# Load XTTS v2 — best free voice clone
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")

# Clone your voice with just 6 seconds of audio!
tts.tts_to_file(
    text="Did you know 90% of creators quit before they go viral?",
    speaker_wav="my_voice_sample.wav",  # your 6-second recording
    language="en",
    file_path="output.wav"
)
""", language="python")

        st.info("💡 **Coqui XTTS v2** needs only 6 seconds of your voice sample. Completely free and runs locally. Quality is ~85% of ElevenLabs.")
