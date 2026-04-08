"""
✈ AI Travel Flyer Creator — PPTX Edition (Canva-Ready)
=======================================================
OUTPUT: .pptx file → import directly into Canva → every element is editable

HOW IT WORKS:
  1. Type ONE line (package description + price + duration etc.)
  2. Upload 1-6 travel photos
  3. AI generates ALL content (Groq → Gemini fallback)
  4. python-pptx builds a professional portrait flyer
  5. Download .pptx → drag into Canva → edit anything

WHY PPTX FOR CANVA:
  • Every text box, shape, image, color = individually editable in Canva
  • Fonts, gradients, rounded corners all preserved
  • Better than PNG (not editable) or HTML (Canva can't import)
  • Also opens in PowerPoint / LibreOffice

Add to requirements.txt:  python-pptx>=0.6.21
"""

import streamlit as st
import sys, os, io, json, re, zipfile, base64, requests, math
from urllib.parse import quote as url_quote

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ── python-pptx imports ───────────────────────────────────────────────────────
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
from pptx.oxml.xmlchemy import OxmlElement
from pptx.oxml.ns import qn
from lxml import etree


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

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

def guess_mime(raw: bytes) -> str:
    if raw[:4] == b'\x89PNG':      return "image/png"
    if raw[:3] == b'\xff\xd8\xff': return "image/jpeg"
    return "image/jpeg"

def _rgb(hex_str: str) -> RGBColor:
    h = hex_str.lstrip("#")
    return RGBColor(int(h[0:2],16), int(h[2:4],16), int(h[4:6],16))

def _inches(n): return Inches(n)
def _pt(n):     return Pt(n)


# ─────────────────────────────────────────────────────────────────────────────
# DESIGN THEMES
# ─────────────────────────────────────────────────────────────────────────────

THEMES = {
    "🏅 Classic Navy Gold": {
        "primary":  "1a1a5e", "primary2": "0d2d6b",
        "accent":   "c9a84c", "accent2":  "f0c040",
        "dark":     "0d1035", "light":    "ffffff",
        "text_on_dark": "ffffff", "text_on_light": "1a1a5e",
        "muted":    "8888bb", "price_bg": "c9a84c",
        "hl_bg":    "f4f6ff", "incl_bg":  "0d2d6b",
    },
    "🌿 Emerald Luxury": {
        "primary":  "0a3d2e", "primary2": "0d5540",
        "accent":   "d4a843", "accent2":  "f5c842",
        "dark":     "052a1e", "light":    "ffffff",
        "text_on_dark": "ffffff", "text_on_light": "0a3d2e",
        "muted":    "4a8a6a", "price_bg": "d4a843",
        "hl_bg":    "f0f8f4", "incl_bg":  "0d5540",
    },
    "🌊 Ocean Blue": {
        "primary":  "004e7c", "primary2": "006b9f",
        "accent":   "00c9c8", "accent2":  "40e0d0",
        "dark":     "003055", "light":    "ffffff",
        "text_on_dark": "ffffff", "text_on_light": "004e7c",
        "muted":    "2a6a8a", "price_bg": "009b9a",
        "hl_bg":    "f0faff", "incl_bg":  "006b9f",
    },
    "🌙 Midnight Premium": {
        "primary":  "0a0a2a", "primary2": "1a1a4e",
        "accent":   "d4af37", "accent2":  "ffd700",
        "dark":     "000010", "light":    "ffffff",
        "text_on_dark": "ffffff", "text_on_light": "0a0a2a",
        "muted":    "6a6a9a", "price_bg": "d4af37",
        "hl_bg":    "f0f0fa", "incl_bg":  "1a1a4e",
    },
    "🌺 Coral Vibrant": {
        "primary":  "b03020", "primary2": "d44030",
        "accent":   "f5a623", "accent2":  "ffd050",
        "dark":     "7a1a10", "light":    "ffffff",
        "text_on_dark": "ffffff", "text_on_light": "7a1a10",
        "muted":    "c06050", "price_bg": "f5a623",
        "hl_bg":    "fff5f0", "incl_bg":  "d44030",
    },
}

CERT_NAMES = ["IATA", "OTAI", "ADTOI", "NIMA", "ETAA", "ISO", "TripAdvisor", "Google Rated"]


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
            max_tokens=tokens, temperature=0.75,
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
    body = {"contents":[{"parts":[{"text":prompt}]}],
            "generationConfig":{"maxOutputTokens":tokens,"temperature":0.8,
                                "responseMimeType":"application/json"}}
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
  services (array of 5 services offered by agency),
  hashtags, instagram_caption, facebook_caption, whatsapp_status,
  youtube_title, youtube_desc, reel_script,
  website, phone, email, social_fb, social_ig, social_yt,
  theme (one of: Classic Navy Gold/Emerald Luxury/Ocean Blue/Midnight Premium/Coral Vibrant)
"""
    usr_p = f"Package: \"{free_text}\"\nPhotos: {n_photos}\nGenerate:"
    raw = _llm(sys_p, usr_p, 1200)
    data = _parse_json(raw) if raw else {}
    dest = free_text.split()[0].title() if free_text else "India"
    defaults = {
        "company_name":"Your Travel Company",
        "package_name":f"{dest} Package",
        "destination":dest,
        "headline":f"DISCOVER {dest.upper()}",
        "subheadline":"Unforgettable Journeys | Premium Holiday Deals",
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
        "services":["Tour Packages","Visa Assistance","Hotel Bookings",
                    "Flight Bookings","Travel Insurance"],
        "hashtags":f"#{dest.replace(' ','')} #Travel #TourPackage #India",
        "instagram_caption":f"✈️ {dest} awaits! Book now. #{dest.replace(' ','')} #Travel",
        "facebook_caption":f"Amazing {dest} package available! Contact us.",
        "whatsapp_status":f"✈️ {dest} Package!\n📞 Call to Book!",
        "youtube_title":f"{dest} Travel Package | Best Deals 2026",
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
# PPTX DRAWING HELPERS (PREMIUM)
# ─────────────────────────────────────────────────────────────────────────────

def _set_shape_alpha(shape, alpha=65000):
    """
    alpha: 0 = transparent, 100000 = opaque
    """
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
              font_name="Aptos", wrap=True,
              margin_left=0.08, margin_right=0.08,
              margin_top=0.04, margin_bottom=0.04):
    txBox = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = txBox.text_frame
    tf.word_wrap = wrap
    tf.margin_left   = Inches(margin_left)
    tf.margin_right  = Inches(margin_right)
    tf.margin_top    = Inches(margin_top)
    tf.margin_bottom = Inches(margin_bottom)

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

def _add_picture(slide, img_bytes, x, y, w, h):
    try:
        buf = io.BytesIO(img_bytes)
        return slide.shapes.add_picture(buf, Inches(x), Inches(y), Inches(w), Inches(h))
    except Exception:
        return None

def _send_to_back(slide, shape):
    try:
        slide.shapes._spTree.remove(shape._element)
        slide.shapes._spTree.insert(2, shape._element)
    except Exception:
        pass

def _glass_card(slide, x, y, w, h, alpha=70000):
    card = _add_rounded_rect(slide, x, y, w, h, "ffffff")
    _set_shape_alpha(card, alpha)
    return card

def _shadow_card(slide, x, y, w, h, radius=True):
    shadow = _add_rounded_rect(slide, x+0.04, y+0.05, w, h, "000000")
    _set_shape_alpha(shadow, 22000)
    return shadow

def _add_divider(slide, x, y, w, color_hex="ffffff", alpha=50000):
    d = _add_rect(slide, x, y, w, 0.02, color_hex)
    _set_shape_alpha(d, alpha)

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
# PREMIUM PPTX FLYER BUILDER (A4 POSTER STYLE)
# ─────────────────────────────────────────────────────────────────────────────

SLIDE_W = 8.27
SLIDE_H = 11.69


def build_flyer_pptx(
    content: dict,
    theme_name: str,
    photos: list,
    logo_bytes: bytes | None,
    cert_bytes: bytes | None,
    variant: str = "package",
) -> bytes:

    t = THEMES.get(theme_name, THEMES["🏅 Classic Navy Gold"])
    prs = Presentation()

    prs.slide_width  = Inches(SLIDE_W)
    prs.slide_height = Inches(SLIDE_H)

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    W = SLIDE_W

    # Background
    _add_rect(slide, 0, 0, W, SLIDE_H, "ffffff")

    # ========== HERO PHOTO ==========
    HERO_Y = 0
    HERO_H = 3.6

    if photos:
        pic = _add_picture(slide, photos[0], 0, HERO_Y, W, HERO_H)
        if pic:
            _send_to_back(slide, pic)

    # cinematic overlay
    ov1 = _add_rect(slide, 0, HERO_Y, W, HERO_H, t["dark"])
    _set_shape_alpha(ov1, 25000)

    ov2 = _add_rect(slide, 0, HERO_Y + HERO_H - 1.6, W, 1.6, t["dark"])
    _set_shape_alpha(ov2, 65000)

    # watermark destination big
    _add_text(slide, content.get("destination", "").upper(),
              0.18, HERO_Y + 0.9, W - 0.3, 1.0,
              font_size=52, bold=True, color_hex="ffffff",
              align=PP_ALIGN.LEFT, font_name="Aptos Display")

    # watermark fade look
    try:
        last = slide.shapes[-1]
        _set_shape_alpha(last, 15000)
    except Exception:
        pass

    # logo top-left
    if logo_bytes:
        _add_picture(slide, logo_bytes, 0.25, 0.22, 1.3, 0.72)
    else:
        pill = _glass_card(slide, 0.25, 0.22, 1.4, 0.55, alpha=60000)
        _add_text_in_shape(pill, "✈ TRAVEL", font_size=12, bold=True,
                           color_hex=t["accent2"], align=PP_ALIGN.CENTER)

    # badge top-right
    badge_shadow = _shadow_card(slide, W - 2.05, 0.26, 1.75, 0.5)
    badge = _add_rounded_rect(slide, W - 2.1, 0.22, 1.75, 0.5, t["accent"])
    _add_text_in_shape(badge, content.get("price_label", "SPECIAL OFFER"),
                       font_size=10, bold=True, color_hex="000000")

    # headline
    _add_text(slide, content.get("headline", "DISCOVER"),
              0.25, HERO_Y + HERO_H - 1.35, W - 0.5, 0.7,
              font_size=30, bold=True, color_hex=t["text_on_dark"],
              align=PP_ALIGN.LEFT, font_name="Aptos Display")

    _add_text(slide, content.get("subheadline", ""),
              0.25, HERO_Y + HERO_H - 0.65, W - 0.5, 0.35,
              font_size=12, bold=False, color_hex=t["accent2"],
              align=PP_ALIGN.LEFT, font_name="Aptos")

    CUR_Y = HERO_Y + HERO_H + 0.18

    # ========== DURATION + PACKAGE NAME ==========
    dur = _glass_card(slide, 0.25, CUR_Y, 2.5, 0.55, alpha=65000)
    _add_text_in_shape(dur, f"⏱ {content.get('duration','')}",
                       font_size=12, bold=True,
                       color_hex=t["primary"], align=PP_ALIGN.CENTER)

    pkg = _glass_card(slide, 2.9, CUR_Y, W - 3.15, 0.55, alpha=65000)
    _add_text_in_shape(pkg, content.get("package_name",""),
                       font_size=12, bold=True,
                       color_hex=t["primary"], align=PP_ALIGN.CENTER)

    CUR_Y += 0.7

    # ========== ICON FEATURE STRIP ==========
    features = [
        ("🏨", "Hotels"),
        ("🍽️", "Meals"),
        ("🚗", "Cab"),
        ("🧑‍✈️", "Guide"),
    ]

    strip_shadow = _shadow_card(slide, 0.25, CUR_Y, W - 0.5, 0.8)
    strip = _glass_card(slide, 0.25, CUR_Y, W - 0.5, 0.8, alpha=70000)

    cell_w = (W - 0.5) / 4
    for i,(ic,txt) in enumerate(features):
        x = 0.25 + i*cell_w
        _add_text(slide, ic, x, CUR_Y + 0.05, cell_w, 0.35,
                  font_size=22, bold=True,
                  color_hex="000000", align=PP_ALIGN.CENTER)
        _add_text(slide, txt, x, CUR_Y + 0.45, cell_w, 0.25,
                  font_size=9, bold=True,
                  color_hex=t["primary"], align=PP_ALIGN.CENTER)

    CUR_Y += 1.0

    # ========== ITINERARY (CHIPS STYLE) ==========
    itin = content.get("itinerary", [])
    if itin:
        _add_text(slide, "ITINERARY AT A GLANCE",
                  0.25, CUR_Y, W - 0.5, 0.3,
                  font_size=10, bold=True,
                  color_hex=t["muted"], align=PP_ALIGN.LEFT)

        CUR_Y += 0.35

        chip_y = CUR_Y
        chip_h = 0.55
        gap = 0.12

        max_stops = min(len(itin), 4)
        chip_w = (W - 0.5 - (gap * (max_stops - 1))) / max_stops

        for i, stop in enumerate(itin[:4]):
            cx = 0.25 + i*(chip_w + gap)
            nights = stop.get("nights", "")
            city   = stop.get("city", "")
            hotel  = stop.get("hotel", "")

            shadow = _shadow_card(slide, cx, chip_y, chip_w, chip_h)
            chip = _glass_card(slide, cx, chip_y, chip_w, chip_h, alpha=76000)

            label = f"{nights}N {city}".strip()
            _add_text(slide, label,
                      cx + 0.05, chip_y + 0.07, chip_w - 0.1, 0.25,
                      font_size=10, bold=True,
                      color_hex=t["primary"], align=PP_ALIGN.CENTER)

            if hotel:
                _add_text(slide, hotel[:32],
                          cx + 0.05, chip_y + 0.31, chip_w - 0.1, 0.2,
                          font_size=7.2, italic=True,
                          color_hex=t["muted"], align=PP_ALIGN.CENTER)

        CUR_Y += 0.8

    # ========== PHOTO COLLAGE ==========
    if len(photos) >= 2:
        collage_h = 1.65
        _add_text(slide, "DESTINATION VIBES",
                  0.25, CUR_Y, W - 0.5, 0.25,
                  font_size=10, bold=True,
                  color_hex=t["muted"], align=PP_ALIGN.LEFT)
        CUR_Y += 0.3

        # left big
        _add_picture(slide, photos[1], 0.25, CUR_Y, W*0.58, collage_h)

        if len(photos) >= 3:
            _add_picture(slide, photos[2], W*0.58 + 0.28, CUR_Y, W*0.42 - 0.53, collage_h/2)

        if len(photos) >= 4:
            _add_picture(slide, photos[3], W*0.58 + 0.28, CUR_Y + collage_h/2, W*0.42 - 0.53, collage_h/2)

        CUR_Y += collage_h + 0.25

    # ========== HIGHLIGHTS (GLASS GRID) ==========
    highlights = content.get("highlights", [])
    if highlights:
        _add_text(slide, "HIGHLIGHTS & EXPERIENCES",
                  0.25, CUR_Y, W - 0.5, 0.28,
                  font_size=10, bold=True,
                  color_hex=t["muted"], align=PP_ALIGN.LEFT)

        CUR_Y += 0.32

        col_w = (W - 0.55) / 2
        row_h = 0.48
        for i, hl in enumerate(highlights[:6]):
            col = i % 2
            row = i // 2
            bx  = 0.25 + col * (col_w + 0.08)
            by  = CUR_Y + row * (row_h + 0.08)

            _shadow_card(slide, bx, by, col_w, row_h)
            card = _glass_card(slide, bx, by, col_w, row_h, alpha=75000)

            # accent bar
            bar = _add_rect(slide, bx, by, 0.07, row_h, t["accent"])
            _set_shape_alpha(bar, 90000)

            _add_text(slide, f"  ✦  {hl}",
                      bx + 0.08, by + 0.1, col_w - 0.12, row_h - 0.15,
                      font_size=10, bold=True,
                      color_hex=t["primary"], align=PP_ALIGN.LEFT)

        CUR_Y += 1.7

    # ========== PRICE DEAL CARD ==========
    deal_h = 1.35
    _shadow_card(slide, 0.25, CUR_Y, W - 0.5, deal_h)
    deal = _add_rounded_rect(slide, 0.25, CUR_Y, W - 0.5, deal_h, t["price_bg"])

    _add_text(slide, content.get("price_label", "SPECIAL OFFER"),
              0.45, CUR_Y + 0.18, 2.8, 0.3,
              font_size=11, bold=True,
              color_hex="000000", align=PP_ALIGN.LEFT)

    _add_text(slide, content.get("price", "₹24,999"),
              0.45, CUR_Y + 0.45, 4.5, 0.6,
              font_size=38, bold=True,
              color_hex="000000", align=PP_ALIGN.LEFT,
              font_name="Aptos Display")

    _add_text(slide, content.get("price_note", ""),
              0.45, CUR_Y + 1.05, W - 1.4, 0.25,
              font_size=9, italic=True,
              color_hex="333333", align=PP_ALIGN.LEFT)

    # CTA button
    cta_x = W - 2.35
    cta_y = CUR_Y + 0.45
    _shadow_card(slide, cta_x, cta_y, 1.85, 0.6)
    cta_btn = _add_rounded_rect(slide, cta_x, cta_y, 1.85, 0.6, t["dark"])
    _add_text_in_shape(cta_btn, f"{content.get('cta','BOOK NOW')} →",
                       font_size=12, bold=True,
                       color_hex=t["accent2"], align=PP_ALIGN.CENTER)

    CUR_Y += deal_h + 0.22

    # ========== INCLUSIONS ==========
    inclusions = content.get("inclusions", [])
    if inclusions:
        incl_h = 1.4
        _add_rect(slide, 0, CUR_Y, W, incl_h, t["incl_bg"])
        _set_shape_alpha(slide.shapes[-1], 95000)

        _add_text(slide, "WHAT'S INCLUDED",
                  0.25, CUR_Y + 0.1, W - 0.5, 0.25,
                  font_size=10, bold=True,
                  color_hex=t["accent2"], align=PP_ALIGN.LEFT)

        col_w = (W - 0.6) / 2
        for i, inc in enumerate(inclusions[:6]):
            col = i % 2
            row = i // 2
            ix = 0.25 + col * col_w
            iy = CUR_Y + 0.4 + row * 0.3

            _add_text(slide, f"✓  {inc}",
                      ix, iy, col_w - 0.1, 0.28,
                      font_size=9.5, bold=False,
                      color_hex="ffffff", align=PP_ALIGN.LEFT)

        CUR_Y += incl_h + 0.15

    # ========== SERVICES VARIANT ==========
    if variant == "services":
        services = content.get("services", [])
        if services:
            _add_text(slide, "OUR SERVICES",
                      0.25, CUR_Y, W - 0.5, 0.28,
                      font_size=10, bold=True,
                      color_hex=t["muted"], align=PP_ALIGN.LEFT)
            CUR_Y += 0.35

            svc_icons = ["✈️", "🏨", "🚆", "📋", "🛡️", "🚌"]
            n_svc = min(len(services), 5)
            svc_w = (W - 0.55) / n_svc

            for i, svc in enumerate(services[:5]):
                sx = 0.25 + i * svc_w
                _shadow_card(slide, sx, CUR_Y, svc_w - 0.1, 0.9)
                card = _glass_card(slide, sx, CUR_Y, svc_w - 0.1, 0.9, alpha=78000)

                _add_text(slide, svc_icons[i % len(svc_icons)],
                          sx, CUR_Y + 0.1, svc_w - 0.1, 0.35,
                          font_size=22, align=PP_ALIGN.CENTER,
                          color_hex="000000")
                _add_text(slide, svc,
                          sx + 0.05, CUR_Y + 0.5, svc_w - 0.2, 0.3,
                          font_size=8.2, bold=True,
                          color_hex=t["primary"], align=PP_ALIGN.CENTER)

            CUR_Y += 1.05

    # ========== CERT BAR ==========
    cert_h = 0.62
    _add_rect(slide, 0, CUR_Y, W, cert_h, t["dark"])
    _add_text(slide, "CERTIFICATIONS & TRUSTED MEMBERSHIPS",
              0.25, CUR_Y + 0.05, W - 0.5, 0.2,
              font_size=8, bold=True,
              color_hex=t["accent2"], align=PP_ALIGN.CENTER)

    cert_x = 0.35
    if cert_bytes:
        _add_picture(slide, cert_bytes, cert_x, CUR_Y + 0.28, 0.35, 0.25)
        cert_x += 0.42

    badge_w = 0.75
    gap = 0.06
    for i, nm in enumerate(CERT_NAMES):
        bx = cert_x + i*(badge_w + gap)
        if bx + badge_w > W - 0.2:
            break
        b = _add_rounded_rect(slide, bx, CUR_Y + 0.28, badge_w, 0.26, t["primary2"])
        _add_text_in_shape(b, nm, font_size=7.2, bold=True,
                           color_hex="ffffff", align=PP_ALIGN.CENTER)

    CUR_Y += cert_h

    # ========== SOCIAL STRIP ==========
    soc_h = 0.42
    _add_rect(slide, 0, CUR_Y, W, soc_h, t["primary"])
    social = []
    if content.get("social_fb"): social.append(f"📘 {content['social_fb']}")
    if content.get("social_ig"): social.append(f"📸 {content['social_ig']}")
    if content.get("social_yt"): social.append(f"▶️ {content['social_yt']}")
    _add_text(slide, "   •   ".join(social) if social else "Follow Us",
              0.25, CUR_Y + 0.1, W - 0.5, 0.25,
              font_size=9, bold=True,
              color_hex="ffffff", align=PP_ALIGN.CENTER)
    CUR_Y += soc_h

    # ========== FOOTER CONTACT ==========
    footer_h = SLIDE_H - CUR_Y
    _add_rect(slide, 0, CUR_Y, W, footer_h, t["dark"])

    _add_text(slide, "CONTACT & BOOKINGS",
              0.25, CUR_Y + 0.1, 4.2, 0.25,
              font_size=9, bold=True,
              color_hex=t["accent2"], align=PP_ALIGN.LEFT)

    lines = []
    if content.get("website"): lines.append(f"🌐 {content['website']}")
    if content.get("phone"):   lines.append(f"📞 {content['phone']}")
    if content.get("email"):   lines.append(f"✉️ {content['email']}")

    for i, line in enumerate(lines):
        _add_text(slide, line,
                  0.25, CUR_Y + 0.38 + i*0.22, 4.5, 0.22,
                  font_size=9, color_hex="ffffff",
                  align=PP_ALIGN.LEFT)

    # QR code right
    qr_data = _fetch_qr(content.get("website", "www.yourtravels.com"), size=170)
    if qr_data:
        _add_picture(slide, qr_data, W - 1.4, CUR_Y + 0.12, 1.15, 1.15)
        _add_text(slide, "SCAN TO BOOK",
                  W - 1.5, CUR_Y + 1.25, 1.35, 0.2,
                  font_size=7, bold=True,
                  color_hex=t["accent2"], align=PP_ALIGN.CENTER)

    # Border frame (premium)
    frame = slide.shapes.add_shape(
        MSO_AUTO_SHAPE_TYPE.RECTANGLE,
        Inches(0.06), Inches(0.06),
        Inches(W - 0.12), Inches(SLIDE_H - 0.12)
    )
    frame.fill.background()
    frame.line.color.rgb = _rgb(t["accent"])
    frame.line.width = Pt(2)

    # Save
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# STORY FORMAT (9:16 INSTAGRAM REEL COVER STYLE)
# ─────────────────────────────────────────────────────────────────────────────

STORY_W = 5.4
STORY_H = 9.6


def build_story_pptx(
    content: dict,
    theme_name: str,
    photos: list,
    logo_bytes: bytes | None,
) -> bytes:

    t = THEMES.get(theme_name, THEMES["🏅 Classic Navy Gold"])
    prs = Presentation()
    prs.slide_width  = Inches(STORY_W)
    prs.slide_height = Inches(STORY_H)

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    W = STORY_W

    # background
    _add_rect(slide, 0, 0, W, STORY_H, "ffffff")

    # hero photo
    if photos:
        pic = _add_picture(slide, photos[0], 0, 0, W, STORY_H * 0.58)
        if pic:
            _send_to_back(slide, pic)

    # overlays
    ov = _add_rect(slide, 0, 0, W, STORY_H * 0.58, t["dark"])
    _set_shape_alpha(ov, 25000)

    ov2 = _add_rect(slide, 0, STORY_H * 0.38, W, STORY_H * 0.2, t["dark"])
    _set_shape_alpha(ov2, 65000)

    # logo
    if logo_bytes:
        _add_picture(slide, logo_bytes, 0.22, 0.18, 1.25, 0.62)
    else:
        pill = _glass_card(slide, 0.22, 0.18, 1.35, 0.5, alpha=65000)
        _add_text_in_shape(pill, "✈ TRAVEL", font_size=10, bold=True,
                           color_hex=t["accent2"])

    # offer badge
    badge = _add_rounded_rect(slide, W - 1.65, 0.18, 1.4, 0.42, t["accent"])
    _add_text_in_shape(badge, content.get("price_label","SPECIAL"),
                       font_size=8, bold=True, color_hex="000000")

    # headline
    _add_text(slide, content.get("headline",""),
              0.22, STORY_H * 0.33, W - 0.44, 0.9,
              font_size=24, bold=True,
              color_hex="ffffff", align=PP_ALIGN.LEFT,
              font_name="Aptos Display")

    _add_text(slide, content.get("subheadline",""),
              0.22, STORY_H * 0.43, W - 0.44, 0.3,
              font_size=10, bold=False,
              color_hex=t["accent2"], align=PP_ALIGN.LEFT)

    # bottom panel
    panel_y = STORY_H * 0.58
    _add_rect(slide, 0, panel_y, W, STORY_H - panel_y, t["primary"])

    # duration chip
    chip = _glass_card(slide, 0.22, panel_y + 0.18, W - 0.44, 0.5, alpha=75000)
    _add_text_in_shape(chip, f"⏱ {content.get('duration','')}",
                       font_size=11, bold=True,
                       color_hex=t["primary"], align=PP_ALIGN.CENTER)

    # highlights
    CUR_Y = panel_y + 0.78
    for hl in content.get("highlights", [])[:5]:
        _add_text(slide, f"✦ {hl}",
                  0.3, CUR_Y, W - 0.6, 0.25,
                  font_size=10, bold=True,
                  color_hex="ffffff", align=PP_ALIGN.LEFT)
        CUR_Y += 0.28

    # price strip
    CUR_Y += 0.12
    _shadow_card(slide, 0.22, CUR_Y, W - 0.44, 0.9)
    strip = _add_rounded_rect(slide, 0.22, CUR_Y, W - 0.44, 0.9, t["price_bg"])
    _add_text(slide, content.get("price",""),
              0.25, CUR_Y + 0.15, W - 0.5, 0.5,
              font_size=28, bold=True,
              color_hex="000000", align=PP_ALIGN.CENTER,
              font_name="Aptos Display")

    _add_text(slide, content.get("price_note",""),
              0.25, CUR_Y + 0.62, W - 0.5, 0.25,
              font_size=8, italic=True,
              color_hex="333333", align=PP_ALIGN.CENTER)

    CUR_Y += 1.05

    # CTA
    cta = _add_rounded_rect(slide, 0.85, CUR_Y, W - 1.7, 0.55, t["dark"])
    _add_text_in_shape(cta, f"{content.get('cta','BOOK NOW')} →",
                       font_size=12, bold=True,
                       color_hex=t["accent2"])

    CUR_Y += 0.7

    # contact footer
    _add_text(slide, f"🌐 {content.get('website','')}   📞 {content.get('phone','')}",
              0.22, CUR_Y, W - 0.44, 0.25,
              font_size=8.5, bold=True,
              color_hex="ffffff", align=PP_ALIGN.CENTER)

    _add_text(slide, f"📸 {content.get('social_ig','')}   ▶️ {content.get('social_yt','')}",
              0.22, CUR_Y + 0.25, W - 0.44, 0.25,
              font_size=8, bold=False,
              color_hex=t["accent2"], align=PP_ALIGN.CENTER)

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# PAGE
# ─────────────────────────────────────────────────────────────────────────────

def render():

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=Inter:wght@400;500;600&display=swap');
    .hero { font-family:'Syne',sans-serif;font-size:2.2rem;font-weight:800;
            background:linear-gradient(120deg,#c9a84c,#1a1a5e);
            -webkit-background-clip:text;-webkit-text-fill-color:transparent; }
    .sub  { color:#6b7280;font-size:.9rem;margin-top:2px; }
    .bdg  { display:inline-block;padding:3px 12px;border-radius:20px;
            font-size:.68rem;font-weight:700;letter-spacing:.06em;
            margin-right:6px;margin-bottom:10px; }
    .b1   { background:linear-gradient(135deg,#1a1a5e,#c9a84c);color:#fff; }
    .b2   { background:linear-gradient(135deg,#065f46,#0284c7);color:#fff; }
    .canva-tip { background:#1e293b;border:1px solid #334155;border-radius:8px;
                 padding:10px 14px;font-size:.82rem;color:#94a3b8;margin:8px 0; }
    div[data-testid="stTabs"] button[aria-selected="true"] {
      border-bottom:2px solid #c9a84c !important;color:#c9a84c !important; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<span class="bdg b1">✦ PPTX → CANVA READY</span>'
                '<span class="bdg b2">🤖 ONE-PROMPT AI</span>', unsafe_allow_html=True)
    st.markdown('<div class="hero">✈ AI Travel Flyer Studio</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub">One line → AI generates everything → '
                'Download PPTX → Import to Canva → Edit anything</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="canva-tip">
    📌 <b>How to edit in Canva:</b>
    Download PPTX → Go to <b>canva.com</b> → Click <b>Create a design</b> →
    <b>Import file</b> → Upload your .pptx →
    Every text box, shape, photo & colour becomes individually editable!
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ── BRAND KIT ─────────────────────────────────────────────────────────────
    with st.expander("🏷️ Brand Kit  —  Logo · Cert Badge · Contact Info · API Keys", expanded=False):
        r1, r2, r3 = st.columns(3)
        with r1:
            st.markdown("**🖼️ Company Logo**")
            lu = st.file_uploader("PNG (transparent preferred)",
                                   type=["png","jpg","jpeg"], key="bk_logo")
            if lu:
                lu.seek(0); raw = lu.read()
                st.session_state["brand_logo"] = raw
            if st.session_state.get("brand_logo"):
                st.image(st.session_state["brand_logo"], width=100)
                if st.button("✕ Remove", key="rm_logo"):
                    st.session_state.pop("brand_logo", None)

        with r2:
            st.markdown("**🏅 Cert / Award Badge**")
            cu = st.file_uploader("Badge image", type=["png","jpg","jpeg"], key="bk_cert")
            if cu:
                cu.seek(0); raw = cu.read()
                st.session_state["brand_cert"] = raw
            if st.session_state.get("brand_cert"):
                st.image(st.session_state["brand_cert"], width=75)
                if st.button("✕ Remove", key="rm_cert"):
                    st.session_state.pop("brand_cert", None)

        with r3:
            st.markdown("**🔗 Brand Info**")
            for bk, label, ph in [
                ("bk_company","Company Name","7 Wonders World Travels Pvt Ltd"),
                ("bk_phone",  "Phone",       "+91 97112 81598"),
                ("bk_email",  "Email",        "info@7wwtravels.com"),
                ("bk_website","Website",      "www.7wwtravels.com"),
                ("bk_fb",     "Facebook",     "7wwtravels"),
                ("bk_ig",     "Instagram",    "@7ww_travels"),
                ("bk_yt",     "YouTube",      "@7wwtravels"),
            ]:
                v = st.text_input(label, value=st.session_state.get(bk,""),
                                  placeholder=ph, key=f"_bk_{bk}")
                if v: st.session_state[bk] = v
            if st.button("💾 Save Brand Kit", use_container_width=True):
                st.success("Saved!")

        st.markdown("---")
        k1, k2 = st.columns(2)
        with k1:
            gq = st.text_input("⚡ Groq API Key (free)",
                                type="password",
                                value=st.session_state.get("groq_key",""),
                                placeholder="gsk_xxxxxxxx",
                                help="console.groq.com → API Keys")
            if gq: st.session_state["groq_key"] = gq.strip()
            st.success("✓ Groq active") if _groq_key() else st.info("console.groq.com")
        with k2:
            gm = st.text_input("🔵 Gemini API Key (free fallback)",
                                type="password",
                                value=st.session_state.get("gemini_key",""),
                                placeholder="AIzaSy...",
                                help="aistudio.google.com/app/apikey")
            if gm: st.session_state["gemini_key"] = gm.strip()
            st.success("✓ Gemini active") if _gemini_key() else st.info("aistudio.google.com")

    logo_bytes = st.session_state.get("brand_logo")
    cert_bytes = st.session_state.get("brand_cert")

    st.markdown("---")

    # ── ONE-PROMPT INPUT ──────────────────────────────────────────────────────
    st.markdown("### ✍️ Describe your travel package in one line")
    st.caption("Include: destination · duration · cities · price · inclusions · company · phone · website")

    free_text = st.text_area(
        "", height=90, label_visibility="collapsed",
        placeholder=(
            "5 night 6 day Bhutan trip, 2 nights Thimphu Lhayuel Hotel, "
            "1 night Punakha White Dragon, 2 nights Paro Taktshang Lodge, "
            "Toyota vehicle, breakfast & dinner, guide & sightseeing, "
            "price Rs 28777 per person, min 4 guests, valid till Sep 2026, "
            "company 7 Wonders World Travels, phone 97112 81598, website 7wwtravels.com"
        ),
        key="main_prompt",
    )

    photos_input = st.file_uploader(
        "📸 Upload 1-6 travel photos (embedded in the PPTX flyer)",
        type=["jpg","jpeg","png","webp"],
        accept_multiple_files=True,
        key="main_photos",
    )

    if photos_input:
        names = [p.name for p in photos_input]
        if st.session_state.get("_photo_names") != names:
            cached = []
            for p in photos_input[:6]:
                try:
                    p.seek(0)
                    cached.append(p.read())
                except Exception:
                    pass
            st.session_state["_photos_raw"]  = cached
            st.session_state["_photo_names"] = names

    photos_raw: list = st.session_state.get("_photos_raw", [])

    if photos_raw:
        from PIL import Image as PILImage
        cols = st.columns(min(len(photos_raw), 6))
        for i, raw in enumerate(photos_raw):
            try:
                img = PILImage.open(io.BytesIO(raw))
                scale = 110 / img.width
                thumb = img.resize((110, int(img.height * scale)), PILImage.LANCZOS)
                buf = io.BytesIO()
                thumb.save(buf, format="JPEG", quality=80)
                cols[i].image(buf.getvalue(), use_container_width=True)
            except Exception:
                cols[i].warning(f"Photo {i+1}")

    c1, c2 = st.columns([3,1])
    with c1:
        gen_btn = st.button("🚀 Generate AI Content",
                            type="primary", use_container_width=True,
                            disabled=not free_text.strip())
    with c2:
        if not _llm_ok(): st.warning("Add API key ↑")
        elif not free_text.strip(): st.info("Type package ↑")

    if gen_btn and free_text.strip():
        bk_extra = " ".join([
            f", company: {st.session_state.get('bk_company','')}" if st.session_state.get('bk_company') else "",
            f", phone: {st.session_state.get('bk_phone','')}" if st.session_state.get('bk_phone') else "",
            f", email: {st.session_state.get('bk_email','')}" if st.session_state.get('bk_email') else "",
            f", website: {st.session_state.get('bk_website','')}" if st.session_state.get('bk_website') else "",
            f", facebook: {st.session_state.get('bk_fb','')}" if st.session_state.get('bk_fb') else "",
            f", instagram: {st.session_state.get('bk_ig','')}" if st.session_state.get('bk_ig') else "",
            f", youtube: {st.session_state.get('bk_yt','')}" if st.session_state.get('bk_yt') else "",
        ])
        with st.spinner("🤖 AI generating complete flyer content…"):
            data = ai_generate_all(free_text + bk_extra, len(photos_raw))

        for bk, dk in [("bk_company","company_name"),("bk_phone","phone"),
                       ("bk_email","email"),("bk_website","website"),
                       ("bk_fb","social_fb"),("bk_ig","social_ig"),("bk_yt","social_yt")]:
            v = st.session_state.get(bk,"")
            if v:
                data[dk] = v

        st.session_state["ai_data"] = data
        st.success(f"✅  **{data.get('headline','')}**  ·  "
                   f"Theme: {data.get('theme','')}  ·  Price: {data.get('price','')}")

    ai = st.session_state.get("ai_data", {})
    st.markdown("---")

    tab_flyer, tab_story, tab_copy, tab_bulk = st.tabs([
        "🖼️ Package Flyer (A4)",
        "📱 Story / Reel (9:16)",
        "📋 Social Captions",
        "📦 Bulk Download",
    ])

    # TAB 1
    with tab_flyer:
        if not ai:
            st.info("👆 Type your package description and click **Generate AI Content**.")
        else:
            fl, fr = st.columns([1, 1.2], gap="large")

            with fl:
                st.markdown("### 🎨 Customise")

                theme_keys = list(THEMES.keys())
                ai_theme   = ai.get("theme", "Classic Navy Gold")
                theme_idx  = next((i for i,k in enumerate(theme_keys)
                                   if ai_theme.split()[-1] in k), 0)
                sel_theme  = st.selectbox("Design Theme", theme_keys,
                                           index=theme_idx, key="fl_theme")

                sel_variant = st.selectbox("Layout Variant", [
                    "package", "services"
                ], format_func=lambda x: {
                    "package":  "📦 Tour Package (highlights + price + itinerary)",
                    "services": "🛎️ Services Overview (adds service grid)",
                }.get(x,x), key="fl_var")

                st.markdown("#### 🔧 Edit AI Copy")
                ai["headline"]     = st.text_input("Headline (ALL CAPS)", value=ai.get("headline",""),    key="e_hl")
                ai["subheadline"]  = st.text_input("Subheadline",          value=ai.get("subheadline",""), key="e_sub")
                ai["package_name"] = st.text_input("Package Name",         value=ai.get("package_name",""),key="e_pkg")
                ai["price"]        = st.text_input("Price",                value=ai.get("price",""),       key="e_price")
                ai["price_label"]  = st.text_input("Price Label",          value=ai.get("price_label","SPECIAL OFFER"), key="e_plbl")
                ai["price_note"]   = st.text_input("Price Note",           value=ai.get("price_note",""),  key="e_pnote")
                ai["duration"]     = st.text_input("Duration",             value=ai.get("duration",""),    key="e_dur")
                ai["validity"]     = st.text_input("Validity",             value=ai.get("validity",""),    key="e_val")
                ai["cta"]          = st.text_input("CTA Button",           value=ai.get("cta","BOOK NOW"), key="e_cta")

                hl_raw = st.text_area("Highlights (one per line)",
                    value="\n".join(ai.get("highlights",[])), height=100, key="e_hl_list")
                ai["highlights"] = [l.strip() for l in hl_raw.splitlines() if l.strip()]

                incl_raw = st.text_area("Inclusions (one per line)",
                    value="\n".join(ai.get("inclusions",[])), height=90, key="e_incl")
                ai["inclusions"] = [l.strip() for l in incl_raw.splitlines() if l.strip()]

                render_btn = st.button("🎨 Build PPTX Flyer",
                                        type="primary", use_container_width=True)

            with fr:
                st.markdown("### 📥 Download")

                if render_btn:
                    with st.spinner("Building Premium PPTX flyer…"):
                        try:
                            pptx_bytes = build_flyer_pptx(
                                content=ai,
                                theme_name=sel_theme,
                                photos=photos_raw,
                                logo_bytes=logo_bytes,
                                cert_bytes=cert_bytes,
                                variant=sel_variant,
                            )
                            st.session_state["flyer_pptx"]  = pptx_bytes
                            st.session_state["flyer_name"]  = ai.get("package_name","flyer")
                        except Exception as e:
                            st.error(f"PPTX build error: {e}")

                pptx = st.session_state.get("flyer_pptx")
                if pptx:
                    fname = st.session_state.get("flyer_name","flyer").replace(" ","_")
                    st.download_button(
                        "📥 Download Premium PPTX (Canva / PowerPoint)",
                        data=pptx,
                        file_name=f"{fname}_flyer.pptx",
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        use_container_width=True,
                    )
                    st.success(f"✅ {len(pptx)//1024} KB PPTX ready!")

    # TAB 2
    with tab_story:
        if not ai:
            st.info("👆 Generate content first.")
        else:
            sl, sr = st.columns([1,1.2], gap="large")
            with sl:
                st.markdown("### 📱 Story / Reel Format (9:16)")
                story_theme = st.selectbox("Theme", list(THEMES.keys()),
                    index=next((i for i,k in enumerate(THEMES)
                                if ai.get("theme","").split()[-1] in k), 0),
                    key="st_theme")
                story_btn = st.button("📱 Build Premium Story PPTX",
                                       type="primary", use_container_width=True)

            with sr:
                st.markdown("### 📥 Download")
                if story_btn:
                    with st.spinner("Building story PPTX…"):
                        try:
                            story_pptx = build_story_pptx(
                                content=ai, theme_name=story_theme,
                                photos=photos_raw, logo_bytes=logo_bytes,
                            )
                            st.session_state["story_pptx"] = story_pptx
                        except Exception as e:
                            st.error(f"Build error: {e}")

                sp = st.session_state.get("story_pptx")
                if sp:
                    fname = ai.get("package_name","story").replace(" ","_")
                    st.download_button(
                        "📥 Download Premium Story PPTX",
                        data=sp,
                        file_name=f"{fname}_story.pptx",
                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                        use_container_width=True,
                    )
                    st.success(f"✅ {len(sp)//1024} KB ready! Import to Canva and export 1080×1920.")

    # TAB 3
    with tab_copy:
        if not ai:
            st.info("👆 Generate content first.")
        else:
            st.markdown("### 📋 AI-Generated Copy")
            pairs = [
                ("📸 Instagram Caption",  "instagram_caption"),
                ("👥 Facebook Caption",   "facebook_caption"),
                ("📱 WhatsApp Status",    "whatsapp_status"),
                ("📺 YouTube Title",      "youtube_title"),
                ("📺 YouTube Description","youtube_desc"),
                ("🎬 30-sec Reel Script", "reel_script"),
                ("🔖 Hashtags",           "hashtags"),
            ]
            for label,key in pairs:
                val = ai.get(key,"")
                if val:
                    st.markdown(f"**{label}**")
                    st.text_area("", value=val, height=120,
                                 key=f"cp_{key}", label_visibility="collapsed")

    # TAB 4
    with tab_bulk:
        if not ai:
            st.info("👆 Generate content first.")
        else:
            st.markdown("### 📦 Bulk — All Themes × All Formats in One ZIP")

            bl, br = st.columns([1,1])
            with bl:
                bulk_themes  = st.multiselect("Themes", list(THEMES.keys()),
                                               default=list(THEMES.keys())[:2])
                bulk_formats = st.multiselect("Formats",
                    ["A4 Flyer (package)","A4 Flyer (services)","Story 9:16"],
                    default=["A4 Flyer (package)","Story 9:16"])
                bulk_btn = st.button("📦 Generate ZIP",
                                      type="primary", use_container_width=True,
                                      disabled=not (bulk_themes and bulk_formats))

            with br:
                if bulk_btn and bulk_themes and bulk_formats:
                    zbuf = io.BytesIO()
                    total = len(bulk_themes) * len(bulk_formats)
                    prog  = st.progress(0,"Generating…")
                    done  = 0

                    with zipfile.ZipFile(zbuf,"w",zipfile.ZIP_DEFLATED) as zf:
                        for theme in bulk_themes:
                            tshort = theme.split()[-1].replace("/","").replace(":","")
                            for fmt in bulk_formats:
                                fname_base = f"{ai.get('package_name','flyer').replace(' ','_')}_{tshort}"
                                try:
                                    if "A4 Flyer (package)" == fmt:
                                        data = build_flyer_pptx(ai, theme, photos_raw,
                                                                 logo_bytes, cert_bytes, "package")
                                        zf.writestr(f"{fname_base}_A4_package.pptx", data)
                                    elif "A4 Flyer (services)" == fmt:
                                        data = build_flyer_pptx(ai, theme, photos_raw,
                                                                 logo_bytes, cert_bytes, "services")
                                        zf.writestr(f"{fname_base}_A4_services.pptx", data)
                                    elif "Story 9:16" == fmt:
                                        data = build_story_pptx(ai, theme, photos_raw, logo_bytes)
                                        zf.writestr(f"{fname_base}_story.pptx", data)
                                except Exception as e:
                                    st.warning(f"Skipped {fmt}/{theme}: {e}")
                                done += 1
                                prog.progress(done/total, text=f"{tshort} {fmt}…")

                    prog.empty()
                    zbuf.seek(0)
                    st.success(f"✅ {done} PPTX files in ZIP!")
                    st.download_button(
                        "📥 Download ZIP",
                        data=zbuf.getvalue(),
                        file_name=f"{ai.get('package_name','flyers').replace(' ','_')}_all.zip",
                        mime="application/zip",
                        use_container_width=True,
                    )


# if running directly
if __name__ == "__main__":
    render()
