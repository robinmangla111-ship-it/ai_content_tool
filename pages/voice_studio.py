import streamlit as st
import sys, os, base64, requests

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ─────────────────────────────────────────────────────────────────────────────
# ALL Azure Indian voices (English India + Hindi India)
# Source: Microsoft Azure Speech docs + community hub announcements
# ─────────────────────────────────────────────────────────────────────────────

EN_IN_VOICES = {
    # Name (display)           : (voice_id, gender, styles_supported)
    "Neerja — Female (Classic, Expressive)": (
        "en-IN-NeerjaNeural", "Female",
        ["general", "cheerful", "empathetic", "newscast"]
    ),
    "Aarti — Female (Soft, Conversational)": (
        "en-IN-AartiNeural", "Female",
        ["general", "cheerful", "empathetic"]
    ),
    "Meera — Female (Natural)": (
        "en-IN-MeeraNeural", "Female",
        ["general"]
    ),
    "Riya — Female (Young)": (
        "en-IN-RiyaNeural", "Female",
        ["general"]
    ),
    "Ananya — Female": (
        "en-IN-AnanyaNeural", "Female",
        ["general"]
    ),
    "Kavya — Female": (
        "en-IN-KavyaNeural", "Female",
        ["general"]
    ),
    "Prabhat — Male (Classic)": (
        "en-IN-PrabhatNeural", "Male",
        ["general"]
    ),
    "Arjun — Male (Conversational)": (
        "en-IN-ArjunNeural", "Male",
        ["general", "cheerful", "empathetic"]
    ),
    "Rehaan — Male (Newscast)": (
        "en-IN-RehaanNeural", "Male",
        ["general", "newscast"]
    ),
    "Arun — Male": (
        "en-IN-ArunNeural", "Male",
        ["general"]
    ),
    "Vivaan — Male (Young)": (
        "en-IN-VivaanNeural", "Male",
        ["general"]
    ),
}

HI_IN_VOICES = {
    "Swara — Female (Classic, Expressive)": (
        "hi-IN-SwaraNeural", "Female",
        ["general", "cheerful", "empathetic", "newscast"]
    ),
    "Aarti — Female (Soft, Bilingual)": (
        "hi-IN-AartiNeural", "Female",
        ["general", "cheerful", "empathetic"]
    ),
    "Ananya — Female": (
        "hi-IN-AnanyaNeural", "Female",
        ["general"]
    ),
    "Madhur — Male (Classic)": (
        "hi-IN-MadhurNeural", "Male",
        ["general"]
    ),
    "Arjun — Male (Bilingual)": (
        "hi-IN-ArjunNeural", "Male",
        ["general", "cheerful", "empathetic"]
    ),
    "Vivaan — Male (Young)": (
        "hi-IN-VivaanNeural", "Male",
        ["general"]
    ),
}

# ── Style metadata ────────────────────────────────────────────────────────────
# Maps style key → (display label, description)
STYLE_META = {
    "general":       ("🗣️ Default",         "Natural conversational speech"),
    "cheerful":      ("😊 Cheerful",         "Upbeat, positive, energetic"),
    "empathetic":    ("💙 Empathetic",        "Warm, caring, emotional"),
    "newscast":      ("📰 Newscast",          "Clear, authoritative, broadcast style"),
    "excited":       ("🔥 Excited",           "High energy, enthusiastic"),
    "friendly":      ("👋 Friendly",          "Casual, warm, approachable"),
    "hopeful":       ("🌅 Hopeful",           "Optimistic, uplifting"),
    "sad":           ("😢 Sad",              "Slow, melancholic"),
    "whispering":    ("🤫 Whisper",           "Soft, intimate, secretive"),
    "shouting":      ("📢 Shouting",          "Loud, high energy"),
    "advertisement_upbeat": ("📣 Ad Upbeat", "Energetic marketing style"),
    "poetry-reading":("🎵 Poetry/Lyrical",   "Rhythmic, expressive, verse style"),
    "chat":          ("💬 Chat",             "Casual, informal, like texting aloud"),
    "customerservice": ("🎧 Professional",   "Clear, helpful, formal"),
    "narration-professional": ("📖 Narration", "Documentary / storytelling narration"),
    "documentary-narration": ("🎬 Documentary","Deep, informative narration"),
    "sports-commentary": ("⚽ Sports",       "Fast, exciting commentary"),
    "livecommercial": ("🛍️ Live Commerce",  "Energetic product showcase"),
}

# ── YouTube content presets ───────────────────────────────────────────────────
YT_PRESETS = {
    "🎬 YouTube Shorts Hook": {
        "style":         "excited",
        "rate":          1.1,
        "pitch":         2,
        "style_degree":  1.5,
        "description":   "Fast, punchy, grabs attention in first 3 seconds",
        "ssml_extras":   "",
    },
    "📖 Storytelling / Narration": {
        "style":         "narration-professional",
        "rate":          0.95,
        "pitch":         -1,
        "style_degree":  1.2,
        "description":   "Calm, engaging, like a YouTube documentary",
        "ssml_extras":   "",
    },
    "😊 Motivational / Inspiring": {
        "style":         "hopeful",
        "rate":          1.0,
        "pitch":         1,
        "style_degree":  1.5,
        "description":   "Positive, uplifting, inspirational content",
        "ssml_extras":   "",
    },
    "📰 News / Educational": {
        "style":         "newscast",
        "rate":          1.05,
        "pitch":         0,
        "style_degree":  1.0,
        "description":   "Clear and authoritative, great for facts and news",
        "ssml_extras":   "",
    },
    "😂 Casual / Funny": {
        "style":         "cheerful",
        "rate":          1.1,
        "pitch":         3,
        "style_degree":  1.8,
        "description":   "Fun, upbeat, casual — entertainment content",
        "ssml_extras":   "",
    },
    "🤫 Intimate / Whisper": {
        "style":         "whispering",
        "rate":          0.9,
        "pitch":         -2,
        "style_degree":  1.0,
        "description":   "ASMR style, secrets, close conversation",
        "ssml_extras":   "",
    },
    "🎵 Rhyme / Lyrical": {
        "style":         "poetry-reading",
        "rate":          0.9,
        "pitch":         2,
        "style_degree":  2.0,
        "description":   "Musical rhythm, verse-like delivery for poems/jingles",
        "ssml_extras":   "",
    },
    "📣 Ad / Promo": {
        "style":         "advertisement_upbeat",
        "rate":          1.05,
        "pitch":         2,
        "style_degree":  1.5,
        "description":   "High energy product/brand promotion",
        "ssml_extras":   "",
    },
    "🎧 Professional / Tutorial": {
        "style":         "customerservice",
        "rate":          1.0,
        "pitch":         0,
        "style_degree":  1.0,
        "description":   "Clear, step-by-step tutorial / how-to content",
        "ssml_extras":   "",
    },
    "⚽ Sports / Energetic": {
        "style":         "sports-commentary",
        "rate":          1.15,
        "pitch":         3,
        "style_degree":  2.0,
        "description":   "High energy sports commentary style",
        "ssml_extras":   "",
    },
    "✏️ Custom (manual)": {
        "style":         "general",
        "rate":          1.0,
        "pitch":         0,
        "style_degree":  1.0,
        "description":   "Set every parameter manually",
        "ssml_extras":   "",
    },
}


# ── Key helpers ───────────────────────────────────────────────────────────────

def _get_secret(session_key, secret_key, env_key):
    v = st.session_state.get(session_key, "").strip()
    if v: return v
    try:
        v = str(st.secrets.get(secret_key, "")).strip()
        if v: return v
    except Exception:
        pass
    return os.getenv(env_key, "").strip()

def _azure_key():    return _get_secret("azure_tts_key", "AZURE_TTS_KEY", "AZURE_TTS_KEY")
def _azure_region(): return _get_secret("azure_tts_region", "AZURE_TTS_REGION", "AZURE_TTS_REGION") or "eastus"


# ── Azure API ─────────────────────────────────────────────────────────────────

def _build_ssml(text, voice_id, lang, style, style_degree, rate, pitch):
    """Build SSML with style, prosody and natural speech enhancements."""
    rate_str  = f"{int((rate - 1) * 100):+d}%"
    pitch_str = f"{int(pitch):+d}Hz"

    if style and style != "general":
        style_block = f"""<mstts:express-as style="{style}" styledegree="{style_degree:.1f}">"""
        style_close = "</mstts:express-as>"
    else:
        style_block = ""
        style_close = ""

    return f"""<speak version='1.0'
    xmlns='http://www.w3.org/2001/10/synthesis'
    xmlns:mstts='http://www.w3.org/2001/mstts'
    xml:lang='{lang}'>
  <voice name='{voice_id}'>
    <mstts:silence type="Sentenceboundary" value="80ms"/>
    <prosody rate='{rate_str}' pitch='{pitch_str}'>
      {style_block}
        {text}
      {style_close}
    </prosody>
  </voice>
</speak>"""


def azure_tts(text, voice_id, lang, style, style_degree, rate, pitch) -> bytes | None:
    key    = _azure_key()
    region = _azure_region()
    ssml   = _build_ssml(text, voice_id, lang, style, style_degree, rate, pitch)

    url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-24khz-160kbitrate-mono-mp3",
        "User-Agent": "ContentAIStudio",
    }
    try:
        r = requests.post(url, data=ssml.encode("utf-8"), headers=headers, timeout=40)
        if r.status_code == 401:
            st.error("❌ Azure key invalid (401). Check your key and region below.")
            return None
        if r.status_code == 400:
            # style not supported on this voice — retry without style
            st.warning(f"⚠️ Style '{style}' not supported on this voice — retrying without style...")
            ssml2 = _build_ssml(text, voice_id, lang, "general", 1.0, rate, pitch)
            r2 = requests.post(url, data=ssml2.encode("utf-8"), headers=headers, timeout=40)
            if r2.status_code == 200:
                return r2.content
            st.error(f"❌ Azure error: {r.text[:300]}")
            return None
        r.raise_for_status()
        return r.content
    except Exception as e:
        st.error(f"❌ Error: {e}")
        return None


def azure_test_key(key, region) -> tuple[bool, str]:
    url = f"https://{region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
    try:
        r = requests.post(url, headers={"Ocp-Apim-Subscription-Key": key}, timeout=8)
        if r.status_code == 200:   return True,  "✅ Key valid!"
        if r.status_code == 401:   return False, "❌ 401 — Invalid key."
        if r.status_code == 403:   return False, "❌ 403 — Wrong region, try 'eastus' or 'centralindia'."
        return False, f"❌ HTTP {r.status_code}"
    except Exception as e:
        return False, f"❌ {e}"


def audio_html(audio_bytes: bytes) -> str:
    b64 = base64.b64encode(audio_bytes).decode()
    return (f'<audio controls style="width:100%;margin-top:8px;border-radius:8px">'
            f'<source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>')


# ── Page ──────────────────────────────────────────────────────────────────────

def render():
    st.markdown("# 🎙️ Voice Studio")
    st.markdown("All Indian English + Hindi voices · YouTube-optimised styles · 500k chars/month free")
    st.markdown("---")

    # ── Key config (collapsible) ──────────────────────────────────────────────
    with st.expander("🔑 Azure API Key Settings", expanded=not _azure_key()):
        c1, c2, c3 = st.columns([3, 1.2, 1])
        with c1:
            key_val = st.text_input(
                "Azure Speech Key",
                type="password",
                value=st.session_state.get("azure_tts_key", ""),
                placeholder="Key 1 from Azure portal → Speech → Keys & Endpoint",
            )
            if key_val:
                st.session_state["azure_tts_key"] = key_val.strip()
        with c2:
            region_val = st.text_input(
                "Region",
                value=st.session_state.get("azure_tts_region", "centralindia"),
                placeholder="centralindia",
                help="Use 'centralindia' for lowest latency from India",
            )
            if region_val:
                st.session_state["azure_tts_region"] = region_val.strip()
        with c3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔍 Test Key", use_container_width=True):
                k = _azure_key(); r = _azure_region()
                ok, msg = azure_test_key(k, r)
                st.success(msg) if ok else st.error(msg)

        if not _azure_key():
            st.info("**Get free Azure key:** portal.azure.com → Search 'Speech' → Create → Free F0 tier → Keys & Endpoint → copy Key 1")

    if not _azure_key():
        st.warning("⚠️ Add your Azure key above to generate audio.")
        return

    st.markdown("---")

    # ── Main layout ───────────────────────────────────────────────────────────
    col_l, col_r = st.columns([1, 1], gap="large")

    with col_l:
        # Language + voice
        lang_tab = st.radio(
            "Language",
            ["🇮🇳 English (India)", "🇮🇳 Hindi (India)"],
            horizontal=True,
        )
        is_hindi = "Hindi" in lang_tab
        voice_dict = HI_IN_VOICES if is_hindi else EN_IN_VOICES
        lang_code  = "hi-IN" if is_hindi else "en-IN"

        voice_label = st.selectbox(
            "Voice",
            list(voice_dict.keys()),
            help="All are Azure Neural voices — natural, human-like quality",
        )
        voice_id, gender, supported_styles = voice_dict[voice_label]
        st.caption(f"Voice ID: `{voice_id}` · {gender}")

        st.markdown("---")

        # Preset selector
        preset_name = st.selectbox(
            "🎬 YouTube Style Preset",
            list(YT_PRESETS.keys()),
            help="Pick a preset that matches your video type — it auto-fills speed, pitch and style",
        )
        preset = YT_PRESETS[preset_name]
        st.caption(f"_{preset['description']}_")

        is_custom = preset_name == "✏️ Custom (manual)"

        # Style picker — filtered to what this voice supports
        all_available_styles = supported_styles + [
            s for s in ["excited", "friendly", "hopeful", "sad", "whispering",
                         "shouting", "advertisement_upbeat", "poetry-reading",
                         "chat", "customerservice", "narration-professional",
                         "documentary-narration", "sports-commentary", "livecommercial"]
            if s not in supported_styles
        ]

        if is_custom:
            style_options = {STYLE_META.get(s, (s, ""))[0]: s for s in all_available_styles}
            style_label   = st.selectbox("Speaking Style", list(style_options.keys()))
            chosen_style  = style_options[style_label]
            style_degree  = st.slider("Style Intensity", 0.5, 2.0, 1.0, 0.1,
                                      help="Higher = more exaggerated style")
            c1, c2 = st.columns(2)
            with c1: rate  = st.slider("Speed",  0.5, 2.0, 1.0, 0.05)
            with c2: pitch = st.slider("Pitch (Hz)", -20, 20, 0, 1)
        else:
            chosen_style = preset["style"]
            style_degree = preset["style_degree"]
            rate         = preset["rate"]
            pitch        = preset["pitch"]

            # Show values (read-only display)
            s_label = STYLE_META.get(chosen_style, (chosen_style, ""))[0]
            st.markdown(
                f"Style: **{s_label}** · Speed: `{rate}x` · "
                f"Pitch: `{pitch:+d}Hz` · Intensity: `{style_degree}`"
            )

        st.markdown("---")

        # Script text
        text = st.text_area(
            "📝 Script / Text",
            value=st.session_state.get("last_script", ""),
            height=200,
            placeholder="Paste your script here, or generate one in Script Generator...\n\nTip: For rhymes/poetry, write each line on a new line.",
        )
        char_count = len(text)
        c = "red" if char_count > 480000 else "orange" if char_count > 100000 else "green"
        st.markdown(f'<p style="font-size:12px;color:{c}">{char_count:,} chars · 500,000 free/month</p>',
                    unsafe_allow_html=True)

        gen_btn = st.button("🎙️ Generate Audio", use_container_width=True,
                            type="primary", disabled=not text.strip())

    # ── Output column ─────────────────────────────────────────────────────────
    with col_r:
        st.markdown("### 🔊 Output")

        if gen_btn and text.strip():
            with st.spinner(f"Generating with {voice_label.split('—')[0].strip()} · {preset_name}..."):
                audio_bytes = azure_tts(
                    text, voice_id, lang_code,
                    chosen_style, style_degree, rate, pitch,
                )
            if audio_bytes:
                st.session_state["last_audio"]       = audio_bytes
                st.session_state["last_audio_meta"]  = {
                    "voice": voice_label, "style": preset_name,
                    "lang": lang_code,
                }
                st.success(f"✅ Done! {len(audio_bytes)/1024:.0f} KB")

        audio = st.session_state.get("last_audio")
        if audio:
            meta = st.session_state.get("last_audio_meta", {})
            st.markdown(f"**{meta.get('voice','')}** · {meta.get('style','')}")
            st.markdown(audio_html(audio), unsafe_allow_html=True)
            st.download_button(
                "📥 Download MP3",
                data=audio,
                file_name="voiceover.mp3",
                mime="audio/mp3",
                use_container_width=True,
            )

            st.markdown("---")
            st.markdown("### ▶️ Next step: Avatar video")
            st.markdown("""
Download MP3 above → upload to a free avatar tool:

🥇 **[Vidnoz](https://app.vidnoz.com)** — 60 min/month free  
🥈 **[D-ID Studio](https://studio.d-id.com)** — 14-day trial  
🥉 **[HeyGen](https://app.heygen.com)** — 3 free videos  

Then: **[CapCut](https://www.capcut.com)** → Auto Captions → Export 1080×1920 → Upload!
            """)
        else:
            st.markdown("""
            <div style="border:0.5px solid var(--color-border-tertiary);border-radius:12px;
                        padding:60px 20px;text-align:center">
                <div style="font-size:48px">🎙️</div>
                <div style="color:var(--color-text-secondary);margin-top:12px;font-size:14px">
                    Pick a voice, choose a YouTube style, paste script → Generate
                </div>
            </div>""", unsafe_allow_html=True)

    # ── Style guide ───────────────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("📖 Style guide — which preset for which video?"):
        cols = st.columns(3)
        for i, (name, preset) in enumerate(YT_PRESETS.items()):
            if name == "✏️ Custom (manual)":
                continue
            with cols[i % 3]:
                st.markdown(f"**{name}**")
                st.caption(preset["description"])
                st.markdown("")

    # ── SSML tips ─────────────────────────────────────────────────────────────
    with st.expander("⚡ Pro tips — make audio more natural"):
        st.markdown("""
**Add natural pauses** — insert a blank line or `...` between sentences. Azure adds a natural pause automatically.

**For Hindi+English mixed (Hinglish)** — just write it mixed, Aarti and Arjun voices handle code-switching automatically:
> "Bhai, ye AI tool literally sabka kaam kar deta hai in just 60 seconds!"

**For rhymes/poetry** (Lyrical preset) — write each line separately:
```
Sapno ki duniya mein,
Ek nayi kahani hai,
AI ke saath humari,
Ye naye kal ki nishani hai.
```

**For YouTube Shorts hooks** — keep it under 15 words, start with a question or shocking stat:
> "Kya tum jaante ho? 90% creators pehle saal quit kar dete hain."

**Boost expressiveness** — use the Style Intensity slider. 2.0 = very dramatic, 1.0 = subtle.
        """)
