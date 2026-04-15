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
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

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
# CONFIG
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
# CSS
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

    footer { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE
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
# CONTENT GENERATION
# ─────────────────────────────────────────────────────────────────────────────
LANG_PROMPTS = {
    "English": "Generate ALL content strictly in English.",
    "Hindi": "सभी सामग्री सख्ती से हिंदी में उत्पन्न करें। केवल देवनागरी लिपि का उपयोग करें।",
    "Hinglish": "Generate all content in Hinglish (mix Hindi + English in Roman script).",
}

def generate_slide_content(topic: str, language: str, num_slides: int, api_key: str, model: str) -> Optional[Dict]:
    if not GROQ_OK:
        st.error("Groq library not installed.")
        return None

    lang_instr = LANG_PROMPTS.get(language, LANG_PROMPTS["English"])

    prompt = f"""
{lang_instr}

Create a YouTube slide presentation about: "{topic}"
Generate exactly {num_slides} slides.

Return ONLY valid JSON (no markdown):

{{
  "title": "Video Title",
  "description_short": "One sentence hook",
  "slides": [
    {{
      "slide_number": 1,
      "heading": "Short heading",
      "content": "3-5 bullet points",
      "speaker_notes": "Narration text",
      "image_prompt": "English prompt for image generation"
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
        raw = re.sub(r"^```json\s*", "", raw)
        raw = re.sub(r"```$", "", raw).strip()

        return json.loads(raw)

    except Exception as e:
        st.error(f"Content generation failed: {e}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# UI STEPS
# ─────────────────────────────────────────────────────────────────────────────
def progress_bar(current: int, total: int = 6):
    bars = ""
    for i in range(1, total + 1):
        cls = "done" if i < current else ("active" if i == current else "")
        bars += f'<div class="progress-step {cls}"></div>'
    st.markdown(f"""
    <style>
    .progress-bar {{ display:flex; gap:6px; margin-bottom:1.5rem; }}
    .progress-step {{ flex:1; height:6px; border-radius:3px; background:rgba(255,255,255,0.1); }}
    .progress-step.done {{ background:#FFA500; }}
    .progress-step.active {{ background:rgba(255,165,0,0.5); }}
    </style>
    <div class="progress-bar">{bars}</div>
    """, unsafe_allow_html=True)


def step_badge(n: int, label: str):
    st.markdown(
        f'<div class="step-badge">Step {n}</div><h3 style="color:#FFA500;margin-top:4px">{label}</h3>',
        unsafe_allow_html=True,
    )


def page_step1():
    step_badge(1, "Topic & Settings")
    progress_bar(1)

    st.session_state.topic = st.text_area(
        "🎯 Enter Topic",
        value=st.session_state.topic,
        height=120
    )

    st.session_state.language = st.radio(
        "🌐 Language",
        ["English", "Hindi", "Hinglish"],
        index=["English", "Hindi", "Hinglish"].index(st.session_state.language),
        horizontal=True
    )

    st.session_state.num_slides = st.slider(
        "📌 Slides Count",
        3, 10, st.session_state.num_slides
    )

    st.session_state.groq_api_key = st.text_input(
        "🔑 Groq API Key",
        type="password",
        value=st.session_state.groq_api_key
    )

    model = st.selectbox("🤖 Groq Model", CFG["groq"]["models"])
    st.session_state["selected_groq_model"] = model

    ready = bool(st.session_state.topic.strip() and st.session_state.groq_api_key.strip())

    if st.button("🚀 Generate Slides", disabled=not ready):
        with st.spinner("Generating content..."):
            data = generate_slide_content(
                st.session_state.topic,
                st.session_state.language,
                st.session_state.num_slides,
                st.session_state.groq_api_key,
                model
            )

        if data:
            st.session_state.slide_content = data
            st.session_state.step = 2
            st.success("✅ Slide content generated!")
            st.rerun()


def page_step2():
    step_badge(2, "Review Content")
    progress_bar(2)

    sc = st.session_state.slide_content
    if not sc:
        st.warning("No content generated yet.")
        return

    st.markdown(f"## 🎬 {sc.get('title','')}")
    st.caption(sc.get("description_short", ""))

    for slide in sc.get("slides", []):
        with st.expander(f"Slide {slide['slide_number']} - {slide['heading']}", expanded=False):
            slide["heading"] = st.text_input(
                f"Heading (Slide {slide['slide_number']})",
                slide["heading"],
                key=f"h_{slide['slide_number']}"
            )
            slide["content"] = st.text_area(
                f"Content (Slide {slide['slide_number']})",
                slide["content"],
                height=120,
                key=f"c_{slide['slide_number']}"
            )
            slide["speaker_notes"] = st.text_area(
                f"Speaker Notes (Slide {slide['slide_number']})",
                slide.get("speaker_notes", ""),
                height=100,
                key=f"n_{slide['slide_number']}"
            )

    st.session_state.slide_content = sc

    if st.button("➡ Next Step"):
        st.session_state.step = 3
        st.rerun()


def sidebar():
    with st.sidebar:
        st.markdown("## 🏖️ Slider Creator")
        st.markdown("---")

        st.markdown("### Navigation")
        if st.button("Step 1 - Setup"): st.session_state.step = 1
        if st.button("Step 2 - Review"): st.session_state.step = 2
        if st.button("Step 3 - Next"): st.session_state.step = 3

        st.markdown("---")
        st.caption("Slider Content Creator Module")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN RENDER FUNCTION (IMPORTANT)
# ─────────────────────────────────────────────────────────────────────────────
def render():
    inject_css()
    init_state()
    sidebar()

    st.markdown("""
    <div class="main-header">
        <h1>🏖️ Slider Content Creator</h1>
        <p>Create Instagram slider content using AI (Groq + HF + Video Export)</p>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.step == 1:
        page_step1()
    elif st.session_state.step == 2:
        page_step2()
    else:
        st.info("Step 3 will be added next (images/video export).")
