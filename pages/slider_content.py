"""
🏖️ Slider Content Creator
A complete pipeline: Idea → Content → Images → Slides → Video → YouTube Meta
Supports English, Hindi, and Hinglish
"""

import streamlit as st
import os, json, re, io, time, base64, tempfile, zipfile
from pathlib import Path
from typing import Optional, List, Dict, Tuple
import requests
import yaml
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

# PPTX
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

# ── Optional imports ──────────────────────────────────────────────────────────
try:
    from groq import Groq
    GROQ_OK = True
except ImportError:
    GROQ_OK = False

try:
    from huggingface_hub import InferenceClient
    HF_OK = True
except ImportError:
    HF_OK = False

try:
    from gtts import gTTS
    GTTS_OK = True
except ImportError:
    GTTS_OK = False

try:
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
    MOVIEPY_OK = True
except ImportError:
    MOVIEPY_OK = False

try:
    from openai import OpenAI
    OPENAI_OK = True
except ImportError:
    OPENAI_OK = False


# ─────────────────────────────────────────────────────────────────────────────
# LOAD CONFIG
# ─────────────────────────────────────────────────────────────────────────────
CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"

@st.cache_resource
def load_config():
    if not CONFIG_PATH.exists():
        st.error(f"❌ config.yaml not found at: {CONFIG_PATH}")
        return {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

CFG = load_config()


# ─────────────────────────────────────────────────────────────────────────────
# CUSTOM CSS
# ─────────────────────────────────────────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&family=Noto+Sans:wght@400;700&display=swap');

    html, body, [class*="css"] { font-family: 'Space Grotesk', 'Noto Sans', sans-serif; }

    .main-header {
        background: linear-gradient(135deg, #0f0f19 0%, #1a0a3e 50%, #0a1a2e 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        border: 1px solid rgba(255,165,0,0.3);
        box-shadow: 0 8px 32px rgba(0,0,0,0.4);
    }
    .main-header h1 { color: #FFA500; font-size: 2.2rem; margin: 0; font-weight: 700; }
    .main-header p  { color: rgba(255,255,255,0.7); margin: 0.4rem 0 0; font-size: 1rem; }

    .step-badge {
        display: inline-block;
        background: linear-gradient(90deg, #FFA500, #FF6400);
        color: #000;
        font-weight: 700;
        font-size: 0.75rem;
        padding: 3px 12px;
        border-radius: 20px;
        margin-bottom: 0.6rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .meta-tag {
        display: inline-block;
        background: rgba(255,165,0,0.15);
        border: 1px solid rgba(255,165,0,0.4);
        color: #FFA500;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        margin: 3px;
    }

    .status-ok   { color: #00E676; }
    .status-warn { color: #FFA500; }
    .status-err  { color: #FF5252; }

    .progress-bar { display: flex; gap: 6px; margin-bottom: 1.5rem; }
    .progress-step { flex: 1; height: 6px; border-radius: 3px; background: rgba(255,255,255,0.1); }
    .progress-step.done { background: #FFA500; }
    .progress-step.active { background: rgba(255,165,0,0.5); }

    footer { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE INITIALIZER
# ─────────────────────────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "step": 1,
        "topic": "",
        "language": "English",
        "num_slides": 5,
        "slide_content": None,
        "generated_images": {},
        "selected_images": {},
        "theme": "Cinematic Dark",
        "slide_duration": 5,
        "add_audio": True,
        "audio_src": "gTTS (Free)",
        "video_path": None,
        "pptx_path": None,
        "youtube_meta": None,
        "groq_api_key": "",
        "hf_token": "",
        "openai_api_key": "",
        "slide_imgs": None,
        "selected_groq_model": None,
    }

    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ─────────────────────────────────────────────────────────────────────────────
# CONTENT GENERATION
# ─────────────────────────────────────────────────────────────────────────────
LANG_PROMPTS = {
    "English": "Generate ALL content strictly in English.",
    "Hindi": "सभी सामग्री सख्ती से हिंदी में उत्पन्न करें। केवल देवनागरी लिपि का उपयोग करें।",
    "Hinglish": "Generate all content in Hinglish (a natural mix of Hindi + English). Use Roman script for Hindi words.",
}

def _safe_json_extract(raw: str) -> Dict:
    raw = raw.strip()

    # Remove markdown fences
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"^```", "", raw)
    raw = re.sub(r"```$", "", raw).strip()

    # Extract only JSON block
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if m:
        raw = m.group()

    # Remove invalid control characters (important fix)
    raw = re.sub(r"[\x00-\x1F\x7F]", "", raw)

    # Fix smart quotes if model returns them
    raw = raw.replace("“", '"').replace("”", '"').replace("’", "'")

    return json.loads(raw)


def generate_slide_content(topic: str, language: str, num_slides: int, api_key: str, model: str) -> Optional[Dict]:
    if not GROQ_OK:
        st.error("Groq not installed.")
        return None

    lang_instr = LANG_PROMPTS.get(language, LANG_PROMPTS["English"])

    prompt = f"""
{lang_instr}

Create Instagram slider content about: "{topic}"
Generate exactly {num_slides} slides.

Return ONLY VALID JSON.
Do NOT use newline characters inside JSON strings.
Use \\n for new lines inside content.

Output format exactly:

{{
  "title": "...",
  "description_short": "...",
  "slides": [
    {{
      "slide_number": 1,
      "heading": "...",
      "content": "Line1\\nLine2\\nLine3",
      "speaker_notes": "Line1\\nLine2",
      "image_prompt": "..."
    }}
  ]
}}
""".strip()

    try:
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.75,
            max_tokens=4000,
        )
        raw = resp.choices[0].message.content
        return _safe_json_extract(raw)

    except Exception as e:
        st.error(f"Content generation failed: {e}")
        return None


def generate_youtube_meta(slide_content: Dict, language: str, category: str, api_key: str, model: str) -> Optional[Dict]:
    if not GROQ_OK:
        return None

    lang_instr = LANG_PROMPTS.get(language, LANG_PROMPTS["English"])
    slides_summary = "\n".join(
        f"Slide {s['slide_number']}: {s['heading']}" for s in slide_content.get("slides", [])
    )

    prompt = f"""
{lang_instr}

Based on this Instagram slider content:
Title: {slide_content.get('title', '')}

Slides:
{slides_summary}

Generate SEO metadata for posting as a Reel + YouTube Shorts version.

Return ONLY valid JSON:

{{
  "title": "SEO title (max 70 chars)",
  "description": "Description (200-300 words) with hashtags at end",
  "tags": ["tag1","tag2", "..."],
  "hashtags": ["#hashtag1", "#hashtag2", "..."],
  "category": "{category}",
  "thumbnail_text": "Max 5 words",
  "thumbnail_subtext": "Max 6 words",
  "seo_keywords": ["keyword1", "keyword2", "..."]
}}

Include at least 20 tags and 10 hashtags.
""".strip()

    try:
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000,
        )
        raw = resp.choices[0].message.content
        return _safe_json_extract(raw)

    except Exception as e:
        st.error(f"Meta generation failed: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# IMAGE GENERATION (HUGGING FACE)
# ─────────────────────────────────────────────────────────────────────────────
def generate_image_hf(prompt: str, hf_token: str, model_id: str) -> Optional[Image.Image]:
    if not HF_OK:
        return None
    try:
        client = InferenceClient(token=hf_token)
        enhanced = f"{prompt}, ultra detailed, 4k, cinematic lighting, sharp focus"
        img = client.text_to_image(enhanced, model=model_id)
        if isinstance(img, Image.Image):
            return img
        return Image.open(io.BytesIO(img))
    except Exception as e:
        st.warning(f"Image gen error: {e}")
        return None


def generate_images_for_slide(prompt: str, count: int, hf_token: str, model_id: str) -> List[Image.Image]:
    imgs = []
    variations = [
        prompt,
        f"{prompt}, different angle, wide shot",
        f"{prompt}, close-up, macro detail",
        f"{prompt}, dramatic lighting, golden hour",
        f"{prompt}, minimalist background",
    ]

    for i in range(min(count, 5)):
        with st.spinner(f"Generating image {i+1}/{count}..."):
            img = generate_image_hf(variations[i], hf_token, model_id)
            if img:
                imgs.append(img)
            time.sleep(1)

    return imgs


# ─────────────────────────────────────────────────────────────────────────────
# SLIDE RENDERING (PIL)
# ─────────────────────────────────────────────────────────────────────────────
W, H = 1080, 1350  # Instagram slider ratio (4:5)

def make_gradient(c1: Tuple[int,int,int], c2: Tuple[int,int,int], w=W, h=H) -> Image.Image:
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    for i in range(h):
        t = i / h
        arr[i] = [int(c1[j] + (c2[j] - c1[j]) * t) for j in range(3)]
    return Image.fromarray(arr, "RGB")


def wrap_text(text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> List[str]:
    words = text.split()
    lines, line = [], ""
    for w in words:
        test = f"{line} {w}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


def get_font(size: int, bold: bool = False):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()


def render_slide_pil(slide_data: Dict, bg_image: Optional[Image.Image], theme: Dict, slide_num: int, total: int) -> Image.Image:
    bg = make_gradient(tuple(theme["gradient_start"]), tuple(theme["gradient_end"]))

    if bg_image:
        try:
            bgi = bg_image.convert("RGB").resize((W, H), Image.LANCZOS)
            bgi = ImageEnhance.Brightness(bgi).enhance(0.55)
            bg = Image.blend(bg, bgi, alpha=0.65)
        except Exception:
            pass

    draw = ImageDraw.Draw(bg)

    f_heading = get_font(64, bold=True)
    f_body = get_font(42)
    f_small = get_font(28)

    tc = tuple(theme["text_color"])
    ac = tuple(theme["accent_color"])
    hc = tuple(theme["heading_color"])

    # top counter
    draw.text((W - 170, 40), f"{slide_num}/{total}", font=f_small, fill=ac)

    # heading
    y = 120
    head_lines = wrap_text(slide_data.get("heading", ""), f_heading, W - 160, draw)
    for ln in head_lines[:3]:
        draw.text((82, y + 3), ln, font=f_heading, fill=(0, 0, 0))
        draw.text((80, y), ln, font=f_heading, fill=hc)
        y += 78

    # separator
    y += 10
    draw.rectangle([80, y, 420, y + 6], fill=ac)
    y += 40

    # content
    content = slide_data.get("content", "")
    lines = content.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            y += 18
            continue

        if line.startswith(("•", "-", "*")):
            clean = line.lstrip("•-* ").strip()
            draw.text((88, y), "▸", font=f_body, fill=ac)
            x = 140
        else:
            clean = line
            x = 80

        wrapped = wrap_text(clean, f_body, W - x - 90, draw)
        for wl in wrapped:
            draw.text((x + 2, y + 2), wl, font=f_body, fill=(0, 0, 0))
            draw.text((x, y), wl, font=f_body, fill=tc)
            y += 56

    # footer
    draw.rectangle([0, H - 90, W, H], fill=(0, 0, 0))
    draw.text((80, H - 65), "🏖️ Slider Content Creator", font=f_small, fill=ac)

    return bg


# ─────────────────────────────────────────────────────────────────────────────
# PPTX EXPORT
# ─────────────────────────────────────────────────────────────────────────────
def create_pptx(slide_content: Dict, selected_images: Dict, theme: Dict) -> bytes:
    prs = Presentation()
    prs.slide_width = Inches(10)
    prs.slide_height = Inches(7.5)

    slides = slide_content.get("slides", [])

    for idx, sd in enumerate(slides):
        slide = prs.slides.add_slide(prs.slide_layouts[6])

        # Title
        tb = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(9), Inches(1))
        p = tb.text_frame.paragraphs[0]
        run = p.add_run()
        run.text = sd.get("heading", "")
        run.font.size = Pt(34)
        run.font.bold = True
        run.font.color.rgb = RGBColor(*theme["accent_color"])

        # Content
        cb = slide.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(9), Inches(5))
        cb.text_frame.word_wrap = True

        first = True
        for ln in sd.get("content", "").split("\n"):
            ln = ln.strip()
            if not ln:
                continue
            para = cb.text_frame.paragraphs[0] if first else cb.text_frame.add_paragraph()
            first = False
            para.text = ln
            para.font.size = Pt(18)
            para.font.color.rgb = RGBColor(*theme["text_color"])

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# AUDIO + VIDEO
# ─────────────────────────────────────────────────────────────────────────────
def generate_audio_gtts(text: str, lang_code: str, outpath: str) -> bool:
    if not GTTS_OK:
        return False
    try:
        tts = gTTS(text=text, lang=lang_code)
        tts.save(outpath)
        return True
    except Exception as e:
        st.warning(f"TTS error: {e}")
        return False


def generate_audio_openai(text: str, outpath: str, api_key: str, voice: str = "nova") -> bool:
    if not OPENAI_OK:
        return False
    try:
        client = OpenAI(api_key=api_key)
        resp = client.audio.speech.create(model="tts-1", voice=voice, input=text)
        resp.stream_to_file(outpath)
        return True
    except Exception as e:
        st.warning(f"OpenAI TTS error: {e}")
        return False


def build_video(slide_images: List[Image.Image], audio_files: List[Optional[str]], duration: int, output_path: str) -> bool:
    if not MOVIEPY_OK:
        return False

    clips = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, (img, apath) in enumerate(zip(slide_images, audio_files)):
            frame_path = os.path.join(tmp, f"slide_{i}.png")
            img.save(frame_path)

            if apath and os.path.exists(apath):
                aud = AudioFileClip(apath)
                dur = max(aud.duration + 0.5, duration)
                clip = ImageClip(frame_path).set_duration(dur).set_audio(aud)
            else:
                clip = ImageClip(frame_path).set_duration(duration)

            clips.append(clip)

        final = concatenate_videoclips(clips, method="compose")
        final.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", logger=None)
        final.close()

    return True


# ─────────────────────────────────────────────────────────────────────────────
# UI HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def progress_bar(current: int, total: int = 6):
    bars = ""
    for i in range(1, total + 1):
        cls = "done" if i < current else ("active" if i == current else "")
        bars += f'<div class="progress-step {cls}"></div>'
    st.markdown(f'<div class="progress-bar">{bars}</div>', unsafe_allow_html=True)


def step_badge(n: int, label: str):
    st.markdown(
        f'<div class="step-badge">Step {n}</div><h3 style="color:#FFA500;margin-top:4px">{label}</h3>',
        unsafe_allow_html=True,
    )


def nav_buttons(prev_step: Optional[int] = None, next_step: Optional[int] = None):
    cols = st.columns([1, 4, 1])
    if prev_step and cols[0].button("← Back"):
        st.session_state.step = prev_step
        st.rerun()
    if next_step and cols[2].button("Next →"):
        st.session_state.step = next_step
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# STEP VALIDATION
# ─────────────────────────────────────────────────────────────────────────────
def _step_ready(n: int) -> bool:
    if n == 1: return bool(st.session_state.topic)
    if n == 2: return bool(st.session_state.slide_content)
    if n == 3: return bool(st.session_state.slide_content)
    if n == 4: return bool(st.session_state.slide_content)
    if n == 5: return bool(st.session_state.pptx_path)
    if n == 6: return bool(st.session_state.youtube_meta)
    return False

def _step_accessible(n: int) -> bool:
    if n == 1: return True
    if n == 2: return bool(st.session_state.slide_content)
    if n >= 3: return bool(st.session_state.slide_content)
    return False


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
def sidebar():
    with st.sidebar:
        st.markdown("## 🏖️ Slider Content Creator")
        st.markdown("---")

        st.markdown("### 📍 Steps")
        step_labels = {
            1: "📝 Topic & Settings",
            2: "✏️ Review Content",
            3: "🖼️ Images",
            4: "🎨 Style & Preview",
            5: "🎬 Build Video",
            6: "📊 Metadata",
        }

        for n, label in step_labels.items():
            is_cur = st.session_state.step == n
            has_data = _step_ready(n)
            icon = "▶" if is_cur else ("✓" if has_data else "○")
            if st.sidebar.button(
                f"{icon} {label}",
                key=f"nav_slider_{n}",
                disabled=(not _step_accessible(n)),
                use_container_width=True
            ):
                st.session_state.step = n
                st.rerun()

        st.markdown("---")
        st.markdown("### ⚙️ Status")
        st.markdown(f"🤖 Groq: {'<span class=status-ok>✓</span>' if GROQ_OK else '<span class=status-err>✗</span>'}", unsafe_allow_html=True)
        st.markdown(f"🖼️ HF: {'<span class=status-ok>✓</span>' if HF_OK else '<span class=status-err>✗</span>'}", unsafe_allow_html=True)
        st.markdown(f"🔊 gTTS: {'<span class=status-ok>✓</span>' if GTTS_OK else '<span class=status-warn>✗</span>'}", unsafe_allow_html=True)
        st.markdown(f"🎬 MoviePy: {'<span class=status-ok>✓</span>' if MOVIEPY_OK else '<span class=status-warn>✗</span>'}", unsafe_allow_html=True)

        st.markdown("---")
        if st.button("🔄 Start Over", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# STEP PAGES
# ─────────────────────────────────────────────────────────────────────────────
def page_step1_setup():
    step_badge(1, "Topic, Language & Settings")
    progress_bar(1)

    c1, c2 = st.columns([3, 2])
    with c1:
        st.session_state.topic = st.text_area(
            "🎯 Enter your slider topic",
            value=st.session_state.topic,
            height=120,
            placeholder="Example: '5 habits that make you successful'"
        )

        st.session_state.language = st.radio(
            "🌐 Content Language",
            options=list(CFG.get("languages", {}).keys()),
            index=list(CFG.get("languages", {}).keys()).index(st.session_state.language)
            if CFG.get("languages") else 0,
            horizontal=True,
        )

    with c2:
        st.session_state.num_slides = st.slider("📊 Number of Slides", 3, 10, st.session_state.num_slides)

        models = CFG.get("groq", {}).get("models", [])
        if not models:
            st.error("❌ No Groq models found in config.yaml")
            return

        model = st.selectbox("🤖 Groq Model", models, index=0, key="slider_groq_model")
        st.session_state.selected_groq_model = model

        st.markdown("---")
        st.markdown("**🔑 API Keys**")

        st.session_state.groq_api_key = st.text_input("Groq API Key", type="password", value=st.session_state.groq_api_key)
        st.session_state.hf_token = st.text_input("HuggingFace Token", type="password", value=st.session_state.hf_token)
        st.session_state.openai_api_key = st.text_input("OpenAI Key (optional)", type="password", value=st.session_state.openai_api_key)

    st.markdown("---")

    ready = bool(st.session_state.topic.strip() and st.session_state.groq_api_key.strip())

    if st.button("🚀 Generate Slider Content", disabled=not ready):
        with st.spinner("Generating slider content..."):
            result = generate_slide_content(
                st.session_state.topic,
                st.session_state.language,
                st.session_state.num_slides,
                st.session_state.groq_api_key,
                st.session_state.selected_groq_model
            )

        if result:
            st.session_state.slide_content = result
            st.session_state.step = 2
            st.success("✅ Content generated!")
            st.rerun()


def page_step2_review():
    step_badge(2, "Review & Edit Content")
    progress_bar(2)

    sc = st.session_state.slide_content
    if not sc:
        st.warning("No content yet. Go back to Step 1.")
        nav_buttons(prev_step=1)
        return

    st.markdown(f"### 🏖️ `{sc.get('title', '')}`")
    st.caption(sc.get("description_short", ""))

    slides = sc.get("slides", [])
    for i, s in enumerate(slides):
        with st.expander(f"Slide {s['slide_number']}: {s['heading']}", expanded=(i == 0)):
            col1, col2 = st.columns([3, 2])
            with col1:
                slides[i]["heading"] = st.text_input("Heading", value=s["heading"], key=f"sh_{i}")
                slides[i]["content"] = st.text_area("Content", value=s["content"], height=120, key=f"sc_{i}")
            with col2:
                slides[i]["speaker_notes"] = st.text_area("Voiceover Text", value=s.get("speaker_notes", ""), height=80, key=f"sn_{i}")
                slides[i]["image_prompt"] = st.text_input("Image Prompt (English)", value=s.get("image_prompt", ""), key=f"sp_{i}")

    sc["slides"] = slides
    st.session_state.slide_content = sc

    nav_buttons(prev_step=1)
    if st.button("✅ Next → Generate Images"):
        st.session_state.step = 3
        st.rerun()


def page_step3_images():
    step_badge(3, "Generate & Select Images")
    progress_bar(3)

    sc = st.session_state.slide_content
    if not sc:
        nav_buttons(prev_step=2)
        return

    slides = sc.get("slides", [])
    hf_token = st.session_state.hf_token

    if not hf_token:
        st.warning("⚠️ HuggingFace token not set — you can upload images manually.")

    hf_models = CFG.get("huggingface", {}).get("image_models", [])
    if not hf_models:
        st.warning("No HuggingFace image models configured in config.yaml.")
        nav_buttons(prev_step=2)
        return

    hf_model = st.selectbox(
        "🖼️ Image Model",
        options=[m["id"] for m in hf_models],
        format_func=lambda x: next(m["label"] for m in hf_models if m["id"] == x),
        key="slider_hf_model",
    )

    imgs_per_slide = st.slider("Images per slide", 1, 5, 3)

    if st.button("🎨 Generate All Images", disabled=not bool(hf_token)):
        prog = st.progress(0.0, text="Generating images...")
        for i, s in enumerate(slides):
            prog.progress((i + 0.1) / len(slides), text=f"Slide {i+1}/{len(slides)}...")
            imgs = generate_images_for_slide(
                s.get("image_prompt", s["heading"]),
                imgs_per_slide,
                hf_token,
                hf_model
            )
            st.session_state.generated_images[i] = imgs
            if imgs:
                st.session_state.selected_images[i] = imgs[0]
        prog.progress(1.0)
        st.success("✅ Images generated!")

    st.markdown("---")
    st.markdown("### Select one image per slide")

    for i, s in enumerate(slides):
        st.markdown(f"**Slide {i+1}: {s['heading']}**")

        imgs = st.session_state.generated_images.get(i, [])
        if imgs:
            cols = st.columns(min(len(imgs), 5))
            for j, img in enumerate(imgs):
                with cols[j]:
                    st.image(img, use_container_width=True)
                    if st.button("✔ Use", key=f"slider_use_{i}_{j}"):
                        st.session_state.selected_images[i] = img
                        st.rerun()
        else:
            st.caption("No AI images generated yet.")

        up = st.file_uploader(f"Upload your image (Slide {i+1})", type=["png","jpg","jpeg"], key=f"slider_up_{i}")
        if up:
            st.session_state.selected_images[i] = Image.open(up)

        st.markdown("---")

    nav_buttons(prev_step=2)
    if st.button("🎨 Next → Style & Preview"):
        st.session_state.step = 4
        st.rerun()


def page_step4_style():
    step_badge(4, "Style & Preview")
    progress_bar(4)

    sc = st.session_state.slide_content
    if not sc:
        nav_buttons(prev_step=3)
        return

    themes = CFG.get("themes", {})
    if not themes:
        st.error("❌ No themes found in config.yaml")
        nav_buttons(prev_step=3)
        return

    c1, c2 = st.columns([2, 3])
    with c1:
        theme_name = st.selectbox(
            "🎨 Theme",
            list(themes.keys()),
            index=list(themes.keys()).index(st.session_state.theme)
            if st.session_state.theme in themes else 0
        )
        st.session_state.theme = theme_name
        theme = themes[theme_name]

        st.session_state.slide_duration = st.slider("⏱️ Seconds per slide", 3, 15, st.session_state.slide_duration)
        st.session_state.add_audio = st.toggle("🔊 Add voiceover audio", value=st.session_state.add_audio)

        if st.session_state.add_audio:
            st.session_state.audio_src = st.radio(
                "Audio Source",
                ["gTTS (Free)", "OpenAI TTS (Better quality)"],
                horizontal=True
            )

    with c2:
        slides = sc.get("slides", [])
        idx = st.selectbox("Preview slide", range(1, len(slides) + 1))
        slide_data = slides[idx - 1]
        bg_img = st.session_state.selected_images.get(idx - 1)
        preview = render_slide_pil(slide_data, bg_img, theme, idx, len(slides))
        st.image(preview, use_container_width=True)

    nav_buttons(prev_step=3)
    if st.button("🎬 Next → Build Video"):
        st.session_state.step = 5
        st.rerun()


def page_step5_build():
    step_badge(5, "Build Slides + Video")
    progress_bar(5)

    sc = st.session_state.slide_content
    if not sc:
        nav_buttons(prev_step=4)
        return

    slides = sc.get("slides", [])
    theme = CFG["themes"][st.session_state.theme]
    lang_cfg = CFG["languages"][st.session_state.language]

    if not MOVIEPY_OK:
        st.warning("⚠️ MoviePy not installed. MP4 export won't work.")
    if not GTTS_OK and not OPENAI_OK:
        st.warning("⚠️ No TTS engine installed.")

    if st.button("🚀 Build Everything Now"):
        prog = st.progress(0.0, text="Rendering slider images...")

        slide_imgs = []
        for i, sd in enumerate(slides):
            prog.progress(i / (len(slides) * 3), text=f"Rendering slide {i+1}...")
            img = render_slide_pil(sd, st.session_state.selected_images.get(i), theme, i+1, len(slides))
            slide_imgs.append(img)

        # PPTX
        prog.progress(0.35, text="Creating PPTX...")
        pptx_bytes = create_pptx(sc, st.session_state.selected_images, theme)
        pptx_path = os.path.join(tempfile.gettempdir(), "slider_slides.pptx")
        with open(pptx_path, "wb") as f:
            f.write(pptx_bytes)
        st.session_state.pptx_path = pptx_path

        # Audio
        audio_files = [None] * len(slides)
        if st.session_state.add_audio:
            prog.progress(0.45, text="Generating voiceover audio...")
            for i, sd in enumerate(slides):
                text = sd.get("speaker_notes") or sd.get("content", "")
                apath = os.path.join(tempfile.gettempdir(), f"slider_audio_{i}.mp3")

                if "OpenAI" in st.session_state.audio_src and st.session_state.openai_api_key:
                    ok = generate_audio_openai(text, apath, st.session_state.openai_api_key)
                else:
                    ok = generate_audio_gtts(text, lang_cfg["gtts_code"], apath)

                audio_files[i] = apath if ok else None

        # Video
        video_path = None
        if MOVIEPY_OK:
            prog.progress(0.72, text="Building MP4 video...")
            video_path = os.path.join(tempfile.gettempdir(), "slider_video.mp4")
            ok = build_video(slide_imgs, audio_files, st.session_state.slide_duration, video_path)
            if ok:
                st.session_state.video_path = video_path
            else:
                st.warning("Video build failed. Check FFmpeg.")

        st.session_state.slide_imgs = slide_imgs

        prog.progress(1.0, text="Done!")
        st.success("✅ All slider assets generated!")
        st.rerun()

    # Downloads
    if st.session_state.pptx_path and os.path.exists(st.session_state.pptx_path):
        st.markdown("---")
        st.markdown("### 📥 Download Assets")

        c1, c2, c3 = st.columns(3)

        with open(st.session_state.pptx_path, "rb") as f:
            c1.download_button(
                "⬇️ Download PPTX",
                f.read(),
                "slider_slides.pptx",
                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
            )

        if st.session_state.slide_imgs:
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as zf:
                for i, img in enumerate(st.session_state.slide_imgs):
                    ibuf = io.BytesIO()
                    img.save(ibuf, format="PNG")
                    zf.writestr(f"slide_{i+1:02d}.png", ibuf.getvalue())

            c2.download_button("⬇️ Download Slides (ZIP)", zip_buf.getvalue(), "slider_images.zip", mime="application/zip")

        if st.session_state.video_path and os.path.exists(st.session_state.video_path):
            with open(st.session_state.video_path, "rb") as f:
                c3.download_button("⬇️ Download MP4", f.read(), "slider_video.mp4", mime="video/mp4")
            st.video(st.session_state.video_path)

    nav_buttons(prev_step=4)
    if st.button("📊 Next → Generate Metadata"):
        st.session_state.step = 6
        st.rerun()


def page_step6_meta():
    step_badge(6, "SEO Metadata")
    progress_bar(6)

    sc = st.session_state.slide_content
    if not sc:
        nav_buttons(prev_step=5)
        return

    category = st.selectbox("📂 Category", CFG.get("youtube_categories", ["Education", "Entertainment", "News"]))

    if st.button("🤖 Generate Metadata"):
        with st.spinner("Generating SEO metadata..."):
            meta = generate_youtube_meta(
                sc,
                st.session_state.language,
                category,
                st.session_state.groq_api_key,
                st.session_state.selected_groq_model or CFG["groq"]["default_model"]
            )
        if meta:
            st.session_state.youtube_meta = meta

    meta = st.session_state.youtube_meta
    if meta:
        st.markdown("---")

        c1, c2 = st.columns([3, 2])
        with c1:
            meta["title"] = st.text_input("Title", value=meta.get("title", ""))
            meta["description"] = st.text_area("Description", value=meta.get("description", ""), height=220)

            tags = meta.get("tags", [])
            tags_edit = st.text_area("Tags (comma separated)", value=", ".join(tags), height=80)
            meta["tags"] = [t.strip() for t in tags_edit.split(",") if t.strip()]

        with c2:
            st.markdown("#### Hashtags")
            hashtags = meta.get("hashtags", [])
            ht_edit = st.text_area("Hashtags (comma separated)", value=", ".join(hashtags), height=120)
            meta["hashtags"] = [h.strip() for h in ht_edit.split(",") if h.strip()]

            st.markdown("#### Thumbnail Text")
            meta["thumbnail_text"] = st.text_input("Thumbnail Text", value=meta.get("thumbnail_text", ""))
            meta["thumbnail_subtext"] = st.text_input("Thumbnail Subtext", value=meta.get("thumbnail_subtext", ""))

        st.session_state.youtube_meta = meta

        export = {
            "metadata": meta,
            "slides": sc.get("slides", [])
        }

        st.download_button(
            "⬇️ Download Metadata JSON",
            data=json.dumps(export, ensure_ascii=False, indent=2),
            file_name="slider_metadata.json",
            mime="application/json"
        )

    nav_buttons(prev_step=5)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN RENDER
# ─────────────────────────────────────────────────────────────────────────────
def render():
    inject_css()
    init_state()
    sidebar()

    st.markdown("""
    <div class="main-header">
        <h1>🏖️ Slider Content Creator</h1>
        <p>Idea → AI Content → Images → Slides → Video → SEO Metadata</p>
    </div>
    """, unsafe_allow_html=True)

    step = st.session_state.step
    if step == 1:
        page_step1_setup()
    elif step == 2:
        page_step2_review()
    elif step == 3:
        page_step3_images()
    elif step == 4:
        page_step4_style()
    elif step == 5:
        page_step5_build()
    elif step == 6:
        page_step6_meta()
