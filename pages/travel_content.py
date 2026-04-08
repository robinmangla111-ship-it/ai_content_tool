"""
✈ AI Travel Flyer Creator — PPTX Edition (Canva-Ready)
=======================================================
OUTPUT: .pptx file → import directly into Canva → every element is editable

PREMIUM FEATURES:
  ✅ Slide 1: A4 Flyer (Luxury Poster)
  ✅ Slide 2: Instagram Story (9:16)
  ✅ Slide 3: Day-wise itinerary + inclusions + services
  ✅ Auto photo brightness detection → text placed left/right automatically
  ✅ Auto dominant color palette extraction from hero photo → dynamic theme
  ✅ Auto collage layout selection (2–6 photos)
  ✅ Hotel cards + highlights grid + premium deal card
  ✅ Dynamic font scaling (headline/subheadline/price)
  ✅ Glass cards + shadows
  ✅ QR code + CTA buttons
  ✅ Destination watermark typography (luxury style)

REQUIREMENTS:
  python-pptx>=0.6.21
  pillow>=10.0.0
  requests
"""

import streamlit as st
import sys, os, io, json, re, requests
from urllib.parse import quote as url_quote

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.oxml.xmlchemy import OxmlElement
from pptx.oxml.ns import qn

from PIL import Image, ImageOps, ImageEnhance


# ─────────────────────────────────────────────────────────────────────────────
# BASIC UTILS
# ─────────────────────────────────────────────────────────────────────────────

def _rgb(hex_str: str) -> RGBColor:
    h = hex_str.lstrip("#")
    return RGBColor(int(h[0:2],16), int(h[2:4],16), int(h[4:6],16))

def _get(sk, sec, ev=""):
    v = st.session_state.get(sk, "").strip()
    if v:
        return v
    try:
        v = str(st.secrets.get(sec, "")).strip()
        if v:
            return v
    except Exception:
        pass
    return os.getenv(ev, "").strip()

def _groq_key():   return _get("groq_key",   "GROQ_API_KEY",   "GROQ_API_KEY")
def _gemini_key(): return _get("gemini_key", "GEMINI_API_KEY", "GEMINI_API_KEY")
def _llm_ok():     return bool(_groq_key() or _gemini_key())


# ─────────────────────────────────────────────────────────────────────────────
# THEMES
# ─────────────────────────────────────────────────────────────────────────────

THEMES = {
    "🏅 Classic Navy Gold": {
        "primary":  "1a1a5e",
        "primary2": "0d2d6b",
        "accent":   "c9a84c",
        "accent2":  "f0c040",
        "dark":     "0d1035",
        "light":    "ffffff",
        "text_on_dark": "ffffff",
        "text_on_light": "1a1a5e",
        "muted":    "8888bb",
        "price_bg": "c9a84c",
        "hl_bg":    "f4f6ff",
        "incl_bg":  "0d2d6b",
    },
    "🌿 Emerald Luxury": {
        "primary":  "0a3d2e",
        "primary2": "0d5540",
        "accent":   "d4a843",
        "accent2":  "f5c842",
        "dark":     "052a1e",
        "light":    "ffffff",
        "text_on_dark": "ffffff",
        "text_on_light": "0a3d2e",
        "muted":    "4a8a6a",
        "price_bg": "d4a843",
        "hl_bg":    "f0f8f4",
        "incl_bg":  "0d5540",
    },
    "🌊 Ocean Blue": {
        "primary":  "004e7c",
        "primary2": "006b9f",
        "accent":   "00c9c8",
        "accent2":  "40e0d0",
        "dark":     "003055",
        "light":    "ffffff",
        "text_on_dark": "ffffff",
        "text_on_light": "004e7c",
        "muted":    "2a6a8a",
        "price_bg": "009b9a",
        "hl_bg":    "f0faff",
        "incl_bg":  "006b9f",
    },
    "🌙 Midnight Premium": {
        "primary":  "0a0a2a",
        "primary2": "1a1a4e",
        "accent":   "d4af37",
        "accent2":  "ffd700",
        "dark":     "000010",
        "light":    "ffffff",
        "text_on_dark": "ffffff",
        "text_on_light": "0a0a2a",
        "muted":    "6a6a9a",
        "price_bg": "d4af37",
        "hl_bg":    "f0f0fa",
        "incl_bg":  "1a1a4e",
    },
    "🌺 Coral Vibrant": {
        "primary":  "b03020",
        "primary2": "d44030",
        "accent":   "f5a623",
        "accent2":  "ffd050",
        "dark":     "7a1a10",
        "light":    "ffffff",
        "text_on_dark": "ffffff",
        "text_on_light": "7a1a10",
        "muted":    "c06050",
        "price_bg": "f5a623",
        "hl_bg":    "fff5f0",
        "incl_bg":  "d44030",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# LLM
# ─────────────────────────────────────────────────────────────────────────────

def _groq(sys_p, usr_p, tokens=1100):
    key = _groq_key()
    if not key:
        return ""
    try:
        from groq import Groq
        r = Groq(api_key=key).chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"system","content":sys_p},
                      {"role":"user","content":usr_p}],
            max_tokens=tokens,
            temperature=0.75,
            response_format={"type":"json_object"},
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        st.toast(f"Groq: {e}", icon="⚠️")
        return ""

def _gemini(prompt, tokens=1100):
    key = _gemini_key()
    if not key:
        return ""
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    body = {
        "contents":[{"parts":[{"text":prompt}]}],
        "generationConfig":{
            "maxOutputTokens":tokens,
            "temperature":0.8,
            "responseMimeType":"application/json"
        }
    }
    try:
        r = requests.post(url, params={"key":key}, json=body, timeout=35)
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        st.toast(f"Gemini: {e}", icon="⚠️")
        return ""

def _llm(sys_p, usr_p, tokens=1100):
    out = _groq(sys_p, usr_p, tokens)
    return out or _gemini(f"{sys_p}\n\nReturn ONLY valid JSON.\n\n{usr_p}", tokens)

def _parse_json(raw):
    try:
        clean = re.sub(r"```(?:json)?|```","",raw).strip()
        s = clean.find("{")
        return json.loads(clean[s:]) if s >= 0 else json.loads(clean)
    except Exception:
        return {}

def ai_generate_all(free_text: str, n_photos: int) -> dict:
    sys_p = """You are an expert travel marketing AI for Indian travel agencies.
From a one-line description, generate ALL flyer content. Return ONLY valid JSON:
  company_name, package_name, destination, headline (ALL CAPS, max 8 words),
  subheadline (one punchy line), duration (e.g. "5 Nights / 6 Days"),
  price (e.g. "₹28,777"), price_label (e.g. "SPECIAL OFFER"),
  price_note (e.g. "per person twin sharing | Breakfast & Dinner | min 4 guests"),
  validity (e.g. "Valid till 30th Sep 2026 | T&C Apply"),
  cta (e.g. "BOOK NOW"),
  highlights (array of 6, max 4 words each),
  inclusions (array of 6 key inclusions),
  itinerary (array of {city, nights, hotel} for 2-4 stops),
  day_plan (array of {day, title, details}),
  services (array of 5 services offered by agency),
  hashtags, instagram_caption, facebook_caption, whatsapp_status,
  youtube_title, youtube_desc, reel_script,
  website, phone, email, social_fb, social_ig, social_yt,
  theme (one of: Classic Navy Gold/Emerald Luxury/Ocean Blue/Midnight Premium/Coral Vibrant)
"""
    usr_p = f"Package: \"{free_text}\"\nPhotos: {n_photos}\nGenerate:"
    raw = _llm(sys_p, usr_p, 1400)
    data = _parse_json(raw) if raw else {}

    dest = free_text.split()[0].title() if free_text else "India"
    defaults = {
        "company_name":"Your Travel Company",
        "package_name":f"{dest} Package",
        "destination":dest,
        "headline":f"DISCOVER {dest.upper()}",
        "subheadline":"Unforgettable Journeys | Expert Guided Tours",
        "duration":"7 Days / 6 Nights",
        "price":"₹24,999",
        "price_label":"SPECIAL OFFER",
        "price_note":"per person twin sharing",
        "validity":"Limited Seats | T&C Apply",
        "cta":"BOOK NOW",
        "highlights":[f"{dest} Sightseeing","Scenic Landscapes","Cultural Experiences",
                      "Heritage Sites","Local Cuisine","Guided Tours"],
        "inclusions":["Airport Transfers","Hotel Accommodation","Daily Breakfast",
                      "All Sightseeing","Expert Tour Guide","24/7 Support"],
        "itinerary":[{"city":dest,"nights":3,"hotel":"Premium Hotel / Similar"}],
        "day_plan":[
            {"day":"Day 1","title":"Arrival & Check-in","details":"Arrive, transfer to hotel, leisure time."},
            {"day":"Day 2","title":"City Sightseeing","details":"Local attractions, markets, evening leisure."},
            {"day":"Day 3","title":"Excursion Day","details":"Scenic excursion with guide, photo stops."},
            {"day":"Day 4","title":"Departure","details":"Breakfast, checkout, transfer to airport."},
        ],
        "services":["Tour Packages","Visa Assistance","Hotel Bookings",
                    "Flight Bookings","Travel Insurance"],
        "hashtags":f"#{dest.replace(' ','')} #Travel #TourPackage #India",
        "instagram_caption":f"✈️ {dest} awaits! Book now. #{dest.replace(' ','')} #Travel",
        "facebook_caption":f"Amazing {dest} package available! Contact us.",
        "whatsapp_status":f"✈️ {dest} Package!\n📞 Call to Book!",
        "youtube_title":f"{dest} Travel Package | Best Deals 2025",
        "youtube_desc":f"Discover {dest} with our amazing package.",
        "reel_script":f"{dest} is calling! Book your dream trip today!",
        "website":"www.yourtravels.com",
        "phone":"+91 98765 43210",
        "email":"info@yourtravels.com",
        "social_fb":"yourtravels",
        "social_ig":"@yourtravels",
        "social_yt":"@yourtravels",
        "theme":"Classic Navy Gold",
    }
    for k,v in defaults.items():
        data.setdefault(k,v)
    return data


# ─────────────────────────────────────────────────────────────────────────────
# PREMIUM PALETTE EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

def _rgb_to_hex(rgb):
    return "%02x%02x%02x" % rgb

def _brightness(rgb):
    r, g, b = rgb
    return (0.299*r + 0.587*g + 0.114*b)

def extract_palette_from_photo(img_bytes: bytes):
    try:
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        img = img.resize((180, 180))

        img_q = img.quantize(colors=10, method=2).convert("RGB")
        pixels = list(img_q.getdata())

        freq = {}
        for p in pixels:
            freq[p] = freq.get(p, 0) + 1

        sorted_colors = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        dominant = sorted_colors[0][0]
        second = sorted_colors[1][0] if len(sorted_colors) > 1 else dominant
        third  = sorted_colors[2][0] if len(sorted_colors) > 2 else second

        candidates = [dominant, second, third]
        candidates_sorted = sorted(candidates, key=lambda c: _brightness(c))

        dark_col  = candidates_sorted[0]
        mid_col   = candidates_sorted[1]
        light_col = candidates_sorted[-1]

        accent_col = mid_col if _brightness(mid_col) > 80 else light_col

        price_bg = (
            min(accent_col[0] + 30, 255),
            min(accent_col[1] + 20, 255),
            min(accent_col[2] + 20, 255),
        )

        text_on_dark = "ffffff" if _brightness(dark_col) < 140 else "000000"

        return {
            "primary": _rgb_to_hex(dark_col),
            "primary2": _rgb_to_hex(mid_col),
            "dark": _rgb_to_hex(dark_col),
            "accent": _rgb_to_hex(accent_col),
            "accent2": _rgb_to_hex(light_col),
            "price_bg": _rgb_to_hex(price_bg),
            "text_on_dark": text_on_dark,
        }
    except Exception:
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# PPTX HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _set_shape_alpha(shape, alpha=65000):
    try:
        sp = shape._element
        solid = sp.find(".//" + qn("a:solidFill"))
        if solid is not None:
            srgb = solid.find(qn("a:srgbClr"))
            if srgb is not None:
                a = OxmlElement("a:alpha")
                a.set("val", str(alpha))
                srgb.append(a)
    except Exception:
        pass

def _no_border(shape):
    try:
        shape.line.fill.background()
        shape.line.width = Pt(0)
    except Exception:
        pass

def _add_rect(slide, x, y, w, h, fill_hex):
    shp = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RECTANGLE,
        Inches(x), Inches(y), Inches(w), Inches(h)
    )
    shp.fill.solid()
    shp.fill.fore_color.rgb = _rgb(fill_hex)
    _no_border(shp)
    return shp

def _add_rounded_rect(slide, x, y, w, h, fill_hex):
    shp = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.ROUNDED_RECTANGLE,
        Inches(x), Inches(y), Inches(w), Inches(h)
    )
    shp.fill.solid()
    shp.fill.fore_color.rgb = _rgb(fill_hex)
    _no_border(shp)
    return shp

def _add_circle(slide, x, y, d, fill_hex):
    shp = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.OVAL,
        Inches(x), Inches(y), Inches(d), Inches(d)
    )
    shp.fill.solid()
    shp.fill.fore_color.rgb = _rgb(fill_hex)
    _no_border(shp)
    return shp

def _add_text(slide, text, x, y, w, h,
              font_size=12, bold=False, italic=False,
              color_hex="000000", align=PP_ALIGN.LEFT,
              font_name="Aptos", wrap=True):
    txBox = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = txBox.text_frame
    tf.word_wrap = wrap
    tf.margin_left   = Inches(0.08)
    tf.margin_right  = Inches(0.08)
    tf.margin_top    = Inches(0.04)
    tf.margin_bottom = Inches(0.04)

    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = str(text)
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = _rgb(color_hex)
    run.font.name = font_name
    return txBox

def _add_text_in_shape(shape, text, font_size=12, bold=False,
                       color_hex="ffffff", align=PP_ALIGN.CENTER,
                       font_name="Aptos"):
    tf = shape.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.margin_left   = Inches(0.08)
    tf.margin_right  = Inches(0.08)
    tf.margin_top    = Inches(0.04)
    tf.margin_bottom = Inches(0.04)

    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = str(text)
    run.font.size = Pt(font_size)
    run.font.bold = bold
    run.font.color.rgb = _rgb(color_hex)
    run.font.name = font_name

def _glass_card(slide, x, y, w, h, alpha=72000):
    card = _add_rounded_rect(slide, x, y, w, h, "ffffff")
    _set_shape_alpha(card, alpha)
    return card

def _shadow_card(slide, x, y, w, h):
    shadow = _add_rounded_rect(slide, x+0.04, y+0.05, w, h, "000000")
    _set_shape_alpha(shadow, 22000)
    return shadow


# ─────────────────────────────────────────────────────────────────────────────
# SMART FONT
# ─────────────────────────────────────────────────────────────────────────────

def _smart_font_size(text: str, max_chars: int, base: int, min_size: int = 10):
    if not text:
        return base
    length = len(text.strip())
    if length <= max_chars:
        return base
    scale = max_chars / length
    size = int(base * scale)
    return max(size, min_size)


# ─────────────────────────────────────────────────────────────────────────────
# IMAGE CROPPING
# ─────────────────────────────────────────────────────────────────────────────

def crop_to_fit(img_bytes: bytes, target_w: int, target_h: int) -> bytes:
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    img = ImageOps.fit(img, (target_w, target_h), method=Image.LANCZOS, centering=(0.5, 0.5))

    img = ImageEnhance.Contrast(img).enhance(1.08)
    img = ImageEnhance.Color(img).enhance(1.12)
    img = ImageEnhance.Sharpness(img).enhance(1.05)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()

def _add_picture(slide, img_bytes, x, y, w, h, dpi=180):
    px_w = int(w * dpi)
    px_h = int(h * dpi)
    cropped = crop_to_fit(img_bytes, px_w, px_h)
    buf = io.BytesIO(cropped)
    return slide.shapes.add_picture(buf, Inches(x), Inches(y), Inches(w), Inches(h))


# ─────────────────────────────────────────────────────────────────────────────
# HERO BRIGHTNESS DETECTION
# ─────────────────────────────────────────────────────────────────────────────

def detect_best_text_side(img_bytes: bytes) -> str:
    try:
        img = Image.open(io.BytesIO(img_bytes)).convert("L")
        img = img.resize((600, 300))

        w, h = img.size
        left  = img.crop((0, 0, w//2, h))
        right = img.crop((w//2, 0, w, h))

        left_mean = sum(left.getdata()) / (w//2 * h)
        right_mean = sum(right.getdata()) / (w//2 * h)

        return "left" if left_mean < right_mean else "right"
    except Exception:
        return "left"


# ─────────────────────────────────────────────────────────────────────────────
# QR CODE
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_qr(text: str, size: int = 150) -> bytes | None:
    try:
        url = f"https://api.qrserver.com/v1/create-qr-code/?size={size}x{size}&data={url_quote(text)}&bgcolor=ffffff&color=000000&margin=4"
        r = requests.get(url, timeout=8)
        if r.status_code == 200:
            return r.content
    except Exception:
        pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
# SLIDE DIMENSIONS
# ─────────────────────────────────────────────────────────────────────────────

SLIDE_W = 8.27
SLIDE_H = 11.69

STORY_W = 5.4
STORY_H = 9.6


# ─────────────────────────────────────────────────────────────────────────────
# HOTEL CARDS
# ─────────────────────────────────────────────────────────────────────────────

def _draw_hotel_cards(slide, itinerary, t, start_y, width):
    if not itinerary:
        return start_y

    CUR_Y = start_y

    _add_text(slide, "HOTEL STAY PLAN",
              0.25, CUR_Y, width-0.5, 0.3,
              font_size=10, bold=True,
              color_hex=t["muted"])
    CUR_Y += 0.35

    card_h = 0.75
    gap = 0.15

    for stop in itinerary[:4]:
        city = stop.get("city", "").strip()
        nights = stop.get("nights", "")
        hotel = stop.get("hotel", "").strip()

        if not city:
            continue

        _shadow_card(slide, 0.25, CUR_Y, width-0.5, card_h)
        _glass_card(slide, 0.25, CUR_Y, width-0.5, card_h)

        badge = _add_circle(slide, 0.35, CUR_Y+0.15, 0.45, t["accent"])
        _add_text_in_shape(badge, str(nights),
                           font_size=14, bold=True,
                           color_hex="000000")

        _add_text(slide, city.upper(),
                  0.9, CUR_Y+0.14, 2.4, 0.3,
                  font_size=12, bold=True,
                  color_hex=t["primary"])

        _add_text(slide, hotel if hotel else "Premium Hotel / Similar",
                  0.9, CUR_Y+0.42, width-1.3, 0.25,
                  font_size=9,
                  color_hex="333333")

        CUR_Y += card_h + gap

    return CUR_Y + 0.15


# ─────────────────────────────────────────────────────────────────────────────
# COLLAGE AUTO LAYOUT (2–6 PHOTOS)
# ─────────────────────────────────────────────────────────────────────────────

def _auto_collage(slide, photos, x, y, w, h):
    """
    Best layout depending on photo count.
    """
    n = len(photos)
    if n <= 0:
        return

    if n == 1:
        _add_picture(slide, photos[0], x, y, w, h)
        return

    if n == 2:
        _add_picture(slide, photos[0], x, y, w/2-0.05, h)
        _add_picture(slide, photos[1], x+w/2+0.05, y, w/2-0.05, h)
        return

    if n == 3:
        _add_picture(slide, photos[0], x, y, w*0.6, h)
        _add_picture(slide, photos[1], x+w*0.6+0.05, y, w*0.4-0.05, h/2-0.05)
        _add_picture(slide, photos[2], x+w*0.6+0.05, y+h/2+0.05, w*0.4-0.05, h/2-0.05)
        return

    if n == 4:
        _add_picture(slide, photos[0], x, y, w*0.55, h)
        _add_picture(slide, photos[1], x+w*0.55+0.05, y, w*0.45-0.05, h/3-0.05)
        _add_picture(slide, photos[2], x+w*0.55+0.05, y+h/3+0.05, w*0.45-0.05, h/3-0.05)
        _add_picture(slide, photos[3], x+w*0.55+0.05, y+2*h/3+0.05, w*0.45-0.05, h/3-0.05)
        return

    if n == 5:
        _add_picture(slide, photos[0], x, y, w*0.6, h*0.6)
        _add_picture(slide, photos[1], x+w*0.6+0.05, y, w*0.4-0.05, h*0.3-0.05)
        _add_picture(slide, photos[2], x+w*0.6+0.05, y+h*0.3+0.05, w*0.4-0.05, h*0.3-0.05)
        _add_picture(slide, photos[3], x, y+h*0.6+0.05, w*0.5-0.05, h*0.4-0.05)
        _add_picture(slide, photos[4], x+w*0.5+0.05, y+h*0.6+0.05, w*0.5-0.05, h*0.4-0.05)
        return

    # n >= 6
    _add_picture(slide, photos[0], x, y, w*0.65, h*0.6)
    _add_picture(slide, photos[1], x+w*0.65+0.05, y, w*0.35-0.05, h*0.3-0.05)
    _add_picture(slide, photos[2], x+w*0.65+0.05, y+h*0.3+0.05, w*0.35-0.05, h*0.3-0.05)

    _add_picture(slide, photos[3], x, y+h*0.6+0.05, w*0.33-0.05, h*0.4-0.05)
    _add_picture(slide, photos[4], x+w*0.33+0.05, y+h*0.6+0.05, w*0.33-0.05, h*0.4-0.05)
    _add_picture(slide, photos[5], x+w*0.66+0.05, y+h*0.6+0.05, w*0.34-0.05, h*0.4-0.05)


# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 3 — ITINERARY BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def _slide3_itinerary(slide, t, content, photos, logo_bytes, W, H):

    # background
    _add_rect(slide, 0, 0, W, H, "ffffff")

    # header band
    _add_rect(slide, 0, 0, W, 1.2, t["dark"])
    _add_rect(slide, 0, 1.15, W, 0.06, t["accent"])

    if logo_bytes:
        _add_picture(slide, logo_bytes, 0.25, 0.2, 1.2, 0.7)

    # Title
    title = f"{content.get('destination','').upper()} ITINERARY"
    _add_text(slide, title,
              1.55, 0.25, W-1.8, 0.5,
              font_size=24, bold=True,
              color_hex=t.get("text_on_dark","ffffff"),
              font_name="Aptos Display")

    _add_text(slide, content.get("duration",""),
              1.55, 0.75, W-1.8, 0.3,
              font_size=12, bold=True,
              color_hex=t["accent2"])

    # hero side image
    if photos:
        _add_picture(slide, photos[0], W-2.9, 1.45, 2.6, 2.0)
        ov = _add_rect(slide, W-2.9, 1.45, 2.6, 2.0, t["dark"])
        _set_shape_alpha(ov, 20000)

    # watermark destination
    wm = slide.shapes.add_textbox(Inches(0.25), Inches(1.35), Inches(W-0.5), Inches(1.0))
    tf = wm.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT
    r = p.add_run()
    r.text = content.get("destination","").upper()
    r.font.size = Pt(56)
    r.font.bold = True
    r.font.name = "Aptos Display"
    r.font.color.rgb = _rgb(t["primary"])
    # make watermark very light
    try:
        r.font.color.brightness = 0.7
    except Exception:
        pass

    # itinerary list
    CUR_Y = 1.5
    day_plan = content.get("day_plan", [])

    _add_text(slide, "DAY-WISE PLAN",
              0.25, CUR_Y, 3.0, 0.3,
              font_size=12, bold=True,
              color_hex=t["primary"])
    CUR_Y += 0.4

    card_h = 0.85
    for dp in day_plan[:7]:
        day = dp.get("day","Day")
        title = dp.get("title","")
        details = dp.get("details","")

        _shadow_card(slide, 0.25, CUR_Y, W-3.4, card_h)
        _glass_card(slide, 0.25, CUR_Y, W-3.4, card_h)

        badge = _add_rounded_rect(slide, 0.35, CUR_Y+0.18, 0.9, 0.45, t["accent"])
        _add_text_in_shape(badge, day.upper(),
                           font_size=10, bold=True,
                           color_hex="000000")

        _add_text(slide, title,
                  1.3, CUR_Y+0.15, W-4.8, 0.3,
                  font_size=12, bold=True,
                  color_hex=t["primary"])

        _add_text(slide, details,
                  1.3, CUR_Y+0.45, W-4.8, 0.35,
                  font_size=9,
                  color_hex="333333")

        CUR_Y += card_h + 0.12

    # right panel: inclusions + services
    panel_x = W-2.9
    _add_rounded_rect(slide, panel_x, 3.6, 2.6, H-3.85, t["primary2"])
    _set_shape_alpha(slide.shapes[-1], 95000)

    _add_text(slide, "INCLUSIONS",
              panel_x+0.15, 3.75, 2.3, 0.25,
              font_size=11, bold=True,
              color_hex=t.get("text_on_dark","ffffff"))

    y2 = 4.05
    for inc in content.get("inclusions", [])[:7]:
        _add_text(slide, f"✓ {inc}",
                  panel_x+0.15, y2, 2.3, 0.25,
                  font_size=9,
                  color_hex=t.get("text_on_dark","ffffff"))
        y2 += 0.3

    y2 += 0.1
    _add_text(slide, "SERVICES",
              panel_x+0.15, y2, 2.3, 0.25,
              font_size=11, bold=True,
              color_hex=t["accent2"])
    y2 += 0.32

    for s in content.get("services", [])[:6]:
        _add_text(slide, f"• {s}",
                  panel_x+0.15, y2, 2.3, 0.25,
                  font_size=9,
                  color_hex=t.get("text_on_dark","ffffff"))
        y2 += 0.28

    # footer
    _add_rect(slide, 0, H-0.8, W, 0.8, t["dark"])
    _add_text(slide, f"📞 {content.get('phone','')}   🌐 {content.get('website','')}",
              0.25, H-0.62, W-0.5, 0.3,
              font_size=10, bold=True,
              color_hex=t.get("text_on_dark","ffffff"),
              align=PP_ALIGN.CENTER)

    qr = _fetch_qr(content.get("website","www.example.com"), 150)
    if qr:
        _add_picture(slide, qr, W-1.55, H-0.75, 0.7, 0.7)


# ─────────────────────────────────────────────────────────────────────────────
# PREMIUM PPTX BUILDER (3 SLIDES)
# ─────────────────────────────────────────────────────────────────────────────

def build_premium_3slide_pptx(content, theme_name, photos, logo_bytes=None):
    t = THEMES.get(theme_name, THEMES["🏅 Classic Navy Gold"]).copy()

    # AUTO THEME FROM PHOTO
    if photos and len(photos) > 0:
        palette = extract_palette_from_photo(photos[0])
        if palette:
            for k, v in palette.items():
                t[k] = v

    prs = Presentation()

    # ─────────────────────────────────────────
    # SLIDE 1 — A4 FLYER
    # ─────────────────────────────────────────
    prs.slide_width = Inches(SLIDE_W)
    prs.slide_height = Inches(SLIDE_H)
    slide1 = prs.slides.add_slide(prs.slide_layouts[6])
    W = SLIDE_W

    _add_rect(slide1, 0, 0, W, SLIDE_H, "ffffff")

    HERO_H = 3.6

    text_side = "left"
    if photos:
        _add_picture(slide1, photos[0], 0, 0, W, HERO_H)
        text_side = detect_best_text_side(photos[0])

    base_ov = _add_rect(slide1, 0, 0, W, HERO_H, t["dark"])
    _set_shape_alpha(base_ov, 25000)

    if text_side == "left":
        side = _add_rect(slide1, 0, 0, W*0.62, HERO_H, t["dark"])
    else:
        side = _add_rect(slide1, W*0.38, 0, W*0.62, HERO_H, t["dark"])
    _set_shape_alpha(side, 65000)

    ov2 = _add_rect(slide1, 0, HERO_H-1.4, W, 1.4, t["dark"])
    _set_shape_alpha(ov2, 80000)

    # watermark destination
    wm = slide1.shapes.add_textbox(Inches(0.3), Inches(0.7), Inches(W-0.6), Inches(1.1))
    tf = wm.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT if text_side=="left" else PP_ALIGN.RIGHT
    r = p.add_run()
    r.text = content.get("destination","").upper()
    r.font.size = Pt(54)
    r.font.bold = True
    r.font.name = "Aptos Display"
    r.font.color.rgb = _rgb(t["accent2"])
    try:
        r.font.color.brightness = 0.8
    except Exception:
        pass

    if logo_bytes:
        if text_side == "left":
            _add_picture(slide1, logo_bytes, 0.25, 0.2, 1.3, 0.75)
        else:
            _add_picture(slide1, logo_bytes, W-1.55, 0.2, 1.3, 0.75)

    if text_side == "left":
        tx_x = 0.35
        align = PP_ALIGN.LEFT
    else:
        tx_x = W - 4.8
        align = PP_ALIGN.RIGHT

    headline = content.get("headline", "DISCOVER")
    hl_size = _smart_font_size(headline, max_chars=20, base=32, min_size=18)

    _add_text(slide1, headline,
              tx_x, HERO_H-1.35, 4.4, 0.7,
              font_size=hl_size, bold=True,
              color_hex=t.get("text_on_dark","ffffff"),
              font_name="Aptos Display",
              align=align)

    subheadline = content.get("subheadline", "")
    sub_size = _smart_font_size(subheadline, max_chars=50, base=13, min_size=9)

    _add_text(slide1, subheadline,
              tx_x, HERO_H-0.65, 4.4, 0.35,
              font_size=sub_size,
              color_hex=t["accent2"],
              align=align)

    CUR_Y = HERO_H + 0.25

    _shadow_card(slide1, 0.25, CUR_Y, W-0.5, 0.65)
    _glass_card(slide1, 0.25, CUR_Y, W-0.5, 0.65)

    _add_text(slide1, f"⏱ {content.get('duration','')}",
              0.35, CUR_Y+0.15, 3.2, 0.35,
              font_size=12, bold=True,
              color_hex=t["primary"])

    pkg = content.get("package_name", "")
    pkg_size = _smart_font_size(pkg, max_chars=30, base=12, min_size=9)

    _add_text(slide1, pkg,
              W-4.5, CUR_Y+0.15, 4.1, 0.35,
              font_size=pkg_size, bold=True,
              color_hex=t["primary"],
              align=PP_ALIGN.RIGHT)

    CUR_Y += 0.9

    # auto collage (uses photos[1:])
    if len(photos) > 1:
        collage_h = 1.85
        _auto_collage(slide1, photos[1:], 0.25, CUR_Y, W-0.5, collage_h)
        CUR_Y += collage_h + 0.25

    # highlights
    highlights = content.get("highlights", [])
    if highlights:
        _add_text(slide1, "HIGHLIGHTS",
                  0.25, CUR_Y, W-0.5, 0.3,
                  font_size=10, bold=True,
                  color_hex=t["muted"])
        CUR_Y += 0.35

        col_w = (W-0.55)/2
        row_h = 0.5
        for i, hl in enumerate(highlights[:6]):
            col = i % 2
            row = i // 2
            bx = 0.25 + col*(col_w+0.08)
            by = CUR_Y + row*(row_h+0.08)

            _shadow_card(slide1, bx, by, col_w, row_h)
            _glass_card(slide1, bx, by, col_w, row_h)

            bar = _add_rect(slide1, bx, by, 0.07, row_h, t["accent"])
            _set_shape_alpha(bar, 95000)

            hl_size = _smart_font_size(hl, max_chars=20, base=10, min_size=8)

            _add_text(slide1, f"✦ {hl}",
                      bx+0.12, by+0.12, col_w-0.2, 0.3,
                      font_size=hl_size, bold=True,
                      color_hex=t["primary"])
        CUR_Y += 1.8

    # hotels
    CUR_Y = _draw_hotel_cards(slide1, content.get("itinerary", []), t, CUR_Y, W)

    # deal card
    _shadow_card(slide1, 0.25, CUR_Y, W-0.5, 1.35)
    _add_rounded_rect(slide1, 0.25, CUR_Y, W-0.5, 1.35, t["price_bg"])

    price = content.get("price","₹24,999")
    price_size = _smart_font_size(price, max_chars=10, base=40, min_size=22)

    _add_text(slide1, price,
              0.45, CUR_Y+0.35, 4.5, 0.7,
              font_size=price_size, bold=True,
              color_hex="000000",
              font_name="Aptos Display")

    note = content.get("price_note","per person")
    note_size = _smart_font_size(note, max_chars=55, base=9, min_size=7)

    _add_text(slide1, note,
              0.45, CUR_Y+1.05, 4.8, 0.25,
              font_size=note_size, italic=True,
              color_hex="333333")

    sticker = _add_circle(slide1, W-2.1, CUR_Y+0.2, 1.3, t["dark"])
    _add_text_in_shape(sticker, "SAVE\nBIG",
                       font_size=14, bold=True,
                       color_hex=t["accent2"])

    _shadow_card(slide1, W-2.75, CUR_Y+0.72, 2.2, 0.55)
    cta = _add_rounded_rect(slide1, W-2.75, CUR_Y+0.7, 2.2, 0.55, t["dark"])
    _add_text_in_shape(cta, f"{content.get('cta','BOOK NOW')} →",
                       font_size=12, bold=True,
                       color_hex=t["accent2"])

    CUR_Y += 1.55

    # inclusions
    inclusions = content.get("inclusions", [])
    if inclusions:
        incl_h = 1.4
        _add_rect(slide1, 0, CUR_Y, W, incl_h, t["incl_bg"])

        _add_text(slide1, "INCLUSIONS",
                  0.25, CUR_Y+0.1, W-0.5, 0.25,
                  font_size=10, bold=True,
                  color_hex=t["accent2"])

        col_w = (W-0.6)/2
        for i, inc in enumerate(inclusions[:6]):
            col = i % 2
            row = i // 2
            ix = 0.25 + col*col_w
            iy = CUR_Y + 0.4 + row*0.32

            inc_size = _smart_font_size(inc, max_chars=35, base=9, min_size=7)

            _add_text(slide1, f"✓ {inc}",
                      ix, iy, col_w-0.1, 0.28,
                      font_size=inc_size,
                      color_hex=t.get("text_on_dark","ffffff"))

        CUR_Y += incl_h

    footer_h = SLIDE_H - CUR_Y
    _add_rect(slide1, 0, CUR_Y, W, footer_h, t["dark"])

    _add_text(slide1, f"📞 {content.get('phone','')}   🌐 {content.get('website','')}",
              0.25, CUR_Y+0.15, W-0.5, 0.3,
              font_size=10, bold=True,
              color_hex=t.get("text_on_dark","ffffff"),
              align=PP_ALIGN.CENTER)

    qr = _fetch_qr(content.get("website","www.example.com"), 160)
    if qr:
        _add_picture(slide1, qr, W-1.45, CUR_Y+0.15, 1.2, 1.2)

    frame = slide1.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RECTANGLE,
        Inches(0.06), Inches(0.06),
        Inches(W-0.12), Inches(SLIDE_H-0.12)
    )
    frame.fill.background()
    frame.line.color.rgb = _rgb(t["accent"])
    frame.line.width = Pt(2)

    # ─────────────────────────────────────────
    # SLIDE 2 — STORY FORMAT
    # ─────────────────────────────────────────
    prs.slide_width = Inches(STORY_W)
    prs.slide_height = Inches(STORY_H)
    slide2 = prs.slides.add_slide(prs.slide_layouts[6])

    W2 = STORY_W
    H2 = STORY_H

    _add_rect(slide2, 0, 0, W2, H2, "ffffff")

    story_text_side = "left"
    if photos:
        _add_picture(slide2, photos[0], 0, 0, W2, H2*0.55)
        story_text_side = detect_best_text_side(photos[0])

    base_story_ov = _add_rect(slide2, 0, 0, W2, H2*0.55, t["dark"])
    _set_shape_alpha(base_story_ov, 25000)

    if story_text_side == "left":
        story_side = _add_rect(slide2, 0, 0, W2*0.62, H2*0.55, t["dark"])
    else:
        story_side = _add_rect(slide2, W2*0.38, 0, W2*0.62, H2*0.55, t["dark"])
    _set_shape_alpha(story_side, 65000)

    panel_y = H2*0.55
    _add_rect(slide2, 0, panel_y, W2, H2-panel_y, t["primary"])

    # watermark
    wm2 = slide2.shapes.add_textbox(Inches(0.2), Inches(0.8), Inches(W2-0.4), Inches(0.9))
    tf = wm2.text_frame
    tf.clear()
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.LEFT if story_text_side=="left" else PP_ALIGN.RIGHT
    r = p.add_run()
    r.text = content.get("destination","").upper()
    r.font.size = Pt(38)
    r.font.bold = True
    r.font.name = "Aptos Display"
    r.font.color.rgb = _rgb(t["accent2"])

    if logo_bytes:
        if story_text_side == "left":
            _add_picture(slide2, logo_bytes, 0.18, 0.18, 1.2, 0.6)
        else:
            _add_picture(slide2, logo_bytes, W2-1.38, 0.18, 1.2, 0.6)

    badge = _add_rounded_rect(slide2, W2-1.55, 0.2, 1.35, 0.35, t["accent"])
    _add_text_in_shape(badge, content.get("price_label","OFFER"),
                       font_size=8, bold=True,
                       color_hex="000000")

    if story_text_side == "left":
        tx2_x = 0.22
        align2 = PP_ALIGN.LEFT
    else:
        tx2_x = W2-3.2
        align2 = PP_ALIGN.RIGHT

    headline2 = content.get("headline","")
    hl2_size = _smart_font_size(headline2, max_chars=18, base=22, min_size=14)

    _add_text(slide2, headline2,
              tx2_x, H2*0.30, 3.0, 0.9,
              font_size=hl2_size, bold=True,
              color_hex=t.get("text_on_dark","ffffff"),
              font_name="Aptos Display",
              align=align2)

    _add_text(slide2, content.get("subheadline",""),
              tx2_x, H2*0.30+0.75, 3.0, 0.35,
              font_size=10,
              color_hex=t["accent2"],
              align=align2)

    _add_text(slide2, content.get("duration",""),
              0.2, panel_y+0.2, W2-0.4, 0.3,
              font_size=11, bold=True,
              color_hex=t["accent2"],
              align=PP_ALIGN.CENTER)

    CUR2 = panel_y+0.6
    for hl in content.get("highlights", [])[:5]:
        _add_text(slide2, f"✦ {hl}",
                  0.35, CUR2, W2-0.6, 0.28,
                  font_size=10,
                  color_hex=t.get("text_on_dark","ffffff"))
        CUR2 += 0.32

    CUR2 += 0.1
    _add_rect(slide2, 0, CUR2, W2, 0.75, t["price_bg"])

    _add_text(slide2, content.get("price",""),
              0.2, CUR2+0.12, W2-0.4, 0.4,
              font_size=26, bold=True,
              color_hex="000000",
              align=PP_ALIGN.CENTER,
              font_name="Aptos Display")

    _add_text(slide2, content.get("price_note",""),
              0.2, CUR2+0.5, W2-0.4, 0.22,
              font_size=8,
              color_hex="333333",
              align=PP_ALIGN.CENTER)

    CUR2 += 0.9

    _shadow_card(slide2, (W2-2.2)/2, CUR2+0.08, 2.2, 0.55)
    cta2 = _add_rounded_rect(slide2, (W2-2.2)/2, CUR2, 2.2, 0.55, t["dark"])
    _add_text_in_shape(cta2, f"{content.get('cta','BOOK NOW')} →",
                       font_size=12, bold=True,
                       color_hex=t["accent2"])

    CUR2 += 0.75

    _add_text(slide2, f"📞 {content.get('phone','')}",
              0.2, CUR2+0.05, W2-0.4, 0.25,
              font_size=9,
              color_hex=t.get("text_on_dark","ffffff"),
              align=PP_ALIGN.CENTER)

    _add_text(slide2, f"🌐 {content.get('website','')}",
              0.2, CUR2+0.28, W2-0.4, 0.25,
              font_size=9,
              color_hex=t["accent2"],
              align=PP_ALIGN.CENTER)

    # ─────────────────────────────────────────
    # SLIDE 3 — ITINERARY PAGE
    # ─────────────────────────────────────────
    prs.slide_width = Inches(SLIDE_W)
    prs.slide_height = Inches(SLIDE_H)
    slide3 = prs.slides.add_slide(prs.slide_layouts[6])
    _slide3_itinerary(slide3, t, content, photos, logo_bytes, SLIDE_W, SLIDE_H)

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# STREAMLIT UI
# ─────────────────────────────────────────────────────────────────────────────

def render():

    st.title("✈ Premium AI Travel Flyer Generator (PPTX)")
    st.caption("3-slide output: A4 Flyer + Story + Day-wise Itinerary")

    theme_name = st.selectbox("Theme", list(THEMES.keys()))

    free_text = st.text_area(
        "Enter Package Details",
        height=120,
        placeholder="Example: 5N/6D Bhutan, Thimphu 2N, Punakha 1N, Paro 2N, valid till Sep 2026, price 28777"
    )

    logo_up = st.file_uploader("Upload Company Logo (optional)", type=["png","jpg","jpeg"])
    logo_bytes = logo_up.read() if logo_up else None

    photos_input = st.file_uploader(
        "Upload Photos (1-6)",
        type=["jpg","jpeg","png","webp"],
        accept_multiple_files=True
    )

    photos_raw = []
    if photos_input:
        for p in photos_input[:6]:
            p.seek(0)
            photos_raw.append(p.read())

    if st.button("Generate AI Content"):
        with st.spinner("AI writing content..."):
            ai = ai_generate_all(free_text, len(photos_raw))
        st.session_state["ai"] = ai

    ai = st.session_state.get("ai")

    if not ai:
        st.info("Generate AI content first.")
        return

    st.subheader("Edit Generated Copy (Optional)")
    ai["headline"] = st.text_input("Headline", ai.get("headline",""))
    ai["subheadline"] = st.text_input("Subheadline", ai.get("subheadline",""))
    ai["duration"] = st.text_input("Duration", ai.get("duration",""))
    ai["price"] = st.text_input("Price", ai.get("price",""))
    ai["price_note"] = st.text_input("Price Note", ai.get("price_note",""))
    ai["website"] = st.text_input("Website", ai.get("website",""))
    ai["phone"] = st.text_input("Phone", ai.get("phone",""))

    if st.button("🎨 Generate Premium PPTX (3 Slides)", type="primary"):
        with st.spinner("Building PPTX..."):
            pptx_bytes = build_premium_3slide_pptx(
                content=ai,
                theme_name=theme_name,
                photos=photos_raw,
                logo_bytes=logo_bytes
            )

        st.download_button(
            "📥 Download PPTX",
            data=pptx_bytes,
            file_name="premium_flyer_3slides.pptx",
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )


if __name__ == "__main__":
    render()
