import streamlit as st
import sys, os, base64, requests, json

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ─────────────────────────────────────────────────────────────────────────────
# PROVIDER: Microsoft Azure Text-to-Speech
#   Free tier: 500,000 chars/month FOREVER (no expiry, no credit card)
#   API key:   console.azure.com → Speech → Keys & Endpoint
#   Voices:    400+ neural voices, very natural quality
#
# FALLBACK: OpenAI TTS
#   Uses your existing Groq/OpenAI key if Azure not configured
#   6 voices (alloy, echo, fable, onyx, nova, shimmer)
# ─────────────────────────────────────────────────────────────────────────────

# ── Curated Azure voice list (best English + popular accents) ─────────────────
AZURE_VOICES = {
    # English - Male
    "Andrew (EN-US, Natural Male)":     ("en-US", "en-US-AndrewNeural"),
    "Brian (EN-US, Calm Male)":         ("en-US", "en-US-BrianNeural"),
    "Ryan (EN-GB, British Male)":       ("en-GB", "en-GB-RyanNeural"),
    "Liam (EN-CA, Canadian Male)":      ("en-CA", "en-CA-LiamNeural"),
    "William (EN-AU, Australian Male)": ("en-AU", "en-AU-WilliamNeural"),
    # English - Female
    "Emma (EN-US, Natural Female)":     ("en-US", "en-US-EmmaNeural"),
    "Jenny (EN-US, Friendly Female)":   ("en-US", "en-US-JennyNeural"),
    "Aria (EN-US, Expressive Female)":  ("en-US", "en-US-AriaNeural"),
    "Sonia (EN-GB, British Female)":    ("en-GB", "en-GB-SoniaNeural"),
    "Natasha (EN-AU, Australian F)":    ("en-AU", "en-AU-NatashaNeural"),
    # Indian English
    "Neerja (EN-IN, Indian Female)":    ("en-IN", "en-IN-NeerjaNeural"),
    "Prabhat (EN-IN, Indian Male)":     ("en-IN", "en-IN-PrabhatNeural"),
    # Hindi
    "Madhur (HI-IN, Hindi Male)":       ("hi-IN", "hi-IN-MadhurNeural"),
    "Swara (HI-IN, Hindi Female)":      ("hi-IN", "hi-IN-SwaraNeural"),
    # Other languages
    "Diego (ES-US, Spanish Male)":      ("es-US", "es-US-AlonsoNeural"),
    "Dena (FR-FR, French Female)":      ("fr-FR", "fr-FR-DeniseNeural"),
    "Conrad (DE-DE, German Male)":      ("de-DE", "de-DE-ConradNeural"),
}

OPENAI_VOICES = {
    "Alloy (neutral)":  "alloy",
    "Echo (male)":      "echo",
    "Fable (british)":  "fable",
    "Onyx (deep male)": "onyx",
    "Nova (female)":    "nova",
    "Shimmer (female)": "shimmer",
}


# ── Key resolution ────────────────────────────────────────────────────────────

def _get(session_key: str, secret_key: str, env_key: str) -> str:
    v = st.session_state.get(session_key, "").strip()
    if v: return v
    try:
        v = str(st.secrets.get(secret_key, "")).strip()
        if v: return v
    except Exception:
        pass
    return os.getenv(env_key, "").strip()


def _azure_key() -> str:
    return _get("azure_tts_key", "AZURE_TTS_KEY", "AZURE_TTS_KEY")

def _azure_region() -> str:
    return _get("azure_tts_region", "AZURE_TTS_REGION", "AZURE_TTS_REGION") or "eastus"

def _openai_key() -> str:
    return _get("api_key", "OPENAI_API_KEY", "OPENAI_API_KEY")


# ── Azure TTS ─────────────────────────────────────────────────────────────────

def azure_tts(text: str, voice_name: str, lang: str, rate: float, pitch: float) -> bytes | None:
    """Call Azure Cognitive Services TTS. Returns MP3 bytes."""
    key    = _azure_key()
    region = _azure_region()

    # Build SSML
    rate_str  = f"{int((rate-1)*100):+d}%"
    pitch_str = f"{int(pitch):+d}Hz"
    ssml = f"""<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='{lang}'>
  <voice name='{voice_name}'>
    <prosody rate='{rate_str}' pitch='{pitch_str}'>
      {text}
    </prosody>
  </voice>
</speak>"""

    url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-24khz-96kbitrate-mono-mp3",
        "User-Agent": "ContentAIStudio",
    }
    try:
        r = requests.post(url, data=ssml.encode("utf-8"), headers=headers, timeout=30)
        if r.status_code == 401:
            st.error("❌ Azure key invalid (401). Check your key and region.")
            return None
        if r.status_code == 400:
            st.error(f"❌ Azure bad request: {r.text[:300]}")
            return None
        r.raise_for_status()
        return r.content
    except Exception as e:
        st.error(f"❌ Azure TTS error: {e}")
        return None


def azure_check_key(key: str, region: str) -> tuple[bool, str]:
    """Quick validation by hitting the token endpoint."""
    url = f"https://{region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
    try:
        r = requests.post(url, headers={"Ocp-Apim-Subscription-Key": key}, timeout=8)
        if r.status_code == 200:
            return True, "✅ Azure key valid!"
        elif r.status_code == 401:
            return False, "❌ 401 — Invalid key. Double check you copied the correct key."
        elif r.status_code == 403:
            return False, "❌ 403 — Key valid but wrong region. Try 'eastus', 'westeurope', etc."
        else:
            return False, f"❌ HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, f"❌ Connection error: {e}"


# ── OpenAI TTS fallback ───────────────────────────────────────────────────────

def openai_tts(text: str, voice: str, model: str) -> bytes | None:
    key = _openai_key()
    if not key:
        st.error("No OpenAI key found either. Add at least one key above.")
        return None
    try:
        r = requests.post(
            "https://api.openai.com/v1/audio/speech",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model, "input": text, "voice": voice, "response_format": "mp3"},
            timeout=60,
        )
        if r.status_code == 401:
            st.error("❌ OpenAI key invalid (401).")
            return None
        r.raise_for_status()
        return r.content
    except Exception as e:
        st.error(f"❌ OpenAI TTS error: {e}")
        return None


# ── Audio player ──────────────────────────────────────────────────────────────

def audio_html(audio_bytes: bytes) -> str:
    b64 = base64.b64encode(audio_bytes).decode()
    return f"""<audio controls style="width:100%;margin-top:8px;border-radius:8px">
        <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
    </audio>"""


# ── Page ──────────────────────────────────────────────────────────────────────

def render():
    st.markdown("# 🎙️ Voice Studio")
    st.markdown("Convert your script to audio — **500,000 chars/month free** via Azure Neural TTS.")
    st.markdown("---")

    # ── Provider tabs ─────────────────────────────────────────────────────────
    tab_azure, tab_openai = st.tabs(["☁️ Azure TTS (recommended — 500k free/mo)", "🤖 OpenAI TTS (uses your existing key)"])

    with tab_azure:
        _render_azure_setup()

    with tab_openai:
        _render_openai_setup()

    st.markdown("---")

    # ── Main generator (shared) ───────────────────────────────────────────────
    provider = st.session_state.get("tts_provider", "azure")
    _render_generator(provider)


def _render_azure_setup():
    st.markdown("### 🔑 Azure Speech key setup")
    st.info("""
**Get your free Azure key (takes 3 minutes):**
1. Go to [portal.azure.com](https://portal.azure.com) → Sign up free (no credit card for free tier)
2. Search **"Speech"** → Create → Choose **Free F0 tier** → Create
3. Go to your Speech resource → **Keys and Endpoint**
4. Copy **Key 1** and your **Region** (e.g. `eastus`)
    """)

    c1, c2 = st.columns([3, 1])
    with c1:
        key = st.text_input(
            "Azure Speech Key",
            type="password",
            value=st.session_state.get("azure_tts_key", ""),
            placeholder="Paste Key 1 from Azure portal...",
        )
        if key:
            st.session_state["azure_tts_key"] = key.strip()

    with c2:
        region = st.text_input(
            "Region",
            value=st.session_state.get("azure_tts_region", "eastus"),
            placeholder="eastus",
        )
        if region:
            st.session_state["azure_tts_region"] = region.strip()

    col_btn, col_status = st.columns([1, 2])
    with col_btn:
        if st.button("🔍 Test Azure Key", use_container_width=True):
            k = st.session_state.get("azure_tts_key", "")
            r = st.session_state.get("azure_tts_region", "eastus")
            if not k:
                st.error("Paste your key first.")
            else:
                with st.spinner("Testing..."):
                    ok, msg = azure_check_key(k, r)
                if ok:
                    st.session_state["tts_provider"] = "azure"
                    col_status.success(msg)
                else:
                    col_status.error(msg)

    if st.session_state.get("tts_provider") == "azure":
        st.success("✅ Using Azure TTS — 500k chars/month free")
    else:
        if st.button("➡️ Use Azure TTS anyway", use_container_width=False):
            st.session_state["tts_provider"] = "azure"
            st.rerun()


def _render_openai_setup():
    st.markdown("### 🤖 OpenAI TTS")
    st.info("Uses your existing OpenAI API key from the sidebar. 6 high-quality voices. Not free — costs ~$0.015/1k chars.")
    existing = _openai_key()
    if existing:
        st.success(f"✅ OpenAI key found (`{existing[:8]}...`)")
        if st.button("Use OpenAI TTS"):
            st.session_state["tts_provider"] = "openai"
            st.rerun()
    else:
        st.warning("No OpenAI key found. Add it in the sidebar under API Keys.")


def _render_generator(provider: str):
    st.markdown("### 🎛️ Generate Audio")

    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        # Voice selector
        if provider == "azure":
            st.markdown("**Voice** (400+ neural voices)")
            voice_label = st.selectbox(
                "Select voice",
                list(AZURE_VOICES.keys()),
                index=0,
                label_visibility="collapsed",
            )
            lang, voice_name = AZURE_VOICES[voice_label]

            c1, c2 = st.columns(2)
            with c1:
                rate = st.slider("Speed", 0.5, 2.0, 1.0, 0.1,
                                 help="1.0 = normal speed")
            with c2:
                pitch = st.slider("Pitch (Hz)", -20, 20, 0, 1,
                                  help="0 = default pitch")
        else:
            st.markdown("**Voice**")
            voice_label = st.selectbox("Select voice", list(OPENAI_VOICES.keys()),
                                       label_visibility="collapsed")
            voice_name = OPENAI_VOICES[voice_label]
            oai_model = st.selectbox("Model", ["tts-1", "tts-1-hd"],
                                     help="tts-1 = fast, tts-1-hd = higher quality")
            lang = None
            rate = pitch = None

        st.markdown("---")
        st.markdown("**Script text**")

        text = st.text_area(
            "Text",
            value=st.session_state.get("last_script", ""),
            height=220,
            placeholder="Paste your script or generate one in Script Generator first...",
            label_visibility="collapsed",
        )

        char_count = len(text)
        remaining = 500000 - char_count if provider == "azure" else None
        color = "red" if char_count > 480000 else "orange" if char_count > 400000 else "green"
        st.markdown(
            f'<p style="font-size:12px;color:{color}">'
            f"Characters: {char_count:,}"
            + (f" / 500,000 free" if provider == "azure" else "")
            + "</p>",
            unsafe_allow_html=True,
        )

        gen_btn = st.button(
            "🎙️ Generate Audio",
            use_container_width=True,
            type="primary",
            disabled=not text.strip(),
        )

    with col_right:
        st.markdown("**Output**")

        if gen_btn and text.strip():
            with st.spinner("Generating audio..."):
                if provider == "azure":
                    audio_bytes = azure_tts(text, voice_name, lang, rate, pitch)
                else:
                    audio_bytes = openai_tts(text, voice_name, oai_model)

            if audio_bytes:
                st.session_state["last_audio"] = audio_bytes
                st.session_state["last_audio_label"] = voice_label
                st.success(f"✅ {len(audio_bytes)/1024:.0f} KB generated!")

        audio = st.session_state.get("last_audio")
        if audio:
            lbl = st.session_state.get("last_audio_label", "")
            st.markdown(f"**Voice:** {lbl}")
            st.markdown(audio_html(audio), unsafe_allow_html=True)
            st.download_button(
                "📥 Download MP3",
                data=audio,
                file_name="voiceover.mp3",
                mime="audio/mp3",
                use_container_width=True,
            )

            st.markdown("---")
            st.markdown("### ▶️ Next: Avatar video")
            st.markdown("""
Download your MP3, then upload to a free avatar tool:

🥇 **[Vidnoz](https://app.vidnoz.com)** — 60 min/month free  
🥈 **[D-ID](https://studio.d-id.com)** — 14-day free trial  
🥉 **[HeyGen](https://app.heygen.com)** — 3 free videos  

Then add captions in **[CapCut](https://www.capcut.com)** → export 1080×1920 → publish!
            """)
        else:
            st.markdown("""
            <div style="border:0.5px solid var(--color-border-tertiary);border-radius:12px;
                        padding:60px 20px;text-align:center">
                <div style="font-size:48px">🎙️</div>
                <div style="color:var(--color-text-secondary);margin-top:12px;font-size:14px">
                    Select a voice, paste your script, hit Generate
                </div>
            </div>""", unsafe_allow_html=True)
