import streamlit as st
import sys, os, base64, requests

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ── ElevenLabs API helpers ────────────────────────────────────────────────────

def _el_key() -> str:
    """Resolve ElevenLabs API key from session → secrets → env."""
    k = st.session_state.get("eleven_key", "")
    if k:
        return k
    try:
        k = st.secrets.get("ELEVEN_API_KEY", "")
        if k:
            return k
    except Exception:
        pass
    return os.getenv("ELEVEN_API_KEY", "")


def _headers() -> dict:
    return {"xi-api-key": _el_key(), "Content-Type": "application/json"}


def fetch_voices() -> list[dict]:
    """Fetch all voices from the user's ElevenLabs account."""
    try:
        r = requests.get(
            "https://api.elevenlabs.io/v1/voices",
            headers={"xi-api-key": _el_key()},
            timeout=10,
        )
        if r.status_code == 401:
            return []
        r.raise_for_status()
        voices = r.json().get("voices", [])
        # Sort: cloned first, then premade
        return sorted(voices, key=lambda v: (
            0 if v.get("category") in ("cloned", "professional") else 1,
            v.get("name", ""),
        ))
    except Exception as e:
        st.error(f"Failed to fetch voices: {e}")
        return []


def generate_audio(text: str, voice_id: str, model: str, stability: float, similarity: float) -> bytes | None:
    """Call ElevenLabs TTS API and return raw MP3 bytes."""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    payload = {
        "text": text,
        "model_id": model,
        "voice_settings": {
            "stability": round(stability, 2),
            "similarity_boost": round(similarity, 2),
            "style": 0.2,
            "use_speaker_boost": True,
        },
        "output_format": "mp3_44100_128",
    }
    try:
        r = requests.post(url, json=payload, headers=_headers(), timeout=60)
        if r.status_code == 401:
            st.error("❌ Invalid ElevenLabs API key. Check your key in Settings.")
            return None
        if r.status_code == 422:
            st.error(f"❌ API error: {r.json()}")
            return None
        r.raise_for_status()
        return r.content
    except Exception as e:
        st.error(f"❌ Audio generation failed: {e}")
        return None


def audio_player_html(audio_bytes: bytes) -> str:
    """Embed an HTML5 audio player for the MP3 bytes."""
    b64 = base64.b64encode(audio_bytes).decode()
    return f"""
    <audio controls style="width:100%;margin-top:8px;border-radius:8px">
        <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
    </audio>"""


# ── Page ──────────────────────────────────────────────────────────────────────

def render():
    st.markdown("# 🎙️ Voice Studio")
    st.markdown("Generate audio from your script using your ElevenLabs voices.")
    st.markdown("---")

    # ── API key check ─────────────────────────────────────────────────────────
    el_key = _el_key()
    if not el_key:
        st.warning("⚠️ No ElevenLabs API key found.")
        st.markdown("""
        **Add your key in one of two ways:**
        - **Sidebar** → paste it in the API Keys section (Settings page)
        - **Streamlit Secrets** → add `ELEVEN_API_KEY = "your_key"` at share.streamlit.io → ⋮ → Settings → Secrets

        Get a free key at [elevenlabs.io](https://elevenlabs.io) — free tier gives 10,000 characters/month.
        """)
        # Still show the UI so user can enter key inline
        inline_key = st.text_input("Or paste your ElevenLabs key here:", type="password", placeholder="sk_...")
        if inline_key:
            st.session_state["eleven_key"] = inline_key
            st.rerun()
        return

    # ── Fetch voices ──────────────────────────────────────────────────────────
    with st.spinner("Loading your voices from ElevenLabs..."):
        voices = fetch_voices()

    if not voices:
        st.error("❌ Could not load voices. Check your API key is correct.")
        if st.button("🔄 Retry"):
            st.rerun()
        return

    # ── Layout ────────────────────────────────────────────────────────────────
    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.markdown("### 🎛️ Voice Settings")

        # Group voices by category for display
        cloned   = [v for v in voices if v.get("category") in ("cloned", "professional")]
        premade  = [v for v in voices if v.get("category") not in ("cloned", "professional")]

        voice_options = {}
        if cloned:
            for v in cloned:
                label = f"⭐ {v['name']} (your clone)"
                voice_options[label] = v["voice_id"]
        for v in premade:
            label = f"{v['name']} ({v.get('category', 'premade')})"
            voice_options[label] = v["voice_id"]

        selected_label = st.selectbox(
            "Select Voice",
            list(voice_options.keys()),
            help="⭐ = your cloned/professional voices appear first",
        )
        selected_voice_id = voice_options[selected_label]

        # Show preview player if available
        selected_voice_obj = next((v for v in voices if v["voice_id"] == selected_voice_id), None)
        if selected_voice_obj and selected_voice_obj.get("preview_url"):
            st.markdown("**Preview voice:**")
            st.audio(selected_voice_obj["preview_url"])

        st.markdown("---")

        model = st.selectbox(
            "Model",
            options=[
                "eleven_turbo_v2_5",
                "eleven_multilingual_v2",
                "eleven_flash_v2_5",
                "eleven_v3",
            ],
            index=0,
            help="Turbo = fast + high quality (recommended). Flash = ultra fast. Multilingual = 70+ languages. v3 = most expressive.",
        )

        c1, c2 = st.columns(2)
        with c1:
            stability = st.slider(
                "Stability", 0.0, 1.0, 0.5, 0.05,
                help="Higher = more consistent. Lower = more expressive/varied.",
            )
        with c2:
            similarity = st.slider(
                "Similarity", 0.0, 1.0, 0.85, 0.05,
                help="How closely to match the original voice. Keep high for clones.",
            )

        st.markdown("---")
        st.markdown("### 📝 Script Text")

        # Pre-fill from script generator if available
        last_script = st.session_state.get("last_script", "")
        text = st.text_area(
            "Text to convert",
            value=last_script,
            height=220,
            placeholder="Paste your script here, or generate one in the Script Generator first...",
            help="Free tier: 10,000 characters/month",
        )

        char_count = len(text)
        char_color = "red" if char_count > 9000 else "orange" if char_count > 7000 else "green"
        st.markdown(
            f'<p style="font-size:12px;color:{char_color}">'
            f"Characters: {char_count:,} / 10,000 free tier</p>",
            unsafe_allow_html=True,
        )

        generate_btn = st.button(
            "🎙️ Generate Audio",
            use_container_width=True,
            type="primary",
            disabled=(not text.strip()),
        )

    # ── Output ────────────────────────────────────────────────────────────────
    with col_right:
        st.markdown("### 🔊 Generated Audio")

        if generate_btn:
            if not text.strip():
                st.error("Please enter some text first.")
            else:
                with st.spinner(f"Generating audio with **{selected_label}**..."):
                    audio_bytes = generate_audio(
                        text=text,
                        voice_id=selected_voice_id,
                        model=model,
                        stability=stability,
                        similarity=similarity,
                    )

                if audio_bytes:
                    st.session_state["last_audio"] = audio_bytes
                    st.session_state["last_audio_voice"] = selected_label
                    st.success(f"✅ Audio generated! ({len(audio_bytes)/1024:.0f} KB)")

        # Show player if audio exists
        audio_bytes = st.session_state.get("last_audio")
        if audio_bytes:
            voice_label = st.session_state.get("last_audio_voice", "")
            st.markdown(f"**Voice:** {voice_label}")
            st.markdown(audio_player_html(audio_bytes), unsafe_allow_html=True)

            st.download_button(
                "📥 Download MP3",
                data=audio_bytes,
                file_name="voiceover.mp3",
                mime="audio/mp3",
                use_container_width=True,
            )

            st.markdown("---")
            st.markdown("### ▶️ Next Step: Create Avatar Video")
            st.info(
                "Download your MP3 above, then upload it to one of these free avatar tools "
                "to generate a talking-head video lip-synced to your voice:"
            )

            tools = [
                ("🥇", "Vidnoz", "https://app.vidnoz.com", "60 min free/month"),
                ("🥈", "D-ID",   "https://studio.d-id.com", "14-day free trial"),
                ("🥉", "HeyGen", "https://app.heygen.com",  "3 free videos"),
            ]
            for rank, name, url, note in tools:
                st.markdown(
                    f'{rank} **[{name}]({url})** — {note}',
                    unsafe_allow_html=False,
                )

            st.markdown("---")
            st.markdown("### 🎬 After the avatar video is ready")
            st.markdown("""
1. Download the MP4 from your avatar tool
2. Open **[CapCut](https://www.capcut.com)** (free)
3. Import your MP4 → click **Captions → Auto Captions**
4. Export as **1080×1920** (vertical for Shorts/Reels)
5. Upload to YouTube Shorts, Instagram Reels, or TikTok
            """)

        else:
            st.markdown("""
            <div style="border:0.5px solid var(--color-border-tertiary);border-radius:12px;
                        padding:60px 20px;text-align:center;">
                <div style="font-size:48px">🎙️</div>
                <div style="color:var(--color-text-secondary);margin-top:12px;font-size:14px">
                    Select a voice and hit Generate
                </div>
            </div>""", unsafe_allow_html=True)

    # ── Voice list reference ───────────────────────────────────────────────────
    st.markdown("---")
    with st.expander(f"📋 All your voices ({len(voices)} total) — click to see IDs"):
        for v in voices:
            cat   = v.get("category", "unknown")
            icon  = "⭐" if cat in ("cloned", "professional") else "🔊"
            st.markdown(
                f"{icon} **{v['name']}** &nbsp;·&nbsp; "
                f"`{v['voice_id']}` &nbsp;·&nbsp; "
                f"<span style='color:var(--color-text-tertiary);font-size:12px'>{cat}</span>",
                unsafe_allow_html=True,
            )
