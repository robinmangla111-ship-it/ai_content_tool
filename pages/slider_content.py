"""
🏖️ Slider Content Creator (PRO DESIGN)
Pipeline: Idea → AI Content → Pro HTML Slides → Screenshots → Video → Metadata
Supports English, Hindi, Hinglish
Uses Tailwind HTML + Playwright screenshot for Canva-like design
"""

import streamlit as st
import os, json, re, io, tempfile, zipfile
from pathlib import Path
from typing import Optional, List, Dict
import yaml
import random
import numpy as np
from PIL import Image, ImageFilter

import os
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"
# PPTX
from pptx import Presentation
from pptx.util import Inches

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
    from moviepy.editor import (
        ImageClip, concatenate_videoclips, vfx,
        AudioFileClip
    )
    MOVIEPY_OK = True
except ImportError:
    MOVIEPY_OK = False

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
        "youtube_meta": None,
        "groq_api_key": get_env_key("GROQ_API_KEY"),
        "hf_token": get_env_key("HF_TOKEN"),
        "selected_groq_model": None,
        "png_paths": [],
        "video_path": None,
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


def progress_bar(current: int, total: int = 5):
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
- Only image_prompt MUST be in English.

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
        "template": "luxury_offer / itinerary / minimal_quote / bold_typography / split_modern / price_focus / comparison / checklist_card / devotional_glow / health_tip",
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
# OPTIONAL HF IMAGE GENERATION (NOT USED BY DEFAULT)
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
    accent = (accent or "").lower().strip()

    if accent == "pink":
        return ("#fb7185", "#f472b6")
    if accent == "blue":
        return ("#38bdf8", "#6366f1")
    if accent == "green":
        return ("#22c55e", "#10b981")
    if accent == "red":
        return ("#fb7185", "#ef4444")
    return ("#fbbf24", "#f97316")


def build_slide_html(slide: Dict, bg_img_path: Optional[str] = None) -> str:
    heading = slide.get("heading", "")
    subheading = slide.get("subheading", "")
    content = slide.get("content", "").split("\\n")
    highlight = slide.get("highlight", "")
    cta = slide.get("cta", "")
    price = slide.get("price", "")

    design = slide.get("design", {})
    template = design.get("template", "")
    accent = design.get("accent", "gold")
    text_align = design.get("text_align", "left")

    all_templates = [
        "luxury_offer", "itinerary", "minimal_quote", "bold_typography",
        "split_modern", "price_focus", "comparison", "checklist_card",
        "devotional_glow", "health_tip"
    ]
    if template not in all_templates:
        template = random.choice(all_templates)

    c1, c2 = _accent_colors(accent)
    align_class = "text-center items-center" if text_align == "center" else "text-left items-start"

    bg_style = ""
    if bg_img_path and os.path.exists(bg_img_path):
        bg_style = f"background-image:url('file://{bg_img_path}'); background-size:cover; background-position:center;"

    def bullets(lines, icon="✔"):
        out = ""
        for ln in lines:
            ln = ln.strip()
            if not ln:
                continue
            out += f"""
            <div class="flex gap-4 items-start">
                <div class="text-[48px] font-extrabold" style="color:{c1}">{icon}</div>
                <div class="text-[46px] font-semibold text-white/90 leading-snug">{ln}</div>
            </div>
            """
        return out

    if template == "luxury_offer":
        body_block = f"""
        <div class="absolute inset-0 bg-gradient-to-b from-black/60 via-black/40 to-black/75"></div>

        <div class="relative px-16 pt-20 flex flex-col justify-between h-full">
            <div>
                <div class="inline-flex items-center gap-3 px-10 py-4 rounded-full font-extrabold text-black text-[38px] shadow-2xl"
                     style="background:linear-gradient(90deg,{c1},{c2});">
                    ✨ {highlight or "LIMITED OFFER"}
                </div>

                <div class="mt-10 text-[100px] font-extrabold leading-[1.02] tracking-tight drop-shadow-2xl">
                    {heading}
                </div>

                <div class="mt-6 text-[50px] font-semibold text-white/80 max-w-[900px]">
                    {subheading}
                </div>
            </div>

            <div class="mb-20 bg-white/10 backdrop-blur-2xl border border-white/15 rounded-[60px] p-14 shadow-2xl">
                <div class="space-y-8">
                    {bullets(content[:5], "✔")}
                </div>

                <div class="mt-12 flex justify-between items-center">
                    <div class="text-[68px] font-extrabold" style="color:{c1}">
                        {price}
                    </div>

                    <div class="px-14 py-5 rounded-[50px] text-[46px] font-extrabold text-black shadow-2xl"
                         style="background:linear-gradient(90deg,{c1},{c2});">
                        {cta or "BOOK NOW"}
                    </div>
                </div>
            </div>
        </div>
        """

    elif template == "itinerary":
        items_html = ""
        for idx, line in enumerate(content[:6], start=1):
            items_html += f"""
            <div class="flex gap-5 items-start">
                <div class="w-[72px] h-[72px] rounded-2xl flex items-center justify-center font-extrabold text-[38px] text-black shadow-xl"
                     style="background:linear-gradient(90deg,{c1},{c2});">
                    {idx}
                </div>
                <div class="text-[46px] font-semibold text-white/90 leading-snug">{line}</div>
            </div>
            """

        body_block = f"""
        <div class="absolute inset-0 bg-gradient-to-b from-black/65 via-black/40 to-black/80"></div>

        <div class="relative px-16 pt-20">
            <div class="flex justify-between items-start">
                <div>
                    <div class="text-[92px] font-extrabold leading-[1.05] drop-shadow-xl">
                        {heading}
                    </div>
                    <div class="mt-6 text-[46px] text-white/80 font-semibold">
                        {subheading}
                    </div>
                </div>

                <div class="px-10 py-4 rounded-full text-[40px] font-extrabold text-black shadow-2xl"
                     style="background:linear-gradient(90deg,{c1},{c2});">
                    {highlight or "ITINERARY"}
                </div>
            </div>

            <div class="mt-20 bg-white/10 backdrop-blur-2xl border border-white/15 rounded-[55px] p-14 space-y-10 shadow-2xl">
                {items_html}
            </div>

            <div class="mt-14 flex justify-between items-center">
                <div class="text-[64px] font-extrabold" style="color:{c1}">
                    {price}
                </div>

                <div class="px-14 py-5 rounded-[50px] text-[46px] font-extrabold text-black shadow-2xl"
                     style="background:linear-gradient(90deg,{c1},{c2});">
                    {cta or "BOOK NOW"}
                </div>
            </div>
        </div>
        """

    elif template == "minimal_quote":
        body_block = f"""
        <div class="absolute inset-0 bg-black/70"></div>

        <div class="relative flex flex-col justify-center h-full px-20 {align_class}">
            <div class="text-[110px] font-extrabold leading-[1.05] tracking-tight drop-shadow-2xl">
                {heading}
            </div>

            <div class="mt-10 text-white/85 text-[50px] font-semibold max-w-[900px] leading-snug">
                {" ".join(content[:3])}
            </div>

            <div class="mt-16 px-14 py-5 rounded-full font-extrabold text-black text-[44px] shadow-2xl"
                 style="background:linear-gradient(90deg,{c1},{c2});">
                {cta or "FOLLOW FOR MORE"}
            </div>
        </div>
        """

    elif template == "bold_typography":
        body_block = f"""
        <div class="absolute inset-0 bg-gradient-to-tr from-black/80 via-black/40 to-black/90"></div>

        <div class="relative flex flex-col justify-between h-full px-16 pt-20 pb-20">
            <div>
                <div class="text-[130px] font-extrabold leading-[0.95] tracking-tight drop-shadow-2xl">
                    {heading}
                </div>
                <div class="mt-8 text-[52px] font-semibold text-white/80 max-w-[950px]">
                    {subheading}
                </div>
            </div>

            <div class="bg-white/10 backdrop-blur-2xl border border-white/15 rounded-[55px] p-14 shadow-2xl space-y-8">
                {bullets(content[:4], "➤")}
            </div>

            <div class="flex justify-between items-center mt-12">
                <div class="px-10 py-4 rounded-full font-extrabold text-black text-[40px] shadow-2xl"
                     style="background:linear-gradient(90deg,{c1},{c2});">
                    {highlight or "TRENDING"}
                </div>
                <div class="text-[62px] font-extrabold" style="color:{c1}">
                    {price}
                </div>
            </div>
        </div>
        """

    elif template == "split_modern":
        body_block = f"""
        <div class="absolute inset-0 bg-gradient-to-b from-black/30 via-black/60 to-black/85"></div>

        <div class="relative grid grid-cols-2 h-full">
            <div class="p-16 flex flex-col justify-between">
                <div>
                    <div class="inline-block px-10 py-4 rounded-full font-extrabold text-black text-[38px] shadow-2xl"
                         style="background:linear-gradient(90deg,{c1},{c2});">
                        {highlight or "SPECIAL DEAL"}
                    </div>

                    <div class="mt-10 text-[88px] font-extrabold leading-[1.05] drop-shadow-2xl">
                        {heading}
                    </div>

                    <div class="mt-6 text-[48px] font-semibold text-white/80">
                        {subheading}
                    </div>
                </div>

                <div class="text-[66px] font-extrabold" style="color:{c1}">
                    {price}
                </div>
            </div>

            <div class="p-16 flex flex-col justify-end">
                <div class="bg-white/10 backdrop-blur-2xl border border-white/15 rounded-[60px] p-14 shadow-2xl space-y-8">
                    {bullets(content[:5], "✔")}
                </div>

                <div class="mt-10 px-14 py-5 rounded-[50px] text-[46px] font-extrabold text-black shadow-2xl text-center"
                     style="background:linear-gradient(90deg,{c1},{c2});">
                    {cta or "BOOK NOW"}
                </div>
            </div>
        </div>
        """

    elif template == "price_focus":
        body_block = f"""
        <div class="absolute inset-0 bg-gradient-to-b from-black/75 via-black/40 to-black/90"></div>

        <div class="relative flex flex-col justify-center h-full px-16 text-center items-center">
            <div class="px-12 py-5 rounded-full font-extrabold text-black text-[42px] shadow-2xl"
                 style="background:linear-gradient(90deg,{c1},{c2});">
                {highlight or "FLASH SALE"}
            </div>

            <div class="mt-12 text-[110px] font-extrabold leading-[1.0] drop-shadow-2xl">
                {heading}
            </div>

            <div class="mt-6 text-[56px] font-semibold text-white/80 max-w-[950px]">
                {subheading}
            </div>

            <div class="mt-16 text-[140px] font-extrabold tracking-tight drop-shadow-2xl"
                 style="color:{c1}">
                {price}
            </div>

            <div class="mt-14 bg-white/10 backdrop-blur-2xl border border-white/15 rounded-[60px] p-14 shadow-2xl w-full max-w-[950px] space-y-8 text-left">
                {bullets(content[:4], "✔")}
            </div>

            <div class="mt-16 px-16 py-6 rounded-[60px] text-[52px] font-extrabold text-black shadow-2xl"
                 style="background:linear-gradient(90deg,{c1},{c2});">
                {cta or "BOOK NOW"}
            </div>
        </div>
        """

    elif template == "comparison":
        left = content[:3]
        right = content[3:6]

        def block(title, lines, accent_color):
            items = ""
            for ln in lines:
                items += f"<div class='text-[42px] font-semibold text-white/90'>• {ln}</div>"
            return f"""
            <div class="bg-white/10 backdrop-blur-2xl border border-white/15 rounded-[55px] p-12 shadow-2xl">
                <div class="text-[54px] font-extrabold mb-6" style="color:{accent_color}">{title}</div>
                <div class="space-y-5">{items}</div>
            </div>
            """

        body_block = f"""
        <div class="absolute inset-0 bg-gradient-to-br from-black/80 via-black/40 to-black/90"></div>

        <div class="relative px-16 pt-20">
            <div class="text-[92px] font-extrabold drop-shadow-2xl">{heading}</div>
            <div class="mt-6 text-[48px] font-semibold text-white/80">{subheading}</div>

            <div class="mt-18 grid grid-cols-2 gap-10">
                {block("Option A", left, c1)}
                {block("Option B", right, c2)}
            </div>

            <div class="mt-16 flex justify-between items-center">
                <div class="text-[66px] font-extrabold" style="color:{c1}">
                    {price}
                </div>

                <div class="px-14 py-5 rounded-[55px] text-[46px] font-extrabold text-black shadow-2xl"
                     style="background:linear-gradient(90deg,{c1},{c2});">
                    {cta or "CHOOSE NOW"}
                </div>
            </div>
        </div>
        """

    elif template == "checklist_card":
        body_block = f"""
        <div class="absolute inset-0 bg-gradient-to-b from-black/65 via-black/40 to-black/90"></div>

        <div class="relative px-16 pt-20">
            <div class="inline-block px-10 py-4 rounded-full font-extrabold text-black text-[40px] shadow-2xl"
                 style="background:linear-gradient(90deg,{c1},{c2});">
                {highlight or "MUST KNOW"}
            </div>

            <div class="mt-10 text-[100px] font-extrabold drop-shadow-2xl leading-[1.02]">
                {heading}
            </div>

            <div class="mt-6 text-[52px] font-semibold text-white/80 max-w-[950px]">
                {subheading}
            </div>

            <div class="mt-18 bg-white/10 backdrop-blur-2xl border border-white/15 rounded-[65px] p-16 shadow-2xl space-y-10">
                {bullets(content[:6], "☑")}
            </div>

            <div class="mt-16 px-16 py-6 rounded-[60px] text-[50px] font-extrabold text-black shadow-2xl text-center"
                 style="background:linear-gradient(90deg,{c1},{c2});">
                {cta or "SAVE THIS"}
            </div>
        </div>
        """

    elif template == "devotional_glow":
        body_block = f"""
        <div class="absolute inset-0 bg-gradient-to-b from-black/80 via-black/55 to-black/90"></div>

        <div class="absolute top-[-200px] left-[-200px] w-[600px] h-[600px] rounded-full blur-[120px]"
             style="background:{c1}; opacity:0.35;"></div>

        <div class="absolute bottom-[-250px] right-[-250px] w-[700px] h-[700px] rounded-full blur-[150px]"
             style="background:{c2}; opacity:0.25;"></div>

        <div class="relative flex flex-col justify-center h-full px-16 text-center items-center">
            <div class="text-[100px] font-extrabold drop-shadow-2xl">
                {heading}
            </div>

            <div class="mt-8 text-[54px] font-semibold text-white/80 max-w-[950px]">
                {subheading}
            </div>

            <div class="mt-14 bg-white/10 backdrop-blur-2xl border border-white/15 rounded-[65px] p-16 shadow-2xl space-y-10 w-full max-w-[950px]">
                <div class="text-[50px] font-semibold text-white/90 leading-snug">
                    {" ".join(content[:4])}
                </div>
            </div>

            <div class="mt-16 px-16 py-6 rounded-[60px] text-[52px] font-extrabold text-black shadow-2xl"
                 style="background:linear-gradient(90deg,{c1},{c2});">
                {cta or "🙏 जय श्री राम"}
            </div>
        </div>
        """

    else:  # health_tip
        body_block = f"""
        <div class="absolute inset-0 bg-gradient-to-b from-black/75 via-black/45 to-black/90"></div>

        <div class="relative px-16 pt-20">
            <div class="inline-block px-10 py-4 rounded-full font-extrabold text-black text-[40px] shadow-2xl"
                 style="background:linear-gradient(90deg,{c1},{c2});">
                {highlight or "HEALTH TIP"}
            </div>

            <div class="mt-10 text-[100px] font-extrabold drop-shadow-2xl leading-[1.02]">
                {heading}
            </div>

            <div class="mt-6 text-[52px] font-semibold text-white/80 max-w-[950px]">
                {subheading}
            </div>

            <div class="mt-18 bg-white/10 backdrop-blur-2xl border border-white/15 rounded-[65px] p-16 shadow-2xl space-y-10">
                {bullets(content[:6], "✔")}
            </div>

            <div class="mt-16 px-16 py-6 rounded-[60px] text-[50px] font-extrabold text-black shadow-2xl text-center"
                 style="background:linear-gradient(90deg,{c1},{c2});">
                {cta or "SAVE THIS"}
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
          filter: contrast(1.1) saturate(1.1);
        }}
        .grain {{
          position:absolute;
          inset:0;
          background-image:url("https://grainy-gradients.vercel.app/noise.svg");
          opacity:0.14;
          mix-blend-mode:overlay;
        }}
        .vignette {{
          position:absolute;
          inset:0;
          background: radial-gradient(circle at center, rgba(0,0,0,0.15), rgba(0,0,0,0.85));
        }}
      </style>
    </head>
    <body>
      <div class="bg"></div>
      <div class="grain"></div>
      <div class="vignette"></div>

      {body_block}

      <div class="absolute bottom-8 left-14 text-white/40 text-[34px] font-semibold">
        Premium Shorts • Slide Design
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
        st.error("Playwright not installed.")
        return False

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            page = browser.new_page(viewport={"width": 1080, "height": 1920})
            page.set_content(html, wait_until="networkidle")
            page.wait_for_timeout(1500)
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
# VIDEO BUILDER (CINEMATIC)
# ─────────────────────────────────────────────────────────────────────────────
def ken_burns_effect(clip, zoom=1.12, pan_x=0.06, pan_y=0.04, direction="in"):
    w, h = clip.size

    def make_frame(t):
        frame = clip.get_frame(t)
        img = Image.fromarray(frame)

        progress = t / clip.duration

        if direction == "out":
            z = zoom - (zoom - 1) * progress
        else:
            z = 1 + (zoom - 1) * progress

        new_w = int(w * z)
        new_h = int(h * z)

        img = img.resize((new_w, new_h), Image.LANCZOS)

        dx = int((new_w - w) * pan_x * progress)
        dy = int((new_h - h) * pan_y * progress)

        img = img.crop((dx, dy, dx + w, dy + h))
        return np.array(img)

    return clip.fl(make_frame, apply_to=["mask"])


def motion_blur_effect(clip, blur_strength=2):
    def blur_frame(get_frame, t):
        frame = get_frame(t)
        img = Image.fromarray(frame)
        img = img.filter(ImageFilter.GaussianBlur(radius=blur_strength))
        return np.array(img)

    return clip.fl(blur_frame)


def swipe_transition(clip1, clip2, duration=0.5, direction="left"):
    w, h = clip1.size
    clip2 = clip2.set_start(clip1.duration - duration)

    def make_frame(t):
        if t < clip1.duration - duration:
            return clip1.get_frame(t)

        tt = (t - (clip1.duration - duration)) / duration
        tt = min(max(tt, 0), 1)

        f1 = clip1.get_frame(t)
        f2 = clip2.get_frame(t - (clip1.duration - duration))

        if direction == "left":
            x = int(w * tt)
            out = np.zeros_like(f1)
            out[:, :w-x] = f1[:, x:]
            out[:, w-x:] = f2[:, :x]

        elif direction == "right":
            x = int(w * tt)
            out = np.zeros_like(f1)
            out[:, x:] = f1[:, :w-x]
            out[:, :x] = f2[:, w-x:]

        elif direction == "up":
            y = int(h * tt)
            out = np.zeros_like(f1)
            out[:h-y, :] = f1[y:, :]
            out[h-y:, :] = f2[:y, :]

        else:  # down
            y = int(h * tt)
            out = np.zeros_like(f1)
            out[y:, :] = f1[:h-y, :]
            out[:y, :] = f2[h-y:, :]

        return out

    return ImageClip(make_frame, duration=clip1.duration)


def build_video_from_pngs(
    png_paths: List[str],
    duration: int,
    output_path: str,
    bg_music_path: Optional[str] = None,
    music_volume: float = 0.15
) -> bool:
    if not MOVIEPY_OK:
        return False

    clips = []
    for path in png_paths:
        base = ImageClip(path).set_duration(duration)

        direction = random.choice(["in", "out"])
        zoom = random.choice([1.08, 1.12, 1.15])
        pan_x = random.choice([0.0, 0.05, 0.1])
        pan_y = random.choice([0.0, 0.03, 0.06])

        animated = ken_burns_effect(base, zoom=zoom, pan_x=pan_x, pan_y=pan_y, direction=direction)

        if random.random() > 0.6:
            animated = motion_blur_effect(animated, blur_strength=random.choice([1, 2, 3]))

        animated = animated.fx(vfx.fadein, 0.25).fx(vfx.fadeout, 0.25)
        clips.append(animated)

    merged = clips[0]
    for i in range(1, len(clips)):
        swipe_dir = random.choice(["left", "right", "up", "down"])
        merged = swipe_transition(merged, clips[i], duration=0.5, direction=swipe_dir)

    final = merged

    if bg_music_path and os.path.exists(bg_music_path):
        music = AudioFileClip(bg_music_path).volumex(music_volume)

        if music.duration < final.duration:
            loops = int(final.duration // music.duration) + 1
            music = concatenate_videoclips([music] * loops).audio

        music = music.subclip(0, final.duration)
        final = final.set_audio(music)

    final.write_videofile(
        output_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
        bitrate="9000k",
        threads=4,
        logger=None
    )

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
    step_badge(2, "Review, Edit & Upload Images")
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

            up = st.file_uploader(
                f"📷 Upload Background Image (Slide {i+1})",
                type=["png", "jpg", "jpeg"],
                key=f"upload_slide_{i}"
            )

            if up:
                img_path = str(Path(tempfile.gettempdir()) / f"user_slide_{i+1:02d}.png")
                with open(img_path, "wb") as f:
                    f.write(up.getbuffer())

                slides[i]["uploaded_bg"] = img_path
                st.success("✅ Image attached to slide!")

            if slides[i].get("uploaded_bg") and os.path.exists(slides[i]["uploaded_bg"]):
                st.image(slides[i]["uploaded_bg"], caption="Selected Background", use_container_width=True)

    sc["slides"] = slides
    st.session_state.slide_content = sc

    if st.button("➡ Next: Render Pro Slides"):
        st.session_state.step = 3
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3
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

            for old in out_dir.glob("slide_*.png"):
                try:
                    old.unlink()
                except:
                    pass

            png_paths = []
            for i, slide in enumerate(slides):
                bg_img = slide.get("uploaded_bg")
                html = build_slide_html(slide, bg_img_path=bg_img)

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
    step_badge(4, "Export Assets (PNG / PPTX / MP4)")
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
    st.download_button(
        "⬇️ Download PPTX",
        pptx_bytes,
        "slider_slides.pptx",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )

    st.markdown("---")
    st.markdown("### 🎵 Optional Background Music")
    bg_music = st.file_uploader("Upload MP3", type=["mp3"])
    music_path = None

    if bg_music:
        music_path = str(Path(tempfile.gettempdir()) / "bg_music.mp3")
        with open(music_path, "wb") as f:
            f.write(bg_music.getbuffer())
        st.success("✅ Music uploaded!")

    st.markdown("---")
    if MOVIEPY_OK:
        duration = st.slider("Seconds per slide (video)", 2, 10, 5)

        if st.button("🎬 Build Cinematic MP4 Video"):
            out_mp4 = str(Path(tempfile.gettempdir()) / "slider_video.mp4")

            with st.spinner("Creating cinematic video with transitions..."):
                ok = build_video_from_pngs(png_paths, duration, out_mp4, bg_music_path=music_path)

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
