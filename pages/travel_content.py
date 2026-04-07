"""
🏖️ Travel Content Creator — Hybrid (Production Ready)
=======================================================
Architecture:
  • REAL PHOTOS     → you upload actual travel images (always best quality)
  • AI DESIGN       → Groq generates: headlines, captions, hashtags, colour palette,
                      layout suggestions, video scene order
  • PILLOW ENGINE   → composes everything: photo + text + logo + cert + social bar
  • REUSABLE BRAND  → logo, cert badge, social links saved in session state
  • OUTPUT          → PNG banners (all platforms) + animated GIF video + ZIP bulk export

No external image API needed. No quota errors. No cold starts.
"""

import streamlit as st
import sys, os, io, json, zipfile, base64, textwrap, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ── Platform sizes ────────────────────────────────────────────────────────────
PLATFORMS = {
    "Instagram Post 1:1 (1080×1080)":      (1080, 1080),
    "Instagram / Reels Story 9:16 (1080×1920)": (1080, 1920),
    "YouTube Thumbnail 16:9 (1280×720)":   (1280,  720),
    "YouTube Shorts 9:16 (1080×1920)":     (1080, 1920),
    "Facebook Post (1200×630)":            (1200,  630),
    "Facebook Cover (820×312)":            (820,   312),
    "WhatsApp Status 9:16 (1080×1920)":    (1080, 1920),
    "Twitter/X Post (1200×675)":           (1200,  675),
    "LinkedIn Post (1200×628)":            (1200,  628),
}

# ── Design templates ──────────────────────────────────────────────────────────
TEMPLATES = {
    "🌅 Bold Overlay":       "full_overlay",
    "📰 Bottom Strip":       "bottom_strip",
    "🎬 Cinematic Bars":     "cinematic",
    "💎 Luxury Dark":        "luxury",
    "🌿 Nature Clean":       "nature",
    "⬛ Minimal Side Panel": "side_panel",
    "🔲 Split Screen":       "split_screen",
    "🌊 Gradient Wave":      "gradient_wave",
}

# ── Colour palettes ───────────────────────────────────────────────────────────
PALETTES = {
    "Sunset Gold":    {"primary": (255,180,40),  "dark": (30,15,5),    "light": (255,245,220)},
    "Ocean Blue":     {"primary": (0,170,210),   "dark": (5,20,50),    "light": (220,245,255)},
    "Forest Green":   {"primary": (80,180,100),  "dark": (10,35,20),   "light": (220,245,225)},
    "Royal Purple":   {"primary": (160,100,220), "dark": (20,5,40),    "light": (240,225,255)},
    "Coral Red":      {"primary": (240,80,60),   "dark": (40,10,5),    "light": (255,235,230)},
    "Midnight Black": {"primary": (200,170,100), "dark": (8,8,12),     "light": (255,250,240)},
    "Rose Gold":      {"primary": (210,130,110), "dark": (35,15,10),   "light": (255,240,235)},
    "Teal Breeze":    {"primary": (0,190,170),   "dark": (5,30,30),    "light": (215,250,248)},
}

# ── Key helpers ───────────────────────────────────────────────────────────────
def _get(sk, sec, ev):
    v = st.session_state.get(sk, "").strip()
    if v: return v
    try:
        v = str(st.secrets.get(sec, "")).strip()
        if v: return v
    except: pass
    return os.getenv(ev, "").strip()

def _llm_key(): return _get("api_key", "GROQ_API_KEY", "GROQ_API_KEY")

# ── Font loader ───────────────────────────────────────────────────────────────
_FONT_CACHE = {}
def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    key = (size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    candidates = [
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf",
        f"/usr/share/fonts/truetype/liberation/LiberationSans{'-Bold' if bold else '-Regular'}.ttf",
        f"/usr/share/fonts/truetype/ubuntu/Ubuntu-{'B' if bold else 'R'}.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                f = ImageFont.truetype(p, size)
                _FONT_CACHE[key] = f
                return f
            except: pass
    return ImageFont.load_default()

# ── AI content generator ──────────────────────────────────────────────────────
def ai_generate_content(
    destination: str,
    package_name: str,
    duration: str,
    highlights: list[str],
    price: str,
    platform: str,
    tone: str,
) -> dict:
    """
    Uses Groq to generate: headline, subheadline, caption, hashtags,
    recommended palette, video scene captions, and CTA text.
    Returns dict with all fields. Falls back to smart defaults if no key.
    """
    key = _llm_key()

    defaults = {
        "headline":     f"Discover {destination}",
        "subheadline":  " · ".join(highlights[:3]) if highlights else "An unforgettable journey",
        "caption":      f"Experience the magic of {destination} with our {package_name}. Book now!",
        "hashtags":     f"#{destination.replace(' ','')} #Travel #TravelIndia #Wanderlust #TourPackage",
        "cta":          "Book Now →",
        "palette":      "Sunset Gold",
        "scene_captions": [h for h in highlights[:6]] if highlights else [destination],
        "youtube_title":f"{destination} Travel Package | {package_name} | {price}",
        "youtube_desc": f"Discover {destination} with our {package_name}.\n\nHighlights:\n" +
                        "\n".join(f"• {h}" for h in highlights),
    }

    if not key:
        return defaults

    prompt_data = {
        "destination": destination,
        "package": package_name,
        "duration": duration,
        "highlights": highlights[:8],
        "price": price,
        "platform": platform,
        "tone": tone,
    }

    system = """You are an expert travel marketing copywriter for Indian travel agencies.
Generate compelling social media content. Return ONLY valid JSON, no markdown, no explanation.
JSON keys: headline (max 8 words), subheadline (max 12 words), caption (2-3 sentences),
hashtags (10-12 relevant hashtags as one string), cta (3-5 words with arrow),
palette (one of: Sunset Gold/Ocean Blue/Forest Green/Royal Purple/Coral Red/Midnight Black/Rose Gold/Teal Breeze),
scene_captions (array of short captions for each highlight, max 5 words each),
youtube_title (SEO optimised, max 60 chars), youtube_desc (3 paragraphs)."""

    try:
        from groq import Groq
        client = Groq(api_key=key)
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": f"Generate travel content for: {json.dumps(prompt_data)}"}
            ],
            max_tokens=800, temperature=0.75,
            response_format={"type": "json_object"},
        )
        result = json.loads(resp.choices[0].message.content)
        # Merge with defaults for any missing keys
        for k, v in defaults.items():
            result.setdefault(k, v)
        return result
    except Exception as e:
        st.warning(f"AI content generation failed ({e}). Using smart defaults.")
        return defaults

# ── Image processing helpers ──────────────────────────────────────────────────
def _fit_cover(img: Image.Image, w: int, h: int) -> Image.Image:
    """Resize + centre-crop image to exactly w×h (cover mode)."""
    img = img.convert("RGBA")
    ratio = max(w / img.width, h / img.height)
    nw, nh = int(img.width * ratio), int(img.height * ratio)
    img = img.resize((nw, nh), Image.LANCZOS)
    left = (nw - w) // 2
    top  = (nh - h) // 2
    return img.crop((left, top, left + w, top + h))


def _enhance_photo(img: Image.Image, brightness: float = 1.05,
                   contrast: float = 1.1, saturation: float = 1.15) -> Image.Image:
    """Slightly enhance photo for social media pop."""
    img = ImageEnhance.Brightness(img).enhance(brightness)
    img = ImageEnhance.Contrast(img).enhance(contrast)
    img = ImageEnhance.Color(img).enhance(saturation)
    return img


def _wrap_text(text: str, font, max_w: int, draw: ImageDraw.ImageDraw) -> str:
    words = text.split()
    lines, line = [], ""
    for word in words:
        test = (line + " " + word).strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_w:
            line = test
        else:
            if line: lines.append(line)
            line = word
    if line: lines.append(line)
    return "\n".join(lines)


def _shadow(draw, xy, text, font, fill, shadow_px=3, shadow_alpha=160):
    sx, sy = xy[0] + shadow_px, xy[1] + shadow_px
    draw.text((sx, sy), text, font=font, fill=(0, 0, 0, shadow_alpha))
    draw.text(xy, text, font=font, fill=fill)


def _multiline_shadow(draw, xy, text, font, fill, spacing=8, shadow_px=3):
    sx, sy = xy[0] + shadow_px, xy[1] + shadow_px
    draw.multiline_text((sx, sy), text, font=font, fill=(0, 0, 0, 150), spacing=spacing)
    draw.multiline_text(xy, text, font=font, fill=fill, spacing=spacing)


def _pill(draw, x, y, text, font, bg_rgba, fg_rgba, rx=12, pad_x=18, pad_y=10):
    bb = draw.textbbox((0, 0), text, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    draw.rounded_rectangle(
        [x, y, x + tw + pad_x * 2, y + th + pad_y * 2],
        radius=rx, fill=bg_rgba
    )
    draw.text((x + pad_x, y + pad_y), text, font=font, fill=fg_rgba)
    return x + tw + pad_x * 2 + 12   # right edge + gap


def _overlay_rect(draw, box, fill_rgba):
    draw.rectangle(box, fill=fill_rgba)


def _paste_logo(canvas, logo_bytes, pos: str, max_px: int, bottom_pad: int = 70):
    if not logo_bytes: return canvas
    logo = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
    r = min(max_px / logo.width, max_px / logo.height)
    nw, nh = int(logo.width * r), int(logo.height * r)
    logo = logo.resize((nw, nh), Image.LANCZOS)
    W, H = canvas.size
    m = 22
    pos_map = {
        "Top Left":     (m, m),
        "Top Right":    (W - nw - m, m),
        "Bottom Left":  (m, H - nh - m - bottom_pad),
        "Bottom Right": (W - nw - m, H - nh - m - bottom_pad),
    }
    x, y = pos_map.get(pos, (W - nw - m, m))
    canvas.paste(logo, (x, y), logo)
    return canvas


def _paste_cert(canvas, cert_bytes, max_px: int = 90, bottom_pad: int = 70):
    if not cert_bytes: return canvas
    badge = Image.open(io.BytesIO(cert_bytes)).convert("RGBA")
    r = min(max_px / badge.width, max_px / badge.height)
    nw, nh = int(badge.width * r), int(badge.height * r)
    badge = badge.resize((nw, nh), Image.LANCZOS)
    W, H = canvas.size
    canvas.paste(badge, (22, H - nh - 22 - bottom_pad), badge)
    return canvas


def _social_bar(draw, w, h, fb, insta, web, primary_rgb, font, bar_h=60):
    draw.rectangle([0, h - bar_h, w, h], fill=(0, 0, 0, 185))
    items = []
    if fb:    items.append(f"f  {fb}")
    if insta: items.append(f"@  {insta}")
    if web:   items.append(f"   {web}")
    if not items: return
    line = "   ·   ".join(items)
    bb = draw.textbbox((0, 0), line, font=font)
    tw = bb[2] - bb[0]
    tx = max(0, (w - tw) // 2)
    ty = h - bar_h + (bar_h - (bb[3] - bb[1])) // 2
    draw.text((tx, ty), line, font=font, fill=primary_rgb + (255,))

# ── Template renderers ────────────────────────────────────────────────────────

def _render_full_overlay(canvas, draw, w, h, sc, pal, content, show_price, show_cta, fonts):
    fTitle, fSub, fHL, fPrice, fCTA, fSm = fonts
    primary = pal["primary"]; dark = pal["dark"]; light = pal["light"]
    margin = int(55 * sc); mw = w - margin * 2; cy = int(55 * sc)

    # gradient overlay — top lighter, bottom darker
    ov = Image.new("RGBA", (w, h))
    ovd = ImageDraw.Draw(ov)
    for y in range(h):
        t = y / h
        a = int(80 + 140 * t)
        r, g, b = [int(dark[i] + (dark[i] - dark[i]) * t) for i in range(3)]
        ovd.line([(0, y), (w, y)], fill=(*dark, a))
    canvas.alpha_composite(ov)
    draw = ImageDraw.Draw(canvas)

    # Package pill
    pkg = content.get("package_name", "")
    if pkg:
        _pill(draw, margin, cy, f"  ✈  {pkg.upper()}  ", fSm,
              (*primary, 210), (*dark, 255), pad_x=16, pad_y=10)
        cy += int(52 * sc)
        draw.rectangle([margin, cy, margin + int(70*sc), cy+3], fill=(*primary, 255))
        cy += int(16 * sc)

    # Headline
    hl = content.get("headline", "")
    if hl:
        wrapped = _wrap_text(hl, fTitle, mw, draw)
        _multiline_shadow(draw, (margin, cy), wrapped, fTitle, (*light, 255))
        bb = draw.multiline_textbbox((margin, cy), wrapped, font=fTitle)
        cy += bb[3] - bb[1] + int(12 * sc)

    # Subheadline
    sub = content.get("subheadline", "")
    if sub:
        wrapped = _wrap_text(sub, fSub, mw, draw)
        _multiline_shadow(draw, (margin, cy), wrapped, fSub, (*primary, 255))
        bb = draw.multiline_textbbox((margin, cy), wrapped, font=fSub)
        cy += bb[3] - bb[1] + int(24 * sc)

    # Highlights as bullets
    for hlt in content.get("highlights", [])[:5]:
        _shadow(draw, (margin, cy), f"  ✓  {hlt}", fHL, (*light, 220))
        bb = draw.textbbox((margin, cy), f"  ✓  {hlt}", font=fHL)
        cy += bb[3] - bb[1] + int(6 * sc)

    if content.get("highlights"):
        cy += int(14 * sc)

    # Price
    if show_price and content.get("price"):
        _shadow(draw, (margin, cy), f"From  {content['price']}", fPrice, (*primary, 255))
        bb = draw.textbbox((margin, cy), f"From  {content['price']}", font=fPrice)
        cy += bb[3] - bb[1] + int(20 * sc)

    # CTA
    if show_cta and content.get("cta"):
        _pill(draw, margin, cy, f"  {content['cta']}  ", fCTA,
              (*primary, 230), (*dark, 255), pad_x=20, pad_y=12)

    return draw


def _render_bottom_strip(canvas, draw, w, h, sc, pal, content, show_price, show_cta, fonts):
    fTitle, fSub, fHL, fPrice, fCTA, fSm = fonts
    primary = pal["primary"]; dark = pal["dark"]; light = pal["light"]

    strip_h = int(h * 0.38)
    strip_y = h - strip_h
    draw.rectangle([0, strip_y, w, h], fill=(*dark, 220))
    draw.rectangle([0, strip_y, w, strip_y + 4], fill=(*primary, 255))

    margin = int(40 * sc)
    cy = strip_y + int(22 * sc)
    mw = w - margin * 2

    pkg = content.get("package_name", "")
    if pkg:
        _pill(draw, margin, cy, f" ✈ {pkg} ", fSm,
              (*primary, 200), (*dark, 255), pad_x=12, pad_y=6)
        cy += int(44 * sc)

    hl = content.get("headline", "")
    if hl:
        wrapped = _wrap_text(hl, fTitle, mw, draw)
        _multiline_shadow(draw, (margin, cy), wrapped, fTitle, (*light, 255))
        bb = draw.multiline_textbbox((margin, cy), wrapped, font=fTitle)
        cy += bb[3] - bb[1] + int(8 * sc)

    sub = content.get("subheadline", "")
    if sub:
        wrapped = _wrap_text(sub, fSub, mw, draw)
        draw.multiline_text((margin, cy), wrapped, font=fSub, fill=(*primary, 255))
        bb = draw.multiline_textbbox((margin, cy), wrapped, font=fSub)
        cy += bb[3] - bb[1] + int(10 * sc)

    # Price + CTA side by side
    row_y = cy
    if show_price and content.get("price"):
        _shadow(draw, (margin, row_y), f"From {content['price']}", fPrice, (*primary, 255))
    if show_cta and content.get("cta"):
        cta_w = draw.textbbox((0,0), f"  {content['cta']}  ", font=fCTA)[2]
        _pill(draw, w - margin - cta_w - 32, row_y, f"  {content['cta']}  ", fCTA,
              (*primary, 230), (*dark, 255), pad_x=16, pad_y=10)
    return draw


def _render_cinematic(canvas, draw, w, h, sc, pal, content, show_price, show_cta, fonts):
    """Cinematic black bars top and bottom."""
    fTitle, fSub, fHL, fPrice, fCTA, fSm = fonts
    primary = pal["primary"]; dark = pal["dark"]; light = pal["light"]
    bar = int(h * 0.16)

    draw.rectangle([0, 0, w, bar], fill=(*dark, 230))
    draw.rectangle([0, h - bar, w, h], fill=(*dark, 230))
    draw.rectangle([0, bar, w, bar + 3], fill=(*primary, 255))
    draw.rectangle([0, h - bar - 3, w, h - bar], fill=(*primary, 255))

    margin = int(50 * sc)
    # Top bar: package name centred
    pkg = content.get("package_name", "")
    if pkg:
        bb = draw.textbbox((0, 0), pkg.upper(), font=fSm)
        tx = (w - (bb[2] - bb[0])) // 2
        draw.text((tx, (bar - (bb[3]-bb[1])) // 2), pkg.upper(), font=fSm, fill=(*primary, 255))

    # Middle overlay for headline
    mid_ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    mid_d  = ImageDraw.Draw(mid_ov)
    mid_h  = int(h * 0.32)
    mid_y  = bar + (h - 2*bar - mid_h) // 2
    mid_d.rectangle([0, mid_y, w, mid_y + mid_h], fill=(*dark, 160))
    canvas.alpha_composite(mid_ov)
    draw = ImageDraw.Draw(canvas)

    hl = content.get("headline", "")
    if hl:
        wrapped = _wrap_text(hl, fTitle, w - margin*2, draw)
        bb = draw.multiline_textbbox((0, 0), wrapped, font=fTitle)
        tx = (w - (bb[2]-bb[0])) // 2
        ty = mid_y + (mid_h - (bb[3]-bb[1])) // 2
        _multiline_shadow(draw, (tx, ty), wrapped, fTitle, (*light, 255), spacing=8)

    # Bottom bar
    cy = h - bar + int(8 * sc)
    parts = []
    if show_price and content.get("price"): parts.append(f"From {content['price']}")
    sub = content.get("subheadline", "")
    if sub: parts.append(sub)
    if show_cta and content.get("cta"): parts.append(content["cta"])
    line = "   |   ".join(parts)
    if line:
        bb = draw.textbbox((0,0), line, font=fSm)
        tx = (w - (bb[2]-bb[0])) // 2
        draw.text((tx, cy), line, font=fSm, fill=(*primary, 255))
    return draw


def _render_luxury(canvas, draw, w, h, sc, pal, content, show_price, show_cta, fonts):
    """Dark luxury with gold accents and thin borders."""
    fTitle, fSub, fHL, fPrice, fCTA, fSm = fonts
    primary = pal["primary"]; dark = (8,8,12); light = (255, 245, 220)

    # Very dark overlay
    ov = Image.new("RGBA", (w, h), (*dark, 190))
    canvas.alpha_composite(ov)

    # Thin decorative border
    bd = 18
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([bd, bd, w-bd, h-bd], outline=(*primary, 180), width=1)
    draw.rectangle([bd+8, bd+8, w-bd-8, h-bd-8], outline=(*primary, 80), width=1)

    margin = int(65 * sc); mw = w - margin*2
    cy = int(80 * sc)

    # Small ornament
    cx = w // 2
    draw.line([(cx-60, cy), (cx-10, cy)], fill=(*primary, 200), width=1)
    draw.line([(cx+10, cy), (cx+60, cy)], fill=(*primary, 200), width=1)
    draw.ellipse([(cx-5, cy-4), (cx+5, cy+4)], fill=(*primary, 230))
    cy += int(28 * sc)

    pkg = content.get("package_name", "")
    if pkg:
        bb = draw.textbbox((0,0), pkg.upper(), font=fSm)
        tx = (w - (bb[2]-bb[0])) // 2
        draw.text((tx, cy), pkg.upper(), font=fSm, fill=(*primary, 200))
        cy += int(40 * sc)

    hl = content.get("headline", "")
    if hl:
        wrapped = _wrap_text(hl, fTitle, mw, draw)
        bb = draw.multiline_textbbox((0,0), wrapped, font=fTitle)
        tx = (w - (bb[2]-bb[0])) // 2
        _multiline_shadow(draw, (tx, cy), wrapped, fTitle, (*light, 255), spacing=10)
        bb2 = draw.multiline_textbbox((tx, cy), wrapped, font=fTitle)
        cy += bb2[3]-bb2[1] + int(20 * sc)

    draw.line([(margin*2, cy), (w-margin*2, cy)], fill=(*primary, 150), width=1)
    cy += int(20 * sc)

    sub = content.get("subheadline","")
    if sub:
        wrapped = _wrap_text(sub, fSub, mw, draw)
        bb = draw.multiline_textbbox((0,0), wrapped, font=fSub)
        tx = (w - (bb[2]-bb[0])) // 2
        draw.multiline_text((tx, cy), wrapped, font=fSub, fill=(*primary, 200))
        bb2 = draw.multiline_textbbox((tx, cy), wrapped, font=fSub)
        cy += bb2[3]-bb2[1] + int(30 * sc)

    for hlt in content.get("highlights", [])[:4]:
        bb = draw.textbbox((0,0), f"◆  {hlt}", font=fHL)
        tx = (w - (bb[2]-bb[0])) // 2
        draw.text((tx, cy), f"◆  {hlt}", font=fHL, fill=(*light, 190))
        cy += int(36 * sc)

    if show_price and content.get("price"):
        cy += int(10 * sc)
        price_txt = f"FROM  {content['price']}"
        bb = draw.textbbox((0,0), price_txt, font=fPrice)
        tx = (w - (bb[2]-bb[0])) // 2
        _shadow(draw, (tx, cy), price_txt, fPrice, (*primary, 255))
        cy += bb[3]-bb[1] + int(20*sc)

    if show_cta and content.get("cta"):
        cta_txt = f"  {content['cta']}  "
        bb = draw.textbbox((0,0), cta_txt, font=fCTA)
        tx = (w - (bb[2]-bb[0]) - 40) // 2
        _pill(draw, tx, cy, cta_txt, fCTA, (*primary, 210), (*dark, 255), pad_x=20, pad_y=12)
    return draw


# ── Master compose function ───────────────────────────────────────────────────

def compose(
    photo_bytes: bytes,
    w: int, h: int,
    template: str,
    palette_name: str,
    content: dict,
    logo_bytes: bytes | None,
    logo_pos: str,
    cert_bytes: bytes | None,
    fb: str, insta: str, web: str,
    show_price: bool = True,
    show_cta: bool = True,
    enhance: bool = True,
    overlay_strength: int = 3,  # 1=light 2=medium 3=strong
) -> Image.Image:

    pal = PALETTES.get(palette_name, PALETTES["Sunset Gold"])
    sc  = min(w, h) / 1080

    # 1. Load + fit photo
    bg = Image.open(io.BytesIO(photo_bytes))
    bg = _fit_cover(bg, w, h)
    if enhance:
        bg = _enhance_photo(bg)
    canvas = bg.convert("RGBA")

    # 2. Font set
    fonts = (
        _font(int(72*sc), bold=True),   # title
        _font(int(38*sc), bold=False),  # sub
        _font(int(29*sc), bold=False),  # highlights
        _font(int(54*sc), bold=True),   # price
        _font(int(36*sc), bold=True),   # CTA
        _font(int(23*sc), bold=False),  # small
    )
    draw = ImageDraw.Draw(canvas)

    # 3. Render template
    tpl_map = {
        "full_overlay":  _render_full_overlay,
        "bottom_strip":  _render_bottom_strip,
        "cinematic":     _render_cinematic,
        "luxury":        _render_luxury,
        "nature":        _render_full_overlay,   # reuse with green palette
        "side_panel":    _render_bottom_strip,   # reuse with side feel
        "split_screen":  _render_cinematic,
        "gradient_wave": _render_full_overlay,
    }
    renderer = tpl_map.get(template, _render_full_overlay)
    draw = renderer(canvas, draw, w, h, sc, pal, content,
                    show_price, show_cta, fonts)

    # 4. Social bar
    _social_bar(draw, w, h, fb, insta, web, pal["primary"], fonts[5], bar_h=int(60*sc))

    # 5. Logo + cert
    canvas = _paste_logo(canvas, logo_bytes, logo_pos,
                         max_px=int(130*sc), bottom_pad=int(65*sc))
    canvas = _paste_cert(canvas, cert_bytes,
                         max_px=int(90*sc), bottom_pad=int(65*sc))

    return canvas.convert("RGB")


def to_bytes(img: Image.Image, fmt="PNG") -> bytes:
    buf = io.BytesIO()
    img.save(buf, format=fmt, quality=95)
    return buf.getvalue()


def make_slideshow_gif(frames: list[Image.Image], sec_per_frame: int = 3) -> bytes:
    thumbs = []
    for f in frames:
        scale = 540 / f.width
        thumbs.append(f.resize((540, int(f.height * scale)), Image.LANCZOS))
    buf = io.BytesIO()
    thumbs[0].save(
        buf, format="GIF", save_all=True,
        append_images=thumbs[1:],
        duration=sec_per_frame * 1000, loop=0, optimize=True,
    )
    return buf.getvalue()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE
# ─────────────────────────────────────────────────────────────────────────────

def render():
    st.markdown("# 🏖️ Travel Content Creator")
    st.markdown(
        "Upload your **real travel photos** · AI writes the copy · "
        "Pillow composes production-ready banners & videos"
    )
    st.markdown("---")

    # ── BRAND KIT ─────────────────────────────────────────────────────────────
    with st.expander("🏷️ Brand Kit — upload once, applies to everything", expanded=False):
        bk1, bk2, bk3 = st.columns(3)
        with bk1:
            st.markdown("**Company Logo**")
            lu = st.file_uploader("Logo (PNG with transparency best)",
                                   type=["png","jpg","jpeg"], key="bk_logo")
            if lu:
                st.session_state["brand_logo"] = lu.read()
            if st.session_state.get("brand_logo"):
                st.image(st.session_state["brand_logo"], width=120)
                if st.button("Clear logo", key="clr_logo"):
                    del st.session_state["brand_logo"]

        with bk2:
            st.markdown("**Certification Badge**")
            cu = st.file_uploader("Cert/award badge",
                                   type=["png","jpg","jpeg"], key="bk_cert")
            if cu:
                st.session_state["brand_cert"] = cu.read()
            if st.session_state.get("brand_cert"):
                st.image(st.session_state["brand_cert"], width=80)
                if st.button("Clear cert", key="clr_cert"):
                    del st.session_state["brand_cert"]

        with bk3:
            st.markdown("**Social Links**")
            fb_v = st.text_input("Facebook",  value=st.session_state.get("bk_fb",""),  key="_bk_fb")
            ig_v = st.text_input("Instagram", value=st.session_state.get("bk_ig",""),  key="_bk_ig")
            wb_v = st.text_input("Website",   value=st.session_state.get("bk_wb",""),  key="_bk_wb")
            lp_v = st.radio("Logo position",
                            ["Top Right","Top Left","Bottom Right","Bottom Left"],
                            horizontal=True, index=0, key="bk_lpos")
            if st.button("💾 Save Brand Kit", key="save_bk"):
                st.session_state.update({"bk_fb": fb_v, "bk_ig": ig_v,
                                         "bk_wb": wb_v, "bk_lpos": lp_v})
                st.success("Saved!")

    # Pull brand values
    logo_bytes = st.session_state.get("brand_logo")
    cert_bytes = st.session_state.get("brand_cert")
    fb    = st.session_state.get("bk_fb", "")
    insta = st.session_state.get("bk_ig", "")
    web   = st.session_state.get("bk_wb", "")
    logo_pos = st.session_state.get("bk_lpos", "Top Right")

    st.markdown("---")

    # ── TABS ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs([
        "🖼️ Single Banner",
        "🎬 Video Slideshow (20-30s)",
        "📦 Bulk Export — All Platforms",
    ])

    # ════════════════════════════════════════════════════════════════════
    # TAB 1 — SINGLE BANNER
    # ════════════════════════════════════════════════════════════════════
    with tab1:
        cl, cr = st.columns([1, 1], gap="large")
        with cl:
            st.markdown("### 📸 Photo")
            photo = st.file_uploader("Upload your travel photo",
                                      type=["jpg","jpeg","png","webp"], key="s_photo")
            if photo:
                # Read bytes immediately — Streamlit file objects exhaust after first .read()
                photo_bytes = photo.read()
                st.image(photo_bytes, use_container_width=True, caption="Preview")
            else:
                photo_bytes = None

            st.markdown("### 📐 Format & Design")
            platform  = st.selectbox("Platform", list(PLATFORMS.keys()), key="s_plat")
            template  = st.selectbox("Template", list(TEMPLATES.keys()), key="s_tpl")
            ai_palette = st.checkbox("✨ Let AI choose colour palette", value=True, key="s_aipal")
            if not ai_palette:
                palette = st.selectbox("Colour palette", list(PALETTES.keys()), key="s_pal")
            enhance_photo = st.checkbox("Auto-enhance photo colours", value=True, key="s_enh")

            st.markdown("### ✍️ Package Info")
            destination = st.text_input("Destination",   placeholder="Rajasthan, India", key="s_dest")
            pkg_name    = st.text_input("Package name",  placeholder="Royal Rajasthan — 7 Days", key="s_pkg")
            duration    = st.text_input("Duration",      placeholder="7 Days / 6 Nights", key="s_dur")
            price       = st.text_input("Price",         placeholder="₹29,999/person", key="s_price")
            hl_raw      = st.text_area("Highlights (one per line)",
                                        placeholder="Amber Fort Sunrise\nDesert Safari\nJaipur Markets\nCamel Camp",
                                        height=110, key="s_hl")
            highlights  = [l.strip() for l in hl_raw.splitlines() if l.strip()]

            tone        = st.selectbox("Tone / Style", [
                "Exciting & Adventurous", "Luxury & Premium",
                "Family Friendly", "Romantic", "Budget Friendly", "Cultural & Heritage",
            ], key="s_tone")

            st.markdown("### ⚙️ Options")
            c1, c2 = st.columns(2)
            with c1:
                show_price = st.checkbox("Show price", value=True, key="s_sp")
                show_cta   = st.checkbox("Show CTA button", value=True, key="s_sc")
            with c2:
                show_hash  = st.checkbox("Show hashtags below", value=True, key="s_sh")

            gen = st.button("🚀 Generate Banner", type="primary",
                            use_container_width=True,
                            disabled=photo_bytes is None)

        with cr:
            st.markdown("### 👁️ Preview")
            if gen and photo_bytes:
                with st.spinner("Step 1/3: AI generating copy & palette..."):
                    content_ai = ai_generate_content(
                        destination, pkg_name, duration,
                        highlights, price, platform, tone,
                    )
                    content_ai["package_name"] = pkg_name
                    content_ai["highlights"]   = highlights
                    content_ai["price"]        = price
                    sel_pal = content_ai.get("palette", "Sunset Gold") \
                              if ai_palette else palette

                with st.spinner("Step 2/3: Compositing banner..."):
                    w, h = PLATFORMS[platform]
                    img = compose(
                        photo_bytes, w, h,
                        TEMPLATES[template], sel_pal, content_ai,
                        logo_bytes, logo_pos, cert_bytes,
                        fb, insta, web,
                        show_price=show_price, show_cta=show_cta,
                        enhance=enhance_photo,
                    )

                b = to_bytes(img)
                st.session_state.update({"s_result": b, "s_ai": content_ai,
                                          "s_fname": f"{pkg_name or 'banner'}_{platform[:12]}.png"})

            if st.session_state.get("s_result"):
                st.image(st.session_state["s_result"], use_container_width=True)
                st.download_button("📥 Download PNG",
                                   data=st.session_state["s_result"],
                                   file_name=st.session_state.get("s_fname","banner.png"),
                                   mime="image/png", use_container_width=True)

                ai = st.session_state.get("s_ai", {})
                with st.expander("✨ AI-Generated Copy — copy for your posts"):
                    st.markdown(f"**Headline:** {ai.get('headline','')}")
                    st.markdown(f"**Subheadline:** {ai.get('subheadline','')}")
                    st.markdown(f"**Caption:**")
                    st.text_area("", value=ai.get("caption",""), height=80, key="cap_out")
                    if show_hash:
                        st.markdown(f"**Hashtags:**")
                        st.text_area("", value=ai.get("hashtags",""), height=60, key="hash_out")
                    st.markdown(f"**YouTube Title:** {ai.get('youtube_title','')}")
                    st.text_area("YouTube Description", value=ai.get("youtube_desc",""),
                                  height=120, key="yt_desc_out")
            else:
                st.markdown("""
                <div style="border:0.5px solid var(--color-border-tertiary);border-radius:12px;
                            padding:80px 20px;text-align:center">
                    <div style="font-size:48px">📸</div>
                    <div style="color:var(--color-text-secondary);margin-top:12px;font-size:14px">
                        Upload your photo → AI writes copy → Banner generated
                    </div>
                </div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════
    # TAB 2 — VIDEO SLIDESHOW
    # ════════════════════════════════════════════════════════════════════
    with tab2:
        st.markdown("### 🎬 Multi-scene slideshow (20-30 seconds)")
        st.info(
            "Upload 4-10 travel photos → AI writes a caption for each scene → "
            "Pillow composes every frame → Download animated GIF → "
            "Add music in CapCut → Export as MP4"
        )
        vl, vr = st.columns([1, 1], gap="large")
        with vl:
            v_photos_raw = st.file_uploader(
                "Upload 4-10 travel photos (in scene order)",
                type=["jpg","jpeg","png","webp"],
                accept_multiple_files=True, key="v_photos",
            )
            # Read ALL file bytes immediately — multi-file objects exhaust after first .read()
            v_photos = [f.read() for f in (v_photos_raw or [])]
            if v_photos:
                st.caption(f"{len(v_photos)} photos uploaded")

            v_dest    = st.text_input("Destination",  placeholder="Kerala, India", key="v_dest")
            v_pkg     = st.text_input("Package name", placeholder="Backwaters Bliss — 5 Days", key="v_pkg")
            v_dur     = st.text_input("Duration",     placeholder="5 Days / 4 Nights", key="v_dur")
            v_price   = st.text_input("Price",        placeholder="₹22,999/person", key="v_price")
            v_hl_raw  = st.text_area("Scene highlights (one per line — matches photo order)",
                                      placeholder="Houseboat Sunrise\nBackwaters Cruise\nElephant Safari\nTea Plantation\nVarkala Beach",
                                      height=110, key="v_hl")
            v_highlights = [l.strip() for l in v_hl_raw.splitlines() if l.strip()]

            v_plat    = st.selectbox("Format", [
                "Instagram / Reels Story 9:16 (1080×1920)",
                "YouTube Shorts 9:16 (1080×1920)",
                "Instagram Post 1:1 (1080×1080)",
                "YouTube Thumbnail 16:9 (1280×720)",
            ], key="v_plat")
            v_tpl     = st.selectbox("Template", list(TEMPLATES.keys()), key="v_tpl")
            v_tone    = st.selectbox("Tone", ["Exciting & Adventurous","Luxury & Premium",
                                              "Family Friendly","Romantic"], key="v_tone")
            v_secs    = st.slider("Seconds per scene", 2, 6, 3, key="v_secs")
            v_enh     = st.checkbox("Auto-enhance photos", value=True, key="v_enh")

            gen_vid = st.button("🎬 Generate Slideshow", type="primary",
                                use_container_width=True,
                                disabled=len(v_photos) < 2)

        with vr:
            st.markdown("### 👁️ Preview")
            if gen_vid and v_photos:
                vw, vh = PLATFORMS[v_plat]

                with st.spinner("Generating AI captions for each scene..."):
                    content_ai = ai_generate_content(
                        v_dest, v_pkg, v_dur, v_highlights,
                        v_price, v_plat, v_tone,
                    )
                    scene_caps = content_ai.get("scene_captions", v_highlights)
                    palette    = content_ai.get("palette", "Sunset Gold")

                frames = []
                prog   = st.progress(0, text="Compositing frames...")
                for i, pf_bytes in enumerate(v_photos[:10]):
                    prog.progress(i / len(v_photos),
                                  text=f"Scene {i+1}/{len(v_photos)}...")
                    # Build per-frame content
                    cap = scene_caps[i] if i < len(scene_caps) else (
                          v_highlights[i] if i < len(v_highlights) else v_dest)

                    frame_content = {
                        "package_name": v_pkg if i == 0 else "",
                        "headline":     cap,
                        "subheadline":  "",
                        "highlights":   [],
                        "price":        v_price if i == len(v_photos)-1 else "",
                        "cta":          "Book Now →" if i == len(v_photos)-1 else "",
                    }
                    frame = compose(
                        pf_bytes, vw, vh,
                        TEMPLATES[v_tpl], palette, frame_content,
                        logo_bytes, logo_pos, cert_bytes,
                        fb, insta, web,
                        show_price=(i == len(v_photos)-1),
                        show_cta=(i == len(v_photos)-1),
                        enhance=v_enh,
                    )
                    frames.append(frame)

                prog.empty()
                gif = make_slideshow_gif(frames, sec_per_frame=v_secs)
                st.session_state["v_gif"]    = gif
                st.session_state["v_frames"] = [to_bytes(f) for f in frames]
                st.session_state["v_pkg"]    = v_pkg
                st.success(f"✅ {len(frames)}-scene slideshow · {len(gif)//1024} KB")

            gif = st.session_state.get("v_gif")
            if gif:
                b64 = base64.b64encode(gif).decode()
                st.markdown(
                    f'<img src="data:image/gif;base64,{b64}" style="width:100%;border-radius:8px">',
                    unsafe_allow_html=True,
                )
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button("📥 Download GIF",
                                       data=gif,
                                       file_name=f"{st.session_state.get('v_pkg','video')}.gif",
                                       mime="image/gif", use_container_width=True)
                with col2:
                    if st.session_state.get("v_frames"):
                        zbuf = io.BytesIO()
                        with zipfile.ZipFile(zbuf, "w") as zf:
                            for i, fb_b in enumerate(st.session_state["v_frames"]):
                                zf.writestr(f"scene_{i+1:02d}.png", fb_b)
                        zbuf.seek(0)
                        st.download_button("📥 Frames ZIP",
                                           data=zbuf.getvalue(),
                                           file_name="frames.zip",
                                           mime="application/zip",
                                           use_container_width=True)

                st.markdown("---")
                st.markdown("### 🎵 Add music → export as MP4")
                st.markdown("""
1. Open **[CapCut](https://capcut.com)** (free) → import your GIF
2. Add music from **[YouTube Audio Library](https://studio.youtube.com/channel/music)** or **[Mixkit](https://mixkit.co/free-stock-music/)** (both 100% free)
3. Adjust timing to 20-30s total
4. Export **1080×1920 MP4** → upload to Shorts / Reels
                """)
            else:
                st.markdown("""
                <div style="border:0.5px solid var(--color-border-tertiary);border-radius:12px;
                            padding:80px 20px;text-align:center">
                    <div style="font-size:48px">🎬</div>
                    <div style="color:var(--color-text-secondary);margin-top:12px;font-size:14px">
                        Upload photos in scene order → Generate
                    </div>
                </div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════
    # TAB 3 — BULK EXPORT
    # ════════════════════════════════════════════════════════════════════
    with tab3:
        st.markdown("### 📦 One photo → All platform sizes → ZIP")
        st.info("Generate your banner once and export it for every social platform in one click.")

        bl, br = st.columns([1, 1], gap="large")
        with bl:
            b_photo_raw = st.file_uploader("Upload hero photo",
                                        type=["jpg","jpeg","png","webp"], key="b_photo")
            if b_photo_raw:
                b_photo_bytes = b_photo_raw.read()
                st.image(b_photo_bytes, use_container_width=True)
            else:
                b_photo_bytes = None

            b_dest  = st.text_input("Destination",  placeholder="Goa, India", key="b_dest")
            b_pkg   = st.text_input("Package name", placeholder="Goa Beach Holiday — 5N/6D", key="b_pkg")
            b_dur   = st.text_input("Duration",     placeholder="5 Nights / 6 Days", key="b_dur")
            b_price = st.text_input("Price",        placeholder="₹18,999/person", key="b_price")
            b_hl    = st.text_area("Highlights", height=90, key="b_hl",
                                    placeholder="Baga Beach\nWater Sports\nSunset Cruise\nCasinos")
            b_hl_list = [l.strip() for l in b_hl.splitlines() if l.strip()]
            b_tone  = st.selectbox("Tone", ["Exciting & Adventurous","Luxury & Premium",
                                            "Family Friendly","Romantic"], key="b_tone")
            b_tpl   = st.selectbox("Template", list(TEMPLATES.keys()), key="b_tpl")

            b_plats = st.multiselect("Export for these platforms",
                                      list(PLATFORMS.keys()),
                                      default=list(PLATFORMS.keys())[:4])

            b_gen = st.button("📦 Generate All Sizes", type="primary",
                              use_container_width=True,
                              disabled=(not b_photo_bytes or not b_plats))

        with br:
            st.markdown("### 📋 Results")
            if b_gen and b_photo_bytes and b_plats:
                with st.spinner("AI generating copy..."):
                    b_content = ai_generate_content(
                        b_dest, b_pkg, b_dur, b_hl_list,
                        b_price, b_plats[0], b_tone,
                    )
                    b_content.update({
                        "package_name": b_pkg,
                        "highlights": b_hl_list,
                        "price": b_price,
                    })
                    b_palette = b_content.get("palette", "Sunset Gold")

                zbuf = io.BytesIO()
                prog = st.progress(0, "Generating banners...")
                preview_shown = False

                with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as zf:
                    for i, pname in enumerate(b_plats):
                        prog.progress(i / len(b_plats), f"Compositing {pname[:30]}...")
                        pw, ph = PLATFORMS[pname]
                        img = compose(
                            b_photo_bytes, pw, ph,
                            TEMPLATES[b_tpl], b_palette, b_content,
                            logo_bytes, logo_pos, cert_bytes,
                            fb, insta, web,
                        )
                        safe = pname.split("(")[0].strip().replace(" ","_").replace("/","-")
                        zf.writestr(f"{b_pkg or 'banner'}_{safe}_{pw}x{ph}.png", to_bytes(img))
                        if not preview_shown:
                            st.image(to_bytes(img), caption=pname, use_container_width=True)
                            preview_shown = True

                prog.empty()
                zbuf.seek(0)
                st.success(f"✅ {len(b_plats)} banners ready!")
                st.download_button("📥 Download ZIP",
                                   data=zbuf.getvalue(),
                                   file_name=f"{b_pkg or 'banners'}_all_platforms.zip",
                                   mime="application/zip",
                                   use_container_width=True)

                with st.expander("📋 AI Copy for all platforms"):
                    st.text_area("Caption", value=b_content.get("caption",""), height=80)
                    st.text_area("Hashtags", value=b_content.get("hashtags",""), height=60)
                    st.text_input("YouTube Title", value=b_content.get("youtube_title",""))
            else:
                st.markdown("""
                <div style="border:0.5px solid var(--color-border-tertiary);border-radius:12px;
                            padding:80px 20px;text-align:center">
                    <div style="font-size:48px">📦</div>
                    <div style="color:var(--color-text-secondary);margin-top:12px;font-size:14px">
                        Upload one photo → export for every platform in one ZIP
                    </div>
                </div>""", unsafe_allow_html=True)

    # ── Tips ──────────────────────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("📸 Photo tips for best results"):
        st.markdown("""
**Best photos for travel banners:**
- Landscape/wide shots work best — avoid tight portraits
- Golden hour (sunrise/sunset) gives warmth automatically
- Clear sky shots — the overlay reads best on clean backgrounds
- High resolution — minimum 1920×1080, 2-5MB ideal

**Template guide:**
| Template | Best for |
|---|---|
| Bold Overlay | Action shots, landscapes |
| Bottom Strip | Portraits, tall shots |
| Cinematic Bars | Wide panoramic shots |
| Luxury Dark | Premium packages, night shots |

**Colour palette tips:**
- Let AI choose — it picks based on your destination and tone
- Sunset Gold = universal, works for most travel
- Ocean Blue = beaches, water destinations
- Forest Green = hills, wildlife, nature
- Midnight Black = premium luxury packages
        """)
