"""
✈ AI Travel Content Creator  —  Production Edition
=====================================================
FREE tools:
  • HF FLUX.1-schnell / FLUX.1-dev  → AI background generation
  • Groq llama-3.3-70b              → prompt enhancement + all copy
  • Gemini 2.5 Flash (fallback)     → copy generation
  • Pillow                          → advanced compositing

NEW vs old version:
  ✦ 8 pro visual THEMES (gradient mesh, duotone, vignette, film burn)
  ✦ 5 LAYOUT templates (Magazine, Minimal, Bold, Cinematic, Story)
  ✦ Advanced typography: tracking, mixed weights, drop caps
  ✦ Decorative elements: geometric overlays, diagonal bands, corner frames
  ✦ Per-platform layout intelligence (horizontal/vertical aware)
  ✦ Accent color picker
  ✦ Full AI copy tab: all captions + scene prompts + script
  ✦ Video: scene-by-scene progress with live preview thumbnails
  ✦ Bulk: generate master once, smart-crop per platform
  ✦ Persistent brand kit (logo, cert, social, colors)
  ✦ Download: PNG, JPEG, GIF, ZIP frames, ZIP all-platforms
"""

import streamlit as st
import sys, os, io, json, re, time, base64, zipfile, math
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageChops

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ─────────────────────────────────────────────────────────────────────────────
# KEY HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get(sk, sec, env=""):
    v = st.session_state.get(sk, "").strip()
    if v: return v
    try:
        v = str(st.secrets.get(sec, "")).strip()
        if v: return v
    except Exception:
        pass
    return os.getenv(env, "").strip()

def _hf_key():     return _get("hf_token",     "HF_TOKEN",       "HF_TOKEN")
def _groq_key():   return _get("groq_key",     "GROQ_API_KEY",   "GROQ_API_KEY")
def _gemini_key(): return _get("gemini_key",   "GEMINI_API_KEY", "GEMINI_API_KEY")
def _llm_ok():     return bool(_groq_key() or _gemini_key())

# ─────────────────────────────────────────────────────────────────────────────
# PLATFORMS
# ─────────────────────────────────────────────────────────────────────────────

PLATFORMS = {
    "YouTube Thumbnail  16:9  1280×720":   (1280,  720),
    "YouTube Shorts     9:16  1080×1920":  (1080, 1920),
    "Instagram Post     1:1   1080×1080":  (1080, 1080),
    "Instagram Story    9:16  1080×1920":  (1080, 1920),
    "Instagram Reel     9:16  1080×1920":  (1080, 1920),
    "Facebook Post      1.9:1 1200×630":   (1200,  630),
    "Facebook Cover     2.7:1 820×312":    ( 820,  312),
    "WhatsApp Status    9:16  1080×1920":  (1080, 1920),
    "Twitter/X Post     16:9  1200×675":   (1200,  675),
    "LinkedIn Banner    4:1   1584×396":   (1584,  396),
}

# ─────────────────────────────────────────────────────────────────────────────
# VISUAL THEMES  — overlay colour + accent + gradient + style flags
# ─────────────────────────────────────────────────────────────────────────────

THEMES = {
    "🌅 Golden Hour": {
        "ov": (20, 10, 0, 155), "accent": (255, 195, 40),
        "grad_a": (180, 70, 10), "grad_b": (10, 5, 30),
        "text": (255, 255, 255), "style": "diagonal",
    },
    "🌊 Deep Ocean": {
        "ov": (0, 20, 60, 165), "accent": (0, 220, 230),
        "grad_a": (0, 50, 120), "grad_b": (0, 10, 40),
        "text": (255, 255, 255), "style": "vignette",
    },
    "🖤 Dark Luxury": {
        "ov": (5, 5, 10, 195), "accent": (212, 175, 55),
        "grad_a": (15, 12, 30), "grad_b": (5, 3, 10),
        "text": (255, 255, 255), "style": "corner_frame",
    },
    "🌿 Emerald Jungle": {
        "ov": (5, 40, 20, 160), "accent": (80, 230, 120),
        "grad_a": (10, 80, 40), "grad_b": (5, 25, 10),
        "text": (255, 255, 255), "style": "diagonal",
    },
    "🌸 Blossom Pink": {
        "ov": (80, 10, 50, 155), "accent": (255, 165, 210),
        "grad_a": (180, 30, 90), "grad_b": (60, 5, 35),
        "text": (255, 255, 255), "style": "vignette",
    },
    "🏜️ Desert Dunes": {
        "ov": (70, 40, 5, 155), "accent": (255, 185, 60),
        "grad_a": (160, 100, 30), "grad_b": (60, 35, 5),
        "text": (255, 255, 255), "style": "diagonal",
    },
    "🌙 Midnight": {
        "ov": (5, 5, 35, 185), "accent": (100, 140, 255),
        "grad_a": (10, 10, 60), "grad_b": (3, 3, 20),
        "text": (255, 255, 255), "style": "corner_frame",
    },
    "❄️ Arctic": {
        "ov": (20, 50, 100, 145), "accent": (180, 235, 255),
        "grad_a": (30, 80, 150), "grad_b": (10, 30, 80),
        "text": (255, 255, 255), "style": "vignette",
    },
    "🔥 Fire & Passion": {
        "ov": (80, 10, 0, 165), "accent": (255, 120, 30),
        "grad_a": (180, 30, 0), "grad_b": (60, 5, 0),
        "text": (255, 255, 255), "style": "diagonal",
    },
    "🪷 Lavender Dream": {
        "ov": (50, 15, 80, 158), "accent": (210, 175, 255),
        "grad_a": (90, 40, 140), "grad_b": (30, 10, 60),
        "text": (255, 255, 255), "style": "vignette",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT TEMPLATES
# ─────────────────────────────────────────────────────────────────────────────

LAYOUTS = {
    "Magazine":   "Top pill → bold title → accent subtitle → checkmarks → price → CTA",
    "Cinematic":  "Large centered title, minimal text, dramatic bottom strip",
    "Bold":       "Oversized headline, thick accent bar, strong CTA pill",
    "Minimal":    "Clean typography, generous whitespace, understated CTA",
    "Story":      "Optimized for 9:16 — stacked for thumb-stop on mobile",
}

# ─────────────────────────────────────────────────────────────────────────────
# IMAGE STYLES
# ─────────────────────────────────────────────────────────────────────────────

IMG_STYLES = {
    "📸 Photorealistic":      "ultra-realistic travel photography, golden hour lighting, professional DSLR, 8k UHD, tack sharp, award-winning National Geographic",
    "🎨 Cinematic Film":      "cinematic wide shot, anamorphic lens, dramatic Rembrandt lighting, film grain, movie still, Christopher Nolan aesthetic",
    "🌅 Aerial Drone":        "aerial drone photography, bird's eye view, DJI Mavic Pro, stunning landscape, vivid saturated colors, 8k",
    "🖼️ Vintage Travel Poster":"vintage travel poster illustration, 1950s retro art deco, bold flat colors, graphic design, poster art",
    "✏️ Digital Illustration": "digital illustration, travel poster style, vibrant colors, flat design with depth, professional graphic art",
    "🌙 Night & Neon":        "night photography, city lights, 30-second long exposure, moody cinematic atmosphere, neon reflections on wet pavement",
    "🏺 Cultural Painting":   "impressionist oil painting style, cultural art, rich textures, warm earthy tones, museum quality",
    "🌫️ Misty & Ethereal":    "misty atmosphere, ethereal soft light, dreamy bokeh, pastel tones, fine art photography, Brooke Shaden style",
}

# ─────────────────────────────────────────────────────────────────────────────
# FONT LOADER
# ─────────────────────────────────────────────────────────────────────────────

def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    paths = [
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf",
        f"/usr/share/fonts/truetype/liberation/LiberationSans{'-Bold' if bold else '-Regular'}.ttf",
        f"/usr/share/fonts/truetype/ubuntu/Ubuntu-{'B' if bold else 'R'}.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()

# ─────────────────────────────────────────────────────────────────────────────
# LLM  (Groq first → Gemini fallback)
# ─────────────────────────────────────────────────────────────────────────────

def _groq(system: str, user: str, max_tokens: int = 900) -> str:
    key = _groq_key()
    if not key: return ""
    try:
        from groq import Groq
        r = Groq(api_key=key).chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"system","content":system},{"role":"user","content":user}],
            max_tokens=max_tokens, temperature=0.75,
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        st.toast(f"Groq: {e}", icon="⚠️")
        return ""

def _gemini(prompt: str, max_tokens: int = 900) -> str:
    key = _gemini_key()
    if not key: return ""
    url  = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    body = {"contents":[{"parts":[{"text":prompt}]}],
            "generationConfig":{"maxOutputTokens":max_tokens,"temperature":0.8}}
    try:
        r = requests.post(url, params={"key":key}, json=body, timeout=30)
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        st.toast(f"Gemini: {e}", icon="⚠️")
        return ""

def _llm(system: str, user: str, max_tokens: int = 900) -> str:
    out = _groq(system, user, max_tokens)
    if not out:
        out = _gemini(f"{system}\n\n{user}", max_tokens)
    return out

def _parse_json(raw: str):
    clean = re.sub(r"```(?:json)?|```", "", raw).strip()
    s = min((clean.find("{") if "{" in clean else 9999),
            (clean.find("[") if "[" in clean else 9999))
    return json.loads(clean[s:])

# ─────────────────────────────────────────────────────────────────────────────
# LLM TASKS
# ─────────────────────────────────────────────────────────────────────────────

def llm_enhance_image_prompt(desc: str, style: str, dest: str) -> str:
    sys_ = (
        "You are an expert FLUX/Stable Diffusion image prompt writer for luxury travel photography. "
        "Create a rich, detailed visual prompt. "
        "RULES: No people. No text. No logos. Pure scenery/place/atmosphere/architecture. "
        "Include: specific lighting quality, time of day, color palette, "
        "lens/composition style, weather/atmosphere, texture details. "
        "Output ONLY the final prompt. Max 130 words."
    )
    usr = f"Destination: {dest}\nDescription: {desc}\nStyle: {style}\nWrite the image prompt:"
    out = _llm(sys_, usr, max_tokens=160)
    return out or f"{desc}, {dest}, {style}, no text, no watermark, no people"


def llm_generate_all_copy(dest: str, pkg_type: str, duration: str, extra: str) -> dict:
    sys_ = (
        "You are a world-class travel marketing copywriter specialising in Indian tourism. "
        "Return ONLY valid JSON — no markdown, no preamble, no explanation."
    )
    usr = (
        f"Destination: {dest}\nPackage type: {pkg_type}\n"
        f"Duration: {duration}\nKey details: {extra or 'none'}\n\n"
        "Generate JSON with keys:\n"
        "  title (6-8 word punchy headline with 1 emoji),\n"
        "  subtitle (subheadline with 3 aspects separated by  ·),\n"
        "  package_name (short label e.g. 'Golden Triangle 7D/6N'),\n"
        "  price_hint (e.g. '₹24,999/person'),\n"
        "  cta ('Book Now →' or similar, include arrow),\n"
        "  highlights (array of exactly 6 short sight/activity strings, each < 5 words),\n"
        "  youtube_title (YouTube title with 2 emojis, curiosity-driven),\n"
        "  youtube_desc (YouTube description, 4 lines, include hashtags),\n"
        "  instagram_caption (4-6 lines with emojis + 8 hashtags),\n"
        "  facebook_caption (3-4 lines, conversational, 4 hashtags),\n"
        "  whatsapp_status (2 lines max, emoji-rich),\n"
        "  short_video_script (3 punchy sentences, voiceover for 30-sec reel),\n"
        "  scene_prompts (array of exactly 6 AI image scene descriptions, "
        "each 1 sentence describing ONLY the visual scene — no people, no text)."
    )
    raw = _llm(sys_, usr, max_tokens=1100)
    if not raw: return {}
    try:
        return _parse_json(raw)
    except Exception:
        return {}


def llm_scene_captions(pkg: str, scenes: list, n: int) -> list:
    sys_ = (
        "Write punchy travel video slide captions. "
        "Each: max 5 words, include 1 travel emoji. "
        "Output ONLY a JSON array of strings. Nothing else."
    )
    usr = f"Package: {pkg}\nScenes: {scenes}\nWrite {n} captions:"
    raw = _llm(sys_, usr, max_tokens=220)
    if not raw: return [f"✨ Scene {i+1}" for i in range(n)]
    try:
        data = _parse_json(raw)
        return [str(c) for c in data[:n]]
    except Exception:
        return [s[:28] for s in scenes[:n]]

# ─────────────────────────────────────────────────────────────────────────────
# AI IMAGE GENERATION  (HF InferenceClient)
# ─────────────────────────────────────────────────────────────────────────────

def generate_ai_image(prompt: str, width: int, height: int,
                       model: str = "black-forest-labs/FLUX.1-schnell") -> Image.Image | None:
    hf_key = _hf_key()
    if not hf_key:
        return None
    try:
        from huggingface_hub import InferenceClient
    except ImportError:
        st.error("Add `huggingface_hub>=0.23.0` to requirements.txt")
        return None

    safe_w = min(width,  1024)
    safe_h = min(height, 1024)

    def _crop_to_canvas(img: Image.Image) -> Image.Image:
        img = img.convert("RGBA")
        ratio = max(width / img.width, height / img.height)
        nw, nh = int(img.width * ratio), int(img.height * ratio)
        img = img.resize((nw, nh), Image.LANCZOS)
        l = (nw - width) // 2; t = (nh - height) // 2
        return img.crop((l, t, l + width, t + height))

    def _try_generate(client) -> Image.Image | None:
        img = client.text_to_image(
            prompt, model=model, width=safe_w, height=safe_h,
        )
        return _crop_to_canvas(img)

    try:
        client = InferenceClient(provider="auto", api_key=hf_key)
        return _try_generate(client)
    except Exception as e:
        err = str(e).lower()
        if "401" in err or "unauthorized" in err:
            st.error("❌ HF token invalid — regenerate at huggingface.co → Settings → Access Tokens")
        elif "402" in err or "payment" in err or "billing" in err:
            st.warning("💳 HF Inference Providers need a payment method (~$0.003/image). Add card at huggingface.co → Billing.")
        elif "503" in err or "loading" in err:
            st.toast("⏳ HF model cold-starting, retrying in 20s…")
            time.sleep(20)
            try:
                return _try_generate(InferenceClient(provider="auto", api_key=hf_key))
            except Exception as e2:
                st.warning(f"Retry failed: {e2}")
        elif "429" in err or "rate" in err:
            st.warning("⚠️ HF rate limit — wait 60s and retry.")
        else:
            st.warning(f"⚠️ HF error: {e}")
        return None

# ─────────────────────────────────────────────────────────────────────────────
# BACKGROUND HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _gradient_bg(w: int, h: int, c1: tuple, c2: tuple) -> Image.Image:
    img = Image.new("RGBA", (w, h))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        draw.line([(0,y),(w,y)], fill=(
            int(c1[0]+(c2[0]-c1[0])*t),
            int(c1[1]+(c2[1]-c1[1])*t),
            int(c1[2]+(c2[2]-c1[2])*t), 255))
    return img


def _apply_vignette(img: Image.Image, strength: float = 0.65) -> Image.Image:
    """Darken edges for cinematic vignette effect."""
    w, h = img.size
    mask = Image.new("L", (w, h), 255)
    draw = ImageDraw.Draw(mask)
    cx, cy = w // 2, h // 2
    steps = 80
    for i in range(steps):
        t   = i / steps
        alpha = int(255 * strength * t * t)
        rx  = int(cx * (1 - t * 0.85))
        ry  = int(cy * (1 - t * 0.85))
        draw.ellipse([cx-rx, cy-ry, cx+rx, cy+ry], fill=255-alpha)
    dark = Image.new("RGBA", (w, h), (0, 0, 0, 200))
    result = img.convert("RGBA").copy()
    result.paste(dark, mask=ImageChops.invert(mask))
    return result


def _apply_diagonal_band(img: Image.Image, accent: tuple) -> Image.Image:
    """Add a subtle diagonal accent band."""
    overlay = Image.new("RGBA", img.size, (0,0,0,0))
    draw = ImageDraw.Draw(overlay)
    w, h = img.size
    band_w = int(w * 0.35)
    pts = [(0, h//2 - band_w//2), (w//4, h//2 - band_w//2 - 60),
           (w//4, h//2 + band_w//2 - 60), (0, h//2 + band_w//2)]
    draw.polygon(pts, fill=accent + (18,))
    return Image.alpha_composite(img.convert("RGBA"), overlay)


def _apply_corner_frame(img: Image.Image, accent: tuple) -> Image.Image:
    """Gold corner frame decoration."""
    overlay = Image.new("RGBA", img.size, (0,0,0,0))
    draw = ImageDraw.Draw(overlay)
    w, h = img.size
    m = int(min(w, h) * 0.04)
    seg = int(min(w, h) * 0.1)
    lw = max(2, int(min(w, h) * 0.003))
    col = accent + (200,)
    corners = [(m, m), (w-m, m), (w-m, h-m), (m, h-m)]
    dirs = [(1,0,0,1), (-1,0,0,1), (-1,0,0,-1), (1,0,0,-1)]
    for (cx, cy), (dx1, dy1, dx2, dy2) in zip(corners, dirs):
        draw.line([(cx, cy), (cx+dx1*seg, cy+dy1*seg)], fill=col, width=lw)
        draw.line([(cx, cy), (cx+dx2*seg, cy+dy2*seg)], fill=col, width=lw)
    return Image.alpha_composite(img.convert("RGBA"), overlay)


def _apply_film_grain(img: Image.Image, amount: int = 18) -> Image.Image:
    """Subtle film grain for cinematic feel."""
    import random
    grain = Image.new("RGBA", img.size, (128,128,128,0))
    px = grain.load()
    for y in range(img.height):
        for x in range(img.width):
            v = random.randint(-amount, amount)
            px[x, y] = (128+v, 128+v, 128+v, 12)
    return Image.alpha_composite(img.convert("RGBA"), grain)


def _smart_overlay(img: Image.Image, ov_color: tuple, alpha: int,
                   style: str = "flat") -> Image.Image:
    """Style-aware overlay: flat, gradient-bottom, gradient-top."""
    base = img.convert("RGBA")
    if style == "flat":
        ov = Image.new("RGBA", img.size, ov_color + (alpha,))
        return Image.alpha_composite(base, ov)
    elif style == "gradient_bottom":
        ov = Image.new("RGBA", img.size, (0,0,0,0))
        draw = ImageDraw.Draw(ov)
        h = img.height
        for y in range(h):
            t = (y / h) ** 1.8
            a = int(alpha * t)
            draw.line([(0,y),(img.width,y)], fill=ov_color+(a,))
        return Image.alpha_composite(base, ov)
    elif style == "gradient_top":
        ov = Image.new("RGBA", img.size, (0,0,0,0))
        draw = ImageDraw.Draw(ov)
        h = img.height
        for y in range(h):
            t = 1 - (y / h)
            t = t ** 1.5
            a = int(alpha * t)
            draw.line([(0,y),(img.width,y)], fill=ov_color+(a,))
        return Image.alpha_composite(base, ov)
    return Image.alpha_composite(base, Image.new("RGBA", img.size, ov_color+(alpha,)))

# ─────────────────────────────────────────────────────────────────────────────
# TEXT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _wrap(text: str, font, max_w: int, draw) -> str:
    words = text.split(); lines = []; line = ""
    for word in words:
        test = (line + " " + word).strip()
        if draw.textbbox((0,0), test, font=font)[2] <= max_w:
            line = test
        else:
            if line: lines.append(line)
            line = word
    if line: lines.append(line)
    return "\n".join(lines)


def _shadow(draw, xy, text, font, fill, s=4, spread=2):
    """Multi-layer shadow for depth."""
    for i in range(spread, 0, -1):
        alpha = int(120 * (i / spread))
        draw.text((xy[0]+s*i//spread, xy[1]+s*i//spread), text,
                  font=font, fill=(0,0,0,alpha))
    draw.text(xy, text, font=font, fill=fill)


def _glow(draw, xy, text, font, color, glow_color, radius=3):
    """Text with a colored glow."""
    for dx in range(-radius, radius+1):
        for dy in range(-radius, radius+1):
            if dx*dx + dy*dy <= radius*radius:
                alpha = int(100 * (1 - math.sqrt(dx*dx+dy*dy)/radius))
                draw.text((xy[0]+dx, xy[1]+dy), text, font=font,
                          fill=glow_color+(alpha,))
    draw.text(xy, text, font=font, fill=color)


def _pill(draw, x, y, text, font, bg, fg, pad_x=18, pad_y=8, radius=None):
    bb = draw.textbbox((0,0), text, font=font)
    tw, th = bb[2]-bb[0], bb[3]-bb[1]
    r = radius or (th + pad_y) // 2
    draw.rounded_rectangle([x, y, x+tw+pad_x*2, y+th+pad_y*2], radius=r, fill=bg)
    draw.text((x+pad_x, y+pad_y), text, font=font, fill=fg)
    return x + tw + pad_x*2


def _pill_outline(draw, x, y, text, font, outline_col, text_col, pad_x=16, pad_y=8, lw=2):
    bb = draw.textbbox((0,0), text, font=font)
    tw, th = bb[2]-bb[0], bb[3]-bb[1]
    r = (th+pad_y)//2
    draw.rounded_rectangle([x, y, x+tw+pad_x*2, y+th+pad_y*2],
                            radius=r, outline=outline_col, width=lw)
    draw.text((x+pad_x, y+pad_y), text, font=font, fill=text_col)
    return x + tw + pad_x*2


def _social_bar(draw, w, h, fb, insta, web, accent, font):
    bh = int(min(w, h) * 0.055)
    by = h - bh
    # Gradient bar
    for y in range(by, h):
        a = int(185 * (y - by) / bh)
        draw.line([(0,y),(w,y)], fill=(0,0,0,a))
    items = []
    if fb:    items.append(f"f  {fb}")
    if insta: items.append(f"@  {insta}")
    if web:   items.append(f"🌐 {web}")
    if not items: return
    line = "   ·   ".join(items)
    bb = draw.textbbox((0,0), line, font=font)
    tw = bb[2]-bb[0]
    ty = by + (bh - (bb[3]-bb[1])) // 2
    _shadow(draw, ((w-tw)//2, ty), line, font, accent+(255,), s=2)


def _paste_asset(canvas: Image.Image, asset_bytes: bytes,
                 position: str, max_px: int, bottom_res: int = 60) -> Image.Image:
    asset = Image.open(io.BytesIO(asset_bytes)).convert("RGBA")
    # Soften edges slightly
    r = min(max_px/asset.width, max_px/asset.height)
    nw, nh = int(asset.width*r), int(asset.height*r)
    asset = asset.resize((nw,nh), Image.LANCZOS)
    W, H = canvas.size; m = 24
    pos_map = {
        "Top Left":    (m, m),
        "Top Right":   (W-nw-m, m),
        "Bottom Left": (m, H-nh-m-bottom_res),
        "Bottom Right":(W-nw-m, H-nh-m-bottom_res),
    }
    x, y = pos_map.get(position, (W-nw-m, m))
    # Drop shadow for logo
    shadow = Image.new("RGBA", (nw+8, nh+8), (0,0,0,0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rectangle([4,4,nw+4,nh+4], fill=(0,0,0,80))
    shadow = shadow.filter(ImageFilter.GaussianBlur(4))
    canvas.paste(shadow, (x-2, y+2), shadow)
    canvas.paste(asset, (x,y), asset)
    return canvas

# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT RENDERERS
# ─────────────────────────────────────────────────────────────────────────────

def _layout_magazine(draw, canvas, w, h, sc, theme, fields):
    """Classic travel magazine layout."""
    pkg, title, sub, hl, price, cta = (
        fields["package_name"], fields["headline"], fields["subheadline"],
        fields["highlights"], fields["price"], fields["cta"],
    )
    accent = theme["accent"]; white = (255,255,255,255)
    acc4   = accent+(255,)
    margin = int(58*sc); mw = w-margin*2; cy = int(52*sc)

    fPkg = _font(int(22*sc), bold=True)
    fT   = _font(int(76*sc), bold=True)
    fS   = _font(int(38*sc))
    fH   = _font(int(29*sc))
    fP   = _font(int(60*sc), bold=True)
    fC   = _font(int(36*sc), bold=True)
    fSm  = _font(int(22*sc))

    if pkg:
        _pill(draw, margin, cy, f"  ✈  {pkg.upper()}  ",
              fPkg, accent+(210,), (8,8,8,255), pad_x=18, pad_y=9)
        cy += int(58*sc)
        # Accent bar
        draw.rectangle([margin, cy, margin+int(80*sc), cy+5], fill=acc4)
        cy += int(22*sc)

    if title:
        wrapped = _wrap(title, fT, mw, draw)
        _shadow(draw, (margin, cy), wrapped, fT, white, s=5)
        bb = draw.multiline_textbbox((margin,cy), wrapped, font=fT)
        cy += bb[3]-bb[1] + int(12*sc)

    if sub:
        wrapped = _wrap(sub, fS, mw, draw)
        _shadow(draw, (margin, cy), wrapped, fS, acc4, s=3)
        bb = draw.multiline_textbbox((margin,cy), wrapped, font=fS)
        cy += bb[3]-bb[1] + int(26*sc)

    for i, item in enumerate(hl[:6]):
        dot_x = margin + int(8*sc)
        # Alternating accent dots
        draw.ellipse([dot_x, cy+int(11*sc), dot_x+int(8*sc), cy+int(19*sc)],
                     fill=accent+(220,))
        _shadow(draw, (dot_x+int(18*sc), cy), f"{item}", fH, white, s=2)
        bb = draw.textbbox((0,0), item, font=fH)
        cy += bb[3]-bb[1] + int(7*sc)
    if hl: cy += int(16*sc)

    if price:
        _shadow(draw, (margin, cy), f"From  {price}", fP, acc4, s=4)
        bb = draw.textbbox((margin,cy), f"From  {price}", font=fP)
        cy += bb[3]-bb[1] + int(20*sc)

    if cta:
        _pill(draw, margin, cy, f"  {cta}  ", fC,
              accent+(235,), (12,12,12,255), pad_x=22, pad_y=12)

    return fSm


def _layout_cinematic(draw, canvas, w, h, sc, theme, fields):
    """Centered cinematic layout — big title, minimal text."""
    title, pkg, price, cta = (
        fields["headline"], fields["package_name"],
        fields["price"], fields["cta"],
    )
    accent = theme["accent"]; white = (255,255,255,255)
    acc4   = accent+(255,)

    fT  = _font(int(88*sc), bold=True)
    fS  = _font(int(36*sc))
    fC  = _font(int(36*sc), bold=True)
    fSm = _font(int(22*sc))

    mw = w - int(80*sc)

    # Horizontal accent lines above and below title
    mid_y = h // 2 - int(80*sc)
    line_y1 = mid_y - int(24*sc)
    draw.rectangle([int(60*sc), line_y1, w-int(60*sc), line_y1+3], fill=acc4)

    if title:
        wrapped = _wrap(title, fT, mw, draw)
        bb = draw.multiline_textbbox((0,0), wrapped, font=fT)
        tx = (w-(bb[2]-bb[0]))//2; ty = mid_y
        _glow(draw, (tx,ty), wrapped, fT, white, accent+(80,), radius=5)

        bb2 = draw.multiline_textbbox((tx,ty), wrapped, font=fT)
        bottom_title = bb2[3]
        draw.rectangle([int(60*sc), bottom_title+int(12*sc), w-int(60*sc),
                        bottom_title+int(12*sc)+3], fill=acc4)

    if pkg:
        bb = draw.textbbox((0,0), pkg, font=fS)
        tx = (w-(bb[2]-bb[0]))//2
        _shadow(draw, (tx, h//2 + int(60*sc)), pkg, fS, acc4, s=3)

    # Bottom strip
    strip_h = int(100*sc)
    strip_y = h - strip_h - int(56*sc)
    draw.rectangle([0, strip_y, w, strip_y+strip_h], fill=(0,0,0,140))
    cy_strip = strip_y + (strip_h-int(48*sc))//2

    if price:
        bb = draw.textbbox((0,0), f"From {price}", font=fC)
        _shadow(draw, (int(60*sc), cy_strip), f"From {price}", fC, acc4, s=3)
    if cta:
        bb = draw.textbbox((0,0), cta, font=fC)
        _pill(draw, w-int(60*sc)-(bb[2]-bb[0])-44, cy_strip, f"  {cta}  ",
              fC, accent+(230,), (10,10,10,255), pad_x=20, pad_y=10)

    return fSm


def _layout_bold(draw, canvas, w, h, sc, theme, fields):
    """Oversized bold headline, thick accent bar, strong CTA."""
    pkg, title, sub, price, cta = (
        fields["package_name"], fields["headline"], fields["subheadline"],
        fields["price"], fields["cta"],
    )
    accent = theme["accent"]; white = (255,255,255,255)
    acc4 = accent+(255,)
    margin = int(50*sc); mw = w-margin*2; cy = int(48*sc)

    fTag = _font(int(18*sc), bold=True)
    fT   = _font(int(96*sc), bold=True)
    fS   = _font(int(40*sc))
    fP   = _font(int(64*sc), bold=True)
    fC   = _font(int(40*sc), bold=True)
    fSm  = _font(int(22*sc))

    # Top tag
    if pkg:
        draw.rectangle([margin, cy, margin+int(8*sc), cy+int(32*sc)], fill=acc4)
        draw.text((margin+int(18*sc), cy), pkg.upper(), font=fTag, fill=acc4)
        cy += int(48*sc)

    # Massive title
    if title:
        # Only first 3-4 words for impact
        words = title.split()
        line1 = " ".join(words[:3])
        line2 = " ".join(words[3:]) if len(words) > 3 else ""
        _shadow(draw, (margin, cy), line1, fT, white, s=6)
        bb = draw.textbbox((margin,cy), line1, font=fT)
        cy += bb[3]-bb[1]
        if line2:
            _shadow(draw, (margin, cy), line2, fT, acc4, s=6)
            bb = draw.textbbox((margin,cy), line2, font=fT)
            cy += bb[3]-bb[1]
        cy += int(10*sc)

    # Thick horizontal accent bar
    draw.rectangle([margin, cy, margin+int(200*sc), cy+int(8*sc)], fill=acc4)
    cy += int(28*sc)

    if sub:
        wrapped = _wrap(sub, fS, mw, draw)
        _shadow(draw, (margin, cy), wrapped, fS, white, s=3)
        bb = draw.multiline_textbbox((margin,cy), wrapped, font=fS)
        cy += bb[3]-bb[1] + int(20*sc)

    # Price + CTA side by side
    if price:
        _shadow(draw, (margin, cy), f"From {price}", fP, acc4, s=4)
    if cta:
        bb_p = draw.textbbox((0,0), f"From {price}", font=fP)
        cta_x = margin + bb_p[2]-bb_p[0] + int(30*sc)
        bb_c = draw.textbbox((0,0), f"  {cta}  ", font=fC)
        cta_y = cy + (bb_p[3]-bb_p[1] - (bb_c[3]-bb_c[1]))//2
        _pill(draw, cta_x, cta_y, f"  {cta}  ", fC,
              accent+(235,), (10,10,10,255), pad_x=20, pad_y=10)

    return fSm


def _layout_minimal(draw, canvas, w, h, sc, theme, fields):
    """Clean minimal — whitespace, refined type."""
    pkg, title, sub, hl, price, cta = (
        fields["package_name"], fields["headline"], fields["subheadline"],
        fields["highlights"], fields["price"], fields["cta"],
    )
    accent = theme["accent"]; white = (255,255,255,255)
    acc4 = accent+(255,)
    margin = int(70*sc); mw = w-margin*2
    cy = h // 3

    fTag = _font(int(18*sc), bold=False)
    fT   = _font(int(68*sc), bold=True)
    fS   = _font(int(34*sc))
    fH   = _font(int(26*sc))
    fP   = _font(int(48*sc), bold=True)
    fC   = _font(int(30*sc), bold=True)
    fSm  = _font(int(22*sc))

    if pkg:
        # Minimal all-caps tag with letter-spacing feel (spaces between chars)
        tag = "  ·  ".join(list(pkg.upper()[:20]))
        bb = draw.textbbox((0,0), tag, font=fTag)
        draw.text(((w-(bb[2]-bb[0]))//2, cy-int(56*sc)), tag, font=fTag,
                  fill=accent+(180,))
        # Thin line
        draw.rectangle([(w//2-int(30*sc)), cy-int(20*sc),
                         (w//2+int(30*sc)), cy-int(18*sc)], fill=acc4)

    if title:
        wrapped = _wrap(title, fT, mw, draw)
        bb = draw.multiline_textbbox((0,0), wrapped, font=fT)
        _shadow(draw, ((w-(bb[2]-bb[0]))//2, cy), wrapped, fT, white, s=4)
        bb2 = draw.multiline_textbbox(((w-(bb[2]-bb[0]))//2,cy), wrapped, font=fT)
        cy = bb2[3] + int(18*sc)

    if sub:
        bb = draw.textbbox((0,0), sub, font=fS)
        draw.text(((w-(bb[2]-bb[0]))//2, cy), sub, font=fS, fill=acc4)
        cy += (bb[3]-bb[1]) + int(28*sc)

    # Minimal dot-separated highlights
    if hl:
        hl_line = "  ·  ".join(hl[:4])
        bb = draw.textbbox((0,0), hl_line, font=fH)
        if bb[2]-bb[0] <= mw:
            draw.text(((w-(bb[2]-bb[0]))//2, cy), hl_line, font=fH,
                      fill=(255,255,255,190))
            cy += (bb[3]-bb[1]) + int(24*sc)

    # Bottom center price + CTA
    bottom_y = h - int(160*sc)
    if price:
        bb = draw.textbbox((0,0), price, font=fP)
        _pill_outline(draw, (w-(bb[2]-bb[0]+60))//2, bottom_y,
                      price, fP, accent+(200,), white, pad_x=30, pad_y=12, lw=2)
        bottom_y += (bb[3]-bb[1]) + int(60*sc)
    if cta:
        bb = draw.textbbox((0,0), cta, font=fC)
        _pill(draw, (w-(bb[2]-bb[0]+64))//2, bottom_y,
              cta, fC, accent+(220,), (10,10,10,255), pad_x=32, pad_y=14)

    return fSm


def _layout_story(draw, canvas, w, h, sc, theme, fields):
    """9:16 story optimised — top package, hero middle, bottom CTA strip."""
    pkg, title, sub, hl, price, cta = (
        fields["package_name"], fields["headline"], fields["subheadline"],
        fields["highlights"], fields["price"], fields["cta"],
    )
    accent = theme["accent"]; white = (255,255,255,255)
    acc4 = accent+(255,)
    margin = int(55*sc); mw = w-margin*2

    fTag = _font(int(20*sc), bold=True)
    fT   = _font(int(72*sc), bold=True)
    fS   = _font(int(36*sc))
    fH   = _font(int(28*sc))
    fP   = _font(int(52*sc), bold=True)
    fC   = _font(int(34*sc), bold=True)
    fSm  = _font(int(22*sc))

    # Top pill
    cy = int(60*sc)
    if pkg:
        bb = draw.textbbox((0,0), f"  ✈  {pkg.upper()}  ", font=fTag)
        tx = (w-(bb[2]-bb[0]+36))//2
        _pill(draw, tx, cy, f"  ✈  {pkg.upper()}  ", fTag,
              accent+(215,), (8,8,8,255), pad_x=18, pad_y=10)
        cy += int(68*sc)

    # Hero title — centred
    if title:
        wrapped = _wrap(title, fT, mw, draw)
        bb = draw.multiline_textbbox((0,0), wrapped, font=fT)
        tx = (w-(bb[2]-bb[0]))//2
        ty = h//3
        _shadow(draw, (tx, ty), wrapped, fT, white, s=5)
        bb2 = draw.multiline_textbbox((tx,ty), wrapped, font=fT)
        cy = bb2[3] + int(16*sc)

    if sub:
        wrapped = _wrap(sub, fS, mw, draw)
        bb = draw.multiline_textbbox((0,0), wrapped, font=fS)
        draw.text(((w-(bb[2]-bb[0]))//2, cy), wrapped, font=fS, fill=acc4)
        bb2 = draw.multiline_textbbox(((w-(bb[2]-bb[0]))//2,cy), wrapped, font=fS)
        cy = bb2[3] + int(22*sc)

    # Highlights in 2-column grid
    if hl:
        col_w = (mw - int(20*sc)) // 2
        for i, item in enumerate(hl[:6]):
            col = i % 2
            row = i // 2
            x = margin + col * (col_w + int(20*sc))
            y = cy + row * int(38*sc)
            draw.ellipse([x, y+int(9*sc), x+int(10*sc), y+int(19*sc)], fill=acc4)
            _shadow(draw, (x+int(16*sc), y), item[:22], fH, white, s=2)
        cy += (len(hl[:6])//2 + 1) * int(38*sc) + int(16*sc)

    # Bottom action strip
    strip_h = int(130*sc)
    strip_y = h - strip_h - int(60*sc)
    draw.rectangle([0, strip_y, w, strip_y+strip_h], fill=(0,0,0,155))
    sy = strip_y + int(18*sc)
    if price:
        bb = draw.textbbox((0,0), f"From {price}", font=fP)
        _shadow(draw, ((w-(bb[2]-bb[0]))//2, sy), f"From {price}", fP, acc4, s=4)
        sy += (bb[3]-bb[1]) + int(12*sc)
    if cta:
        bb = draw.textbbox((0,0), cta, font=fC)
        _pill(draw, (w-(bb[2]-bb[0]+68))//2, sy, f"  {cta}  ",
              fC, accent+(230,), (10,10,10,255), pad_x=34, pad_y=14)

    return fSm


LAYOUT_FNS = {
    "Magazine":  _layout_magazine,
    "Cinematic": _layout_cinematic,
    "Bold":      _layout_bold,
    "Minimal":   _layout_minimal,
    "Story":     _layout_story,
}

# ─────────────────────────────────────────────────────────────────────────────
# MASTER COMPOSE
# ─────────────────────────────────────────────────────────────────────────────

def compose_banner(
    bg_img,  w: int, h: int,
    theme: dict = None,
    layout: str = "Magazine",
    package_name: str = "", headline: str = "",
    subheadline: str = "", highlights: list = None,
    price: str = "", cta: str = "",
    slide_caption: str = "", slide_num: str = None,
    logo_bytes: bytes = None, logo_pos: str = "Top Right",
    cert_bytes: bytes = None,
    fb: str = "", insta: str = "", web: str = "",
    overlay_alpha: int = 145,
    grain: bool = True,
) -> Image.Image:

    if theme is None:
        theme = list(THEMES.values())[0]

    highlights = highlights or []
    sc = min(w, h) / 1080
    accent = theme["accent"]

    # ── Background ────────────────────────────────────────────────────────────
    if bg_img:
        canvas = bg_img.copy().convert("RGBA")
    else:
        canvas = _gradient_bg(w, h, theme["grad_a"], theme["grad_b"])

    # ── Theme-specific effects ────────────────────────────────────────────────
    t_style = theme.get("style","flat")
    if t_style == "vignette":
        canvas = _apply_vignette(canvas, strength=0.55)
        canvas = _smart_overlay(canvas, theme["ov"][:3], overlay_alpha, "flat")
    elif t_style == "diagonal":
        canvas = _smart_overlay(canvas, theme["ov"][:3], overlay_alpha, "gradient_bottom")
        canvas = _apply_diagonal_band(canvas, accent)
    elif t_style == "corner_frame":
        canvas = _smart_overlay(canvas, theme["ov"][:3], overlay_alpha, "flat")

    canvas = canvas.convert("RGBA")

    # Subtle grain
    if grain and bg_img:
        canvas = _apply_film_grain(canvas, amount=12)

    # Corner frame decoration
    if t_style == "corner_frame":
        canvas = _apply_corner_frame(canvas, accent)

    draw = ImageDraw.Draw(canvas)
    fSm  = _font(int(22*sc))

    # ── VIDEO SLIDE MODE ──────────────────────────────────────────────────────
    if slide_caption:
        fSl = _font(int(56*sc), bold=True)
        fNm = _font(int(20*sc))
        mw  = w - int(80*sc)

        if slide_num:
            nb = draw.textbbox((0,0), slide_num, font=fNm)
            draw.text((w - int(50*sc) - (nb[2]-nb[0]), int(30*sc)),
                      slide_num, font=fNm, fill=accent+(190,))

        # Caption pill box — centred vertically
        wrapped = _wrap(slide_caption, fSl, mw, draw)
        bb = draw.multiline_textbbox((0,0), wrapped, font=fSl)
        tx = (w-(bb[2]-bb[0]))//2
        ty = (h-(bb[3]-bb[1]))//2 - int(30*sc)
        # Frosted pill behind text
        pad = int(24*sc)
        draw.rounded_rectangle([tx-pad, ty-pad, tx+(bb[2]-bb[0])+pad,
                                 ty+(bb[3]-bb[1])+pad],
                               radius=int(16*sc), fill=(0,0,0,120))
        _glow(draw, (tx, ty), wrapped, fSl, (255,255,255,255), accent+(60,), radius=4)

        if package_name:
            pb = draw.textbbox((0,0), package_name, font=fSm)
            px = (w-(pb[2]-pb[0])-36)//2
            _pill(draw, px, h-int(115*sc), package_name, fSm,
                  accent+(215,), (10,10,10,255), pad_x=18, pad_y=8)

    else:
        # ── CHOOSE LAYOUT ─────────────────────────────────────────────────────
        # Auto-select Story for 9:16
        effective_layout = layout
        if layout == "Magazine" and h > w * 1.4:
            effective_layout = "Story"

        fields = dict(
            package_name=package_name, headline=headline,
            subheadline=subheadline, highlights=highlights,
            price=price, cta=cta,
        )
        layout_fn = LAYOUT_FNS.get(effective_layout, _layout_magazine)
        fSm = layout_fn(draw, canvas, w, h, sc, theme, fields)

    # ── Social bar ────────────────────────────────────────────────────────────
    _social_bar(draw, w, h, fb, insta, web, accent, fSm)

    # ── Logo ──────────────────────────────────────────────────────────────────
    if logo_bytes:
        canvas = _paste_asset(canvas, logo_bytes, logo_pos, int(130*sc), bottom_res=64)

    # ── Cert badge ────────────────────────────────────────────────────────────
    if cert_bytes:
        canvas = _paste_asset(canvas, cert_bytes, "Bottom Left", int(88*sc), bottom_res=64)

    return canvas.convert("RGB")

# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def to_bytes(img: Image.Image, fmt: str = "PNG", quality: int = 95) -> bytes:
    buf = io.BytesIO()
    if fmt == "JPEG":
        img = img.convert("RGB")
    img.save(buf, format=fmt, quality=quality)
    return buf.getvalue()


def make_gif(frames: list, ms: int = 2500) -> bytes:
    thumbs = []
    for f in frames:
        scale = 540 / f.width
        thumbs.append(f.resize((int(f.width*scale), int(f.height*scale)), Image.LANCZOS))
    buf = io.BytesIO()
    thumbs[0].save(buf, format="GIF", save_all=True,
                   append_images=thumbs[1:], duration=ms, loop=0, optimize=True)
    return buf.getvalue()


def _crop_for_platform(master: Image.Image, pw: int, ph: int) -> Image.Image | None:
    if master is None: return None
    ratio = max(pw/master.width, ph/master.height)
    nw = int(master.width*ratio); nh = int(master.height*ratio)
    img = master.resize((nw,nh), Image.LANCZOS)
    l = (nw-pw)//2; t = (nh-ph)//2
    return img.crop((l,t,l+pw,t+ph))

# ─────────────────────────────────────────────────────────────────────────────
# PAGE
# ─────────────────────────────────────────────────────────────────────────────

def render():

    # ── CSS ───────────────────────────────────────────────────────────────────
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=Inter:wght@400;500;600&display=swap');

    [data-testid="stAppViewContainer"] { background:#0a0f1e; }

    .hero {
        font-family:'Syne',sans-serif; font-size:2.5rem; font-weight:800; line-height:1.1;
        background:linear-gradient(120deg,#f59e0b 0%,#ef4444 40%,#8b5cf6 80%);
        -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    }
    .sub { font-family:'Inter',sans-serif; color:#64748b; font-size:.9rem; margin-top:4px; }

    .bdg { display:inline-flex; align-items:center; gap:6px; padding:4px 14px;
           border-radius:20px; font-size:.72rem; font-weight:700; letter-spacing:.06em;
           margin-right:8px; margin-bottom:12px; }
    .bdg-ai   { background:linear-gradient(135deg,#7c3aed,#db2777); color:#fff; }
    .bdg-free { background:linear-gradient(135deg,#065f46,#0284c7); color:#fff; }
    .bdg-hf   { background:linear-gradient(135deg,#92400e,#d97706); color:#fff; }

    .card { background:#111827; border:1px solid #1f2937; border-radius:14px;
            padding:18px 20px; margin-bottom:12px; }

    .copy-lbl { font-size:.65rem; font-weight:700; letter-spacing:.1em;
                color:#4b5563; text-transform:uppercase; margin-bottom:3px; }
    .copy-val { background:#111827; border:1px solid #1f2937; border-radius:8px;
                padding:11px 15px; font-family:'Inter',sans-serif; font-size:.83rem;
                color:#d1d5db; line-height:1.65; white-space:pre-wrap; margin-bottom:8px; }

    .empty { border:1px dashed #1f2937; border-radius:14px;
             padding:60px 20px; text-align:center; background:#0d1117; }
    .ei { font-size:2.8rem; }
    .et { color:#374151; margin-top:8px; font-size:.85rem; }

    div[data-testid="stTabs"] button[aria-selected="true"] {
        border-bottom:2px solid #f59e0b !important; color:#f59e0b !important;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown(
        '<span class="bdg bdg-ai">✦ AI IMAGE GEN</span>'
        '<span class="bdg bdg-hf">🤗 HF FLUX</span>'
        '<span class="bdg bdg-free">100% FREE</span>',
        unsafe_allow_html=True
    )
    st.markdown('<div class="hero">✈ AI Travel Content Studio</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="sub">Describe → AI generates scene → professional branding composited → '
        'download for every platform</div>', unsafe_allow_html=True
    )
    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # BRAND KIT
    # ─────────────────────────────────────────────────────────────────────────
    with st.expander("🏷️ Brand Kit  —  Logo · Cert · Social · API Keys · Colors", expanded=False):
        r1c1, r1c2, r1c3 = st.columns(3)

        with r1c1:
            st.markdown("**🖼️ Company Logo**")
            lu = st.file_uploader("PNG with transparency preferred",
                                   type=["png","jpg","jpeg"], key="bk_logo")
            if lu: st.session_state["brand_logo"] = lu.read()
            if st.session_state.get("brand_logo"):
                st.image(st.session_state["brand_logo"], width=110)

        with r1c2:
            st.markdown("**🏅 Cert / Award Badge**")
            cu = st.file_uploader("Badge image", type=["png","jpg","jpeg"], key="bk_cert")
            if cu: st.session_state["brand_cert"] = cu.read()
            if st.session_state.get("brand_cert"):
                st.image(st.session_state["brand_cert"], width=80)

        with r1c3:
            st.markdown("**🔗 Social Links**")
            fb_v    = st.text_input("Facebook",    value=st.session_state.get("bk_fb",""),    key="_fb")
            insta_v = st.text_input("Instagram",   value=st.session_state.get("bk_insta",""), key="_ig")
            web_v   = st.text_input("Website",     value=st.session_state.get("bk_web",""),   key="_wb")
            if st.button("💾 Save Brand Kit", use_container_width=True):
                st.session_state.update(bk_fb=fb_v, bk_insta=insta_v, bk_web=web_v)
                st.success("Saved!")

        st.markdown("---")
        st.markdown("##### 🔑 API Keys  —  all 100% free")
        k1, k2, k3 = st.columns(3)

        with k1:
            hf = st.text_input("🤗 Hugging Face Token", type="password",
                                value=st.session_state.get("hf_token",""),
                                placeholder="hf_xxxxxxxxxx",
                                help="huggingface.co → Settings → Access Tokens → New (Read)")
            if hf: st.session_state["hf_token"] = hf.strip()
            if _hf_key():   st.success("✓ HF — AI image gen active")
            else:           st.warning("No HF token → gradient background")

        with k2:
            gq = st.text_input("⚡ Groq API Key", type="password",
                                value=st.session_state.get("groq_key",""),
                                placeholder="gsk_xxxxxxxxxx",
                                help="console.groq.com → API Keys → Create (free, fast)")
            if gq: st.session_state["groq_key"] = gq.strip()
            if _groq_key():  st.success("✓ Groq — fast LLM active")
            else:            st.info("Optional (Gemini used as fallback)")

        with k3:
            gm = st.text_input("🔵 Gemini API Key", type="password",
                                value=st.session_state.get("gemini_key",""),
                                placeholder="AIzaSy...",
                                help="aistudio.google.com/app/apikey — free, 250 req/day")
            if gm: st.session_state["gemini_key"] = gm.strip()
            if _gemini_key(): st.success("✓ Gemini — LLM fallback ready")
            else:             st.info("aistudio.google.com/app/apikey")

    # Pull brand kit
    logo_bytes = st.session_state.get("brand_logo")
    cert_bytes = st.session_state.get("brand_cert")
    bk_fb      = st.session_state.get("bk_fb","")
    bk_insta   = st.session_state.get("bk_insta","")
    bk_web     = st.session_state.get("bk_web","")

    st.markdown("---")

    # ── TABS ──────────────────────────────────────────────────────────────────
    tab_copy, tab_single, tab_video, tab_bulk = st.tabs([
        "🤖 AI Copy Generator",
        "🖼️ Banner Studio",
        "🎬 Video Slideshow",
        "📦 Bulk Export",
    ])

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 1 — AI COPY GENERATOR
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_copy:
        st.markdown("### 🤖 Full Package Copy Generator")
        st.caption("Generates headline, subheadline, highlights, price hint, CTA, "
                   "YouTube title+desc, Instagram/Facebook/WhatsApp captions, "
                   "reel script AND AI scene prompts for the Video tab.")

        cl, cr = st.columns([1,1], gap="large")

        with cl:
            cp_dest  = st.text_input("🗺️ Destination", placeholder="Rajasthan, India")
            cp_type  = st.selectbox("🏷️ Package Type", [
                "Cultural & Heritage Tour", "Beach & Relaxation",
                "Adventure & Trekking", "Wildlife Safari",
                "Honeymoon Package", "Family Holiday",
                "Pilgrimage / Religious Tour", "Luxury Getaway",
                "Budget Backpacker", "Corporate / MICE",
            ])
            cp_dur   = st.text_input("📅 Duration", placeholder="7 Nights / 8 Days")
            cp_extra = st.text_area("💬 Key highlights / inclusions",
                                    placeholder="Desert safari, camel ride, folk dinner, "
                                                "Jaipur city tour, Udaipur lake cruise…", height=100)
            cp_gen = st.button("✨ Generate All Copy + Scene Prompts",
                                type="primary", use_container_width=True,
                                disabled=not (_llm_ok() and cp_dest.strip()))
            if not _llm_ok():
                st.warning("⚠️ Add a Groq or Gemini key in Brand Kit to enable AI copy.")

        with cr:
            if cp_gen:
                with st.spinner("AI crafting your travel marketing copy…"):
                    result = llm_generate_all_copy(cp_dest, cp_type, cp_dur, cp_extra)
                if result:
                    st.session_state["ai_copy"] = result
                    st.session_state["ai_dest"] = cp_dest
                    st.success("✅ All copy generated! Tabs auto-filled.")
                else:
                    st.error("Empty response. Check your API key and try again.")

            ai = st.session_state.get("ai_copy", {})
            if ai:
                def _box(label, val):
                    if not val: return
                    st.markdown(f'<div class="copy-lbl">{label}</div>', unsafe_allow_html=True)
                    v = "\n".join(f"• {h}" for h in val) if isinstance(val, list) else str(val)
                    st.markdown(f'<div class="copy-val">{v}</div>', unsafe_allow_html=True)

                for key, lbl in [
                    ("title","HEADLINE"), ("subtitle","SUBTITLE"),
                    ("package_name","PACKAGE NAME"), ("price_hint","PRICE HINT"),
                    ("cta","CALL TO ACTION"), ("highlights","HIGHLIGHTS"),
                ]:
                    _box(lbl, ai.get(key,""))

                st.markdown("---")
                for key, lbl in [
                    ("youtube_title","📺 YouTube Title"),
                    ("youtube_desc","📺 YouTube Description"),
                    ("instagram_caption","📸 Instagram Caption"),
                    ("facebook_caption","👥 Facebook Caption"),
                    ("whatsapp_status","📱 WhatsApp Status"),
                    ("short_video_script","🎬 30-sec Reel Script"),
                    ("scene_prompts","🎨 AI Scene Prompts (copy to Video tab)"),
                ]:
                    _box(lbl, ai.get(key,""))

                st.info("👉 Go to **Banner Studio** or **Video Slideshow** — all fields are pre-filled!")
            else:
                st.markdown('<div class="empty"><div class="ei">🤖</div>'
                            '<div class="et">Enter destination → Generate</div></div>',
                            unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 2 — BANNER STUDIO
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_single:
        ai = st.session_state.get("ai_copy", {})
        sl, sr = st.columns([1,1], gap="large")

        with sl:
            st.markdown("### 🎨 AI Scene")
            s_dest  = st.text_input("Destination",
                                     value=st.session_state.get("ai_dest",""),
                                     placeholder="Rajasthan, India", key="s_dest")
            s_desc  = st.text_area("Describe the scene for AI to generate",
                                    height=90, key="s_desc",
                                    placeholder="Majestic Amber Fort at golden sunset, "
                                                "Rajasthan desert, warm orange sky, no people")
            s_style = st.selectbox("Image style", list(IMG_STYLES.keys()), key="s_style")
            s_enh   = st.checkbox("✨ AI prompt enhancement", value=True,
                                   disabled=not _llm_ok(), key="s_enh")

            st.markdown("### 📐 Platform & Design")
            s_plat   = st.selectbox("Platform", list(PLATFORMS.keys()), key="s_plat")
            sw, sh   = PLATFORMS[s_plat]
            c1, c2   = st.columns(2)
            with c1: s_theme  = st.selectbox("Visual Theme", list(THEMES.keys()), key="s_theme")
            with c2: s_layout = st.selectbox("Layout", list(LAYOUTS.keys()), key="s_layout")
            c3, c4   = st.columns(2)
            with c3: s_lpos = st.selectbox("Logo pos", ["Top Right","Top Left","Bottom Right","Bottom Left"], key="s_lpos")
            with c4: s_ov   = st.slider("Overlay darkness", 80, 220, 145, key="s_ov")
            s_grain  = st.checkbox("Film grain effect", value=True, key="s_grain")

            st.markdown("### ✍️ Content")
            use_ai   = bool(ai) and st.checkbox("⚡ Auto-fill from AI Copy tab", value=bool(ai))

            s_pkg    = st.text_input("Package name",
                                      value=ai.get("package_name","") if use_ai else "",
                                      placeholder="Royal Rajasthan — 7 Days", key="s_pkg")
            s_head   = st.text_input("Headline",
                                      value=ai.get("title","") if use_ai else "",
                                      placeholder="Discover the Land of Maharajas", key="s_head")
            s_sub    = st.text_input("Subheadline",
                                      value=ai.get("subtitle","") if use_ai else "",
                                      placeholder="Heritage · Desert · Culture", key="s_sub")
            s_price  = st.text_input("Price",
                                      value=ai.get("price_hint","") if use_ai else "",
                                      placeholder="₹29,999/person", key="s_price")
            s_cta    = st.text_input("CTA",
                                      value=ai.get("cta","Book Now →") if use_ai else "Book Now →",
                                      key="s_cta")
            def_hl   = "\n".join(ai.get("highlights",[])) if use_ai else ""
            s_hl_raw = st.text_area("Highlights (one per line)", value=def_hl, height=110,
                                     placeholder="Amber Fort Sunrise\nDesert Safari\nCamel Camp",
                                     key="s_hl")
            s_hl     = [l.strip() for l in s_hl_raw.splitlines() if l.strip()]

            s_gen    = st.button("🚀 Generate Banner", type="primary", use_container_width=True)

        with sr:
            st.markdown("### 👁️ Preview")

            if s_gen:
                if not s_desc.strip():
                    st.error("Describe the scene you want AI to generate.")
                else:
                    with st.spinner("1/3 · Enhancing scene prompt…"):
                        sfx = IMG_STYLES[s_style]
                        final_p = (llm_enhance_image_prompt(s_desc, sfx, s_dest)
                                   if s_enh and _llm_ok()
                                   else f"{s_desc}, {s_dest}, {sfx}, no text, no people")

                    with st.expander("📝 Enhanced prompt", expanded=False):
                        st.caption(final_p)

                    with st.spinner("2/3 · AI generating scene (15-30s)…"):
                        bg = generate_ai_image(final_p, sw, sh)

                    with st.spinner("3/3 · Compositing with pro branding…"):
                        banner = compose_banner(
                            bg_img=bg, w=sw, h=sh,
                            theme=THEMES[s_theme],
                            layout=s_layout,
                            package_name=s_pkg, headline=s_head,
                            subheadline=s_sub, highlights=s_hl,
                            price=s_price, cta=s_cta,
                            logo_bytes=logo_bytes, logo_pos=s_lpos,
                            cert_bytes=cert_bytes,
                            fb=bk_fb, insta=bk_insta, web=bk_web,
                            overlay_alpha=s_ov, grain=s_grain,
                        )

                    st.session_state["s_banner_png"] = to_bytes(banner, "PNG")
                    st.session_state["s_banner_jpg"] = to_bytes(banner, "JPEG", quality=90)
                    st.session_state["s_name"] = f"{s_pkg or 'banner'}_{s_plat[:14]}"

            if st.session_state.get("s_banner_png"):
                st.image(st.session_state["s_banner_png"], use_container_width=True)
                base_name = st.session_state.get("s_name","banner")
                c_dl1, c_dl2 = st.columns(2)
                with c_dl1:
                    st.download_button("📥 PNG (lossless)",
                        data=st.session_state["s_banner_png"],
                        file_name=f"{base_name}.png", mime="image/png",
                        use_container_width=True)
                with c_dl2:
                    st.download_button("📥 JPEG (smaller)",
                        data=st.session_state["s_banner_jpg"],
                        file_name=f"{base_name}.jpg", mime="image/jpeg",
                        use_container_width=True)
                st.success("✅ Ready to post!")
            else:
                st.markdown('<div class="empty"><div class="ei">🎨</div>'
                            '<div class="et">Describe a scene → AI generates it → '
                            'professional brand overlaid</div></div>',
                            unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 3 — VIDEO SLIDESHOW
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_video:
        ai = st.session_state.get("ai_copy", {})
        st.markdown("### 🎬 Multi-Scene Animated Slideshow  (20-30 sec)")
        st.info(
            "Each scene = unique AI image + caption overlay. "
            "Download GIF → import to **CapCut** → add music → export as MP4 for Reels/Shorts."
        )

        vl, vr = st.columns([1,1], gap="large")

        with vl:
            v_dest  = st.text_input("Destination",
                                     value=st.session_state.get("ai_dest",""),
                                     placeholder="Kerala, India", key="v_dest")
            v_pkg   = st.text_input("Package name",
                                     value=ai.get("package_name","") if ai else "",
                                     placeholder="Backwaters Bliss — 5 Days", key="v_pkg")
            v_price = st.text_input("Price (shown on last slide)",
                                     value=ai.get("price_hint","") if ai else "",
                                     placeholder="₹22,999/person", key="v_price")

            c1, c2  = st.columns(2)
            with c1: v_theme = st.selectbox("Theme", list(THEMES.keys()), key="v_theme")
            with c2: v_style = st.selectbox("Style", list(IMG_STYLES.keys()), key="v_style")

            v_plat  = st.selectbox("Format", [
                "Instagram Story    9:16  1080×1920",
                "YouTube Shorts     9:16  1080×1920",
                "Instagram Post     1:1   1080×1080",
                "YouTube Thumbnail  16:9  1280×720",
            ], key="v_plat")
            vw, vh  = PLATFORMS[v_plat]

            v_lpos  = st.selectbox("Logo position", ["Top Right","Top Left"], key="v_lpos")
            v_ov    = st.slider("Overlay darkness", 80, 220, 155, key="v_ov")
            v_dur   = st.slider("Seconds per scene", 2, 5, 3, key="v_dur")
            v_caps  = st.checkbox("✨ AI writes captions per slide",
                                   value=_llm_ok(), disabled=not _llm_ok())

            st.markdown("### 🎞️ Scenes")
            ai_scenes = ai.get("scene_prompts", []) if ai else []
            ai_hls    = ai.get("highlights", []) if ai else []
            n_sc = st.slider("Number of scenes", 3, 8,
                              min(6, max(3, len(ai_scenes))), key="v_nsc")

            scene_descs = []; scene_caps_in = []
            for i in range(n_sc):
                sc_col, cap_col = st.columns([2,1])
                with sc_col:
                    s = st.text_input(f"Scene {i+1} — image description",
                                       value=ai_scenes[i] if i < len(ai_scenes) else "",
                                       placeholder=f"Describe scene {i+1}", key=f"vs_{i}")
                    scene_descs.append(s)
                with cap_col:
                    c = st.text_input("Caption",
                                       value=ai_hls[i] if i < len(ai_hls) else "",
                                       placeholder=f"Caption {i+1}", key=f"vc_{i}")
                    scene_caps_in.append(c)

            v_gen = st.button("🎬 Generate Slideshow",
                               type="primary", use_container_width=True,
                               disabled=not any(s.strip() for s in scene_descs))

        with vr:
            st.markdown("### 👁️ Live Preview")

            if v_gen:
                valid = [(s.strip(), scene_caps_in[i])
                         for i, s in enumerate(scene_descs) if s.strip()]
                if not valid:
                    st.error("Fill in at least one scene description.")
                else:
                    if v_caps and _llm_ok():
                        with st.spinner("AI writing slide captions…"):
                            captions = llm_scene_captions(
                                v_pkg, [s for s,_ in valid], len(valid))
                    else:
                        captions = [c or s[:28] for s,c in valid]

                    sfx    = IMG_STYLES[v_style]
                    frames = []
                    thumb_cols = st.columns(min(len(valid), 4))
                    prog   = st.progress(0, text="Generating scenes…")
                    total  = len(valid)

                    for idx, (scene_desc, _) in enumerate(valid):
                        prog.progress(idx/total,
                                      text=f"Scene {idx+1}/{total}: AI generating…")

                        full_p = (llm_enhance_image_prompt(scene_desc, sfx, v_dest)
                                  if _llm_ok()
                                  else f"{scene_desc}, {v_dest}, {sfx}, no text")

                        bg = generate_ai_image(full_p, vw, vh)
                        cap = captions[idx] if idx < len(captions) else f"✨ {idx+1}"

                        frame = compose_banner(
                            bg_img=bg, w=vw, h=vh,
                            theme=THEMES[v_theme],
                            package_name=v_pkg if idx == 0 else "",
                            price=v_price if idx == total-1 else "",
                            cta="Book Now →" if idx == total-1 else "",
                            slide_caption=cap,
                            slide_num=f"{idx+1:02d} / {total:02d}",
                            logo_bytes=logo_bytes, logo_pos=v_lpos,
                            cert_bytes=cert_bytes,
                            fb=bk_fb, insta=bk_insta, web=bk_web,
                            overlay_alpha=v_ov, grain=True,
                        )
                        frames.append(frame)

                        # Live thumbnail
                        col_idx = idx % 4
                        if col_idx < len(thumb_cols):
                            scale = 120 / frame.width
                            thumb = frame.resize(
                                (int(frame.width*scale), int(frame.height*scale)),
                                Image.LANCZOS)
                            thumb_cols[col_idx].image(to_bytes(thumb),
                                                      caption=cap[:20],
                                                      use_container_width=True)

                    prog.progress(1.0, text="Building GIF…")
                    gif = make_gif(frames, ms=v_dur*1000)
                    st.session_state.update(
                        v_gif=gif,
                        v_frames=[to_bytes(f) for f in frames],
                        v_pkg=v_pkg,
                        v_captions=captions,
                    )
                    prog.empty()
                    st.success(f"✅ {len(frames)}-scene GIF · {len(gif)//1024} KB")

            gif = st.session_state.get("v_gif")
            if gif:
                b64 = base64.b64encode(gif).decode()
                st.markdown(f'<img src="data:image/gif;base64,{b64}" '
                            f'style="width:100%;border-radius:12px;border:1px solid #1f2937">',
                            unsafe_allow_html=True)

                dl1, dl2 = st.columns(2)
                with dl1:
                    st.download_button("📥 Download GIF", data=gif,
                        file_name=f"{st.session_state.get('v_pkg','video')}_slideshow.gif",
                        mime="image/gif", use_container_width=True)
                with dl2:
                    if st.session_state.get("v_frames"):
                        zbuf = io.BytesIO()
                        with zipfile.ZipFile(zbuf,"w") as zf:
                            for i, fb2 in enumerate(st.session_state["v_frames"]):
                                zf.writestr(f"scene_{i+1:02d}.png", fb2)
                        zbuf.seek(0)
                        st.download_button("📥 Frames ZIP (for CapCut)",
                            data=zbuf.getvalue(), file_name="scenes.zip",
                            mime="application/zip", use_container_width=True)

                caps = st.session_state.get("v_captions",[])
                if caps:
                    with st.expander("📝 Slide captions"):
                        for i,c in enumerate(caps):
                            st.markdown(f"**{i+1}.** {c}")

                st.markdown("---")
                st.markdown(
                    "**🎵 MP4 workflow (free):** "
                    "GIF → **[CapCut](https://capcut.com)** → add music "
                    "([Pixabay](https://pixabay.com/music/) / YouTube Audio Library) "
                    "→ export 1080×1920 MP4 → upload to Reels/Shorts"
                )
            else:
                st.markdown('<div class="empty"><div class="ei">🎬</div>'
                            '<div class="et">Add scenes → Generate → Download GIF → CapCut</div>'
                            '</div>', unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 4 — BULK EXPORT
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_bulk:
        ai = st.session_state.get("ai_copy",{})
        st.markdown("### 📦 One AI Image → Every Platform Size")
        st.info("Generates the AI image once at max quality, then smart-crops & composites "
                "for every selected platform. Download a single ZIP.")

        bl, br = st.columns([1,1], gap="large")

        with bl:
            b_dest  = st.text_input("Destination", placeholder="Goa, India", key="b_dest")
            b_desc  = st.text_area("Scene description", height=80, key="b_desc",
                                    placeholder="Pristine beach, turquoise sea, "
                                                "palm trees swaying, golden sunset, no people")
            b_style = st.selectbox("Style", list(IMG_STYLES.keys()), key="b_style")
            b_theme = st.selectbox("Theme", list(THEMES.keys()), key="b_theme")
            b_lay   = st.selectbox("Layout", list(LAYOUTS.keys()), key="b_lay")
            b_ai    = bool(ai) and st.checkbox("⚡ Fill from AI Copy tab", value=bool(ai), key="b_ai")

            b_pkg   = st.text_input("Package Name", key="b_pkg",
                                     value=ai.get("package_name","") if b_ai else "",
                                     placeholder="Goa Beach Holiday — 5N/6D")
            b_head  = st.text_input("Headline", key="b_head",
                                     value=ai.get("title","") if b_ai else "")
            b_sub   = st.text_input("Subheadline", key="b_sub",
                                     value=ai.get("subtitle","") if b_ai else "")
            b_price = st.text_input("Price", key="b_price",
                                     value=ai.get("price_hint","") if b_ai else "")
            b_cta   = st.text_input("CTA", key="b_cta",
                                     value=ai.get("cta","Book Now →") if b_ai else "Book Now →")
            def_hl  = "\n".join(ai.get("highlights",[])) if b_ai else ""
            b_hl    = st.text_area("Highlights (one per line)", key="b_hl",
                                    value=def_hl, height=90,
                                    placeholder="Baga Beach\nWater Sports\nSunset Cruise")
            b_lpos  = st.radio("Logo position",
                                ["Top Right","Top Left","Bottom Right","Bottom Left"],
                                horizontal=True, key="b_lpos")
            b_plats = st.multiselect("Export for", list(PLATFORMS.keys()),
                                      default=list(PLATFORMS.keys())[:5])
            b_gen   = st.button("📦 Generate All Sizes",
                                 type="primary", use_container_width=True,
                                 disabled=not (b_desc.strip() and b_plats))

        with br:
            st.markdown("### 📋 Results")

            if b_gen and b_plats and b_desc.strip():
                sfx = IMG_STYLES[b_style]
                b_highlights = [l.strip() for l in b_hl.splitlines() if l.strip()]

                with st.spinner("1/2 · AI generating master image at full quality…"):
                    final_p = (llm_enhance_image_prompt(b_desc, sfx, b_dest)
                               if _llm_ok()
                               else f"{b_desc}, {b_dest}, {sfx}, no text")
                    master = generate_ai_image(final_p, 1024, 1024)

                with st.spinner(f"2/2 · Compositing {len(b_plats)} platform banners…"):
                    zbuf = io.BytesIO()
                    prog = st.progress(0)
                    preview_shown = False

                    with zipfile.ZipFile(zbuf,"w",zipfile.ZIP_DEFLATED) as zf:
                        for i, p_name in enumerate(b_plats):
                            pw, ph = PLATFORMS[p_name]
                            bg_crop = _crop_for_platform(master, pw, ph)

                            banner = compose_banner(
                                bg_img=bg_crop, w=pw, h=ph,
                                theme=THEMES[b_theme], layout=b_lay,
                                package_name=b_pkg, headline=b_head,
                                subheadline=b_sub, highlights=b_highlights,
                                price=b_price, cta=b_cta,
                                logo_bytes=logo_bytes, logo_pos=b_lpos,
                                cert_bytes=cert_bytes,
                                fb=bk_fb, insta=bk_insta, web=bk_web,
                            )
                            safe = re.sub(r"[^\w]"," ",p_name).strip().replace(" ","_")[:28]
                            fname = f"{b_pkg or 'banner'}_{safe}_{pw}x{ph}.png"
                            zf.writestr(fname, to_bytes(banner))

                            if not preview_shown:
                                st.image(to_bytes(banner), caption=p_name,
                                         use_container_width=True)
                                preview_shown = True

                            prog.progress((i+1)/len(b_plats))

                prog.empty()
                zbuf.seek(0)
                st.success(f"✅ {len(b_plats)} banners ready!")
                st.download_button("📥 Download ZIP (all platforms)",
                    data=zbuf.getvalue(),
                    file_name=f"{b_pkg or 'banners'}_all_platforms.zip",
                    mime="application/zip", use_container_width=True)
            else:
                st.markdown('<div class="empty"><div class="ei">📦</div>'
                            '<div class="et">One AI image → smart-cropped for every platform → ZIP</div>'
                            '</div>', unsafe_allow_html=True)

    # ── TIPS ──────────────────────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("🔑 How to get your free API keys"):
        st.markdown("""
| Key | Where | Free limit | Use |
|---|---|---|---|
| **HF Token** | [huggingface.co](https://huggingface.co) → Settings → Access Tokens → New (Read) | ~50-100 images/month free · pay-per-use after | AI image generation |
| **Groq** | [console.groq.com](https://console.groq.com) → API Keys → Create | Generous daily free limit | Fast LLM (copy, captions, prompts) |
| **Gemini** | [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) → Create key | 250 req/day free | LLM fallback |

**Note on HF billing:** FLUX.1-schnell via Inference Providers costs ~$0.003/image.
Add a card at huggingface.co → Settings → Billing. You're only charged what you use.
For zero-cost images, HF free tier works but has limited monthly credits.
        """)

    with st.expander("💡 Pro tips — stunning travel images"):
        st.markdown("""
**Scene description formula:**
`[Subject] + [Location detail] + [Time of day] + [Atmosphere] + [Composition] + [Quality tags]`

**Examples:**
> *Taj Mahal at golden sunrise, reflection in marble pool, dramatic orange clouds, wide-angle, 8k, no text, no people*

> *Traditional Kerala houseboat gliding on misty backwaters, lush palms, golden hour glow, cinematic, 8k*

> *Baga Beach Goa, crystal turquoise waves, white sand, swaying palms, aerial drone, vibrant, no people*

**Always include:** `no text, no watermark, no people, no logos`

**Theme pairing guide:**
| Destination type | Recommended theme | Layout |
|---|---|---|
| Heritage / Forts | 🌅 Golden Hour | Magazine |
| Beach / Resort | 🌊 Deep Ocean | Story |
| Luxury / Premium | 🖤 Dark Luxury | Bold |
| Adventure / Trek | 🌿 Emerald Jungle | Cinematic |
| Honeymoon | 🌸 Blossom Pink | Minimal |
| Wildlife | 🏜️ Desert Dunes | Magazine |
        """)
