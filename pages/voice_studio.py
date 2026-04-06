import streamlit as st
import sys, os, base64, requests

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

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

def _key():    return _get_secret("azure_tts_key",    "AZURE_TTS_KEY",    "AZURE_TTS_KEY")
def _region(): return _get_secret("azure_tts_region", "AZURE_TTS_REGION", "AZURE_TTS_REGION") or "centralindia"

# ── Fetch voices + styles live from Azure ─────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_indian_voices(key: str, region: str) -> list[dict]:
    """
    Calls Azure /voices/list and returns only en-IN and hi-IN voices.
    Each dict: { name, short_name, gender, locale, styles[] }
    Cached for 1 hour.
    """
    url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/voices/list"
    try:
        r = requests.get(url, headers={"Ocp-Apim-Subscription-Key": key}, timeout=10)
        if r.status_code == 401:
            return []
        r.raise_for_status()
        all_voices = r.json()
    except Exception as e:
        st.error(f"Failed to fetch voices: {e}")
        return []

    indian = []
    for v in all_voices:
        locale = v.get("Locale", "")
        if locale not in ("en-IN", "hi-IN"):
            continue
        styles = v.get("StyleList", [])
        # Normalise style names to lowercase
        styles = [s.lower() for s in styles]
        # Always include "general" as the default
        if "general" not in styles:
            styles = ["general"] + styles
        indian.append({
            "name":       v.get("LocalName", v.get("ShortName", "")),
            "short_name": v.get("ShortName", ""),
            "gender":     v.get("Gender", ""),
            "locale":     locale,
            "styles":     styles,
        })

    # Sort: en-IN first, then hi-IN; within each, alphabetical by name
    indian.sort(key=lambda v: (0 if v["locale"] == "en-IN" else 1, v["name"]))
    return indian


def azure_test_key(key, region) -> tuple[bool, str]:
    url = f"https://{region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
    try:
        r = requests.post(url, headers={"Ocp-Apim-Subscription-Key": key}, timeout=8)
        if r.status_code == 200:
            return True,  "✅ Key valid!"
        if r.status_code == 401:
            return False, "❌ 401 — Invalid key."
        if r.status_code == 403:
            return False, "❌ 403 — Wrong region. Try 'centralindia' or 'eastus'."
        return False, f"❌ HTTP {r.status_code}"
    except Exception as e:
        return False, f"❌ {e}"


# ── YouTube style presets ─────────────────────────────────────────────────────
# Each preset maps to a style NAME that Azure uses.
# If the selected voice doesn't support it, we fall back to "general"
# with prosody adjustments to approximate the feel.

YT_PRESETS = {
    "🎬 YouTube Shorts Hook":       {"style": "excited",               "rate": 1.1,  "pitch": 3,  "degree": 1.8, "desc": "Fast, punchy — grabs attention in 3 seconds"},
    "📖 Storytelling / Narration":  {"style": "narration-professional", "rate": 0.95, "pitch": -1, "degree": 1.2, "desc": "Calm, engaging — documentary / long-form"},
    "😊 Motivational":              {"style": "hopeful",                "rate": 1.0,  "pitch": 2,  "degree": 1.5, "desc": "Positive, uplifting, inspiring content"},
    "📰 News / Educational":        {"style": "newscast",               "rate": 1.05, "pitch": 0,  "degree": 1.0, "desc": "Clear, authoritative broadcast style"},
    "😂 Cheerful / Funny":          {"style": "cheerful",               "rate": 1.1,  "pitch": 3,  "degree": 1.8, "desc": "Fun, upbeat — entertainment content"},
    "💙 Empathetic / Emotional":    {"style": "empathetic",             "rate": 0.95, "pitch": -1, "degree": 1.5, "desc": "Warm, caring — emotional storytelling"},
    "🤫 Whisper / ASMR":            {"style": "whispering",             "rate": 0.9,  "pitch": -2, "degree": 1.0, "desc": "Soft, intimate — ASMR or secret reveals"},
    "🎵 Rhyme / Lyrical":           {"style": "poetry-reading",         "rate": 0.88, "pitch": 2,  "degree": 2.0, "desc": "Rhythmic, musical — poems, jingles, songs"},
    "📣 Ad / Promo":                {"style": "advertisement_upbeat",   "rate": 1.05, "pitch": 2,  "degree": 1.5, "desc": "High energy product promotion"},
    "🎧 Tutorial / How-to":         {"style": "customerservice",        "rate": 1.0,  "pitch": 0,  "degree": 1.0, "desc": "Clear, step-by-step instructions"},
    "⚽ Sports / High Energy":      {"style": "sports-commentary",      "rate": 1.15, "pitch": 3,  "degree": 2.0, "desc": "Fast, exciting commentary"},
    "💬 Casual / Chat":             {"style": "chat",                   "rate": 1.05, "pitch": 1,  "degree": 1.3, "desc": "Relaxed, conversational, like talking to a friend"},
    "✏️ Custom (manual)":           {"style": "general",                "rate": 1.0,  "pitch": 0,  "degree": 1.0, "desc": "Set every parameter manually"},
}

# Friendly display names for styles returned by Azure API
STYLE_LABELS = {
    "general":                  "🗣️ Default",
    "cheerful":                 "😊 Cheerful",
    "empathetic":               "💙 Empathetic",
    "newscast":                 "📰 Newscast",
    "excited":                  "🔥 Excited",
    "friendly":                 "👋 Friendly",
    "hopeful":                  "🌅 Hopeful",
    "sad":                      "😢 Sad",
    "whispering":               "🤫 Whisper",
    "shouting":                 "📢 Shouting",
    "advertisement_upbeat":     "📣 Ad Upbeat",
    "poetry-reading":           "🎵 Poetry / Lyrical",
    "chat":                     "💬 Chat",
    "customerservice":          "🎧 Professional",
    "narration-professional":   "📖 Narration",
    "documentary-narration":    "🎬 Documentary",
    "sports-commentary":        "⚽ Sports",
    "livecommercial":           "🛍️ Live Commerce",
    "assistant":                "🤖 Assistant",
    "calm":                     "😌 Calm",
    "disgruntled":              "😤 Disgruntled",
    "fearful":                  "😨 Fearful",
    "gentle":                   "🌸 Gentle",
    "lyrical":                  "🎶 Lyrical",
    "serious":                  "🧐 Serious",
    "terrified":                "😱 Terrified",
    "unfriendly":               "😒 Unfriendly",
    "angry":                    "😠 Angry",
}


# ── SSML builder ──────────────────────────────────────────────────────────────

def _build_ssml(text, voice_id, lang, style, degree, rate, pitch):
    rate_str  = f"{int((rate - 1) * 100):+d}%"
    pitch_str = f"{int(pitch):+d}Hz"

    use_style = style and style != "general"
    style_open  = f'<mstts:express-as style="{style}" styledegree="{degree:.1f}">' if use_style else ""
    style_close = "</mstts:express-as>" if use_style else ""

    return f"""<speak version='1.0'
    xmlns='http://www.w3.org/2001/10/synthesis'
    xmlns:mstts='http://www.w3.org/2001/mstts'
    xml:lang='{lang}'>
  <voice name='{voice_id}'>
    <mstts:silence type="Sentenceboundary" value="80ms"/>
    <prosody rate='{rate_str}' pitch='{pitch_str}'>
      {style_open}{text}{style_close}
    </prosody>
  </voice>
</speak>"""


def azure_tts(text, voice_id, lang, style, degree, rate, pitch) -> bytes | None:
    key = _key(); region = _region()
    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-24khz-160kbitrate-mono-mp3",
        "User-Agent": "ContentAIStudio",
    }

    ssml = _build_ssml(text, voice_id, lang, style, degree, rate, pitch)
    url  = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"

    try:
        r = requests.post(url, data=ssml.encode("utf-8"), headers=headers, timeout=40)
        if r.status_code == 200:
            return r.content
        if r.status_code == 401:
            st.error("❌ Azure key invalid (401). Check key and region.")
            return None
        if r.status_code == 400:
            # Style not supported — retry with general (no style tag)
            ssml2 = _build_ssml(text, voice_id, lang, "general", 1.0, rate, pitch)
            r2 = requests.post(url, data=ssml2.encode("utf-8"), headers=headers, timeout=40)
            if r2.status_code == 200:
                st.info(f"ℹ️ Style '{style}' isn't available on this voice — generated with Default style + your speed/pitch settings.")
                return r2.content
            st.error(f"❌ Azure error {r.status_code}: {r.text[:200]}")
            return None
        r.raise_for_status()
        return r.content
    except Exception as e:
        st.error(f"❌ {e}")
        return None


def audio_html(b: bytes) -> str:
    b64 = base64.b64encode(b).decode()
    return (f'<audio controls style="width:100%;margin-top:8px;border-radius:8px">'
            f'<source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>')


# ── Page ──────────────────────────────────────────────────────────────────────

def render():
    st.markdown("# 🎙️ Voice Studio")
    st.markdown("All Azure Indian voices (EN + HI) · Styles loaded live from your account · 500k chars/month free")
    st.markdown("---")

    # ── API key ───────────────────────────────────────────────────────────────
    with st.expander("🔑 Azure Key Settings", expanded=not _key()):
        c1, c2, c3 = st.columns([3, 1.2, 1])
        with c1:
            k = st.text_input("Azure Speech Key", type="password",
                              value=st.session_state.get("azure_tts_key", ""),
                              placeholder="Key 1 from Azure portal → Speech → Keys & Endpoint")
            if k: st.session_state["azure_tts_key"] = k.strip()
        with c2:
            reg = st.text_input("Region",
                                value=st.session_state.get("azure_tts_region", "centralindia"),
                                placeholder="centralindia")
            if reg: st.session_state["azure_tts_region"] = reg.strip()
        with c3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("🔍 Test Key", use_container_width=True):
                ok, msg = azure_test_key(_key(), _region())
                st.success(msg) if ok else st.error(msg)
                if ok:
                    # Clear voice cache so it reloads with new key
                    fetch_indian_voices.clear()

        if not _key():
            st.info("**Get free key:** portal.azure.com → Search 'Speech' → Create → Free F0 tier → Keys & Endpoint → copy Key 1")

    if not _key():
        st.warning("⚠️ Add your Azure key above to continue.")
        return

    # ── Load voices ───────────────────────────────────────────────────────────
    with st.spinner("Loading voices from Azure..."):
        all_voices = fetch_indian_voices(_key(), _region())

    if not all_voices:
        st.error("❌ Could not load voices. Check your key and region.")
        if st.button("🔄 Retry"):
            fetch_indian_voices.clear()
            st.rerun()
        return

    en_voices = [v for v in all_voices if v["locale"] == "en-IN"]
    hi_voices = [v for v in all_voices if v["locale"] == "hi-IN"]

    st.success(f"✅ Loaded {len(en_voices)} English (India) + {len(hi_voices)} Hindi voices")

    # ── Main layout ───────────────────────────────────────────────────────────
    col_l, col_r = st.columns([1, 1], gap="large")

    with col_l:
        lang_choice = st.radio("Language", ["🇮🇳 English (India)", "🇮🇳 Hindi (India)"], horizontal=True)
        voice_pool  = en_voices if "English" in lang_choice else hi_voices
        lang_code   = "en-IN"  if "English" in lang_choice else "hi-IN"

        # Build display options
        voice_options = {}
        for v in voice_pool:
            n_styles = len(v["styles"])
            gender_icon = "♀" if v["gender"] == "Female" else "♂"
            label = f"{gender_icon} {v['name']}  ({n_styles} styles)"
            voice_options[label] = v

        voice_label   = st.selectbox("Voice", list(voice_options.keys()))
        selected_voice = voice_options[voice_label]
        voice_id       = selected_voice["short_name"]
        voice_styles   = selected_voice["styles"]   # real styles from API

        st.caption(f"`{voice_id}` · {len(voice_styles)} styles available")

        st.markdown("---")

        # Preset
        preset_name = st.selectbox("🎬 YouTube Style Preset", list(YT_PRESETS.keys()))
        preset      = YT_PRESETS[preset_name]
        is_custom   = preset_name == "✏️ Custom (manual)"
        st.caption(f"_{preset['desc']}_")

        if is_custom:
            # Show only styles this voice actually supports
            style_display = {STYLE_LABELS.get(s, s.title()): s for s in voice_styles}
            chosen_label  = st.selectbox("Style", list(style_display.keys()))
            chosen_style  = style_display[chosen_label]
            degree = st.slider("Style Intensity", 0.5, 2.0, 1.0, 0.1)
            c1, c2 = st.columns(2)
            with c1: rate  = st.slider("Speed",  0.5, 2.0, 1.0, 0.05)
            with c2: pitch = st.slider("Pitch (Hz)", -20, 20, 0, 1)
        else:
            chosen_style  = preset["style"]
            degree        = preset["degree"]
            rate          = preset["rate"]
            pitch         = preset["pitch"]

            # Check if preset style is actually supported by this voice
            if chosen_style not in voice_styles and chosen_style != "general":
                supported_str = ", ".join(STYLE_LABELS.get(s, s) for s in voice_styles)
                st.warning(
                    f"⚠️ **{STYLE_LABELS.get(chosen_style, chosen_style)}** style isn't available "
                    f"on **{selected_voice['name']}**.\n\n"
                    f"This voice supports: {supported_str}\n\n"
                    f"Audio will use **Default** style with the preset's speed & pitch."
                )
                chosen_style = "general"
            else:
                sl = STYLE_LABELS.get(chosen_style, chosen_style)
                st.markdown(f"Style: **{sl}** · Speed: `{rate}x` · Pitch: `{pitch:+d}Hz` · Intensity: `{degree}`")

        st.markdown("---")

        text = st.text_area(
            "📝 Script",
            value=st.session_state.get("last_script", ""),
            height=200,
            placeholder=(
                "Paste your script here...\n\n"
                "Tip for Hinglish: just mix Hindi+English naturally —\n"
                "'Bhai, ye AI tool literally sabka kaam kar deta hai!'"
            ),
        )
        char_count = len(text)
        col = "red" if char_count > 480000 else "orange" if char_count > 100000 else "green"
        st.markdown(f'<p style="font-size:12px;color:{col}">{char_count:,} / 500,000 chars free</p>',
                    unsafe_allow_html=True)

        gen_btn = st.button("🎙️ Generate Audio", use_container_width=True,
                            type="primary", disabled=not text.strip())

    with col_r:
        st.markdown("### 🔊 Output")

        if gen_btn and text.strip():
            label_short = selected_voice["name"]
            with st.spinner(f"Generating · {label_short} · {preset_name}..."):
                audio_bytes = azure_tts(text, voice_id, lang_code,
                                        chosen_style, degree, rate, pitch)
            if audio_bytes:
                st.session_state["last_audio"]      = audio_bytes
                st.session_state["last_audio_meta"] = {
                    "voice": label_short, "preset": preset_name, "lang": lang_code
                }
                st.success(f"✅ Done! {len(audio_bytes)/1024:.0f} KB")

        audio = st.session_state.get("last_audio")
        if audio:
            meta = st.session_state.get("last_audio_meta", {})
            st.markdown(f"**{meta.get('voice','')}** · {meta.get('preset','')}")
            st.markdown(audio_html(audio), unsafe_allow_html=True)
            st.download_button("📥 Download MP3", data=audio,
                               file_name="voiceover.mp3", mime="audio/mp3",
                               use_container_width=True)
            st.markdown("---")
            st.markdown("### ▶️ Next: Avatar video")
            st.markdown("""
Download MP3 → upload to a free avatar tool:

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
                    Pick a voice, choose a YouTube style preset, paste your script → Generate
                </div>
            </div>""", unsafe_allow_html=True)

    # ── Voice + styles reference ──────────────────────────────────────────────
    st.markdown("---")
    with st.expander(f"📋 All loaded voices + their real supported styles ({len(all_voices)} total)"):
        for locale_label, pool in [("🇮🇳 English India (en-IN)", en_voices),
                                    ("🇮🇳 Hindi India (hi-IN)",   hi_voices)]:
            st.markdown(f"**{locale_label}**")
            for v in pool:
                styles_str = " · ".join(STYLE_LABELS.get(s, s) for s in v["styles"])
                gender_icon = "♀" if v["gender"] == "Female" else "♂"
                st.markdown(
                    f"{gender_icon} **{v['name']}** &nbsp;`{v['short_name']}`  \n"
                    f"<span style='font-size:12px;color:var(--color-text-tertiary)'>{styles_str}</span>",
                    unsafe_allow_html=True,
                )
            st.markdown("")

    with st.expander("💡 Tips for more natural audio"):
        st.markdown("""
**Hinglish (mix Hindi+English)** — Aarti and Arjun voices handle it natively:
> "Bhai, ye AI tool literally 60 seconds mein poora kaam kar deta hai!"

**Poetry / Rhymes** — write each line on its own line, use the 🎵 Lyrical preset.

**YouTube Shorts hook** — keep it under 15 words, use 🎬 Shorts Hook preset:
> "Kya tum jaante ho? 90% creators pehle saal quit kar dete hain."

**Style Intensity** (in Custom mode) — 2.0 = very dramatic, 0.5 = barely noticeable.

**Neerja & Swara** have the most styles (cheerful, empathetic, newscast) — best for expressive content.
        """)
