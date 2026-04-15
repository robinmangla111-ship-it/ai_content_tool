"""
🎬 YouTube Slide Video Creator
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
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN

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
    from moviepy.editor import (
        ImageClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip
    )
    MOVIEPY_OK = True
except ImportError:
    MOVIEPY_OK = False

try:
    from openai import OpenAI
    OPENAI_OK = True
except ImportError:
    OPENAI_OK = False

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🎬 YouTube Slide Video Creator",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# LOAD CONFIG
# ─────────────────────────────────────────────────────────────────────────────
CONFIG_PATH = Path(__file__).parent / "config.yaml"

@st.cache_resource
def load_config():
    with open(CONFIG_PATH) as f:
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

    .step-card {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border: 1px solid rgba(255,165,0,0.25);
        border-radius: 12px;
        padding: 1.4rem 1.6rem;
        margin-bottom: 1rem;
    }
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

    .slide-card {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 10px;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
    }
    .slide-card h4 { color: #FFA500; margin: 0 0 0.4rem; font-size: 1rem; }
    .slide-card p  { color: rgba(255,255,255,0.8); margin: 0; font-size: 0.88rem; }

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

    .stButton > button {
        background: linear-gradient(90deg, #FFA500, #FF6400) !important;
        color: #000 !important;
        font-weight: 700 !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.6rem 1.8rem !important;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 20px rgba(255,165,0,0.4) !important;
    }

    div[data-testid="stExpander"] > div:first-child {
        border: 1px solid rgba(255,165,0,0.2);
        border-radius: 8px;
    }

    .progress-bar {
        display: flex;
        gap: 6px;
        margin-bottom: 1.5rem;
    }
    .progress-step {
        flex: 1;
        height: 6px;
        border-radius: 3px;
        background: rgba(255,255,255,0.1);
        transition: background 0.3s;
    }
    .progress-step.done   { background: #FFA500; }
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
        "slide_content": None,       # dict from Groq
        "generated_images": {},      # {slide_idx: [PIL.Image, ...]}
        "selected_images": {},       # {slide_idx: PIL.Image or None}
        "theme": "Cinematic Dark",
        "slide_duration": 5,
        "add_audio": True,
        "audio_speed": "normal",
        "video_path": None,
        "pptx_path": None,
        "youtube_meta": None,
        "groq_api_key": "",
        "hf_token": "",
        "openai_api_key": "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

# ─────────────────────────────────────────────────────────────────────────────
# FONT HELPERS
# ─────────────────────────────────────────────────────────────────────────────
FONT_DIR = Path(tempfile.gettempdir()) / "yt_slide_fonts"
FONT_DIR.mkdir(exist_ok=True)

def get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Try to load a system/downloaded font, fall back to default."""
    fname = "NotoSans-Bold.ttf" if bold else "NotoSans-Regular.ttf"
    path = FONT_DIR / fname
    if path.exists():
        try:
            return ImageFont.truetype(str(path), size)
        except Exception:
            pass
    # Try common system fonts
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/Arial.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()


def download_fonts():
    """Download Noto Sans fonts for multilingual support."""
    fonts = CFG.get("fonts", {}).get("google_fonts", [])
    status = []
    for f in fonts:
        dest = FONT_DIR / f["filename"]
        if dest.exists():
            status.append(f"✅ {f['name']} already present")
            continue
        try:
            r = requests.get(f["url"], timeout=30)
            if r.status_code == 200:
                dest.write_bytes(r.content)
                status.append(f"✅ Downloaded {f['name']}")
            else:
                status.append(f"⚠️ Could not download {f['name']}")
        except Exception as e:
            status.append(f"❌ Error: {e}")
    return status

# ─────────────────────────────────────────────────────────────────────────────
# ░░  SECTION 1: CONTENT GENERATION (GROQ)  ░░
# ─────────────────────────────────────────────────────────────────────────────
LANG_PROMPTS = {
    "English": "Generate ALL content strictly in English.",
    "Hindi": "सभी सामग्री सख्ती से हिंदी में उत्पन्न करें। केवल देवनागरी लिपि का उपयोग करें।",
    "Hinglish": "Generate all content in Hinglish (a natural mix of Hindi and English). Use Roman script for Hindi words.",
}

def generate_slide_content(topic: str, language: str, num_slides: int, api_key: str, model: str) -> Optional[Dict]:
    if not GROQ_OK:
        st.error("Groq not installed.")
        return None
    lang_instr = LANG_PROMPTS.get(language, LANG_PROMPTS["English"])
    prompt = f"""
{lang_instr}

Create a compelling YouTube video slide presentation about: "{topic}"
Generate exactly {num_slides} slides.

Return ONLY valid JSON (no markdown, no explanation) with this exact structure:
{{
  "title": "Engaging YouTube video title",
  "description_short": "One-sentence hook for the video",
  "slides": [
    {{
      "slide_number": 1,
      "heading": "Short, punchy heading (max 8 words)",
      "content": "3-5 bullet points or a short paragraph. Be informative and engaging.",
      "speaker_notes": "What the narrator says while this slide is shown (2-4 sentences)",
      "image_prompt": "Detailed English image generation prompt (always in English regardless of content language): photorealistic, specific visual description, 8k, professional photography style"
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
        raw = resp.choices[0].message.content.strip()
        # strip markdown fences if present
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"```$", "", raw).strip()
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            return json.loads(m.group())
        return json.loads(raw)
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

Based on this YouTube video about "{slide_content.get('title', '')}":
{slides_summary}

Generate YouTube metadata. Return ONLY valid JSON:
{{
  "title": "SEO-optimized YouTube title (max 70 chars)",
  "description": "Full YouTube description (200-300 words) with timestamps, hashtags at end",
  "tags": ["tag1", "tag2", "tag3", ...],
  "hashtags": ["#hashtag1", "#hashtag2", ...],
  "category": "{category}",
  "thumbnail_text": "Short bold text for thumbnail (max 5 words)",
  "thumbnail_subtext": "Subtitle for thumbnail (max 6 words)",
  "seo_keywords": ["keyword1", "keyword2", ...]
}}
Include at least 20 tags and 10 hashtags. Make tags highly searchable.
""".strip()

    try:
        client = Groq(api_key=api_key)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000,
        )
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"```$", "", raw).strip()
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            return json.loads(m.group())
        return json.loads(raw)
    except Exception as e:
        st.error(f"Meta generation failed: {e}")
        return None

# ─────────────────────────────────────────────────────────────────────────────
# ░░  SECTION 2: IMAGE GENERATION (HUGGING FACE)  ░░
# ─────────────────────────────────────────────────────────────────────────────
def generate_image_hf(prompt: str, hf_token: str, model_id: str) -> Optional[Image.Image]:
    """Generate one image via HuggingFace Inference API."""
    if not HF_OK:
        return None
    try:
        client = InferenceClient(token=hf_token)
        enhanced = (
            f"{prompt}, high quality, 4k, ultra detailed, professional photography, "
            "sharp focus, vibrant colors, cinematic lighting"
        )
        img = client.text_to_image(enhanced, model=model_id)
        if isinstance(img, Image.Image):
            return img
        return Image.open(io.BytesIO(img))
    except Exception as e:
        st.warning(f"Image gen error: {e}")
        return None


def generate_images_for_slide(
    prompt: str, count: int, hf_token: str, model_id: str
) -> List[Image.Image]:
    """Generate 'count' images for a single slide prompt."""
    imgs = []
    varied_prompts = [
        prompt,
        f"{prompt}, different angle, wide shot",
        f"{prompt}, close-up, macro detail",
        f"{prompt}, dramatic lighting, golden hour",
        f"{prompt}, minimalist, clean background",
    ]
    for i in range(min(count, 5)):
        with st.spinner(f"  Generating image {i+1}/{count}…"):
            img = generate_image_hf(varied_prompts[i], hf_token, model_id)
            if img:
                imgs.append(img)
            time.sleep(1)   # rate-limit guard
    return imgs


def pil_to_b64(img: Image.Image, fmt="JPEG") -> str:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format=fmt, quality=85)
    return base64.b64encode(buf.getvalue()).decode()

# ─────────────────────────────────────────────────────────────────────────────
# ░░  SECTION 3: SLIDE RENDERING (PILLOW)  ░░
# ─────────────────────────────────────────────────────────────────────────────
W, H = 1920, 1080

def hex_to_rgb(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def make_gradient(c1: Tuple, c2: Tuple, w: int = W, h: int = H) -> Image.Image:
    arr = np.zeros((h, w, 3), dtype=np.uint8)
    for i in range(h):
        t = i / h
        arr[i] = [int(c1[j] + (c2[j] - c1[j]) * t) for j in range(3)]
    return Image.fromarray(arr, "RGB")


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw) -> List[str]:
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


def render_slide_pil(
    slide_data: Dict,
    bg_image: Optional[Image.Image],
    theme: Dict,
    slide_num: int,
    total: int,
) -> Image.Image:
    """Render a single slide as a 1920×1080 PIL image."""
    bg = make_gradient(
        tuple(theme["gradient_start"]),
        tuple(theme["gradient_end"]),
    )

    if bg_image:
        try:
            bgi = bg_image.convert("RGB").resize((W, H), Image.LANCZOS)
            # darken and blend
            bgi = ImageEnhance.Brightness(bgi).enhance(0.45)
            bg = Image.blend(bg, bgi, alpha=0.65)
        except Exception:
            pass

    # Subtle vignette overlay
    vgn = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vgn)
    for i in range(120):
        alpha = int(180 * (i / 120) ** 2)
        vd.rectangle([i, i, W - i, H - i], outline=(0, 0, 0, alpha))
    bg = bg.convert("RGBA")
    bg = Image.alpha_composite(bg, vgn).convert("RGB")

    draw = ImageDraw.Draw(bg)

    # ── Fonts ──
    try:
        f_heading = get_font(72, bold=True)
        f_body    = get_font(38)
        f_counter = get_font(28)
        f_accent  = get_font(32, bold=True)
    except Exception:
        f_heading = f_body = f_counter = f_accent = ImageFont.load_default()

    tc    = tuple(theme["text_color"])
    ac    = tuple(theme["accent_color"])
    hc    = tuple(theme["heading_color"])

    # ── Left accent bar ──
    draw.rectangle([60, 120, 68, H - 120], fill=ac)

    # ── Slide counter ──
    counter_txt = f"{slide_num} / {total}"
    draw.text((W - 160, 50), counter_txt, font=f_counter, fill=(*ac, 200))

    # ── Heading ──
    heading = slide_data.get("heading", "")
    head_lines = wrap_text(heading, f_heading, W - 320, draw)
    y = 130
    for line in head_lines[:3]:
        # shadow
        draw.text((102, y + 3), line, font=f_heading, fill=(0, 0, 0, 180))
        draw.text((100, y), line, font=f_heading, fill=hc)
        y += 88

    # ── Accent separator ──
    y += 10
    draw.rectangle([100, y, 400, y + 4], fill=ac)
    y += 30

    # ── Content ──
    content = slide_data.get("content", "")
    lines = content.split("\n")
    max_text_h = H - y - 160
    used_h = 0
    for line in lines:
        line = line.strip()
        if not line:
            y += 20
            used_h += 20
            continue
        # bullet
        if line.startswith(("•", "-", "*")):
            line = line.lstrip("•-* ").strip()
            draw.text((108, y), "▸", font=f_accent, fill=ac)
            x_start = 150
        else:
            x_start = 100
        wrapped = wrap_text(line, f_body, W - x_start - 250, draw)
        for wl in wrapped:
            if used_h > max_text_h:
                break
            draw.text((x_start + 2, y + 2), wl, font=f_body, fill=(0, 0, 0, 120))
            draw.text((x_start, y), wl, font=f_body, fill=tc)
            y += 52
            used_h += 52

    # ── Bottom brand bar ──
    draw.rectangle([0, H - 70, W, H], fill=(*[int(c * 0.6) for c in theme["gradient_end"]], 220))
    draw.text((100, H - 50), "🎬 YouTube Slide Creator", font=f_counter, fill=(*ac, 180))

    return bg


# ─────────────────────────────────────────────────────────────────────────────
# ░░  SECTION 4: PPTX EXPORT  ░░
# ─────────────────────────────────────────────────────────────────────────────
def create_pptx(slide_content: Dict, selected_images: Dict, theme: Dict, theme_name: str) -> bytes:
    prs = Presentation()
    prs.slide_width  = Inches(16)
    prs.slide_height = Inches(9)

    bg_hex   = theme.get("pptx_bg",     "0F0F19")
    txt_hex  = theme.get("pptx_text",   "FFFFFF")
    acc_hex  = theme.get("pptx_accent", "FFA500")

    bg_rgb  = RGBColor(*hex_to_rgb(bg_hex))
    txt_rgb = RGBColor(*hex_to_rgb(txt_hex))
    acc_rgb = RGBColor(*hex_to_rgb(acc_hex))

    slides = slide_content.get("slides", [])

    for idx, sd in enumerate(slides):
        layout = prs.slide_layouts[6]  # blank
        slide  = prs.slides.add_slide(layout)

        # Background color
        bg = slide.background
        fill = bg.fill
        fill.solid()
        fill.fore_color.rgb = bg_rgb

        # If image available, add as background
        img = selected_images.get(idx)
        if img:
            buf = io.BytesIO()
            img.convert("RGB").resize((1920, 1080)).save(buf, format="PNG")
            buf.seek(0)
            pic = slide.shapes.add_picture(buf, 0, 0, Inches(16), Inches(9))
            pic.line.fill.background()
            # darken overlay via semi-transparent rectangle
            from pptx.util import Pt as PtU
            from pptx.oxml.ns import qn
            import lxml.etree as etree
            rect = slide.shapes.add_shape(
                1,  # MSO_SHAPE_TYPE.RECTANGLE
                0, 0, Inches(16), Inches(9)
            )
            rfill = rect.fill
            rfill.solid()
            rfill.fore_color.rgb = RGBColor(*hex_to_rgb(bg_hex))
            rect.line.fill.background()
            # set transparency via XML
            sp_pr = rect._element.spPr
            solid_fill = sp_pr.find(qn("a:solidFill"))
            if solid_fill is not None:
                srgb = solid_fill.find(qn("a:srgbClr"))
                if srgb is not None:
                    alpha = etree.SubElement(srgb, qn("a:alpha"))
                    alpha.set("val", "62000")  # ~62% opacity

        # Heading
        tf = slide.shapes.add_textbox(Inches(0.5), Inches(0.8), Inches(15), Inches(1.6))
        tf.text_frame.word_wrap = True
        p = tf.text_frame.paragraphs[0]
        run = p.add_run()
        run.text = sd.get("heading", "")
        run.font.size   = Pt(44)
        run.font.bold   = True
        run.font.color.rgb = acc_rgb

        # Content
        cf = slide.shapes.add_textbox(Inches(0.5), Inches(2.6), Inches(14), Inches(5.5))
        cf.text_frame.word_wrap = True
        content_lines = sd.get("content", "").split("\n")
        first = True
        for line in content_lines:
            line = line.strip()
            if not line:
                continue
            p2 = cf.text_frame.paragraphs[0] if first else cf.text_frame.add_paragraph()
            first = False
            run2 = p2.add_run()
            clean = line.lstrip("•-* ").strip()
            run2.text = f"▸  {clean}" if line.startswith(("•", "-", "*")) else clean
            run2.font.size  = Pt(22)
            run2.font.color.rgb = txt_rgb

        # Speaker notes
        notes_slide = slide.notes_slide
        tf_notes = notes_slide.notes_text_frame
        tf_notes.text = sd.get("speaker_notes", "")

        # Slide number
        nb = slide.shapes.add_textbox(Inches(14.5), Inches(8.4), Inches(1.2), Inches(0.5))
        nb.text_frame.paragraphs[0].add_run().text = f"{idx + 1}/{len(slides)}"
        nb.text_frame.paragraphs[0].runs[0].font.size  = Pt(14)
        nb.text_frame.paragraphs[0].runs[0].font.color.rgb = acc_rgb

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# ░░  SECTION 5: AUDIO + VIDEO  ░░
# ─────────────────────────────────────────────────────────────────────────────
def generate_audio_gtts(text: str, lang_code: str, outpath: str, slow: bool = False) -> bool:
    if not GTTS_OK:
        return False
    try:
        tts = gTTS(text=text, lang=lang_code, slow=slow)
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


def build_video(
    slides: List[Dict],
    slide_images: List[Image.Image],
    audio_files: List[Optional[str]],
    duration_per_slide: int,
    output_path: str,
) -> bool:
    if not MOVIEPY_OK:
        return False
    clips = []
    with tempfile.TemporaryDirectory() as tmp:
        for i, (pil_img, audio_path) in enumerate(zip(slide_images, audio_files)):
            frame_path = os.path.join(tmp, f"slide_{i}.png")
            pil_img.save(frame_path)
            if audio_path and os.path.exists(audio_path):
                try:
                    aud = AudioFileClip(audio_path)
                    dur = max(aud.duration + 0.5, duration_per_slide)
                    clip = ImageClip(frame_path).set_duration(dur).set_audio(aud)
                except Exception:
                    clip = ImageClip(frame_path).set_duration(duration_per_slide)
            else:
                clip = ImageClip(frame_path).set_duration(duration_per_slide)

            # fade in/out
            clip = clip.fadein(0.4).fadeout(0.4)
            clips.append(clip)

        if not clips:
            return False

        final = concatenate_videoclips(clips, method="compose")
        final.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            threads=2,
            logger=None,
        )
        final.close()
    return True


# ─────────────────────────────────────────────────────────────────────────────
# ░░  UI HELPERS  ░░
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
# ░░  STEP PAGES  ░░
# ─────────────────────────────────────────────────────────────────────────────

def page_step1_setup():
    step_badge(1, "Topic, Language & Settings")
    progress_bar(1)

    c1, c2 = st.columns([3, 2])
    with c1:
        topic = st.text_area(
            "🎯 Enter your video topic / idea",
            value=st.session_state.topic,
            height=120,
            placeholder="e.g., 'Top 5 benefits of meditation for students' or 'India ki economy 2025 mein' or 'भारतीय त्योहारों का महत्व'",
        )
        st.session_state.topic = topic

        lang = st.radio(
            "🌐 Content Language",
            options=list(CFG["languages"].keys()),
            index=list(CFG["languages"].keys()).index(st.session_state.language),
            horizontal=True,
        )
        st.session_state.language = lang

    with c2:
        st.session_state.num_slides = st.slider("📊 Number of Slides", 3, 10, st.session_state.num_slides)
        model = st.selectbox("🤖 Groq Model", CFG["groq"]["models"],
                             index=0, key="groq_model_select")
        st.session_state["selected_groq_model"] = model

        st.markdown("---")
        st.markdown("**🔑 API Keys** *(stored only in session)*")
        st.session_state.groq_api_key = st.text_input(
            "Groq API Key", value=st.session_state.groq_api_key,
            type="password", placeholder="gsk_…"
        )
        st.session_state.hf_token = st.text_input(
            "HuggingFace Token (for images)", value=st.session_state.hf_token,
            type="password", placeholder="hf_…"
        )
        st.session_state.openai_api_key = st.text_input(
            "OpenAI Key (optional, better TTS)", value=st.session_state.openai_api_key,
            type="password", placeholder="sk-…"
        )

    st.markdown("---")
    ready = bool(st.session_state.topic.strip() and st.session_state.groq_api_key.strip())
    if not ready:
        st.info("💡 Enter your topic and Groq API key to continue.")
    if st.button("🚀 Generate Content", disabled=not ready):
        with st.spinner("✨ Generating slide content with AI…"):
            result = generate_slide_content(
                st.session_state.topic,
                st.session_state.language,
                st.session_state.num_slides,
                st.session_state.groq_api_key,
                st.session_state.get("selected_groq_model", CFG["groq"]["default_model"]),
            )
        if result:
            st.session_state.slide_content = result
            st.session_state.step = 2
            st.success("✅ Content generated!")
            st.rerun()


def page_step2_content():
    step_badge(2, "Review & Edit Content")
    progress_bar(2)

    sc = st.session_state.slide_content
    if not sc:
        st.warning("No content yet. Go back to Step 1.")
        nav_buttons(prev_step=1)
        return

    st.markdown(f"### 🎬 `{sc.get('title', '')}`")
    st.caption(sc.get("description_short", ""))

    slides = sc.get("slides", [])
    for i, s in enumerate(slides):
        with st.expander(f"Slide {s['slide_number']}: {s['heading']}", expanded=(i == 0)):
            col1, col2 = st.columns([3, 2])
            with col1:
                new_h = st.text_input("Heading", value=s["heading"], key=f"h_{i}")
                new_c = st.text_area("Content", value=s["content"], height=120, key=f"c_{i}")
                slides[i]["heading"] = new_h
                slides[i]["content"] = new_c
            with col2:
                new_n = st.text_area("Speaker Notes", value=s.get("speaker_notes", ""), height=80, key=f"n_{i}")
                new_p = st.text_input("Image Prompt (English)", value=s.get("image_prompt", ""), key=f"p_{i}")
                slides[i]["speaker_notes"] = new_n
                slides[i]["image_prompt"]   = new_p

    sc["slides"] = slides
    st.session_state.slide_content = sc

    nav_buttons(prev_step=1)
    if st.button("✅ Content looks good → Choose Images"):
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
        st.warning("⚠️ HuggingFace token not set — you can skip images or add token in Step 1.")

    hf_model = st.selectbox(
        "🖼️ Image Model",
        options=[m["id"] for m in CFG["huggingface"]["image_models"]],
        format_func=lambda x: next(m["label"] for m in CFG["huggingface"]["image_models"] if m["id"] == x),
        key="hf_model_select",
    )
    imgs_per_slide = st.slider("Images to generate per slide", 1, 5, 3, key="imgs_per_slide")

    total_cost_warn = len(slides) * imgs_per_slide
    st.caption(f"⏱️ Estimated: {total_cost_warn} images total ({total_cost_warn * 8}–{total_cost_warn * 20}s)")

    gen_all = st.button("🎨 Generate All Images", disabled=not bool(hf_token))
    if gen_all:
        prog = st.progress(0.0, text="Starting image generation…")
        for i, s in enumerate(slides):
            prog.progress((i + 0.1) / len(slides), text=f"Slide {i+1}/{len(slides)}: {s['heading'][:40]}…")
            imgs = generate_images_for_slide(
                s.get("image_prompt", s["heading"]),
                imgs_per_slide,
                hf_token,
                hf_model,
            )
            st.session_state.generated_images[i] = imgs
            # default: pick first
            if imgs:
                st.session_state.selected_images[i] = imgs[0]
            prog.progress((i + 1) / len(slides))
        st.success("✅ Images generated!")

    # Show selection UI per slide
    st.markdown("---")
    st.markdown("### Select one image per slide (or leave blank for text-only)")
    for i, s in enumerate(slides):
        st.markdown(f"**Slide {i+1}: {s['heading']}**")
        imgs = st.session_state.generated_images.get(i, [])
        if imgs:
            cols = st.columns(min(len(imgs), 5))
            for j, img in enumerate(imgs):
                with cols[j]:
                    st.image(img, use_container_width=True)
                    if st.button(f"✔ Use", key=f"sel_{i}_{j}"):
                        st.session_state.selected_images[i] = img
                        st.rerun()
            cur = st.session_state.selected_images.get(i)
            if cur:
                st.caption(f"✅ Image selected for this slide")
        else:
            st.caption("No images generated for this slide yet.")

        # Allow image upload as override
        up = st.file_uploader(f"Or upload your own image (slide {i+1})", type=["png","jpg","jpeg"], key=f"up_{i}")
        if up:
            st.session_state.selected_images[i] = Image.open(up)

        st.markdown("---")

    nav_buttons(prev_step=2)
    if st.button("🎨 Next → Style & Preview Slides"):
        st.session_state.step = 4
        st.rerun()


def page_step4_style():
    step_badge(4, "Style & Preview Slides")
    progress_bar(4)

    sc = st.session_state.slide_content
    if not sc:
        nav_buttons(prev_step=3)
        return

    c1, c2 = st.columns([2, 3])
    with c1:
        theme_name = st.selectbox(
            "🎨 Theme", list(CFG["themes"].keys()),
            index=list(CFG["themes"].keys()).index(st.session_state.theme),
            key="theme_select",
        )
        st.session_state.theme = theme_name
        theme = CFG["themes"][theme_name]

        st.session_state.slide_duration = st.slider("⏱️ Seconds per slide (video)", 3, 15, st.session_state.slide_duration)
        st.session_state.add_audio      = st.toggle("🔊 Add narration audio", value=st.session_state.add_audio)
        if st.session_state.add_audio:
            audio_src = st.radio("Audio source", ["gTTS (Free)", "OpenAI TTS (Better quality)"], horizontal=True)
            st.session_state["audio_src"] = audio_src

    with c2:
        st.markdown("#### 👁️ Slide Preview")
        slides = sc.get("slides", [])
        preview_idx = st.selectbox("Preview slide #", range(1, len(slides) + 1), key="preview_idx")
        slide_data  = slides[preview_idx - 1]
        bg_img      = st.session_state.selected_images.get(preview_idx - 1)
        preview     = render_slide_pil(slide_data, bg_img, theme, preview_idx, len(slides))
        st.image(preview, use_container_width=True)

    nav_buttons(prev_step=3)
    if st.button("🎬 Build Video & Audio"):
        st.session_state.step = 5
        st.rerun()


def page_step5_video():
    step_badge(5, "Generate Video & Audio")
    progress_bar(5)

    sc = st.session_state.slide_content
    if not sc:
        nav_buttons(prev_step=4)
        return

    slides = sc.get("slides", [])
    theme  = CFG["themes"][st.session_state.theme]
    lang_cfg = CFG["languages"][st.session_state.language]

    if not MOVIEPY_OK:
        st.warning("⚠️ MoviePy not installed. Only PPTX & slide images will be exported.")
    if not GTTS_OK and not OPENAI_OK:
        st.warning("⚠️ Neither gTTS nor OpenAI TTS available. Video will have no audio.")

    build_btn = st.button("🚀 Build Everything Now")
    if build_btn:
        prog = st.progress(0.0, text="Rendering slides…")

        # 1) Render all slides as PIL images
        slide_imgs = []
        for i, sd in enumerate(slides):
            prog.progress(i / (len(slides) * 3), text=f"Rendering slide {i+1}…")
            img = render_slide_pil(sd, st.session_state.selected_images.get(i), theme, i+1, len(slides))
            slide_imgs.append(img)

        # 2) Create PPTX
        prog.progress(0.35, text="Creating PPTX…")
        pptx_bytes = create_pptx(sc, st.session_state.selected_images, theme, st.session_state.theme)
        pptx_path = os.path.join(tempfile.gettempdir(), "yt_slides.pptx")
        with open(pptx_path, "wb") as f:
            f.write(pptx_bytes)
        st.session_state.pptx_path = pptx_path

        # 3) Generate audio
        audio_files = [None] * len(slides)
        if st.session_state.add_audio:
            prog.progress(0.45, text="Generating audio narration…")
            audio_src = st.session_state.get("audio_src", "gTTS (Free)")
            for i, sd in enumerate(slides):
                prog.progress(0.45 + 0.25 * i / len(slides), text=f"Audio slide {i+1}…")
                text = sd.get("speaker_notes") or sd.get("content", "")
                apath = os.path.join(tempfile.gettempdir(), f"audio_slide_{i}.mp3")
                if "OpenAI" in audio_src and st.session_state.openai_api_key:
                    ok = generate_audio_openai(text, apath, st.session_state.openai_api_key)
                else:
                    ok = generate_audio_gtts(text, lang_cfg["gtts_code"], apath)
                audio_files[i] = apath if ok else None

        # 4) Build video
        video_path = None
        if MOVIEPY_OK:
            prog.progress(0.72, text="Compiling video (this may take a while)…")
            video_path = os.path.join(tempfile.gettempdir(), "yt_video.mp4")
            ok = build_video(slides, slide_imgs, audio_files, st.session_state.slide_duration, video_path)
            if ok:
                st.session_state.video_path = video_path
            else:
                st.warning("Video build failed — check FFmpeg installation.")

        # 5) Save slide images
        st.session_state["slide_imgs"] = slide_imgs

        prog.progress(1.0, text="Done!")
        st.success("✅ All assets ready!")
        st.rerun()

    # ── Downloads section ──
    if st.session_state.pptx_path and os.path.exists(st.session_state.pptx_path):
        st.markdown("---")
        st.markdown("### 📥 Download Assets")
        dc1, dc2, dc3 = st.columns(3)

        with open(st.session_state.pptx_path, "rb") as f:
            dc1.download_button("⬇️ Download PPTX", f.read(), "youtube_slides.pptx",
                                mime="application/vnd.openxmlformats-officedocument.presentationml.presentation")

        # Slide images zip
        if st.session_state.get("slide_imgs"):
            zip_buf = io.BytesIO()
            with zipfile.ZipFile(zip_buf, "w") as zf:
                for i, img in enumerate(st.session_state["slide_imgs"]):
                    ibuf = io.BytesIO()
                    img.save(ibuf, format="PNG")
                    zf.writestr(f"slide_{i+1:02d}.png", ibuf.getvalue())
            dc2.download_button("⬇️ Download Slides (ZIP)", zip_buf.getvalue(),
                                "slide_images.zip", mime="application/zip")

        if st.session_state.video_path and os.path.exists(st.session_state.video_path):
            with open(st.session_state.video_path, "rb") as f:
                dc3.download_button("⬇️ Download MP4 Video", f.read(),
                                    "youtube_video.mp4", mime="video/mp4")
            st.video(st.session_state.video_path)

    nav_buttons(prev_step=4)
    if st.button("📊 Generate YouTube Metadata →"):
        st.session_state.step = 6
        st.rerun()


def page_step6_meta():
    step_badge(6, "YouTube Metadata & SEO")
    progress_bar(6)

    sc = st.session_state.slide_content
    if not sc:
        nav_buttons(prev_step=5)
        return

    category = st.selectbox("📂 YouTube Category", CFG["youtube_categories"])

    gen_meta_btn = st.button("🤖 Generate YouTube Metadata")
    if gen_meta_btn:
        with st.spinner("Generating SEO metadata…"):
            meta = generate_youtube_meta(
                sc, st.session_state.language, category,
                st.session_state.groq_api_key,
                st.session_state.get("selected_groq_model", CFG["groq"]["default_model"]),
            )
        if meta:
            st.session_state.youtube_meta = meta

    meta = st.session_state.youtube_meta
    if meta:
        st.markdown("---")
        c1, c2 = st.columns([3, 2])
        with c1:
            st.markdown("#### 📝 Title")
            title = st.text_input("YouTube Title", value=meta.get("title", ""), key="yt_title")
            meta["title"] = title

            st.markdown("#### 📄 Description")
            desc = st.text_area("YouTube Description", value=meta.get("description", ""), height=200, key="yt_desc")
            meta["description"] = desc

            st.markdown("#### 🏷️ Tags")
            tags = meta.get("tags", [])
            tags_html = "".join(f'<span class="meta-tag">{t}</span>' for t in tags)
            st.markdown(tags_html, unsafe_allow_html=True)
            tags_edit = st.text_area("Edit tags (comma-separated)", value=", ".join(tags), height=80, key="yt_tags")
            meta["tags"] = [t.strip() for t in tags_edit.split(",") if t.strip()]

        with c2:
            st.markdown("#### # Hashtags")
            hashtags = meta.get("hashtags", [])
            ht_html = "".join(f'<span class="meta-tag">{h}</span>' for h in hashtags)
            st.markdown(ht_html, unsafe_allow_html=True)

            st.markdown("#### 🖼️ Thumbnail Text")
            st.info(f"**{meta.get('thumbnail_text', '')}**\n\n{meta.get('thumbnail_subtext', '')}")

            st.markdown("#### 🔍 SEO Keywords")
            kw_html = "".join(f'<span class="meta-tag">{k}</span>' for k in meta.get("seo_keywords", []))
            st.markdown(kw_html, unsafe_allow_html=True)

        st.session_state.youtube_meta = meta
        st.markdown("---")

        # Export JSON
        export = {
            "video_info": {
                "title": meta.get("title"),
                "description": meta.get("description"),
                "tags": meta.get("tags"),
                "hashtags": meta.get("hashtags"),
                "category": meta.get("category"),
                "thumbnail_text": meta.get("thumbnail_text"),
                "thumbnail_subtext": meta.get("thumbnail_subtext"),
                "seo_keywords": meta.get("seo_keywords"),
            },
            "slides": sc.get("slides", []),
        }
        st.download_button(
            "⬇️ Download Metadata JSON",
            data=json.dumps(export, ensure_ascii=False, indent=2),
            file_name="youtube_metadata.json",
            mime="application/json",
        )

    nav_buttons(prev_step=5)


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
def sidebar():
    with st.sidebar:
        st.markdown("## 🎬 YouTube Slide Creator")
        st.markdown("---")

        # Step navigation
        st.markdown("### 📍 Steps")
        step_labels = {
            1: "📝 Topic & Settings",
            2: "✏️ Review Content",
            3: "🖼️ Images",
            4: "🎨 Style & Preview",
            5: "🎬 Build Video",
            6: "📊 YouTube Meta",
        }
        for n, label in step_labels.items():
            is_cur = st.session_state.step == n
            has_data = _step_ready(n)
            color = "#FFA500" if is_cur else ("#00E676" if has_data else "rgba(255,255,255,0.4)")
            icon  = "▶" if is_cur else ("✓" if has_data else "○")
            if st.sidebar.button(f"{icon} {label}", key=f"nav_{n}",
                                  disabled=(not _step_accessible(n)),
                                  use_container_width=True):
                st.session_state.step = n
                st.rerun()

        st.markdown("---")
        st.markdown("### ⚙️ Status")
        st.markdown(f"🤖 Groq: {'<span class=\'status-ok\'>✓</span>' if GROQ_OK else '<span class=\'status-err\'>✗</span>'}", unsafe_allow_html=True)
        st.markdown(f"🖼️ HF:  {'<span class=\'status-ok\'>✓</span>' if HF_OK else '<span class=\'status-err\'>✗</span>'}", unsafe_allow_html=True)
        st.markdown(f"🔊 TTS: {'<span class=\'status-ok\'>✓ gTTS</span>' if GTTS_OK else '<span class=\'status-warn\'>✗ install gtts</span>'}", unsafe_allow_html=True)
        st.markdown(f"🎬 MP4: {'<span class=\'status-ok\'>✓ MoviePy</span>' if MOVIEPY_OK else '<span class=\'status-warn\'>✗ install moviepy</span>'}", unsafe_allow_html=True)

        st.markdown("---")
        if st.button("🔄 Start Over", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

        if st.button("📥 Download Fonts (Hindi support)", use_container_width=True):
            results = download_fonts()
            for r in results:
                st.write(r)

        st.markdown("---")
        st.caption("Free tier APIs: Groq + HuggingFace\nBuilt with ❤️ using Streamlit")


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
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    inject_css()
    init_state()
    sidebar()

    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🎬 YouTube Slide Video Creator</h1>
        <p>Idea → AI Content → Images → Slides → Video → YouTube SEO &nbsp;|&nbsp;
        English • हिंदी • Hinglish</p>
    </div>
    """, unsafe_allow_html=True)

    step = st.session_state.step
    if   step == 1: page_step1_setup()
    elif step == 2: page_step2_content()
    elif step == 3: page_step3_images()
    elif step == 4: page_step4_style()
    elif step == 5: page_step5_video()
    elif step == 6: page_step6_meta()


if __name__ == "__main__":
    main()
