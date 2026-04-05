import streamlit as st

def render():
    st.markdown("# 🗣️ Voice Clone Setup")
    st.markdown("Step-by-step guide to clone your voice for free using ElevenLabs.")
    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["📋 Setup Guide", "🎙️ Recording Tips", "🔌 API Integration"])

    with tab1:
        steps = [
            ("1", "Create ElevenLabs account", "Go to elevenlabs.io → Sign up free. Free tier gives 10,000 characters/month.", "https://elevenlabs.io"),
            ("2", "Record your voice sample", "Record 1-3 minutes of yourself speaking clearly. Use a quiet room + phone mic or laptop mic.", None),
            ("3", "Create Instant Voice Clone", "Dashboard → Voices → Add Voice → Instant Voice Cloning → Upload your audio file.", None),
            ("4", "Test your clone", "Type any text and click Generate. Your clone reads it back in your voice.", None),
            ("5", "Copy your API key", "Profile → API Key → Copy it. Paste it in the Settings page here.", None),
            ("6", "Use in your workflow", "Script Generator → Generate Script → Click 'Generate Audio' to get your voice reading the script.", None),
        ]

        for num, title, desc, link in steps:
            link_html = f'<a href="{link}" target="_blank" style="color:#5c5cff;font-size:11px">→ Open site</a>' if link else ""
            st.markdown(f"""
            <div class="content-card" style="display:flex;align-items:flex-start;gap:16px">
                <div style="background:linear-gradient(135deg,#5c5cff,#8b5cf6);border-radius:50%;width:36px;height:36px;display:flex;align-items:center;justify-content:center;font-weight:700;color:white;flex-shrink:0;font-size:14px">{num}</div>
                <div style="flex:1">
                    <div style="font-weight:600;color:#e0e0f0;font-size:14px">{title} {link_html}</div>
                    <div style="color:#666;font-size:12px;margin-top:4px;line-height:1.6">{desc}</div>
                </div>
            </div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 💰 Free vs Paid")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("""<div class="content-card" style="border-color:#10b98140">
            <div style="color:#10b981;font-weight:700;font-size:15px">✅ Free Tier</div>
            <ul style="color:#888;font-size:12px;margin-top:8px;padding-left:16px">
            <li>10,000 characters/month</li>
            <li>Instant Voice Clone (yours)</li>
            <li>3 custom voices stored</li>
            <li>~50 Shorts scripts/month</li>
            </ul>
            </div>""", unsafe_allow_html=True)
        with c2:
            st.markdown("""<div class="content-card" style="border-color:#5c5cff40">
            <div style="color:#a78bfa;font-weight:700;font-size:15px">⚡ Starter ($5/mo)</div>
            <ul style="color:#888;font-size:12px;margin-top:8px;padding-left:16px">
            <li>30,000 characters/month</li>
            <li>Professional Voice Clone</li>
            <li>10 custom voices</li>
            <li>Higher quality audio</li>
            </ul>
            </div>""", unsafe_allow_html=True)

    with tab2:
        st.markdown("### 🎙️ Recording Best Practices")
        tips = [
            ("🔇", "Quiet room", "Record in a wardrobe/closet — clothes absorb echo perfectly. Avoid rooms with hard floors."),
            ("📱", "Device", "A modern smartphone mic is fine. Keep it 20-30cm from your mouth. No need for a professional mic."),
            ("🗣️", "What to say", "Read a mix of content: news article, technical explanation, casual conversation, and emotional story. This trains range."),
            ("⏱️", "Duration", "1 min minimum, 3 mins ideal. Longer = better clone quality. Don't just repeat the same sentences."),
            ("🎚️", "Volume", "Speak at your natural YouTube/content volume — not too loud, not quiet. Consistent volume throughout."),
            ("📝", "Script ideas", "Read your favourite YouTube script, a Wikipedia article, or just talk naturally about your day."),
        ]
        for icon, title, desc in tips:
            st.markdown(f"""
            <div class="content-card" style="display:flex;gap:14px;align-items:flex-start">
                <span style="font-size:24px">{icon}</span>
                <div>
                    <div style="font-weight:600;color:#e0e0f0;font-size:13px">{title}</div>
                    <div style="color:#666;font-size:12px;margin-top:3px">{desc}</div>
                </div>
            </div>""", unsafe_allow_html=True)

    with tab3:
        st.markdown("### 🔌 ElevenLabs Python Integration")
        st.markdown("Once you have an API key, use this in your own scripts:")
        st.code("""
import requests, os

ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")  # or hardcode for testing
VOICE_ID = "sTuFDs5r9KT8f6JSiJbq"        # from ElevenLabs dashboard

def text_to_speech(text: str, output_path: str = "output.mp3"):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    headers = {
        "xi-api-key": ELEVEN_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_turbo_v2",   # fastest + free tier
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.85,
            "style": 0.2,
        }
    }
    r = requests.post(url, json=payload, headers=headers)
    with open(output_path, "wb") as f:
        f.write(r.content)
    print(f"Audio saved to {output_path}")
    return output_path

# Usage
text_to_speech("Did you know 90% of creators quit before they go viral?")
""", language="python")

        st.markdown("---")
        st.markdown("### 🔑 Save your ElevenLabs Key")
        el_key = st.text_input("ElevenLabs API Key", type="password", placeholder="sk_...")
        voice_id = st.text_input("Voice ID", placeholder="From ElevenLabs → Voices → your clone → ID")
        if st.button("💾 Save Keys", use_container_width=True):
            if el_key:
                st.session_state["eleven_key"] = el_key
            if voice_id:
                st.session_state["eleven_voice_id"] = voice_id
            st.success("Keys saved for this session!")
