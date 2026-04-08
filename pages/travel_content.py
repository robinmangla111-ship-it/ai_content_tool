"""
✈ AI Travel Content Creator  —  One-Prompt Edition
====================================================
HOW IT WORKS:
  1. You type ONE free text (e.g. "7 day Rajasthan trip with desert safari, 25000 rs")
  2. Upload 2-8 travel photos
  3. AI (Groq → Gemini fallback) generates EVERYTHING:
       • Package name, headline, subheadline, price, CTA
       • Highlights list, hashtags, YouTube title+desc
       • Instagram/Facebook/WhatsApp captions
       • 30-sec reel voiceover script
       • Recommended colour palette & layout style
       • Per-slide video captions
  4. Pillow composites multi-photo banner with:
       • 8 creative layout templates
       • Photo collage / split-screen / hero modes
       • Vignette, film grain, duotone, cinematic effects
       • Logo, cert badge, social bar
  5. Download PNG, JPEG, animated GIF, or ZIP bulk

FREE: Groq (console.groq.com) or Gemini (aistudio.google.com)
"""

import streamlit as st
import sys, os, io, json, re, zipfile, base64, math, random
from PIL import (Image, ImageDraw, ImageFont, ImageFilter,
                 ImageEnhance, ImageChops, ImageOps)

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ─────────────────────────────────────────────────────────────────────────────
# KEY HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get(sk, sec, ev=""):
    v = st.session_state.get(sk, "").strip()
    if v: return v
    try:
        v = str(st.secrets.get(sec, "")).strip()
        if v: return v
    except Exception:
        pass
    return os.getenv(ev, "").strip()

def _groq_key():   return _get("groq_key",   "GROQ_API_KEY",   "GROQ_API_KEY")
def _gemini_key(): return _get("gemini_key", "GEMINI_API_KEY", "GEMINI_API_KEY")
def _llm_ok():     return bool(_groq_key() or _gemini_key())

# ─────────────────────────────────────────────────────────────────────────────
# PLATFORMS
# ─────────────────────────────────────────────────────────────────────────────

PLATFORMS = {
    "YouTube Thumbnail  16:9  1280×720":   (1280,  720),
    "YouTube Shorts     9:16  1080×1920":  (1080, 1920),
    "Instagram Post     1:1   1080×1080":  (1080, 1080),
    "Instagram Story    9:16  1080×1920":  (1080, 1920),
    "Facebook Post      1.9:1 1200×630":   (1200,  630),
    "WhatsApp Status    9:16  1080×1920":  (1080, 1920),
    "Twitter/X          16:9  1200×675":   (1200,  675),
    "LinkedIn Banner    4:1   1584×396":   (1584,  396),
}

# ─────────────────────────────────────────────────────────────────────────────
# DESIGN THEMES  — each has full visual identity
# ─────────────────────────────────────────────────────────────────────────────

THEMES = {
    "Golden Hour": {
        "accent": (255, 190, 40), "accent2": (255, 120, 20),
        "dark": (18, 8, 2), "light": (255, 248, 220),
        "overlay": (15, 8, 2, 160), "grad": [(180,80,10), (40,15,3)],
        "tag": "WARM",
    },
    "Deep Ocean": {
        "accent": (0, 215, 235), "accent2": (0, 140, 200),
        "dark": (2, 14, 38), "light": (220, 248, 255),
        "overlay": (2, 12, 35, 165), "grad": [(0,55,120), (0,18,55)],
        "tag": "COOL",
    },
    "Dark Luxury": {
        "accent": (215, 178, 58), "accent2": (180, 140, 30),
        "dark": (6, 5, 10), "light": (255, 248, 230),
        "overlay": (5, 4, 8, 195), "grad": [(18,14,32), (6,5,12)],
        "tag": "PREMIUM",
    },
    "Emerald": {
        "accent": (70, 230, 110), "accent2": (30, 180, 80),
        "dark": (4, 22, 12), "light": (220, 255, 232),
        "overlay": (4, 20, 10, 162), "grad": [(8,75,35), (3,25,12)],
        "tag": "NATURE",
    },
    "Coral Sunset": {
        "accent": (255, 120, 80), "accent2": (255, 75, 50),
        "dark": (35, 8, 4), "light": (255, 240, 235),
        "overlay": (30, 8, 4, 158), "grad": [(200,60,20), (70,18,6)],
        "tag": "VIBRANT",
    },
    "Midnight Blue": {
        "accent": (100, 148, 255), "accent2": (60, 100, 230),
        "dark": (4, 6, 30), "light": (225, 235, 255),
        "overlay": (3, 5, 28, 178), "grad": [(8,15,65), (3,5,28)],
        "tag": "ELEGANT",
    },
    "Rose Blush": {
        "accent": (255, 160, 195), "accent2": (230, 100, 150),
        "dark": (30, 6, 18), "light": (255, 242, 248),
        "overlay": (28, 5, 16, 155), "grad": [(160,30,80), (60,8,32)],
        "tag": "ROMANTIC",
    },
    "Desert Sand": {
        "accent": (255, 185, 60), "accent2": (220, 140, 30),
        "dark": (45, 25, 5), "light": (255, 245, 225),
        "overlay": (40, 22, 4, 158), "grad": [(155,90,25), (60,35,8)],
        "tag": "EARTHY",
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT STYLES
# ─────────────────────────────────────────────────────────────────────────────

LAYOUTS = {
    "Hero + Strip":       "hero_strip",       # 1 large photo, text bottom strip
    "Magazine Grid":      "magazine_grid",    # 2-3 photos tiled
    "Cinematic":          "cinematic",        # widescreen bars top/bottom
    "Luxury Centre":      "luxury_centre",    # centred all text, dark overlay
    "Bold Left":          "bold_left",        # big text left, photo right
    "Story Stack":        "story_stack",      # 9:16 optimised, photos stacked
    "Collage Mosaic":     "collage_mosaic",   # 3-5 photos mosaic grid
    "Minimal Clean":      "minimal_clean",    # clean whitespace, refined type
}

# ─────────────────────────────────────────────────────────────────────────────
# FONT CACHE
# ─────────────────────────────────────────────────────────────────────────────

_FC: dict = {}

def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    k = (size, bold)
    if k in _FC: return _FC[k]
    paths = [
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf",
        f"/usr/share/fonts/truetype/liberation/LiberationSans{'-Bold' if bold else '-Regular'}.ttf",
        f"/usr/share/fonts/truetype/ubuntu/Ubuntu-{'B' if bold else 'R'}.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                f = ImageFont.truetype(p, size)
                _FC[k] = f
                return f
            except Exception:
                pass
    f = ImageFont.load_default()
    _FC[k] = f
    return f

# ─────────────────────────────────────────────────────────────────────────────
# LLM  (Groq → Gemini fallback)
# ─────────────────────────────────────────────────────────────────────────────

def _groq(system: str, user: str, tokens: int = 1000) -> str:
    key = _groq_key()
    if not key: return ""
    try:
        from groq import Groq
        r = Groq(api_key=key).chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"system","content":system},
                      {"role":"user","content":user}],
            max_tokens=tokens, temperature=0.78,
            response_format={"type":"json_object"},
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        st.toast(f"Groq: {e}", icon="⚠️")
        return ""


def _gemini(prompt: str, tokens: int = 1000) -> str:
    key = _gemini_key()
    if not key: return ""
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    body = {
        "contents": [{"parts":[{"text": prompt}]}],
        "generationConfig": {
            "maxOutputTokens": tokens, "temperature": 0.8,
            "responseMimeType": "application/json",
        }
    }
    try:
        r = __import__("requests").post(url, params={"key":key}, json=body, timeout=30)
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        st.toast(f"Gemini: {e}", icon="⚠️")
        return ""


def _llm(system: str, user: str, tokens: int = 1000) -> str:
    out = _groq(system, user, tokens)
    if not out:
        combined = f"{system}\n\nReturn ONLY valid JSON.\n\n{user}"
        out = _gemini(combined, tokens)
    return out


def _parse_json(raw: str) -> dict:
    try:
        clean = re.sub(r"```(?:json)?|```", "", raw).strip()
        s = clean.find("{")
        return json.loads(clean[s:]) if s >= 0 else json.loads(clean)
    except Exception:
        return {}


def ai_generate_all(free_text: str, num_photos: int) -> dict:
    """
    Single LLM call: from free text → complete travel package content.
    Everything the banner and video need.
    """
    system = """You are an expert Indian travel marketing AI.
From a short free-text description, extract or infer ALL content for travel banners.
Return ONLY valid JSON with these exact keys:
  package_name   (short, e.g. "Golden Rajasthan 7D/6N"),
  destination    (city/region name),
  headline       (7-9 word punchy title with 1 emoji),
  subheadline    (3 aspects joined with ·, e.g. "Heritage · Desert · Culture"),
  price          (formatted price string, infer from text or suggest realistic INR price),
  duration       (e.g. "7 Days / 6 Nights"),
  cta            (call-to-action with arrow, e.g. "Book Now →"),
  highlights     (array of exactly 6 short strings, max 4 words each),
  hashtags       (string of 10 hashtags),
  instagram_caption (4 lines with emojis + 6 hashtags),
  facebook_caption  (3 lines conversational),
  whatsapp_status   (2 lines max, emoji-rich),
  youtube_title     (SEO title max 60 chars),
  youtube_desc      (3 short paragraphs),
  reel_script       (3 punchy sentences for 30-sec voiceover),
  slide_captions    (array of 8 short captions max 5 words each, for video slides),
  theme             (one of: Golden Hour/Deep Ocean/Dark Luxury/Emerald/Coral Sunset/Midnight Blue/Rose Blush/Desert Sand),
  layout            (one of: Hero + Strip/Magazine Grid/Cinematic/Luxury Centre/Bold Left/Story Stack/Collage Mosaic/Minimal Clean),
  mood              (one word: adventurous/romantic/luxurious/family/cultural/relaxing)
"""
    user = (
        f"Free text from travel agent: \"{free_text}\"\n"
        f"Number of photos uploaded: {num_photos}\n"
        "Generate complete travel package content:"
    )
    raw = _llm(system, user, tokens=1100)
    data = _parse_json(raw) if raw else {}

    # Robust defaults if LLM returns partial data
    defaults = {
        "package_name":   "Incredible India Package",
        "destination":    free_text.split()[0].title() if free_text else "India",
        "headline":       f"✨ Discover the Magic of India",
        "subheadline":    "Culture · Adventure · Memories",
        "price":          "₹24,999/person",
        "duration":       "7 Days / 6 Nights",
        "cta":            "Book Now →",
        "highlights":     ["Iconic Landmarks","Local Cuisine","Guided Tours",
                           "Comfortable Hotels","Airport Transfers","24/7 Support"],
        "hashtags":       "#Travel #India #TourPackage #Wanderlust #TravelIndia #Holiday",
        "instagram_caption": "✈️ Your dream trip awaits!\n📍 Incredible India\n💫 Book now and explore!\n#Travel #India",
        "facebook_caption":  "Planning your next holiday? We have the perfect package for you!\nContact us to book your dream trip.",
        "whatsapp_status":   "✈️ Amazing India Package Available!\n📞 Call us to book today!",
        "youtube_title":  "India Travel Package | Best Tour Deals",
        "youtube_desc":   "Discover India with our amazing tour package.\n\nIncludes all major sights and experiences.\n\nBook now for best prices!",
        "reel_script":    "India is calling! From golden deserts to lush backwaters, we cover it all. Book your dream holiday today!",
        "slide_captions": ["Welcome to India ✨","Explore Heritage 🏰","Desert Adventure 🐪",
                           "Local Flavours 🍛","Natural Beauty 🌿","Sunset Views 🌅",
                           "Make Memories 📸","Book Now! →"],
        "theme":  "Golden Hour",
        "layout": "Hero + Strip",
        "mood":   "adventurous",
    }
    for k, v in defaults.items():
        data.setdefault(k, v)
    return data

# ─────────────────────────────────────────────────────────────────────────────
# IMAGE PROCESSING HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _cover(img: Image.Image, w: int, h: int) -> Image.Image:
    """Resize + centre crop to fill w×h (cover mode)."""
    img = img.convert("RGBA")
    r = max(w / img.width, h / img.height)
    nw, nh = int(img.width * r), int(img.height * r)
    img = img.resize((nw, nh), Image.LANCZOS)
    l = (nw - w) // 2; t = (nh - h) // 2
    return img.crop((l, t, l+w, t+h))


def _enhance(img: Image.Image,
             brightness: float = 1.06,
             contrast: float = 1.12,
             saturation: float = 1.20,
             sharpness: float = 1.10) -> Image.Image:
    img = ImageEnhance.Brightness(img).enhance(brightness)
    img = ImageEnhance.Contrast(img).enhance(contrast)
    img = ImageEnhance.Color(img).enhance(saturation)
    img = ImageEnhance.Sharpness(img).enhance(sharpness)
    return img


def _vignette(img: Image.Image, strength: float = 0.60) -> Image.Image:
    w, h = img.size
    mask = Image.new("L", (w, h), 255)
    draw = ImageDraw.Draw(mask)
    cx, cy = w // 2, h // 2
    for i in range(60):
        t = i / 60
        a = int(255 * strength * t * t)
        rx = int(cx * (1 - t * 0.9))
        ry = int(cy * (1 - t * 0.9))
        draw.ellipse([cx-rx, cy-ry, cx+rx, cy+ry], fill=255-a)
    dark = Image.new("RGBA", (w, h), (0, 0, 0, 210))
    out  = img.convert("RGBA").copy()
    out.paste(dark, mask=ImageChops.invert(mask))
    return out


def _grain(img: Image.Image, amount: int = 14) -> Image.Image:
    import random as _r
    grain = Image.new("RGBA", img.size, (0,0,0,0))
    px = grain.load()
    for y in range(0, img.height, 2):
        for x in range(0, img.width, 2):
            v = _r.randint(-amount, amount)
            c = max(0, min(255, 128+v))
            px[x, y] = (c, c, c, 10)
    return Image.alpha_composite(img.convert("RGBA"), grain)


def _gradient_overlay(img: Image.Image, c1: tuple, c2: tuple,
                       alpha_top: int = 60, alpha_bot: int = 200) -> Image.Image:
    w, h = img.size
    ov = Image.new("RGBA", (w, h), (0,0,0,0))
    draw = ImageDraw.Draw(ov)
    for y in range(h):
        t = y / h
        r = int(c1[0] + (c2[0]-c1[0])*t)
        g = int(c1[1] + (c2[1]-c1[1])*t)
        b = int(c1[2] + (c2[2]-c1[2])*t)
        a = int(alpha_top + (alpha_bot-alpha_top)*t)
        draw.line([(0,y),(w,y)], fill=(r,g,b,a))
    return Image.alpha_composite(img.convert("RGBA"), ov)


def _flat_overlay(img: Image.Image, color: tuple, alpha: int) -> Image.Image:
    ov = Image.new("RGBA", img.size, color+(alpha,))
    return Image.alpha_composite(img.convert("RGBA"), ov)

# ─────────────────────────────────────────────────────────────────────────────
# TEXT DRAWING HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _wrap(text: str, font, max_w: int, draw) -> str:
    words = text.split(); lines = []; line = ""
    for word in words:
        test = (line+" "+word).strip()
        if draw.textbbox((0,0), test, font=font)[2] <= max_w:
            line = test
        else:
            if line: lines.append(line)
            line = word
    if line: lines.append(line)
    return "\n".join(lines)


def _shadow(draw, xy, text, font, fill, s=4, blur_alpha=170):
    """Multi-pass shadow for depth."""
    for i in range(3, 0, -1):
        a = int(blur_alpha * (i/3) * 0.6)
        draw.text((xy[0]+i*s//3, xy[1]+i*s//3), text, font=font, fill=(0,0,0,a))
    draw.text(xy, text, font=font, fill=fill)


def _mshadow(draw, xy, text, font, fill, spacing=8, s=4):
    for i in range(3,0,-1):
        a = int(155 * (i/3) * 0.6)
        draw.multiline_text((xy[0]+i*s//3, xy[1]+i*s//3), text, font=font,
                             fill=(0,0,0,a), spacing=spacing)
    draw.multiline_text(xy, text, font=font, fill=fill, spacing=spacing)


def _pill(draw, x, y, text, font, bg, fg, px=18, py=9, r=None):
    bb = draw.textbbox((0,0), text, font=font)
    tw, th = bb[2]-bb[0], bb[3]-bb[1]
    r = r or (th+py)//2
    draw.rounded_rectangle([x, y, x+tw+px*2, y+th+py*2], radius=r, fill=bg)
    draw.text((x+px, y+py), text, font=font, fill=fg)
    return x+tw+px*2


def _pill_outline(draw, x, y, text, font, col, fg, px=18, py=9, lw=2):
    bb = draw.textbbox((0,0), text, font=font)
    tw, th = bb[2]-bb[0], bb[3]-bb[1]
    r = (th+py)//2
    draw.rounded_rectangle([x, y, x+tw+px*2, y+th+py*2], radius=r, outline=col, width=lw)
    draw.text((x+px, y+py), text, font=font, fill=fg)
    return x+tw+px*2


def _social_bar(draw, w, h, fb, insta, web, accent, font):
    bh = max(52, int(h * 0.05))
    by = h - bh
    # gradient bar
    for y in range(by, h):
        a = int(190 * (y-by)/bh)
        draw.line([(0,y),(w,y)], fill=(0,0,0,a))
    items = []
    if fb:    items.append(f"f  {fb}")
    if insta: items.append(f"@  {insta}")
    if web:   items.append(f"🌐 {web}")
    if not items: return
    line = "   ·   ".join(items)
    bb = draw.textbbox((0,0), line, font=font)
    tw = bb[2]-bb[0]; th = bb[3]-bb[1]
    _shadow(draw, ((w-tw)//2, by+(bh-th)//2), line, font, accent+(255,), s=2)


def _paste_logo(canvas, logo_bytes, pos, max_px, bot=66):
    if not logo_bytes: return canvas
    logo = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
    r = min(max_px/logo.width, max_px/logo.height)
    nw, nh = int(logo.width*r), int(logo.height*r)
    logo = logo.resize((nw, nh), Image.LANCZOS)
    W, H = canvas.size; m = 22
    pos_map = {"Top Left":(m,m),"Top Right":(W-nw-m,m),
               "Bottom Left":(m,H-nh-m-bot),"Bottom Right":(W-nw-m,H-nh-m-bot)}
    x, y = pos_map.get(pos, (W-nw-m, m))
    # shadow
    sh = Image.new("RGBA",(nw+8,nh+8),(0,0,0,0))
    ImageDraw.Draw(sh).rectangle([4,4,nw+4,nh+4],fill=(0,0,0,70))
    sh = sh.filter(ImageFilter.GaussianBlur(4))
    canvas.paste(sh,(x-2,y+2),sh)
    canvas.paste(logo,(x,y),logo)
    return canvas


def _paste_cert(canvas, cert_bytes, max_px=88, bot=66):
    if not cert_bytes: return canvas
    badge = Image.open(io.BytesIO(cert_bytes)).convert("RGBA")
    r = min(max_px/badge.width, max_px/badge.height)
    nw, nh = int(badge.width*r), int(badge.height*r)
    badge = badge.resize((nw,nh), Image.LANCZOS)
    W, H = canvas.size
    canvas.paste(badge,(22,H-nh-22-bot),badge)
    return canvas

# ─────────────────────────────────────────────────────────────────────────────
# MULTI-PHOTO CANVAS BUILDERS
# ─────────────────────────────────────────────────────────────────────────────

def _build_hero(photos: list, w: int, h: int) -> Image.Image:
    """Single large hero photo."""
    return _cover(photos[0], w, h)


def _build_hero_strip(photos: list, w: int, h: int) -> Image.Image:
    """Main photo top 65%, 2nd photo strip bottom 35% (if available)."""
    canvas = Image.new("RGBA", (w, h))
    top_h = int(h * 0.65)
    bot_h = h - top_h
    top = _cover(photos[0], w, top_h)
    canvas.paste(top.convert("RGBA"), (0, 0))
    if len(photos) > 1:
        bot = _cover(photos[1], w, bot_h)
        canvas.paste(bot.convert("RGBA"), (0, top_h))
    else:
        bot = _cover(photos[0], w, bot_h)
        canvas.paste(bot.convert("RGBA"), (0, top_h))
    # Blend seam
    seam = Image.new("RGBA",(w,12),(0,0,0,0))
    seam_d = ImageDraw.Draw(seam)
    for i in range(12):
        seam_d.line([(0,i),(w,i)], fill=(0,0,0,int(80*(1-i/12))))
    canvas.alpha_composite(seam, (0, top_h-2))
    return canvas


def _build_magazine_grid(photos: list, w: int, h: int) -> Image.Image:
    """Left 60% = large photo, right 40% = 2 stacked photos."""
    canvas = Image.new("RGBA", (w, h))
    gap = 4
    left_w = int(w * 0.60)
    right_w = w - left_w - gap
    right_h = (h - gap) // 2

    p0 = _cover(photos[0], left_w, h)
    canvas.paste(p0.convert("RGBA"), (0, 0))

    p1 = _cover(photos[1] if len(photos)>1 else photos[0], right_w, right_h)
    canvas.paste(p1.convert("RGBA"), (left_w+gap, 0))

    p2 = _cover(photos[2] if len(photos)>2 else photos[0], right_w, right_h)
    canvas.paste(p2.convert("RGBA"), (left_w+gap, right_h+gap))

    # vertical divider
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([left_w, 0, left_w+gap, h], fill=(0,0,0,180))
    draw.rectangle([left_w+gap, right_h, w, right_h+gap], fill=(0,0,0,180))
    return canvas


def _build_collage_mosaic(photos: list, w: int, h: int) -> Image.Image:
    """3-5 photo mosaic — first large, rest smaller tiles."""
    canvas = Image.new("RGBA", (w, h))
    gap = 5
    n = min(len(photos), 5)

    if n == 1:
        canvas.paste(_cover(photos[0], w, h).convert("RGBA"), (0,0))
    elif n == 2:
        pw = (w-gap)//2
        canvas.paste(_cover(photos[0],pw,h).convert("RGBA"),(0,0))
        canvas.paste(_cover(photos[1],pw,h).convert("RGBA"),(pw+gap,0))
    elif n == 3:
        lw = int(w*0.58); rw = w-lw-gap
        rh = (h-gap)//2
        canvas.paste(_cover(photos[0],lw,h).convert("RGBA"),(0,0))
        canvas.paste(_cover(photos[1],rw,rh).convert("RGBA"),(lw+gap,0))
        canvas.paste(_cover(photos[2],rw,rh).convert("RGBA"),(lw+gap,rh+gap))
    elif n == 4:
        lw = int(w*0.55); rw = w-lw-gap
        th = int(h*0.60); bh = h-th-gap
        canvas.paste(_cover(photos[0],lw,h).convert("RGBA"),(0,0))
        rh2 = (h-gap)//2
        canvas.paste(_cover(photos[1],rw,rh2).convert("RGBA"),(lw+gap,0))
        bw = (rw-gap)//2
        canvas.paste(_cover(photos[2],bw,rh2).convert("RGBA"),(lw+gap,rh2+gap))
        canvas.paste(_cover(photos[3],bw,rh2).convert("RGBA"),(lw+gap+bw+gap,rh2+gap))
    else:  # 5
        tw = (w-gap*2)//3; th = (h-gap)//2
        canvas.paste(_cover(photos[0],tw*2+gap,th).convert("RGBA"),(0,0))
        canvas.paste(_cover(photos[1] if len(photos)>1 else photos[0],tw,th).convert("RGBA"),(tw*2+gap*2,0))
        bw = (w-gap*2)//3
        for i in range(3):
            p = photos[2+i] if (2+i)<len(photos) else photos[0]
            canvas.paste(_cover(p,bw,th).convert("RGBA"),(i*(bw+gap),th+gap))

    # Add gap fills
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0,0,w,gap], fill=(0,0,0,200))
    return canvas


def _build_story_stack(photos: list, w: int, h: int) -> Image.Image:
    """9:16 — 3 photos stacked vertically."""
    canvas = Image.new("RGBA", (w, h))
    n = min(len(photos), 3); gap = 4
    ph = (h - gap*(n-1)) // n
    for i in range(n):
        p = photos[i] if i < len(photos) else photos[0]
        tile = _cover(p, w, ph)
        canvas.paste(tile.convert("RGBA"), (0, i*(ph+gap)))
    return canvas


def _build_side_panel(photos: list, w: int, h: int, theme: dict) -> Image.Image:
    """Photo on right 55%, gradient dark panel on left 45%."""
    canvas = Image.new("RGBA", (w, h))
    photo_w = int(w * 0.55)
    photo_x = w - photo_w
    p = _cover(photos[0], photo_w, h)
    canvas.paste(p.convert("RGBA"), (photo_x, 0))

    # Dark panel gradient
    panel = Image.new("RGBA", (photo_x+60, h))
    draw = ImageDraw.Draw(panel)
    c1, c2 = theme["grad"]
    for y in range(h):
        t = y/h
        r = int(c1[0]+(c2[0]-c1[0])*t)
        g = int(c1[1]+(c2[1]-c1[1])*t)
        b = int(c1[2]+(c2[2]-c1[2])*t)
        draw.line([(0,y),(photo_x+60,y)], fill=(r,g,b,255))
    canvas.alpha_composite(panel, (0, 0))
    return canvas


def build_photo_canvas(photos: list, w: int, h: int,
                        layout: str, theme: dict) -> Image.Image:
    """Route to the correct multi-photo layout builder."""
    if not photos:
        # Pure gradient fallback
        img = Image.new("RGBA", (w, h))
        draw = ImageDraw.Draw(img)
        c1, c2 = theme["grad"]
        for y in range(h):
            t = y/h
            draw.line([(0,y),(w,y)], fill=(
                int(c1[0]+(c2[0]-c1[0])*t),
                int(c1[1]+(c2[1]-c1[1])*t),
                int(c1[2]+(c2[2]-c1[2])*t), 255))
        return img

    lk = layout
    if lk in ("Hero + Strip",) or len(photos) == 1:
        if len(photos) >= 2:
            return _build_hero_strip(photos, w, h)
        return _build_hero(photos, w, h)
    elif lk == "Magazine Grid":
        return _build_magazine_grid(photos, w, h)
    elif lk in ("Collage Mosaic",) and len(photos) >= 3:
        return _build_collage_mosaic(photos, w, h)
    elif lk == "Story Stack" and h > w:
        return _build_story_stack(photos, w, h)
    elif lk == "Bold Left":
        return _build_side_panel(photos, w, h, theme)
    else:
        # Default: hero with strips if multiple photos
        if len(photos) >= 2:
            return _build_hero_strip(photos, w, h)
        return _build_hero(photos, w, h)

# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT TEXT RENDERERS
# ─────────────────────────────────────────────────────────────────────────────

def _render_hero_strip(draw, canvas, w, h, sc, theme, content, fonts, show_p, show_cta):
    fT, fS, fH, fP, fC, fSm = fonts
    a = theme["accent"]; d = theme["dark"]; lt = theme["light"]
    a4 = a+(255,); lt4 = lt+(255,)
    margin = int(55*sc); mw = w-margin*2; cy = int(50*sc)

    if content.get("package_name"):
        _pill(draw, margin, cy, f"  ✈  {content['package_name'].upper()}  ",
              fSm, a+(210,), d+(255,), px=16, py=8)
        cy += int(52*sc)
        draw.rectangle([margin, cy, margin+int(75*sc), cy+4], fill=a4)
        cy += int(18*sc)

    if content.get("headline"):
        wrapped = _wrap(content["headline"], fT, mw, draw)
        _mshadow(draw, (margin,cy), wrapped, fT, lt4, spacing=8, s=5)
        bb = draw.multiline_textbbox((margin,cy), wrapped, font=fT)
        cy += bb[3]-bb[1]+int(12*sc)

    if content.get("subheadline"):
        wrapped = _wrap(content["subheadline"], fS, mw, draw)
        _mshadow(draw, (margin,cy), wrapped, fS, a4, s=3)
        bb = draw.multiline_textbbox((margin,cy), wrapped, font=fS)
        cy += bb[3]-bb[1]+int(22*sc)

    for hl in content.get("highlights",[])[:5]:
        _shadow(draw, (margin,cy), f"  ✓  {hl}", fH, lt4, s=3)
        bb = draw.textbbox((margin,cy), f"  ✓  {hl}", font=fH)
        cy += bb[3]-bb[1]+int(7*sc)
    if content.get("highlights"): cy += int(14*sc)

    if show_p and content.get("price"):
        _shadow(draw, (margin,cy), f"From  {content['price']}", fP, a4, s=4)
        bb = draw.textbbox((margin,cy), f"From  {content['price']}", font=fP)
        cy += bb[3]-bb[1]+int(18*sc)

    if show_cta and content.get("cta"):
        _pill(draw, margin, cy, f"  {content['cta']}  ", fC, a+(228,), d+(255,), px=22, py=12)


def _render_cinematic(draw, canvas, w, h, sc, theme, content, fonts, show_p, show_cta):
    fT, fS, fH, fP, fC, fSm = fonts
    a = theme["accent"]; d = theme["dark"]; lt = theme["light"]
    a4 = a+(255,); lt4 = lt+(255,)

    bar = int(h*0.15)
    # Top + bottom bars with gradient
    for y in range(bar):
        a_val = int(225*(1-y/bar))
        draw.line([(0,y),(w,y)], fill=(*d, a_val))
    for y in range(h-bar, h):
        a_val = int(225*((y-(h-bar))/bar))
        draw.line([(0,y),(w,y)], fill=(*d, a_val))

    draw.rectangle([0,bar,w,bar+3], fill=a4)
    draw.rectangle([0,h-bar-3,w,h-bar], fill=a4)

    pkg = content.get("package_name","")
    if pkg:
        bb = draw.textbbox((0,0),pkg.upper(),font=fSm)
        draw.text(((w-(bb[2]-bb[0]))//2,(bar-(bb[3]-bb[1]))//2),
                  pkg.upper(), font=fSm, fill=a4)

    # Mid title centred
    mid_h = int(h*0.28); mid_y = bar+(h-2*bar-mid_h)//2
    ov = Image.new("RGBA",(w,h),(0,0,0,0))
    ImageDraw.Draw(ov).rectangle([0,mid_y,w,mid_y+mid_h], fill=(*d,155))
    canvas.alpha_composite(ov)
    draw = ImageDraw.Draw(canvas)

    hl = content.get("headline","")
    if hl:
        wrapped = _wrap(hl, fT, w-int(80*sc), draw)
        bb = draw.multiline_textbbox((0,0),wrapped,font=fT)
        tx = (w-(bb[2]-bb[0]))//2; ty = mid_y+(mid_h-(bb[3]-bb[1]))//2
        _mshadow(draw,(tx,ty),wrapped,fT,lt4,spacing=8,s=5)

    # Bottom bar content
    cy = h-bar+int(8*sc)
    parts = []
    if content.get("subheadline"): parts.append(content["subheadline"])
    if show_p and content.get("price"): parts.append(f"From {content['price']}")
    if show_cta and content.get("cta"): parts.append(content["cta"])
    line = "   |   ".join(parts)
    if line:
        bb = draw.textbbox((0,0),line,font=fSm)
        draw.text(((w-(bb[2]-bb[0]))//2,cy),line,font=fSm,fill=a4)


def _render_luxury(draw, canvas, w, h, sc, theme, content, fonts, show_p, show_cta):
    fT, fS, fH, fP, fC, fSm = fonts
    a = theme["accent"]; d = (6,5,10); lt = theme["light"]
    a4 = a+(255,); lt4 = lt+(255,)
    margin = int(62*sc); mw = w-margin*2

    # Heavy overlay
    ov = Image.new("RGBA",(w,h),(*d,195))
    canvas.alpha_composite(ov)
    draw = ImageDraw.Draw(canvas)

    # Corner frame
    bd = int(20*sc); seg = int(min(w,h)*0.09); lw = max(2,int(min(w,h)*0.003))
    for (cx2,cy2),(dx1,dy1,dx2,dy2) in [
        ((bd,bd),(1,0,0,1)),((w-bd,bd),(-1,0,0,1)),
        ((bd,h-bd),(1,0,0,-1)),((w-bd,h-bd),(-1,0,0,-1))
    ]:
        draw.line([(cx2,cy2),(cx2+dx1*seg,cy2+dy1*seg)],fill=a4,width=lw)
        draw.line([(cx2,cy2),(cx2+dx2*seg,cy2+dy2*seg)],fill=a4,width=lw)

    cy = int(80*sc)
    # Ornament
    cx3 = w//2
    draw.line([(cx3-70,cy),(cx3-12,cy)],fill=a+(180,),width=1)
    draw.line([(cx3+12,cy),(cx3+70,cy)],fill=a+(180,),width=1)
    draw.ellipse([(cx3-6,cy-5),(cx3+6,cy+5)],fill=a+(210,))
    cy += int(30*sc)

    pkg = content.get("package_name","")
    if pkg:
        bb = draw.textbbox((0,0),pkg.upper(),font=fSm)
        draw.text(((w-(bb[2]-bb[0]))//2,cy),pkg.upper(),font=fSm,fill=a+(190,))
        cy += int(42*sc)

    hl = content.get("headline","")
    if hl:
        wrapped = _wrap(hl,fT,mw,draw)
        bb = draw.multiline_textbbox((0,0),wrapped,font=fT)
        tx = (w-(bb[2]-bb[0]))//2
        _mshadow(draw,(tx,cy),wrapped,fT,lt4,spacing=10,s=5)
        bb2 = draw.multiline_textbbox((tx,cy),wrapped,font=fT)
        cy += bb2[3]-bb2[1]+int(18*sc)

    draw.line([(margin*2,cy),(w-margin*2,cy)],fill=a+(140,),width=1)
    cy += int(20*sc)

    sub = content.get("subheadline","")
    if sub:
        bb = draw.textbbox((0,0),sub,font=fS)
        draw.text(((w-(bb[2]-bb[0]))//2,cy),sub,font=fS,fill=a+(195,))
        cy += (bb[3]-bb[1])+int(28*sc)

    for hl2 in content.get("highlights",[])[:4]:
        bb = draw.textbbox((0,0),f"◆  {hl2}",font=fH)
        draw.text(((w-(bb[2]-bb[0]))//2,cy),f"◆  {hl2}",font=fH,fill=lt+(180,))
        cy += (bb[3]-bb[1])+int(8*sc)
    if content.get("highlights"): cy += int(14*sc)

    if show_p and content.get("price"):
        pt = f"FROM  {content['price']}"
        bb = draw.textbbox((0,0),pt,font=fP)
        _shadow(draw,((w-(bb[2]-bb[0]))//2,cy),pt,fP,a4,s=4)
        cy += (bb[3]-bb[1])+int(18*sc)

    if show_cta and content.get("cta"):
        bb = draw.textbbox((0,0),f"  {content['cta']}  ",font=fC)
        tx = (w-(bb[2]-bb[0]+44))//2
        _pill(draw,tx,cy,f"  {content['cta']}  ",fC,a+(215,),d+(255,),px=22,py=12)


def _render_bold_left(draw, canvas, w, h, sc, theme, content, fonts, show_p, show_cta):
    fT, fS, fH, fP, fC, fSm = fonts
    a = theme["accent"]; lt = theme["light"]
    a4 = a+(255,); lt4 = lt+(255,)
    margin = int(48*sc); mw = int(w*0.50); cy = int(55*sc)

    pkg = content.get("package_name","")
    if pkg:
        draw.rectangle([margin,cy,margin+int(8*sc),cy+int(32*sc)],fill=a4)
        draw.text((margin+int(16*sc),cy),pkg.upper(),font=fSm,fill=a4)
        cy += int(50*sc)

    hl = content.get("headline","")
    if hl:
        words = hl.split()
        line1 = " ".join(words[:3]); line2 = " ".join(words[3:])
        _shadow(draw,(margin,cy),line1,fT,lt4,s=5)
        bb = draw.textbbox((margin,cy),line1,font=fT)
        cy += bb[3]-bb[1]
        if line2:
            _shadow(draw,(margin,cy),line2,fT,a4,s=5)
            bb = draw.textbbox((margin,cy),line2,font=fT)
            cy += bb[3]-bb[1]
        cy += int(8*sc)

    draw.rectangle([margin,cy,margin+int(180*sc),cy+int(7*sc)],fill=a4)
    cy += int(24*sc)

    sub = content.get("subheadline","")
    if sub:
        wrapped = _wrap(sub,fS,mw,draw)
        _mshadow(draw,(margin,cy),wrapped,fS,lt4,s=3)
        bb = draw.multiline_textbbox((margin,cy),wrapped,font=fS)
        cy += bb[3]-bb[1]+int(18*sc)

    for hl2 in content.get("highlights",[])[:4]:
        _shadow(draw,(margin,cy),f"✓  {hl2}",fH,lt4,s=2)
        bb = draw.textbbox((margin,cy),f"✓  {hl2}",font=fH)
        cy += bb[3]-bb[1]+int(6*sc)
    if content.get("highlights"): cy += int(12*sc)

    if show_p and content.get("price"):
        _shadow(draw,(margin,cy),f"From {content['price']}",fP,a4,s=4)
        bb = draw.textbbox((margin,cy),f"From {content['price']}",font=fP)
        cy += bb[3]-bb[1]+int(16*sc)

    if show_cta and content.get("cta"):
        _pill(draw,margin,cy,f"  {content['cta']}  ",fC,a+(228,),theme["dark"]+(255,),px=20,py=11)


def _render_minimal(draw, canvas, w, h, sc, theme, content, fonts, show_p, show_cta):
    fT, fS, fH, fP, fC, fSm = fonts
    a = theme["accent"]; lt = theme["light"]
    a4 = a+(255,); lt4 = lt+(255,)
    mw = w-int(100*sc)

    cy = h//3
    pkg = content.get("package_name","")
    if pkg:
        tag = "  ·  ".join(pkg.upper())
        bb = draw.textbbox((0,0),tag,font=fSm)
        draw.text(((w-(bb[2]-bb[0]))//2,cy-int(55*sc)),tag,font=fSm,fill=a+(170,))
        draw.rectangle([(w//2-int(28*sc)),cy-int(18*sc),(w//2+int(28*sc)),cy-int(16*sc)],fill=a4)

    hl = content.get("headline","")
    if hl:
        wrapped = _wrap(hl,fT,mw,draw)
        bb = draw.multiline_textbbox((0,0),wrapped,font=fT)
        tx = (w-(bb[2]-bb[0]))//2
        _mshadow(draw,(tx,cy),wrapped,fT,lt4,spacing=8,s=4)
        bb2 = draw.multiline_textbbox((tx,cy),wrapped,font=fT)
        cy = bb2[3]+int(16*sc)

    sub = content.get("subheadline","")
    if sub:
        bb = draw.textbbox((0,0),sub,font=fS)
        draw.text(((w-(bb[2]-bb[0]))//2,cy),sub,font=fS,fill=a4)
        cy += (bb[3]-bb[1])+int(22*sc)

    hls = content.get("highlights",[])
    if hls:
        line = "  ·  ".join(hls[:4])
        bb = draw.textbbox((0,0),line,font=fH)
        if bb[2]-bb[0] <= mw:
            draw.text(((w-(bb[2]-bb[0]))//2,cy),line,font=fH,fill=(255,255,255,185))

    bot = h-int(155*sc)
    if show_p and content.get("price"):
        bb = draw.textbbox((0,0),content["price"],font=fP)
        _pill_outline(draw,(w-(bb[2]-bb[0]+68))//2,bot,content["price"],
                      fP,a+(200,),lt4,px=34,py=13,lw=2)
        bot += (bb[3]-bb[1])+int(60*sc)

    if show_cta and content.get("cta"):
        bb = draw.textbbox((0,0),content["cta"],font=fC)
        _pill(draw,(w-(bb[2]-bb[0]+64))//2,bot,content["cta"],
              fC,a+(220,),theme["dark"]+(255,),px=32,py=13)


def _render_story(draw, canvas, w, h, sc, theme, content, fonts, show_p, show_cta):
    """9:16 optimised — top pill, centred hero title, 2-col highlights, bottom strip."""
    fT, fS, fH, fP, fC, fSm = fonts
    a = theme["accent"]; lt = theme["light"]
    a4 = a+(255,); lt4 = lt+(255,)
    margin = int(52*sc); mw = w-margin*2; cy = int(60*sc)

    pkg = content.get("package_name","")
    if pkg:
        bb = draw.textbbox((0,0),f"  ✈  {pkg.upper()}  ",font=fSm)
        tx = (w-(bb[2]-bb[0]+36))//2
        _pill(draw,tx,cy,f"  ✈  {pkg.upper()}  ",fSm,a+(212,),theme["dark"]+(255,),px=18,py=9)
        cy += int(65*sc)

    hl = content.get("headline","")
    if hl:
        wrapped = _wrap(hl,fT,mw,draw)
        bb = draw.multiline_textbbox((0,0),wrapped,font=fT)
        ty = h//3
        _mshadow(draw,((w-(bb[2]-bb[0]))//2,ty),wrapped,fT,lt4,spacing=8,s=5)
        bb2 = draw.multiline_textbbox(((w-(bb[2]-bb[0]))//2,ty),wrapped,font=fT)
        cy = bb2[3]+int(14*sc)

    sub = content.get("subheadline","")
    if sub:
        bb = draw.textbbox((0,0),sub,font=fS)
        draw.text(((w-(bb[2]-bb[0]))//2,cy),sub,font=fS,fill=a4)
        cy += (bb[3]-bb[1])+int(20*sc)

    hls = content.get("highlights",[])
    if hls:
        col_w = (mw-int(16*sc))//2
        for i,item in enumerate(hls[:6]):
            col = i%2; row = i//2
            x = margin+col*(col_w+int(16*sc)); y = cy+row*int(38*sc)
            draw.ellipse([x,y+int(9*sc),x+int(10*sc),y+int(19*sc)],fill=a4)
            _shadow(draw,(x+int(16*sc),y),item[:22],fH,lt4,s=2)
        cy += (len(hls[:6])//2+1)*int(38*sc)+int(14*sc)

    strip_h = int(125*sc); strip_y = h-strip_h-int(58*sc)
    draw.rectangle([0,strip_y,w,strip_y+strip_h],fill=(0,0,0,152))
    sy = strip_y+int(16*sc)
    if show_p and content.get("price"):
        bb = draw.textbbox((0,0),f"From {content['price']}",font=fP)
        _shadow(draw,((w-(bb[2]-bb[0]))//2,sy),f"From {content['price']}",fP,a4,s=4)
        sy += (bb[3]-bb[1])+int(10*sc)
    if show_cta and content.get("cta"):
        bb = draw.textbbox((0,0),content["cta"],font=fC)
        _pill(draw,(w-(bb[2]-bb[0]+68))//2,sy,f"  {content['cta']}  ",
              fC,a+(228,),theme["dark"]+(255,),px=34,py=13)

# ─────────────────────────────────────────────────────────────────────────────
# MASTER COMPOSE
# ─────────────────────────────────────────────────────────────────────────────

def compose(
    photos: list,          # list of PIL Images (already loaded)
    w: int, h: int,
    theme_name: str,
    layout_name: str,
    content: dict,
    logo_bytes: bytes | None,
    logo_pos: str,
    cert_bytes: bytes | None,
    fb: str, insta: str, web: str,
    show_price: bool = True,
    show_cta: bool = True,
    enhance_photos: bool = True,
    slide_caption: str = "",
    slide_num: str = "",
) -> Image.Image:

    theme = THEMES.get(theme_name, THEMES["Golden Hour"])
    sc = min(w, h) / 1080

    # Enhance photos
    enhanced = [_enhance(p) for p in photos] if enhance_photos else photos

    # 1. Build photo canvas (multi-photo layout)
    canvas = build_photo_canvas(enhanced, w, h, layout_name, theme)
    canvas = canvas.convert("RGBA")

    # 2. Visual effects
    canvas = _vignette(canvas, strength=0.55)

    if layout_name in ("Luxury Centre", "Minimal Clean"):
        canvas = _flat_overlay(canvas, theme["overlay"][:3], theme["overlay"][3])
    elif layout_name == "Bold Left":
        # Lighter overlay (panel already dark)
        canvas = _gradient_overlay(canvas, theme["dark"], theme["dark"],
                                    alpha_top=40, alpha_bot=150)
    else:
        canvas = _gradient_overlay(canvas, theme["overlay"][:3], theme["dark"],
                                    alpha_top=55, alpha_bot=195)

    canvas = _grain(canvas, amount=13)
    canvas = canvas.convert("RGBA")

    draw = ImageDraw.Draw(canvas)
    fT  = _font(int(74*sc), bold=True)
    fS  = _font(int(38*sc))
    fH  = _font(int(29*sc))
    fP  = _font(int(56*sc), bold=True)
    fC  = _font(int(36*sc), bold=True)
    fSm = _font(int(22*sc))
    fonts = (fT, fS, fH, fP, fC, fSm)

    # 3. Slide caption mode (for video)
    if slide_caption:
        fSl = _font(int(54*sc), bold=True)
        lt = theme["light"]+(255,)
        a  = theme["accent"]
        mw = w-int(80*sc)

        if slide_num:
            nb = draw.textbbox((0,0),slide_num,font=fSm)
            draw.text((w-int(48*sc)-(nb[2]-nb[0]),int(28*sc)),
                      slide_num,font=fSm,fill=a+(195,))

        wrapped = _wrap(slide_caption,fSl,mw,draw)
        bb = draw.multiline_textbbox((0,0),wrapped,font=fSl)
        tx = (w-(bb[2]-bb[0]))//2; ty = (h-(bb[3]-bb[1]))//2-int(25*sc)
        pad = int(22*sc)
        draw.rounded_rectangle([tx-pad,ty-pad,tx+(bb[2]-bb[0])+pad,ty+(bb[3]-bb[1])+pad],
                                radius=int(14*sc),fill=(0,0,0,118))
        _mshadow(draw,(tx,ty),wrapped,fSl,lt,spacing=8,s=4)

        if content.get("package_name"):
            pb = draw.textbbox((0,0),content["package_name"],font=fSm)
            px = (w-(pb[2]-pb[0])-36)//2
            _pill(draw,px,h-int(112*sc),content["package_name"],
                  fSm,a+(210,),(8,8,8,255),px=18,py=8)

        if content.get("price") and show_price:
            pt = f"From {content['price']}"
            pb = draw.textbbox((0,0),pt,font=fP)
            _shadow(draw,((w-(pb[2]-pb[0]))//2,h-int(185*sc)),pt,fP,a+(255,),s=4)

    else:
        # 4. Render layout
        renderer_map = {
            "Hero + Strip":   _render_hero_strip,
            "Magazine Grid":  _render_hero_strip,
            "Cinematic":      _render_cinematic,
            "Luxury Centre":  _render_luxury,
            "Bold Left":      _render_bold_left,
            "Story Stack":    _render_story,
            "Collage Mosaic": _render_hero_strip,
            "Minimal Clean":  _render_minimal,
        }
        # Auto-switch to story for tall canvases
        effective = layout_name
        if h > w * 1.35 and layout_name not in ("Story Stack","Luxury Centre","Minimal Clean"):
            effective = "Story Stack"
        renderer = renderer_map.get(effective, _render_hero_strip)
        renderer(draw, canvas, w, h, sc, theme, content, fonts, show_price, show_cta)

    # 5. Social bar
    _social_bar(draw, w, h, fb, insta, web, theme["accent"], fSm)

    # 6. Logo + cert
    canvas = _paste_logo(canvas, logo_bytes, logo_pos, int(128*sc))
    canvas = _paste_cert(canvas, cert_bytes, int(86*sc))

    return canvas.convert("RGB")

# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def to_bytes(img: Image.Image, fmt="PNG", quality=95) -> bytes:
    buf = io.BytesIO()
    if fmt == "JPEG": img = img.convert("RGB")
    img.save(buf, format=fmt, quality=quality)
    return buf.getvalue()


def make_gif(frames: list, ms: int = 2800) -> bytes:
    thumbs = []
    for f in frames:
        scale = 540/f.width
        thumbs.append(f.resize((540,int(f.height*scale)),Image.LANCZOS))
    buf = io.BytesIO()
    thumbs[0].save(buf,format="GIF",save_all=True,
                   append_images=thumbs[1:],duration=ms,loop=0,optimize=True)
    return buf.getvalue()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE
# ─────────────────────────────────────────────────────────────────────────────

def render():

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=Inter:wght@400;500;600&display=swap');

    .hero-h { font-family:'Syne',sans-serif; font-size:2.4rem; font-weight:800;
              background:linear-gradient(120deg,#f59e0b,#ef4444,#8b5cf6);
              -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
    .hero-s { font-family:'Inter',sans-serif; color:#6b7280; font-size:.92rem; margin-top:3px; }

    .bdg { display:inline-block; padding:3px 12px; border-radius:20px;
           font-size:.7rem; font-weight:700; letter-spacing:.06em;
           margin-right:6px; margin-bottom:10px; }
    .b1 { background:linear-gradient(135deg,#7c3aed,#db2777); color:#fff; }
    .b2 { background:linear-gradient(135deg,#065f46,#0284c7); color:#fff; }

    .prompt-box textarea { font-size:1.05rem !important; font-family:'Inter',sans-serif; }

    .copy-card { background:#111827; border:1px solid #1f2937; border-radius:10px;
                 padding:13px 16px; margin-bottom:9px; }
    .copy-lbl  { font-size:.66rem; font-weight:700; letter-spacing:.09em;
                 color:#4b5563; text-transform:uppercase; margin-bottom:3px; }
    .copy-val  { font-family:'Inter',sans-serif; font-size:.83rem;
                 color:#d1d5db; line-height:1.65; white-space:pre-wrap; }

    .empty { border:1px dashed #1f2937; border-radius:14px;
             padding:60px 20px; text-align:center; }
    .ei { font-size:2.8rem; }
    .et { color:#374151; margin-top:8px; font-size:.85rem; }

    div[data-testid="stTabs"] button[aria-selected="true"] {
        border-bottom:2px solid #f59e0b !important; color:#f59e0b !important; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<span class="bdg b1">✦ ONE-PROMPT AI</span>'
                '<span class="bdg b2">📸 REAL PHOTOS</span>', unsafe_allow_html=True)
    st.markdown('<div class="hero-h">✈ AI Travel Content Studio</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-s">Type one line → upload your photos → '
                'AI generates everything → download for every platform</div>', unsafe_allow_html=True)
    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # BRAND KIT
    # ─────────────────────────────────────────────────────────────────────────
    with st.expander("🏷️ Brand Kit  —  Logo · Cert · Social · API Keys", expanded=False):
        r1, r2, r3 = st.columns(3)
        with r1:
            st.markdown("**🖼️ Company Logo**")
            lu = st.file_uploader("PNG (transparent preferred)",
                                   type=["png","jpg","jpeg"], key="bk_logo")
            if lu: st.session_state["brand_logo"] = lu.read()
            if st.session_state.get("brand_logo"):
                st.image(st.session_state["brand_logo"], width=100)
                if st.button("✕ Remove", key="rm_logo"): del st.session_state["brand_logo"]

        with r2:
            st.markdown("**🏅 Cert / Award Badge**")
            cu = st.file_uploader("Badge", type=["png","jpg","jpeg"], key="bk_cert")
            if cu: st.session_state["brand_cert"] = cu.read()
            if st.session_state.get("brand_cert"):
                st.image(st.session_state["brand_cert"], width=78)
                if st.button("✕ Remove", key="rm_cert"): del st.session_state["brand_cert"]

        with r3:
            st.markdown("**🔗 Social Links**")
            fb_v  = st.text_input("Facebook",  value=st.session_state.get("bk_fb",""),  key="_fb")
            ig_v  = st.text_input("Instagram", value=st.session_state.get("bk_ig",""),  key="_ig")
            wb_v  = st.text_input("Website",   value=st.session_state.get("bk_wb",""),  key="_wb")
            lp_v  = st.radio("Logo position",
                              ["Top Right","Top Left","Bottom Right","Bottom Left"],
                              horizontal=True, key="bk_lpos")
            if st.button("💾 Save", use_container_width=True):
                st.session_state.update(bk_fb=fb_v,bk_ig=ig_v,bk_wb=wb_v)
                st.success("Saved!")

        st.markdown("---")
        st.markdown("##### 🔑 LLM API Keys  —  free")
        k1, k2 = st.columns(2)
        with k1:
            gq = st.text_input("⚡ Groq (recommended — fast & free)",
                                type="password",
                                value=st.session_state.get("groq_key",""),
                                placeholder="gsk_xxxxxxxxxx",
                                help="console.groq.com → API Keys → Create")
            if gq: st.session_state["groq_key"] = gq.strip()
            if _groq_key(): st.success("✓ Groq active")
            else: st.info("Get free key: console.groq.com")

        with k2:
            gm = st.text_input("🔵 Gemini (fallback)",
                                type="password",
                                value=st.session_state.get("gemini_key",""),
                                placeholder="AIzaSy...",
                                help="aistudio.google.com/app/apikey — free, 250 req/day")
            if gm: st.session_state["gemini_key"] = gm.strip()
            if _gemini_key(): st.success("✓ Gemini active")
            else: st.info("Get free key: aistudio.google.com")

    # Brand kit values
    logo_bytes = st.session_state.get("brand_logo")
    cert_bytes = st.session_state.get("brand_cert")
    bk_fb   = st.session_state.get("bk_fb","")
    bk_ig   = st.session_state.get("bk_ig","")
    bk_wb   = st.session_state.get("bk_wb","")
    logo_pos = st.session_state.get("bk_lpos","Top Right")

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # ══ ONE-PROMPT INPUT  (top of page, always visible) ══
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("### ✍️ Describe your travel package — just one line")
    st.caption("AI will generate: title · price · highlights · captions · hashtags · everything else")

    free_text = st.text_area(
        "", height=90,
        placeholder=(
            "7 day Rajasthan trip with desert safari, camel ride, Jaipur, Udaipur, "
            "Jodhpur, 3 star hotels, price around 25000 per person, family package"
        ),
        label_visibility="collapsed",
        key="free_text_input",
    )

    photos_input = st.file_uploader(
        "📸 Upload 1-8 travel photos",
        type=["jpg","jpeg","png","webp"],
        accept_multiple_files=True,
        key="main_photos",
    )

    # Show photo thumbnails
    # ── Read ALL photo bytes ONCE immediately after upload ────────────────────
    # Streamlit UploadedFile buffers drain on first read — must read bytes
    # immediately and cache in session_state before any Image.open() calls.
    if photos_input:
        # Only re-read if the set of filenames has changed (avoids re-read on reruns)
        uploaded_names = [pf.name for pf in photos_input]
        if st.session_state.get("_uploaded_names") != uploaded_names:
            fresh_bytes = []
            for pf in photos_input[:8]:
                pf.seek(0)                  # rewind just in case
                fresh_bytes.append(pf.read())
            st.session_state["_uploaded_photo_bytes"] = fresh_bytes
            st.session_state["_uploaded_names"]       = uploaded_names

    cached_photo_bytes: list = st.session_state.get("_uploaded_photo_bytes", [])

    # Thumbnail strip (uses cached bytes, never touches UploadedFile again)
    if cached_photo_bytes:
        thumb_cols = st.columns(min(len(cached_photo_bytes), 8))
        for i, raw_b in enumerate(cached_photo_bytes):
            try:
                img_prev = Image.open(io.BytesIO(raw_b))
                scale = 120 / img_prev.width
                thumb = img_prev.resize((120, int(img_prev.height * scale)), Image.LANCZOS)
                thumb_cols[i].image(to_bytes(thumb), use_container_width=True)
            except Exception:
                thumb_cols[i].warning(f"⚠ Photo {i+1}")

    # ── QUICK GENERATE ────────────────────────────────────────────────────────
    col_gen1, col_gen2 = st.columns([3,1])
    with col_gen1:
        big_gen = st.button(
            "🚀 Generate All Content (AI)",
            type="primary", use_container_width=True,
            disabled=not (free_text.strip() and cached_photo_bytes),
        )
    with col_gen2:
        if not _llm_ok():
            st.warning("Add API key ↑")
        elif not free_text.strip():
            st.info("Type your package ↑")
        elif not cached_photo_bytes:
            st.info("Upload photos ↑")

    if big_gen and free_text.strip() and cached_photo_bytes:
        with st.spinner("🤖 AI generating complete package content…"):
            ai_data = ai_generate_all(free_text, len(cached_photo_bytes))
        st.session_state["ai_data"]   = ai_data
        st.session_state["ai_photos"] = cached_photo_bytes   # already bytes, no .read()
        st.success(
            f"✅ Generated: **{ai_data.get('headline','')}**  ·  "
            f"Theme: {ai_data.get('theme','')}  ·  "
            f"Layout: {ai_data.get('layout','')}"
        )

    ai = st.session_state.get("ai_data", {})
    raw_photos: list = st.session_state.get("ai_photos", [])

    if not ai and big_gen and not _llm_ok():
        st.warning("⚠️ No LLM key — using smart defaults. Add Groq/Gemini key for AI-generated copy.")
        ai = ai_generate_all(free_text, len(cached_photo_bytes))
        st.session_state["ai_data"]   = ai
        st.session_state["ai_photos"] = cached_photo_bytes
        raw_photos = cached_photo_bytes

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # TABS
    # ─────────────────────────────────────────────────────────────────────────
    tab_preview, tab_copy, tab_video, tab_bulk = st.tabs([
        "🖼️ Banner Studio",
        "📋 AI Copy & Captions",
        "🎬 Video Slideshow",
        "📦 Bulk Export",
    ])

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 1 — BANNER STUDIO
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_preview:
        if not ai:
            st.markdown('<div class="empty"><div class="ei">✍️</div>'
                        '<div class="et">Type your package description above and click Generate</div>'
                        '</div>', unsafe_allow_html=True)
        else:
            sl, sr = st.columns([1, 1], gap="large")

            with sl:
                st.markdown("### 🎨 Customise")
                st.caption("AI has pre-selected theme & layout — change anytime")

                c1, c2 = st.columns(2)
                with c1:
                    sel_theme = st.selectbox("Visual Theme", list(THEMES.keys()),
                                              index=list(THEMES.keys()).index(
                                                  ai.get("theme","Golden Hour"))
                                              if ai.get("theme") in THEMES else 0,
                                              key="st_theme")
                with c2:
                    sel_layout = st.selectbox("Layout", list(LAYOUTS.keys()),
                                               index=list(LAYOUTS.keys()).index(
                                                   ai.get("layout","Hero + Strip"))
                                               if ai.get("layout") in LAYOUTS else 0,
                                               key="st_layout")

                c3, c4 = st.columns(2)
                with c3:
                    sel_plat = st.selectbox("Platform", list(PLATFORMS.keys()), key="st_plat")
                with c4:
                    sel_lpos = st.selectbox("Logo pos",
                                             ["Top Right","Top Left","Bottom Right","Bottom Left"],
                                             index=["Top Right","Top Left","Bottom Right","Bottom Left"].index(logo_pos),
                                             key="st_lpos")

                st.markdown("#### 🔧 Fine-tune AI Copy")
                st.caption("Edit any field — AI suggestions shown by default")

                pkg_name  = st.text_input("Package Name", value=ai.get("package_name",""), key="ft_pkg")
                headline  = st.text_input("Headline",     value=ai.get("headline",""),     key="ft_hl")
                subline   = st.text_input("Subheadline",  value=ai.get("subheadline",""),  key="ft_sub")
                price_val = st.text_input("Price",        value=ai.get("price",""),        key="ft_price")
                cta_val   = st.text_input("CTA",          value=ai.get("cta","Book Now →"),key="ft_cta")
                hl_raw    = st.text_area("Highlights (one per line)",
                                          value="\n".join(ai.get("highlights",[])),
                                          height=120, key="ft_hllist")
                hl_list   = [l.strip() for l in hl_raw.splitlines() if l.strip()]

                c5, c6 = st.columns(2)
                with c5: show_price = st.checkbox("Show price", value=True, key="ft_sp")
                with c6: show_cta   = st.checkbox("Show CTA",   value=True, key="ft_sc")
                enhance_p = st.checkbox("Auto-enhance photo colours", value=True, key="ft_enh")
                st.slider("Overlay strength (for text contrast)", 1, 5, 3, key="ft_ov")

                gen_banner = st.button("🎨 Render Banner", type="primary",
                                        use_container_width=True,
                                        disabled=not raw_photos)

            with sr:
                st.markdown("### 👁️ Preview")

                if gen_banner and raw_photos:
                    photos_pil = []
                    for b in raw_photos[:8]:
                        try:
                            photos_pil.append(Image.open(io.BytesIO(bytes(b))).convert("RGBA"))
                        except Exception as _e:
                            st.warning(f"Skipping unreadable photo: {_e}")
                    if not photos_pil:
                        st.error("No valid photos — please re-upload.")
                        st.stop()
                    sw, sh = PLATFORMS[sel_plat]
                    content = dict(
                        package_name=pkg_name, headline=headline,
                        subheadline=subline, price=price_val,
                        cta=cta_val, highlights=hl_list,
                    )
                    with st.spinner("Compositing…"):
                        banner = compose(
                            photos_pil, sw, sh,
                            sel_theme, sel_layout, content,
                            logo_bytes, sel_lpos, cert_bytes,
                            bk_fb, bk_ig, bk_wb,
                            show_price=show_price, show_cta=show_cta,
                            enhance_photos=enhance_p,
                        )
                    st.session_state["s_png"] = to_bytes(banner,"PNG")
                    st.session_state["s_jpg"] = to_bytes(banner,"JPEG",90)
                    st.session_state["s_name"]= f"{pkg_name or 'banner'}_{sel_plat[:14]}"

                if st.session_state.get("s_png"):
                    st.image(st.session_state["s_png"], use_container_width=True)
                    d1, d2 = st.columns(2)
                    with d1:
                        st.download_button("📥 PNG",
                            data=st.session_state["s_png"],
                            file_name=f"{st.session_state['s_name']}.png",
                            mime="image/png", use_container_width=True)
                    with d2:
                        st.download_button("📥 JPEG",
                            data=st.session_state["s_jpg"],
                            file_name=f"{st.session_state['s_name']}.jpg",
                            mime="image/jpeg", use_container_width=True)
                    st.success("✅ Ready to post!")
                else:
                    st.markdown('<div class="empty"><div class="ei">🎨</div>'
                                '<div class="et">Click Render Banner to preview</div>'
                                '</div>', unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 2 — AI COPY
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_copy:
        if not ai:
            st.markdown('<div class="empty"><div class="ei">📋</div>'
                        '<div class="et">Generate content first (above)</div></div>',
                        unsafe_allow_html=True)
        else:
            st.markdown("### 📋 AI-Generated Copy — copy for all platforms")
            st.caption("All generated from your one-line description. Click any field to copy.")

            def _cbox(label, val):
                if not val: return
                st.markdown(f'<div class="copy-lbl">{label}</div>', unsafe_allow_html=True)
                v = "\n".join(f"• {h}" for h in val) if isinstance(val,list) else str(val)
                st.text_area("", value=v, height=max(68, min(200, v.count("\n")*28+68)),
                              key=f"cp_{label}", label_visibility="collapsed")

            c1, c2 = st.columns(2)
            with c1:
                _cbox("HEADLINE",      ai.get("headline",""))
                _cbox("SUBHEADLINE",   ai.get("subheadline",""))
                _cbox("PACKAGE NAME",  ai.get("package_name",""))
                _cbox("PRICE",         ai.get("price",""))
                _cbox("DURATION",      ai.get("duration",""))
                _cbox("CTA",           ai.get("cta",""))
                _cbox("HIGHLIGHTS",    ai.get("highlights",[]))
                _cbox("HASHTAGS",      ai.get("hashtags",""))
            with c2:
                _cbox("📺 YouTube Title",       ai.get("youtube_title",""))
                _cbox("📺 YouTube Description", ai.get("youtube_desc",""))
                _cbox("📸 Instagram Caption",   ai.get("instagram_caption",""))
                _cbox("👥 Facebook Caption",    ai.get("facebook_caption",""))
                _cbox("📱 WhatsApp Status",     ai.get("whatsapp_status",""))
                _cbox("🎬 30-sec Reel Script",  ai.get("reel_script",""))

            st.markdown("---")
            st.info(f"🎨 AI recommended theme: **{ai.get('theme','')}**  ·  "
                    f"Layout: **{ai.get('layout','')}**  ·  "
                    f"Mood: **{ai.get('mood','')}**")

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 3 — VIDEO SLIDESHOW
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_video:
        st.markdown("### 🎬 Animated Slideshow  (20-30 sec)")
        st.info("Each photo = one scene with AI caption. Download GIF → CapCut → add music → MP4 for Reels.")

        if not ai or not raw_photos:
            st.markdown('<div class="empty"><div class="ei">🎬</div>'
                        '<div class="et">Generate content + upload photos first</div>'
                        '</div>', unsafe_allow_html=True)
        else:
            vl, vr = st.columns([1,1], gap="large")

            with vl:
                v_theme  = st.selectbox("Theme", list(THEMES.keys()),
                                         index=list(THEMES.keys()).index(
                                             ai.get("theme","Golden Hour"))
                                         if ai.get("theme") in THEMES else 0, key="v_theme")
                v_plat   = st.selectbox("Format", [
                    "Instagram Story    9:16  1080×1920",
                    "YouTube Shorts     9:16  1080×1920",
                    "Instagram Post     1:1   1080×1080",
                    "YouTube Thumbnail  16:9  1280×720",
                ], key="v_plat")
                vw, vh   = PLATFORMS[v_plat]
                v_dur    = st.slider("Seconds per scene", 2, 5, 3, key="v_dur")
                v_show_p = st.checkbox("Show price on last slide", value=True, key="v_sp")
                v_enh    = st.checkbox("Auto-enhance photos", value=True, key="v_enh")

                st.markdown("#### 📝 Slide Captions")
                st.caption("AI-suggested captions below — edit any")
                ai_caps = ai.get("slide_captions", [f"Scene {i+1}" for i in range(8)])
                user_caps = []
                for i, raw_b in enumerate(raw_photos[:8]):
                    default_cap = ai_caps[i] if i < len(ai_caps) else f"Slide {i+1}"
                    cap = st.text_input(f"Slide {i+1} caption",
                                         value=default_cap, key=f"vcap_{i}")
                    user_caps.append(cap)

                v_gen = st.button("🎬 Generate Slideshow", type="primary",
                                   use_container_width=True)

            with vr:
                st.markdown("### 👁️ Preview")

                if v_gen:
                    photos_pil = []
                    for b in raw_photos[:8]:
                        try:
                            photos_pil.append(Image.open(io.BytesIO(bytes(b))).convert("RGBA"))
                        except Exception as _e:
                            st.warning(f"Skipping unreadable photo: {_e}")
                    frames = []
                    prog = st.progress(0, text="Compositing frames…")
                    live_cols = st.columns(min(len(photos_pil),4))
                    total = len(photos_pil)

                    content_vid = dict(
                        package_name=ai.get("package_name",""),
                        headline="", subheadline="",
                        highlights=[], price=ai.get("price",""),
                        cta=ai.get("cta","Book Now →"),
                    )

                    for idx, photo in enumerate(photos_pil):
                        prog.progress(idx/total, text=f"Scene {idx+1}/{total}…")
                        cap = user_caps[idx] if idx < len(user_caps) else f"Slide {idx+1}"
                        frame = compose(
                            [photo], vw, vh,
                            v_theme, "Hero + Strip", content_vid,
                            logo_bytes, logo_pos, cert_bytes,
                            bk_fb, bk_ig, bk_wb,
                            show_price=(idx==total-1 and v_show_p),
                            show_cta=(idx==total-1),
                            enhance_photos=v_enh,
                            slide_caption=cap,
                            slide_num=f"{idx+1:02d} / {total:02d}",
                        )
                        frames.append(frame)
                        # Live thumbnails
                        col_i = idx % 4
                        if col_i < len(live_cols):
                            sc = 110/frame.width
                            th = frame.resize((110,int(frame.height*sc)),Image.LANCZOS)
                            live_cols[col_i].image(to_bytes(th),
                                                    caption=cap[:16],
                                                    use_container_width=True)

                    prog.progress(1.0, text="Building GIF…")
                    gif = make_gif(frames, ms=v_dur*1000)
                    st.session_state.update(v_gif=gif,
                                             v_frames=[to_bytes(f) for f in frames],
                                             v_pkg=ai.get("package_name","video"))
                    prog.empty()
                    st.success(f"✅ {len(frames)}-scene GIF · {len(gif)//1024} KB")

                gif = st.session_state.get("v_gif")
                if gif:
                    b64 = base64.b64encode(gif).decode()
                    st.markdown(f'<img src="data:image/gif;base64,{b64}" '
                                f'style="width:100%;border-radius:12px;border:1px solid #1f2937">',
                                unsafe_allow_html=True)
                    d1, d2 = st.columns(2)
                    with d1:
                        st.download_button("📥 Download GIF", data=gif,
                            file_name=f"{st.session_state.get('v_pkg','video')}_slideshow.gif",
                            mime="image/gif", use_container_width=True)
                    with d2:
                        if st.session_state.get("v_frames"):
                            zbuf = io.BytesIO()
                            with zipfile.ZipFile(zbuf,"w") as zf:
                                for i,fb2 in enumerate(st.session_state["v_frames"]):
                                    zf.writestr(f"scene_{i+1:02d}.png",fb2)
                            zbuf.seek(0)
                            st.download_button("📥 Frames ZIP", data=zbuf.getvalue(),
                                file_name="scenes.zip", mime="application/zip",
                                use_container_width=True)
                    st.markdown(
                        "**🎵 MP4:** Import GIF → **[CapCut](https://capcut.com)** free → "
                        "add music ([Pixabay](https://pixabay.com/music/)) → export 1080p MP4"
                    )
                else:
                    st.markdown('<div class="empty"><div class="ei">🎬</div>'
                                '<div class="et">Click Generate Slideshow</div></div>',
                                unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 4 — BULK EXPORT
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_bulk:
        st.markdown("### 📦 Bulk Export — All Platforms in One ZIP")
        st.info("Renders your banner for every platform size using your photos and AI content.")

        if not ai or not raw_photos:
            st.markdown('<div class="empty"><div class="ei">📦</div>'
                        '<div class="et">Generate content + upload photos first</div>'
                        '</div>', unsafe_allow_html=True)
        else:
            bl, br = st.columns([1,1], gap="large")
            with bl:
                b_theme  = st.selectbox("Theme", list(THEMES.keys()),
                                         index=list(THEMES.keys()).index(
                                             ai.get("theme","Golden Hour"))
                                         if ai.get("theme") in THEMES else 0, key="b_theme")
                b_layout = st.selectbox("Layout", list(LAYOUTS.keys()),
                                         index=list(LAYOUTS.keys()).index(
                                             ai.get("layout","Hero + Strip"))
                                         if ai.get("layout") in LAYOUTS else 0, key="b_layout")
                b_plats  = st.multiselect("Export for", list(PLATFORMS.keys()),
                                           default=list(PLATFORMS.keys())[:5])
                b_gen    = st.button("📦 Generate All Sizes", type="primary",
                                      use_container_width=True, disabled=not b_plats)

            with br:
                st.markdown("### 📋 Results")
                if b_gen and b_plats:
                    photos_pil = []
                    for b in raw_photos[:8]:
                        try:
                            photos_pil.append(Image.open(io.BytesIO(bytes(b))).convert("RGBA"))
                        except Exception as _e:
                            st.warning(f"Skipping unreadable photo: {_e}")
                    content = dict(
                        package_name=ai.get("package_name",""),
                        headline=ai.get("headline",""),
                        subheadline=ai.get("subheadline",""),
                        price=ai.get("price",""),
                        cta=ai.get("cta","Book Now →"),
                        highlights=ai.get("highlights",[]),
                    )
                    zbuf = io.BytesIO()
                    prog = st.progress(0)
                    preview_done = False

                    with zipfile.ZipFile(zbuf,"w",zipfile.ZIP_DEFLATED) as zf:
                        for i, pname in enumerate(b_plats):
                            pw, ph = PLATFORMS[pname]
                            banner = compose(
                                photos_pil, pw, ph,
                                b_theme, b_layout, content,
                                logo_bytes, logo_pos, cert_bytes,
                                bk_fb, bk_ig, bk_wb,
                            )
                            safe = re.sub(r"[^\w]"," ",pname).strip().replace(" ","_")[:28]
                            zf.writestr(f"{ai.get('package_name','banner')}_{safe}_{pw}x{ph}.png",
                                        to_bytes(banner))
                            if not preview_done:
                                st.image(to_bytes(banner), caption=pname,
                                         use_container_width=True)
                                preview_done = True
                            prog.progress((i+1)/len(b_plats))

                    prog.empty(); zbuf.seek(0)
                    st.success(f"✅ {len(b_plats)} banners ready!")
                    st.download_button("📥 Download ZIP (all platforms)",
                        data=zbuf.getvalue(),
                        file_name=f"{ai.get('package_name','banners')}_all_platforms.zip",
                        mime="application/zip", use_container_width=True)
                else:
                    st.markdown('<div class="empty"><div class="ei">📦</div>'
                                '<div class="et">Select platforms → Generate All Sizes</div>'
                                '</div>', unsafe_allow_html=True)

    # ── TIPS ──────────────────────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("💡 How to write the perfect one-line description"):
        st.markdown("""
**Include as much as you can in one line:**
> *7 day Kerala backwaters trip with houseboat stay, Munnar tea gardens, elephant park, Varkala beach, 3-star hotels, ₹28,000 per person, couple package*

**What AI picks up automatically:**
- Destination, duration, price, package type
- Key activities → become highlights
- Price range → recommends matching colour theme
- "couple / family / adventure" → sets mood + colour palette

**Photo tips for best composite results:**
- Upload 3-5 photos for best magazine/mosaic layouts
- Mix: 1 wide landscape + 1-2 activity shots + 1 food/culture shot
- Minimum 1200px wide for crisp output
- Golden hour photos work best with warm themes

**Theme guide:**
| Mood | Best Theme |
|---|---|
| Desert / Heritage | Desert Sand or Golden Hour |
| Beach / Water | Deep Ocean |
| Luxury / Premium | Dark Luxury |
| Hills / Forest / Wildlife | Emerald |
| Honeymoon / Romance | Rose Blush |
| Adventure / Vibrant | Coral Sunset |
| Night / City | Midnight Blue |

**Free API keys:**
- **Groq:** [console.groq.com](https://console.groq.com) → fast, generous free tier
- **Gemini:** [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) → 250 req/day free
        """)
