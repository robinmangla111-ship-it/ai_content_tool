"""
🏖️ Slider Content Creator (PRO DESIGN)
Pipeline: Idea → AI Content → Pro HTML Slides → Screenshots → Video → Metadata
Supports English, Hindi, Hinglish
Uses Tailwind HTML + Playwright screenshot for Canva-like design
"""

import streamlit as st
import os, json, re, io, time, tempfile, zipfile
from pathlib import Path
from typing import Optional, List, Dict
import yaml
import requests

# PPTX
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

# Optional imports
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
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips
    MOVIEPY_OK = True
except ImportError:
    MOVIEPY_OK = False

try:
    from gtts import gTTS
    GTTS_OK = True
except ImportError:
    GTTS_OK = False

try:
    from openai import OpenAI
    OPENAI_OK = True
except ImportError:
    OPENAI_OK = False

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_OK = True
except ImportError:
    PLAYWRIGHT_OK = False


# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"

@st.cache_resource
def load_config():
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

CFG = load_config()


def get_env_key(name: str) -> str:
    return os.getenv(name, "").strip()


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "step": 1,
        "topic": "",
        "language": "English",
        "content_category": "Travel",
        "num_slides": 5,
        "slide_content": None,
        "generated_images": {},
        "selected_images": {},
        "theme": "Luxury Travel",
        "slide_duration": 5,
        "add_audio": False,
        "audio_src": "gTTS (Free)",
        "video_path": None,
        "pptx_path": None,
        "youtube_meta": None,
        "slide_imgs": None,
        "groq_api_key": get_env_key("GROQ_API_KEY"),
        "hf_token": get_env_key("HF_TOKEN"),
        "openai_api_key": get_env_key("OPENAI_API_KEY"),
        "selected_groq_model": None,
    }

    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700;800&family=Noto+Sans:wght@400;700;800&display=swap');
    html, body, [class*="css"] {
        font-family: 'Montserrat', 'Noto Sans', sans-serif;
    }

    .main-header {
        background: linear-gradient(135deg, #111827 0%, #1f2937 50%, #0b1220 100%);
        padding: 1.8rem 2rem;
        border-radius: 18px;
        margin-bottom: 1.5rem;
        border: 1px solid rgba(255,165,0,0.25);
        box-shadow: 0 8px 30px rgba(0,0,0,0.35);
    }
    .main-header h1 {
        color: #fbbf24;
        font-size: 2rem;
        margin: 0;
        font-weight: 800;
        letter-spacing: 0.5px;
    }
    .main-header p {
        color: rgba(255,255,255,0.7);
        margin: 0.4rem 0 0;
        font-size: 1rem;
    }

    .step-badge {
        display: inline-block;
        background: linear-gradient(90deg, #fbbf24, #fb7185);
        color: #000;
        font-weight: 800;
        font-size: 0.75rem;
        padding: 4px 14px;
        border-radius: 20px;
        margin-bottom: 0.6rem;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .progress-bar { display:flex; gap:6px; margin-bottom:1.5rem; }
    .progress-step { flex:1; height:6px; border-radius:3px; background:rgba(255,255,255,0.1); }
    .progress-step.done { background:#fbbf24; }
    .progress-step.active { background:rgba(251,191,36,0.55); }

    footer { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)


def progress_bar(current: int, total: int = 6):
    bars = ""
    for i in range(1, total + 1):
        cls = "done" if i < current else ("active" if i == current else "")
        bars += f'<div class="progress-step {cls}"></div>'
    st.markdown(f'<div class="progress-bar">{bars}</div>', unsafe_allow_html=True)


def step_badge(n: int, label: str):
    st.markdown(
        f'<div class="step-badge">Step {n}</div><h3 style="color:#fbbf24;margin-top:4px">{label}</h3>',
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────────────────
# JSON SAFE PARSER
# ─────────────────────────────────────────────────────────────────────────────
def _safe_json_extract(raw: str) -> Dict:
    raw = raw.strip()
    raw = re.sub(r"^```json\s*", "", raw)
    raw = re.sub(r"^```", "", raw)
    raw = re.sub(r"```$", "", raw).strip()

    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if m:
        raw = m.group()

    raw = re.sub(r"[\x00-\x1F\x7F]", "", raw)
    raw = raw.replace("“", '"').replace("”", '"').replace("’", "'")

    return json.loads(raw)


# ─────────────────────────────────────────────────────────────────────────────
# CONTENT GENERATION (GROQ)
# ─────────────────────────────────────────────────────────────────────────────
LANG_RULES = {
    "English": "Generate ALL content strictly in English.",
    "Hindi": "सभी टेक्स्ट केवल हिंदी (देवनागरी) में लिखें। अंग्रेजी बिल्कुल नहीं।",
    "Hinglish": "Write in Hinglish (Roman Hindi + English mix). Do NOT use Devanagari.",
}

CATEGORY_RULES = {
    "Travel": "Make it like a professional travel ad. Include packages, highlights, CTA, luxury tone.",
    "Health": "Make it educational and safe. Add do/don't and short disclaimer.",
    "Devotion": "Make it spiritual and devotional. Use bhakti tone.",
    "Finance": "Make it actionable and clear. Add disclaimer 'Not financial advice'.",
    "Motivation": "Make it punchy, viral, reels-style.",
    "Education": "Make it structured and simple to learn.",
    "General": "Make it engaging and useful.",
}


def generate_slide_content(topic: str, language: str, num_slides: int, api_key: str, model: str, category: str) -> Optional[Dict]:
    if not GROQ_OK:
        st.error("Groq library not installed.")
        return None

    lang_instr = LANG_RULES.get(language, LANG_RULES["English"])
    cat_instr = CATEGORY_RULES.get(category, CATEGORY_RULES["General"])

    prompt = f"""
{lang_instr}

You are a professional YouTube Shorts + Instagram Reels creative director.
You create premium slider posters like Canva Pro templates.

CATEGORY: {category}
CATEGORY STYLE: {cat_instr}

TOPIC: "{topic}"

Generate exactly {num_slides} slides.

STRICT RULES:
- All text fields MUST be in {language}.
- Hindi MUST be only Devanagari.
- Hinglish MUST be only Roman script.
- Do NOT include English unless language=English.
- Do NOT use raw newlines inside JSON strings.
- Use \\n inside content and speaker_notes.

Only image_prompt MUST be in English.

Return ONLY VALID JSON:

{{
  "title": "...",
  "description_short": "...",
  "category": "{category}",
  "slides": [
    {{
      "slide_number": 1,
      "heading": "...",
      "subheading": "...",
      "content": "Line1\\nLine2\\nLine3",
      "highlight": "Offer/Hook Badge",
      "cta": "BOOK NOW / SAVE THIS / FOLLOW",
      "price": "optional price like ₹19,999",
      "speaker_notes": "Line1\\nLine2",
      "image_prompt": "English cinematic photo prompt",
      "design": {{
        "template": "luxury_offer / itinerary / minimal_quote / bold_typography / split_modern",
        "accent": "gold / pink / blue / green / red",
        "text_align": "left/center"
      }}
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


# ─────────────────────────────────────────────────────────────────────────────
# YOUTUBE META
# ─────────────────────────────────────────────────────────────────────────────
def generate_youtube_meta(slide_content: Dict, language: str, category: str, api_key: str, model: str) -> Optional[Dict]:
    if not GROQ_OK:
        return None

    lang_instr = LANG_RULES.get(language, LANG_RULES["English"])

    slides_summary = "\n".join(
        f"Slide {s['slide_number']}: {s['heading']}" for s in slide_content.get("slides", [])
    )

    prompt = f"""
{lang_instr}

Create SEO metadata for YouTube Shorts + Instagram Reels.

Slides:
{slides_summary}

Return ONLY JSON:
{{
  "title": "...",
  "description": "...",
  "tags": ["..."],
  "hashtags": ["#..."],
  "thumbnail_text": "...",
  "thumbnail_subtext": "...",
  "seo_keywords": ["..."]
}}

Minimum:
- 20 tags
- 12 hashtags
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
# HUGGINGFACE IMAGE GENERATION (OPTIONAL)
# ─────────────────────────────────────────────────────────────────────────────
def generate_image_hf(prompt: str, hf_token: str, model_id: str):
    if not HF_OK:
        return None
    if not hf_token:
        return None

    try:
        client = InferenceClient(token=hf_token)
        img = client.text_to_image(prompt, model=model_id)
        return img
    except Exception as e:
        st.warning(f"HF image gen failed: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# HTML TEMPLATE ENGINE (TAILWIND)
# ─────────────────────────────────────────────────────────────────────────────
TAILWIND_CDN = "https://cdn.tailwindcss.com"

def _accent_colors(accent: str):
    if accent == "pink":
        return ("#fb7185", "#f472b6")
    if accent == "blue":
        return ("#38bdf8", "#6366f1")
    if accent == "green":
        return ("#22c55e", "#10b981")
    if accent == "red":
        return ("#fb7185", "#ef4444")
    return ("#fbbf24", "#f97316")  # gold/orange default


def build_slide_html(slide: Dict, bg_img_path: Optional[str] = None) -> str:
    heading = slide.get("heading", "")
    subheading = slide.get("subheading", "")
    content = slide.get("content", "").split("\\n")
    highlight = slide.get("highlight", "")
    cta = slide.get("cta", "")
    price = slide.get("price", "")

    design = slide.get("design", {})
    template = design.get("template", "luxury_offer")
    accent = design.get("accent", "gold")
    text_align = design.get("text_align", "left")

    c1, c2 = _accent_colors(accent)

    align_class = "text-center items-center" if text_align == "center" else "text-left items-start"

    bg_style = ""
    if bg_img_path and os.path.exists(bg_img_path):
        bg_style = f"background-image:url('file://{bg_img_path}'); background-size:cover; background-position:center;"

    # Templates
    if template == "minimal_quote":
        body_block = f"""
        <div class="absolute inset-0 bg-black/60"></div>
        <div class="relative flex flex-col justify-center h-full px-20 {align_class}">
            <div class="text-[90px] font-extrabold leading-[1.05] tracking-tight drop-shadow-2xl">
                {heading}
            </div>
            <div class="mt-8 text-white/85 text-[42px] font-semibold max-w-[900px] leading-snug">
                {" ".join(content[:3])}
            </div>
            <div class="mt-10 px-10 py-4 rounded-full font-bold text-black text-[38px]"
                 style="background:linear-gradient(90deg,{c1},{c2});">
                {cta or "FOLLOW FOR MORE"}
            </div>
        </div>
        """

    elif template == "itinerary":
        items_html = ""
        for line in content[:6]:
            items_html += f"""
            <div class="flex gap-4 items-start">
                <div class="w-4 h-4 rounded-full mt-4" style="background:{c1}"></div>
                <div class="text-[44px] font-semibold text-white/90 leading-snug">{line}</div>
            </div>
            """

        body_block = f"""
        <div class="absolute inset-0 bg-black/55"></div>

        <div class="relative px-16 pt-20">
            <div class="flex justify-between items-start">
                <div>
                    <div class="text-[90px] font-extrabold leading-[1.05] drop-shadow-xl">
                        {heading}
                    </div>
                    <div class="mt-6 text-[44px] text-white/80 font-semibold">
                        {subheading}
                    </div>
                </div>

                <div class="px-10 py-4 rounded-full text-[40px] font-extrabold text-black shadow-2xl"
                     style="background:linear-gradient(90deg,{c1},{c2});">
                    {highlight or "BEST DEAL"}
                </div>
            </div>

            <div class="mt-20 bg-white/10 backdrop-blur-2xl border border-white/15 rounded-[50px] p-14 space-y-8 shadow-2xl">
                {items_html}
            </div>

            <div class="mt-14 flex justify-between items-center">
                <div class="text-[60px] font-extrabold" style="color:{c1}">
                    {price}
                </div>

                <div class="px-14 py-5 rounded-[45px] text-[44px] font-extrabold text-black shadow-2xl"
                     style="background:linear-gradient(90deg,{c1},{c2});">
                    {cta or "BOOK NOW"}
                </div>
            </div>
        </div>
        """

    else:  # luxury_offer default
        items_html = ""
        for line in content[:5]:
            items_html += f"""
            <div class="flex gap-4 items-start">
                <div class="text-[46px]" style="color:{c1}">✔</div>
                <div class="text-[44px] font-semibold text-white/90 leading-snug">{line}</div>
            </div>
            """

        body_block = f"""
        <div class="absolute inset-0 bg-black/55"></div>

        <div class="relative px-16 pt-20 flex flex-col justify-between h-full">
            <div>
                <div class="inline-block px-10 py-4 rounded-full font-extrabold text-black text-[38px] shadow-2xl"
                     style="background:linear-gradient(90deg,{c1},{c2});">
                    {highlight or "LIMITED OFFER"}
                </div>

                <div class="mt-10 text-[98px] font-extrabold leading-[1.02] tracking-tight drop-shadow-2xl">
                    {heading}
                </div>

                <div class="mt-6 text-[48px] font-semibold text-white/80 max-w-[900px]">
                    {subheading}
                </div>
            </div>

            <div class="mb-20 bg-white/10 backdrop-blur-2xl border border-white/15 rounded-[60px] p-14 shadow-2xl">
                <div class="space-y-8">
                    {items_html}
                </div>

                <div class="mt-12 flex justify-between items-center">
                    <div class="text-[64px] font-extrabold" style="color:{c1}">
                        {price}
                    </div>

                    <div class="px-14 py-5 rounded-[50px] text-[44px] font-extrabold text-black shadow-2xl"
                         style="background:linear-gradient(90deg,{c1},{c2});">
                        {cta or "BOOK NOW"}
                    </div>
                </div>
            </div>
        </div>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8" />
      <script src="{TAILWIND_CDN}"></script>
      <style>
        body {{
          margin:0;
          width:1080px;
          height:1920px;
          overflow:hidden;
          font-family: 'Montserrat', 'Noto Sans', sans-serif;
        }}
        .bg {{
          position:absolute;
          inset:0;
          {bg_style}
          background-color:#0b1220;
        }}
        .grain {{
          position:absolute;
          inset:0;
          background-image:url("https://grainy-gradients.vercel.app/noise.svg");
          opacity:0.12;
          mix-blend-mode:overlay;
        }}
      </style>
    </head>
    <body>
      <div class="bg"></div>
      <div class="grain"></div>

      {body_block}

      <div class="absolute bottom-8 left-14 text-white/40 text-[34px] font-semibold">
        Slide • Premium Shorts Design
      </div>
    </body>
    </html>
    """
    return html


# ─────────────────────────────────────────────────────────────────────────────
# PLAYWRIGHT RENDER (HTML → PNG)
# ─────────────────────────────────────────────────────────────────────────────
def render_html_to_png(html: str, out_path: str) -> bool:
    if not PLAYWRIGHT_OK:
        return False

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1080, "height": 1920})
            page.set_content(html, wait_until="load")
            page.wait_for_timeout(600)  # allow fonts load
            page.screenshot(path=out_path, full_page=True)
            browser.close()
        return True
    except Exception as e:
        st.error(f"Playwright render failed: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# PPTX EXPORT
# ─────────────────────────────────────────────────────────────────────────────
def create_pptx_from_pngs(png_paths: List[str]) -> bytes:
    prs = Presentation()
    prs.slide_width = Inches(9)
    prs.slide_height = Inches(16)

    for path in png_paths:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        slide.shapes.add_picture(path, 0, 0, prs.slide_width, prs.slide_height)

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# VIDEO BUILDER
# ─────────────────────────────────────────────────────────────────────────────
def build_video_from_pngs(png_paths: List[str], duration: int, output_path: str) -> bool:
    if not MOVIEPY_OK:
        return False

    clips = []
    for pth in png_paths:
        clip = ImageClip(pth).set_duration(duration)
        clips.append(clip)

    final = concatenate_videoclips(clips, method="compose")
    final.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac", logger=None)
    final.close()
    return True


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
def sidebar():
    with st.sidebar:
        st.markdown("## 🏖️ Slider Creator PRO")
        st.markdown("---")

        st.markdown("### Status")
        st.write("Groq:", "✅" if GROQ_OK else "❌")
        st.write("HF:", "✅" if HF_OK else "❌")
        st.write("Playwright:", "✅" if PLAYWRIGHT_OK else "❌")
        st.write("MoviePy:", "✅" if MOVIEPY_OK else "❌")

        st.markdown("---")
        if st.button("🔄 Reset App"):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1
# ─────────────────────────────────────────────────────────────────────────────
def page_step1():
    step_badge(1, "Topic & Settings")
    progress_bar(1)

    c1, c2 = st.columns([3, 2])
    with c1:
        st.session_state.topic = st.text_area(
            "🎯 Enter your slider topic",
            value=st.session_state.topic,
            height=120,
            placeholder="Example: Dubai Travel Package Offer"
        )

        st.session_state.language = st.radio(
            "🌐 Language",
            ["English", "Hindi", "Hinglish"],
            index=["English", "Hindi", "Hinglish"].index(st.session_state.language),
            horizontal=True
        )

        categories = CFG.get("content_categories", ["Travel", "Health", "Devotion", "Motivation", "Finance", "Education", "General"])
        st.session_state.content_category = st.selectbox("📌 Content Type", categories)

    with c2:
        st.session_state.num_slides = st.slider("Slides", 3, 10, st.session_state.num_slides)

        models = CFG.get("groq", {}).get("models", [])
        if not models:
            st.error("No Groq models in config.yaml")
            return

        model = st.selectbox("🤖 Groq Model", models, index=0)
        st.session_state.selected_groq_model = model

        st.markdown("---")
        st.session_state.groq_api_key = st.text_input("Groq API Key", type="password", value=st.session_state.groq_api_key)
        st.session_state.hf_token = st.text_input("HF Token (optional)", type="password", value=st.session_state.hf_token)

    ready = bool(st.session_state.topic.strip() and st.session_state.groq_api_key.strip())

    if st.button("🚀 Generate Slides Content", disabled=not ready):
        with st.spinner("Generating premium content..."):
            result = generate_slide_content(
                st.session_state.topic,
                st.session_state.language,
                st.session_state.num_slides,
                st.session_state.groq_api_key,
                st.session_state.selected_groq_model,
                st.session_state.content_category
            )
        if result:
            st.session_state.slide_content = result
            st.session_state.step = 2
            st.success("✅ Content generated!")
            st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2
# ─────────────────────────────────────────────────────────────────────────────
def page_step2():
    step_badge(2, "Review & Edit")
    progress_bar(2)

    sc = st.session_state.slide_content
    if not sc:
        st.warning("No content yet.")
        return

    st.markdown(f"## {sc.get('title','')}")
    st.caption(sc.get("description_short", ""))

    slides = sc.get("slides", [])
    for i, s in enumerate(slides):
        with st.expander(f"Slide {s['slide_number']} - {s.get('heading','')}", expanded=(i == 0)):
            slides[i]["heading"] = st.text_input("Heading", value=s.get("heading", ""), key=f"h_{i}")
            slides[i]["subheading"] = st.text_input("Subheading", value=s.get("subheading", ""), key=f"sh_{i}")
            slides[i]["content"] = st.text_area("Content", value=s.get("content", ""), height=130, key=f"c_{i}")
            slides[i]["highlight"] = st.text_input("Highlight Badge", value=s.get("highlight", ""), key=f"hl_{i}")
            slides[i]["cta"] = st.text_input("CTA", value=s.get("cta", ""), key=f"cta_{i}")
            slides[i]["price"] = st.text_input("Price", value=s.get("price", ""), key=f"pr_{i}")

            slides[i]["image_prompt"] = st.text_input("Image Prompt (English)", value=s.get("image_prompt", ""), key=f"ip_{i}")

    sc["slides"] = slides
    st.session_state.slide_content = sc

    if st.button("➡ Next: Render Pro Slides"):
        st.session_state.step = 3
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 (HTML → PNG RENDER)
# ─────────────────────────────────────────────────────────────────────────────
def page_step3():
    step_badge(3, "Render Pro Slides (Tailwind + Playwright)")
    progress_bar(3)

    if not PLAYWRIGHT_OK:
        st.error("Playwright not installed. Run: pip install playwright && playwright install chromium")
        return

    sc = st.session_state.slide_content
    slides = sc.get("slides", [])

    st.info("This step renders Canva-style slides using Tailwind HTML templates.")

    if st.button("🎨 Render All Slides to PNG"):
        with st.spinner("Rendering premium designs..."):
            out_dir = Path(tempfile.gettempdir()) / "slider_html_slides"
            out_dir.mkdir(exist_ok=True)

            png_paths = []

            for i, slide in enumerate(slides):
                html = build_slide_html(slide)
                out_png = str(out_dir / f"slide_{i+1:02d}.png")

                ok = render_html_to_png(html, out_png)
                if ok:
                    png_paths.append(out_png)

            st.session_state["png_paths"] = png_paths
            st.success("✅ Slides rendered successfully!")
            st.session_state.step = 4
            st.rerun()

    if st.session_state.get("png_paths"):
        st.markdown("---")
        st.markdown("### Preview")
        for p in st.session_state["png_paths"]:
            st.image(p, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 EXPORT
# ─────────────────────────────────────────────────────────────────────────────
def page_step4():
    step_badge(4, "Export Assets")
    progress_bar(4)

    png_paths = st.session_state.get("png_paths", [])
    if not png_paths:
        st.warning("No slides rendered yet.")
        return

    st.markdown("### Download Slides ZIP")
    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, "w") as zf:
        for p in png_paths:
            zf.write(p, arcname=os.path.basename(p))

    st.download_button("⬇️ Download PNG Slides ZIP", zip_buf.getvalue(), "slider_slides.zip", "application/zip")

    st.markdown("---")

    pptx_bytes = create_pptx_from_pngs(png_paths)
    st.download_button("⬇️ Download PPTX", pptx_bytes, "slider_slides.pptx",
                       "application/vnd.openxmlformats-officedocument.presentationml.presentation")

    st.markdown("---")

    if MOVIEPY_OK:
        duration = st.slider("Seconds per slide (video)", 2, 10, 5)
        if st.button("🎬 Build MP4 Video"):
            out_mp4 = str(Path(tempfile.gettempdir()) / "slider_video.mp4")
            ok = build_video_from_pngs(png_paths, duration, out_mp4)
            if ok:
                st.session_state.video_path = out_mp4
                st.success("✅ MP4 created!")
                st.video(out_mp4)

                with open(out_mp4, "rb") as f:
                    st.download_button("⬇️ Download MP4", f.read(), "slider_video.mp4", "video/mp4")
    else:
        st.warning("MoviePy not installed. MP4 export disabled.")

    st.markdown("---")
    if st.button("➡ Next: Generate SEO Metadata"):
        st.session_state.step = 5
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 META
# ─────────────────────────────────────────────────────────────────────────────
def page_step5():
    step_badge(5, "SEO Metadata")
    progress_bar(5)

    sc = st.session_state.slide_content
    if not sc:
        st.warning("No slide content found.")
        return

    if st.button("🤖 Generate Metadata"):
        with st.spinner("Generating SEO metadata..."):
            meta = generate_youtube_meta(
                sc,
                st.session_state.language,
                st.session_state.content_category,
                st.session_state.groq_api_key,
                st.session_state.selected_groq_model
            )
        if meta:
            st.session_state.youtube_meta = meta

    meta = st.session_state.youtube_meta
    if meta:
        st.json(meta)

        export = {
            "slides": sc.get("slides", []),
            "metadata": meta
        }

        st.download_button(
            "⬇️ Download Metadata JSON",
            data=json.dumps(export, ensure_ascii=False, indent=2),
            file_name="slider_metadata.json",
            mime="application/json"
        )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN RENDER
# ─────────────────────────────────────────────────────────────────────────────
def render():
    inject_css()
    init_state()
    sidebar()

    st.markdown("""
    <div class="main-header">
        <h1>🏖️ Slider Content Creator PRO</h1>
        <p>Premium Tailwind + Playwright designs for YouTube Shorts / Instagram Reels</p>
    </div>
    """, unsafe_allow_html=True)

    step = st.session_state.step

    if step == 1:
        page_step1()
    elif step == 2:
        page_step2()
    elif step == 3:
        page_step3()
    elif step == 4:
        page_step4()
    elif step == 5:
        page_step5()
