import streamlit as st
import sys, os, io, zipfile, base64, json, re
import requests
from PIL import Image, ImageDraw, ImageFont

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ─────────────────────────────────────────────────────────────────────────────
# PLATFORM SIZES
# ─────────────────────────────────────────────────────────────────────────────
SIZES = {
    "YouTube Thumbnail (1280×720)":         (1280, 720),
    "YouTube Shorts / Reels (1080×1920)":   (1080, 1920),
    "Instagram Post Square (1080×1080)":    (1080, 1080),
    "Instagram Story (1080×1920)":          (1080, 1920),
    "Facebook Post (1200×630)":             (1200, 630),
    "Facebook Cover (820×312)":             (820, 312),
    "Twitter/X Post (1200×675)":            (1200, 675),
    "LinkedIn Banner (1584×396)":           (1584, 396),
    "WhatsApp Status (1080×1920)":          (1080, 1920),
}

# ─────────────────────────────────────────────────────────────────────────────
# TRAVEL THEMES
# ─────────────────────────────────────────────────────────────────────────────
THEMES = {
    "🌅 Sunset Gold":    {"overlay": (160, 60, 10, 165),  "accent": (255, 195, 40),  "text": (255,255,255), "grad": ((180,80,20),(60,20,5))},
    "🌊 Ocean Blue":     {"overlay": (8,  50, 110, 165),  "accent": (0,  210, 230),  "text": (255,255,255), "grad": ((10,60,120),(5,20,60))},
    "🌿 Jungle Green":   {"overlay": (15, 70, 35, 165),   "accent": (90, 220, 90),   "text": (255,255,255), "grad": ((20,80,40),(5,30,10))},
    "🏜️ Desert Sand":   {"overlay": (130, 90, 30, 158),  "accent": (255, 175, 50),  "text": (255,255,255), "grad": ((160,110,50),(80,50,10))},
    "❄️ Arctic White":   {"overlay": (25, 55, 110, 145),  "accent": (170, 225, 255), "text": (255,255,255), "grad": ((30,60,120),(10,30,80))},
    "🌸 Cherry Blossom": {"overlay": (150, 30, 70, 152),  "accent": (255, 175, 195), "text": (255,255,255), "grad": ((160,40,80),(70,10,40))},
    "🖤 Dark Luxury":    {"overlay": (8,  8,  18, 195),   "accent": (215, 175, 70),  "text": (255,255,255), "grad": ((15,15,35),(5,5,15))},
    "🌙 Midnight Blue":  {"overlay": (12, 12, 55, 185),   "accent": (95, 145, 255),  "text": (255,255,255), "grad": ((15,15,60),(5,5,30))},
    "☀️ Bright Summer":  {"overlay": (190,110, 0, 145),   "accent": (255, 235, 70),  "text": (255,255,255), "grad": ((200,120,0),(100,60,0))},
    "🪷 Lavender Dusk":  {"overlay": (70, 30, 110, 160),  "accent": (210, 170, 255), "text": (255,255,255), "grad": ((80,40,120),(30,10,60))},
}

# ─────────────────────────────────────────────────────────────────────────────
# GEMINI FREE API
# Model: gemini-2.5-flash  |  Free: 250 req/day, no credit card
# Get key: https://aistudio.google.com/app/apikey
# ─────────────────────────────────────────────────────────────────────────────

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_URL   = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"


def _get_gemini_key() -> str:
    try:
        return "AIzaSyDikfywYg9dySOzqszkNvymIGi0TuhqAxU"
    except Exception:
        return os.environ.get("GEMINI_API_KEY", "")


def call_gemini(prompt: str, max_tokens: int = 900) -> str:
    api_key = _get_gemini_key()
    if not api_key:
        return ""
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 2048, "temperature": 0.85},
    }
    try:
        r = requests.post(GEMINI_URL, params={"key": api_key}, json=body, timeout=30)
        st.write("Status Code:", r.status_code)
        st.write("Response:", r.text)
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        st.error(f"Gemini API error: {e}")
        return ""


def _parse_json(raw: str):
    clean = re.sub(r"```(?:json)?|```", "", raw).strip()
    start = min(
        (clean.find("{") if "{" in clean else len(clean)),
        (clean.find("[") if "[" in clean else len(clean)),
    )
    return json.loads(clean[start:])


def ai_generate_content(destination, package_type, duration, extra) -> dict:
    prompt = f"""You are a top travel marketing copywriter for Indian travel agencies.
Destination: {destination}
Package type: {package_type}
Duration: {duration}
Extra details: {extra or 'none'}

Return ONLY a valid JSON object (no markdown, no preamble) with these exact keys:
- title           (catchy 4-7 word headline with 1-2 emojis)
- subtitle        (subheadline with 3 aspects separated by ·)
- package_name    (short label e.g. "Golden Triangle 7D/6N")
- price_hint      (price string e.g. "₹24,999/person")
- cta             (call to action e.g. "Book Now →")
- highlights      (JSON array of exactly 5 short sight/activity strings)
- youtube_title   (YouTube video title with emojis)
- instagram_caption (Instagram caption with emojis and hashtags, 4-5 lines)
- facebook_caption  (Facebook post caption, 3-4 lines)
- whatsapp_status   (WhatsApp status, max 2 lines)
- short_video_script (3 punchy sentences for a 30-second Reel voiceover)
"""
    raw = call_gemini(prompt, max_tokens=2048)
    if not raw:
        return {}
    try:
        return _parse_json(raw)
    except Exception:
        return {}


def ai_generate_video_captions(destination, highlights, num_slides) -> list:
    prompt = f"""You are a travel video scriptwriter.
Destination: {destination}
Highlights: {', '.join(highlights) if highlights else 'general sightseeing'}
Generate exactly {num_slides} punchy slide captions (max 6 words each, include 1 emoji per caption).
Return ONLY a JSON array of strings. No explanation, no markdown."""
    raw = call_gemini(prompt, max_tokens=2048)
    if not raw:
        return [f"✨ Slide {i+1}" for i in range(num_slides)]
    try:
        data = _parse_json(raw)
        return [str(c) for c in data[:num_slides]]
    except Exception:
        return [f"🌏 Discover {destination}" for _ in range(num_slides)]


# ─────────────────────────────────────────────────────────────────────────────
# FONT HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _font(size: int, bold: bool = False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf" if bold else
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


# ─────────────────────────────────────────────────────────────────────────────
# IMAGE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _load_bg(f, w, h):
    img = Image.open(f).convert("RGBA")
    ratio = max(w / img.width, h / img.height)
    nw, nh = int(img.width * ratio), int(img.height * ratio)
    img = img.resize((nw, nh), Image.LANCZOS)
    l = (nw - w) // 2; t = (nh - h) // 2
    return img.crop((l, t, l + w, t + h))


def _gradient_bg(w, h, c1, c2):
    img = Image.new("RGBA", (w, h))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        draw.line([(0, y), (w, y)], fill=(
            int(c1[0]+(c2[0]-c1[0])*t),
            int(c1[1]+(c2[1]-c1[1])*t),
            int(c1[2]+(c2[2]-c1[2])*t), 255))
    return img


def _overlay(img, colour):
    ov = Image.new("RGBA", img.size, colour)
    return Image.alpha_composite(img.convert("RGBA"), ov)


def _wrap(text, font, max_w, draw):
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


def _shadow(draw, pos, text, font, fill, s=3):
    draw.text((pos[0]+s, pos[1]+s), text, font=font, fill=(0,0,0,175))
    draw.text(pos, text, font=font, fill=fill)


def _pill(draw, x, y, text, font, bg, fg, pad=12):
    bb = draw.textbbox((0,0), text, font=font)
    tw, th = bb[2]-bb[0], bb[3]-bb[1]
    draw.rounded_rectangle([x, y, x+tw+pad*2, y+th+pad], radius=(th+pad)//2, fill=bg)
    draw.text((x+pad, y+pad//2), text, font=font, fill=fg)
    return x+tw+pad*2


def _social_bar(draw, w, h, fb, insta, web, accent, font):
    by = h - 48
    draw.rectangle([0, by, w, h], fill=(0,0,0,165))
    items = []
    if fb:    items.append(f"f/ {fb}")
    if insta: items.append(f"@ {insta}")
    if web:   items.append(f"🌐 {web}")
    if not items: return
    full = "   •   ".join(items)
    bb = draw.textbbox((0,0), full, font=font)
    tw = bb[2]-bb[0]
    draw.text(((w-tw)//2, by+(48-(bb[3]-bb[1]))//2), full, font=font, fill=accent+(255,))


def _paste_logo(canvas, logo_file, position, max_size=120):
    logo = Image.open(logo_file).convert("RGBA")
    ratio = min(max_size/logo.width, max_size/logo.height)
    nw, nh = int(logo.width*ratio), int(logo.height*ratio)
    logo = logo.resize((nw, nh), Image.LANCZOS)
    W, H = canvas.size; m = 20
    pos_map = {"Top Left":(m,m),"Top Right":(W-nw-m,m),
               "Bottom Left":(m,H-nh-m-52),"Bottom Right":(W-nw-m,H-nh-m-52)}
    x, y = pos_map.get(position, pos_map["Top Right"])
    canvas.paste(logo, (x, y), logo)
    return canvas


def _paste_cert(canvas, cert_file, max_size=90):
    badge = Image.open(cert_file).convert("RGBA")
    ratio = min(max_size/badge.width, max_size/badge.height)
    nw, nh = int(badge.width*ratio), int(badge.height*ratio)
    badge = badge.resize((nw, nh), Image.LANCZOS)
    W, H = canvas.size
    canvas.paste(badge, (20, H-nh-20-52), badge)
    return canvas


# ─────────────────────────────────────────────────────────────────────────────
# MAIN BANNER RENDERER
# ─────────────────────────────────────────────────────────────────────────────

def generate_banner(w, h, theme, bg_image=None, title="", subtitle="",
                    package_name="", price="", highlights=None, cta="",
                    fb="", insta="", website="",
                    logo_file=None, logo_pos="Top Right", cert_file=None,
                    slide_caption="", slide_num=None) -> Image.Image:

    highlights = highlights or []
    canvas = _load_bg(bg_image, w, h) if bg_image else \
             _gradient_bg(w, h, theme["grad"][0], theme["grad"][1])
    canvas = _overlay(canvas.convert("RGBA"), theme["overlay"])
    draw   = ImageDraw.Draw(canvas)
    accent = theme["accent"]; white = theme["text"]
    scale  = min(w, h) / 1080

    f_title = _font(int(72*scale), bold=True)
    f_sub   = _font(int(40*scale))
    f_price = _font(int(60*scale), bold=True)
    f_hl    = _font(int(30*scale))
    f_cta   = _font(int(38*scale), bold=True)
    f_sm    = _font(int(24*scale))
    f_slide = _font(int(52*scale), bold=True)
    f_num   = _font(int(22*scale))

    margin = int(60*scale); max_w = w - margin*2; cy = int(55*scale)

    # VIDEO SLIDE MODE
    if slide_caption:
        if slide_num:
            nb = draw.textbbox((0,0), slide_num, font=f_num)
            draw.text((w-margin-(nb[2]-nb[0]), int(28*scale)), slide_num,
                      font=f_num, fill=accent+(200,))
        wrapped = _wrap(slide_caption, f_slide, max_w, draw)
        bb = draw.multiline_textbbox((0,0), wrapped, font=f_slide)
        tx = (w-(bb[2]-bb[0]))//2; ty = (h-(bb[3]-bb[1]))//2 - int(20*scale)
        _shadow(draw, (tx, ty), wrapped, f_slide, white+(255,), s=4)
        if package_name:
            pb = draw.textbbox((0,0), package_name, font=f_sm)
            px = (w-(pb[2]-pb[0])-28)//2
            _pill(draw, px, h-int(110*scale), package_name, f_sm,
                  accent+(210,), (15,15,15,255), pad=14)
    else:
        # NORMAL BANNER
        if package_name:
            _pill(draw, margin, cy, f"✈  {package_name.upper()}",
                  f_sm, accent+(215,), (15,15,15,255), pad=14)
            cy += int(55*scale)
            draw.rectangle([margin, cy, margin+int(90*scale), cy+4], fill=accent+(255,))
            cy += int(20*scale)

        if title:
            wrapped = _wrap(title, f_title, max_w, draw)
            _shadow(draw, (margin, cy), wrapped, f_title, white+(255,))
            bb = draw.multiline_textbbox((margin, cy), wrapped, font=f_title)
            cy += (bb[3]-bb[1]) + int(14*scale)

        if subtitle:
            wrapped = _wrap(subtitle, f_sub, max_w, draw)
            _shadow(draw, (margin, cy), wrapped, f_sub, accent+(255,))
            bb = draw.multiline_textbbox((margin, cy), wrapped, font=f_sub)
            cy += (bb[3]-bb[1]) + int(28*scale)

        for hl in highlights[:6]:
            line = f"  ✓  {hl}"
            _shadow(draw, (margin, cy), line, f_hl, white+(225,))
            bb = draw.textbbox((margin, cy), line, font=f_hl)
            cy += (bb[3]-bb[1]) + int(8*scale)
        if highlights: cy += int(18*scale)

        if price:
            _shadow(draw, (margin, cy), f"From  {price}", f_price, accent+(255,))
            bb = draw.textbbox((margin, cy), f"From  {price}", font=f_price)
            cy += (bb[3]-bb[1]) + int(22*scale)

        if cta:
            _pill(draw, margin, cy, f"  {cta}  ", f_cta, accent+(230,), (15,15,15,255), pad=18)

    _social_bar(draw, w, h, fb, insta, website, accent, f_sm)
    if logo_file:
        canvas = _paste_logo(canvas, logo_file, logo_pos, max_size=int(130*scale))
    if cert_file:
        canvas = _paste_cert(canvas, cert_file, max_size=int(90*scale))

    return canvas.convert("RGB")


def img_to_bytes(img, fmt="PNG") -> bytes:
    buf = io.BytesIO(); img.save(buf, format=fmt, quality=95); return buf.getvalue()


def make_gif(frames, ms=2000) -> bytes:
    buf = io.BytesIO()
    frames[0].save(buf, format="GIF", save_all=True,
                   append_images=frames[1:], duration=ms, loop=0, optimize=True)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# PAGE
# ─────────────────────────────────────────────────────────────────────────────

def render():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=Inter:wght@400;500;600&display=swap');
    .hero-header {
        font-family:'Syne',sans-serif; font-size:2.4rem; font-weight:800;
        background:linear-gradient(135deg,#f59e0b,#ef4444,#8b5cf6);
        -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin-bottom:0;
    }
    .hero-sub { font-family:'Inter',sans-serif; color:#94a3b8; font-size:1rem; margin-top:4px; }
    .ai-badge {
        display:inline-block; background:linear-gradient(135deg,#16a34a,#0284c7);
        color:white; border-radius:20px; padding:3px 14px;
        font-size:.75rem; font-weight:600; letter-spacing:.05em; margin-bottom:12px;
    }
    .copy-box {
        background:#1e293b; border:1px solid #334155; border-radius:10px;
        padding:14px 18px; font-family:'Inter',sans-serif; font-size:.85rem;
        color:#e2e8f0; line-height:1.6; white-space:pre-wrap;
    }
    .copy-label { font-size:.7rem; font-weight:600; letter-spacing:.08em;
                  color:#64748b; text-transform:uppercase; margin-bottom:4px; }
    .empty-state { border:1px dashed #334155; border-radius:14px;
                   padding:70px 20px; text-align:center; }
    .empty-icon { font-size:3rem; }
    .empty-text { color:#64748b; margin-top:10px; font-size:.9rem; }
    .key-info { background:#0f2027; border:1px solid #22c55e44;
                border-radius:10px; padding:14px 18px; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="ai-badge">✦ GEMINI AI — 100% FREE</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="hero-header">✈ Travel Content Studio</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="hero-sub">Describe your travel package → Gemini AI writes all copy → '
        'renders banners & video slideshows for every platform. Completely free.</p>',
        unsafe_allow_html=True
    )

    has_key = bool(_get_gemini_key())
    if not has_key:
        with st.expander("🔑 Set up your FREE Gemini API key — takes 2 minutes", expanded=True):
            st.markdown("""
            <div class="key-info">
            <b>Steps to get your free key:</b><br><br>
            1️⃣ &nbsp;Go to <a href="https://aistudio.google.com/app/apikey" target="_blank">
               <b>aistudio.google.com/app/apikey</b></a><br>
            2️⃣ &nbsp;Sign in with any Google account<br>
            3️⃣ &nbsp;Click <b>"Create API key"</b> and copy it<br>
            4️⃣ &nbsp;Add to <code>.streamlit/secrets.toml</code>:<br>
            &nbsp;&nbsp;&nbsp;&nbsp;<code>GEMINI_API_KEY = "AIzaSy..."</code><br><br>
            ✅ <b>Free tier:</b> 250 requests/day &nbsp;|&nbsp; No credit card &nbsp;|&nbsp; No billing
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("✅ Gemini API key found — AI features are active!")

    st.markdown("---")

    tab_ai, tab_banner, tab_video, tab_bulk = st.tabs([
        "🤖 AI Copy Generator",
        "🖼️ Banner Builder",
        "🎬 Video Slideshow",
        "📦 Bulk Export",
    ])

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 1 — AI COPY GENERATOR
    # ═══════════════════════════════════════════════════════════════════════
    with tab_ai:
        st.markdown("### 🤖 AI Travel Copy Generator")
        st.caption("Powered by Google Gemini 2.5 Flash — free tier, 250 requests/day, no card needed.")

        col_l, col_r = st.columns([1, 1], gap="large")

        with col_l:
            destination  = st.text_input("🗺️ Destination", placeholder="Rajasthan, India")
            package_type = st.selectbox("🏷️ Package Type", [
                "Cultural & Heritage Tour", "Beach & Relaxation",
                "Adventure & Trekking", "Wildlife Safari",
                "Honeymoon Package", "Family Holiday",
                "Pilgrimage / Religious Tour", "Luxury Getaway",
                "Budget Backpacker", "Corporate / MICE",
            ])
            duration = st.text_input("📅 Duration", placeholder="7 Nights / 8 Days")
            extra    = st.text_area("💬 Package highlights / extra details",
                                    placeholder="Desert safari, camel ride, folk dinner, "
                                                "Jaipur city tour, Udaipur lake cruise...",
                                    height=110)
            gen_copy = st.button("✨ Generate AI Copy", type="primary",
                                  use_container_width=True,
                                  disabled=not (has_key and destination.strip()))
            if not has_key:
                st.caption("⚠️ Add your free Gemini key above to enable AI generation.")

        with col_r:
            if gen_copy:
                with st.spinner("Gemini is writing your travel copy… ✍️"):
                    result = ai_generate_content(destination, package_type, duration, extra)
                if result:
                    st.session_state["ai_copy"] = result
                    st.session_state["ai_dest"] = destination
                    st.success("✅ Copy ready! Switch to Banner Builder to render it.")
                else:
                    st.error("Empty response. Check your API key or try again.")

            ai = st.session_state.get("ai_copy", {})

            if ai:
                def _box(label, val):
                    if val:
                        st.markdown(f'<div class="copy-label">{label}</div>', unsafe_allow_html=True)
                        st.markdown(f'<div class="copy-box">{val}</div>', unsafe_allow_html=True)
                        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

                _box("HEADLINE / TITLE", ai.get("title",""))
                _box("SUBTITLE", ai.get("subtitle",""))
                _box("PACKAGE NAME", ai.get("package_name",""))
                _box("PRICE HINT", ai.get("price_hint",""))
                _box("CALL TO ACTION", ai.get("cta",""))
                hl = ai.get("highlights",[])
                if hl: _box("SIGHTS & HIGHLIGHTS", "\n".join(f"• {h}" for h in hl))
                st.markdown("---")
                _box("📺 YouTube Title", ai.get("youtube_title",""))
                _box("📸 Instagram Caption", ai.get("instagram_caption",""))
                _box("👥 Facebook Caption", ai.get("facebook_caption",""))
                _box("📱 WhatsApp Status", ai.get("whatsapp_status",""))
                _box("🎬 30-sec Reel Script", ai.get("short_video_script",""))
                st.info("👉 Go to **Banner Builder** tab — all fields auto-fill from AI output!")
            else:
                st.markdown("""
                <div class="empty-state">
                    <div class="empty-icon">🤖</div>
                    <div class="empty-text">Enter destination details<br>and click Generate AI Copy</div>
                </div>""", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 2 — BANNER BUILDER
    # ═══════════════════════════════════════════════════════════════════════
    with tab_banner:
        ai = st.session_state.get("ai_copy", {})
        col_f, col_p = st.columns([1, 1], gap="large")

        with col_f:
            st.markdown("### 📐 Format & Style")
            size_name  = st.selectbox("Platform & Size", list(SIZES.keys()))
            theme_name = st.selectbox("Theme / Colour", list(THEMES.keys()))

            st.markdown("### 🖼️ Background Photo")
            bg_file = st.file_uploader("Upload photo (landscape / beach / monument...)",
                                        type=["jpg","jpeg","png","webp"], key="bg_single")
            st.caption("No photo? A beautiful gradient is used automatically.")

            st.markdown("### ✍️ Content")
            use_ai = bool(ai) and st.checkbox("⚡ Auto-fill from AI output", value=bool(ai))

            package_name = st.text_input("Package Name",
                value=ai.get("package_name","") if use_ai else "",
                placeholder="Golden Triangle — 7 Days")
            title = st.text_input("Headline",
                value=ai.get("title","") if use_ai else "",
                placeholder="Discover Incredible India")
            subtitle = st.text_input("Subheadline",
                value=ai.get("subtitle","") if use_ai else "",
                placeholder="Sightseeing · Culture · Adventure")
            price = st.text_input("Price",
                value=ai.get("price_hint","") if use_ai else "",
                placeholder="₹24,999 / person")
            cta = st.text_input("Call to Action",
                value=ai.get("cta","Book Now →") if use_ai else "Book Now →")

            st.markdown("### 📍 Highlights")
            default_hl = "\n".join(ai.get("highlights",[])) if use_ai else ""
            hl_raw = st.text_area("One per line (shown as ✓)", value=default_hl, height=110,
                                   placeholder="Taj Mahal Sunrise\nDesert Safari\nBackwaters")
            highlights = [h.strip() for h in hl_raw.strip().splitlines() if h.strip()]

            st.markdown("### 🔗 Social Links")
            c1, c2 = st.columns(2)
            with c1: fb    = st.text_input("Facebook", placeholder="YourTravelPage")
            with c2: insta = st.text_input("Instagram", placeholder="@yourtravel")
            website = st.text_input("Website", placeholder="www.yourtravel.com")

            st.markdown("### 🏷️ Logo & Certification")
            logo_file = st.file_uploader("Company Logo (PNG preferred)",
                                          type=["png","jpg","jpeg"], key="logo_single")
            logo_pos  = st.radio("Logo position",
                                  ["Top Right","Top Left","Bottom Right","Bottom Left"],
                                  horizontal=True)
            cert_file = st.file_uploader("Certification Badge (optional)",
                                          type=["png","jpg","jpeg"], key="cert_single")

            gen_btn = st.button("🎨 Generate Banner", type="primary", use_container_width=True)

        with col_p:
            st.markdown("### 👁️ Preview")
            if gen_btn or st.session_state.get("banner_generated"):
                if gen_btn:
                    w, h = SIZES[size_name]
                    img  = generate_banner(
                        w=w, h=h, theme=THEMES[theme_name], bg_image=bg_file,
                        title=title, subtitle=subtitle, package_name=package_name,
                        price=price, highlights=highlights, cta=cta,
                        fb=fb, insta=insta, website=website,
                        logo_file=logo_file, logo_pos=logo_pos, cert_file=cert_file,
                    )
                    st.session_state["last_banner"]      = img_to_bytes(img)
                    st.session_state["last_banner_name"] = f"{package_name or 'banner'}_{size_name[:15]}.png"
                    st.session_state["banner_generated"] = True

                bb = st.session_state.get("last_banner")
                if bb:
                    st.image(bb, use_container_width=True)
                    st.download_button("📥 Download PNG", data=bb,
                        file_name=st.session_state.get("last_banner_name","banner.png"),
                        mime="image/png", use_container_width=True)
                    st.success("✅ Ready to post!")
            else:
                st.markdown("""
                <div class="empty-state">
                    <div class="empty-icon">🖼️</div>
                    <div class="empty-text">Fill in details & click Generate Banner</div>
                </div>""", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 3 — VIDEO SLIDESHOW
    # ═══════════════════════════════════════════════════════════════════════
    with tab_video:
        st.markdown("### 🎬 AI-Captioned Video Slideshow")
        st.info(
            "Upload travel photos → Gemini AI writes a caption per slide → "
            "generates an animated GIF with your branding. "
            "Import into CapCut / InShot to add music & export MP4."
        )

        ai = st.session_state.get("ai_copy", {})
        col_vl, col_vr = st.columns([1, 1], gap="large")

        with col_vl:
            slide_imgs = st.file_uploader("Upload 2–8 travel photos",
                type=["jpg","jpeg","png","webp"], accept_multiple_files=True, key="slide_imgs")
            v_dest  = st.text_input("Destination (for AI captions)",
                                     value=st.session_state.get("ai_dest",""),
                                     placeholder="Goa, India")
            v_theme = st.selectbox("Theme", list(THEMES.keys()), key="v_theme")
            v_size  = st.selectbox("Format", [
                "Instagram Story / Reels (1080×1920)",
                "YouTube Shorts (1080×1920)",
                "Square Post (1080×1080)",
                "YouTube Thumbnail (1280×720)",
            ], key="v_size")
            v_size_map = {
                "Instagram Story / Reels (1080×1920)": (1080,1920),
                "YouTube Shorts (1080×1920)":          (1080,1920),
                "Square Post (1080×1080)":             (1080,1080),
                "YouTube Thumbnail (1280×720)":        (1280,720),
            }
            vw, vh = v_size_map[v_size]

            v_pkg   = st.text_input("Package name on slides",
                                     value=ai.get("package_name","") if ai else "",
                                     placeholder="7 Days Royal Package")
            v_hl_raw = st.text_area("Highlights (for AI captions, one per line)",
                                     value="\n".join(ai.get("highlights",[])) if ai else "",
                                     placeholder="Desert Safari\nCity Palace\nLake Cruise",
                                     height=90)
            v_highlights = [h.strip() for h in v_hl_raw.strip().splitlines() if h.strip()]

            use_ai_caps = st.checkbox("✨ Gemini AI per-slide captions",
                                       value=has_key, disabled=not has_key)
            v_fb    = st.text_input("Facebook",  key="v_fb")
            v_insta = st.text_input("Instagram", key="v_insta")
            v_web   = st.text_input("Website",   key="v_web")
            v_logo  = st.file_uploader("Logo", type=["png","jpg","jpeg"], key="v_logo")
            v_dur   = st.slider("Seconds per slide", 1, 5, 2)

            n = len(slide_imgs) if slide_imgs else 0
            v_gen = st.button("🎬 Generate Slideshow GIF", type="primary",
                               use_container_width=True, disabled=n < 2)

        with col_vr:
            st.markdown("### 👁️ Preview")

            if v_gen and slide_imgs:
                if use_ai_caps and v_dest:
                    with st.spinner("Gemini writing slide captions…"):
                        captions = ai_generate_video_captions(v_dest, v_highlights, len(slide_imgs))
                else:
                    captions = (v_highlights + [f"Slide {i+1}" for i in range(len(slide_imgs))])[:len(slide_imgs)]

                frames = []; prog = st.progress(0, text="Generating frames…")
                total = min(len(slide_imgs), 8)
                for i, f in enumerate(slide_imgs[:8]):
                    cap = captions[i] if i < len(captions) else f"✨ Slide {i+1}"
                    frame = generate_banner(
                        w=vw, h=vh, theme=THEMES[v_theme], bg_image=f,
                        package_name=v_pkg,
                        fb=v_fb, insta=v_insta, website=v_web,
                        logo_file=v_logo, logo_pos="Top Right",
                        slide_caption=cap, slide_num=f"{i+1:02d} / {total:02d}",
                    )
                    scale = 540 / vw
                    frames.append(frame.resize((int(vw*scale), int(vh*scale)), Image.LANCZOS))
                    prog.progress((i+1)/total)

                prog.empty()
                gif = make_gif(frames, ms=v_dur*1000)
                st.session_state["last_gif"]       = gif
                st.session_state["slide_captions"] = captions
                st.success(f"✅ {total}-slide GIF ready! ({len(gif)//1024} KB)")

            gif = st.session_state.get("last_gif")
            if gif:
                b64 = base64.b64encode(gif).decode()
                st.markdown(f'<img src="data:image/gif;base64,{b64}" '
                            f'style="width:100%;border-radius:10px">', unsafe_allow_html=True)
                st.download_button("📥 Download GIF", data=gif,
                    file_name="travel_slideshow.gif", mime="image/gif", use_container_width=True)
                caps = st.session_state.get("slide_captions",[])
                if caps:
                    with st.expander("📝 AI slide captions"):
                        for i, c in enumerate(caps):
                            st.markdown(f"**Slide {i+1}:** {c}")
                st.caption("💡 Import into **CapCut** or **InShot** → add music → export MP4 for Reels/Shorts")
            else:
                st.markdown("""
                <div class="empty-state">
                    <div class="empty-icon">🎬</div>
                    <div class="empty-text">Upload 2+ photos then click Generate</div>
                </div>""", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 4 — BULK EXPORT
    # ═══════════════════════════════════════════════════════════════════════
    with tab_bulk:
        st.markdown("### 📦 Bulk Export — All Sizes at Once")
        st.info("Configure once → download a ZIP with banners for every selected platform.")

        ai = st.session_state.get("ai_copy", {})
        col_bl, col_br = st.columns([1, 1], gap="large")

        with col_bl:
            b_bg    = st.file_uploader("Background photo", type=["jpg","jpeg","png","webp"], key="b_bg")
            b_theme = st.selectbox("Theme", list(THEMES.keys()), key="b_theme")
            b_ai    = bool(ai) and st.checkbox("⚡ Pre-fill from AI", value=bool(ai), key="b_ai_fill")

            b_pkg   = st.text_input("Package Name", key="b_pkg",
                                     value=ai.get("package_name","") if b_ai else "",
                                     placeholder="Goa Beach Holiday — 5N/6D")
            b_title = st.text_input("Headline",     key="b_title",
                                     value=ai.get("title","") if b_ai else "")
            b_sub   = st.text_input("Subheadline",  key="b_sub",
                                     value=ai.get("subtitle","") if b_ai else "")
            b_price = st.text_input("Price",        key="b_price",
                                     value=ai.get("price_hint","") if b_ai else "")
            b_cta   = st.text_input("CTA",          key="b_cta",
                                     value=ai.get("cta","Book Now →") if b_ai else "Book Now →")
            default_hl = "\n".join(ai.get("highlights",[])) if b_ai else ""
            b_hl    = st.text_area("Highlights (one per line)", key="b_hl",
                                    value=default_hl, height=100,
                                    placeholder="Baga Beach\nWater Sports\nSunset Cruise")
            b_fb    = st.text_input("Facebook",  key="b_fb")
            b_insta = st.text_input("Instagram", key="b_insta")
            b_web   = st.text_input("Website",   key="b_web")
            b_logo  = st.file_uploader("Logo",       type=["png","jpg","jpeg"], key="b_logo")
            b_cert  = st.file_uploader("Cert badge", type=["png","jpg","jpeg"], key="b_cert")
            b_lpos  = st.radio("Logo position",
                                ["Top Right","Top Left","Bottom Right","Bottom Left"],
                                horizontal=True, key="b_lpos")
            platforms = st.multiselect("Select platforms", list(SIZES.keys()),
                default=["YouTube Thumbnail (1280×720)",
                         "Instagram Post Square (1080×1080)",
                         "Instagram Story (1080×1920)",
                         "Facebook Post (1200×630)"])

            bulk_btn = st.button("📦 Generate All & Download ZIP", type="primary",
                                  use_container_width=True, disabled=not platforms)

        with col_br:
            st.markdown("### 📋 Export Preview")
            if bulk_btn and platforms:
                b_highlights = [h.strip() for h in b_hl.strip().splitlines() if h.strip()]
                zip_buf = io.BytesIO()
                prog = st.progress(0, text="Generating…")

                with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    preview_shown = False
                    for i, p_name in enumerate(platforms):
                        pw, ph = SIZES[p_name]
                        img = generate_banner(
                            w=pw, h=ph, theme=THEMES[b_theme], bg_image=b_bg,
                            title=b_title, subtitle=b_sub, package_name=b_pkg,
                            price=b_price, highlights=b_highlights, cta=b_cta,
                            fb=b_fb, insta=b_insta, website=b_web,
                            logo_file=b_logo, logo_pos=b_lpos, cert_file=b_cert,
                        )
                        safe  = p_name.split("(")[0].strip().replace(" ","_").replace("/","-")
                        fname = f"{b_pkg or 'banner'}_{safe}_{pw}x{ph}.png"
                        zf.writestr(fname, img_to_bytes(img))
                        if not preview_shown:
                            st.image(img_to_bytes(img), caption=p_name, use_container_width=True)
                            preview_shown = True
                        prog.progress((i+1)/len(platforms))

                prog.empty(); zip_buf.seek(0)
                st.success(f"✅ {len(platforms)} banners ready!")
                st.download_button("📥 Download ZIP", data=zip_buf.getvalue(),
                    file_name=f"{b_pkg or 'banners'}_all_sizes.zip",
                    mime="application/zip", use_container_width=True)
            else:
                st.markdown("""
                <div class="empty-state">
                    <div class="empty-icon">📦</div>
                    <div class="empty-text">Configure → select platforms → Generate All</div>
                </div>""", unsafe_allow_html=True)

    # ── TIPS ──────────────────────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("💡 Tips — Get the best results"):
        st.markdown("""
**Free Gemini API Setup (one-time, 2 minutes):**
1. Visit [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Sign in with Google → Create API Key → Copy it
3. Add to `.streamlit/secrets.toml`:
   ```
   GEMINI_API_KEY = "AIzaSy..."
   ```
4. **Free tier:** 250 requests/day — no credit card, no billing ever needed

**AI Copy Tips:**
- Be specific: *"7-day Rajasthan with desert safari, camel ride, folk dinner"*
- Mention your USP: budget / luxury / family / honeymoon / adventure

**Photo Tips:**
- High-res (min 1920×1080); golden-hour shots look stunning on all themes
- Leave sky/foreground space — text overlays those areas

**Platform Quick Guide:**

| Platform | Best Size | Key Tip |
|---|---|---|
| YouTube Thumbnail | 1280×720 | Bold text, bright accent colour |
| Instagram Reels | 1080×1920 | Text in upper/lower thirds |
| Facebook Post | 1200×630 | Keep text < 20% of image |
| WhatsApp Status | 1080×1920 | 2-3 lines max, large font |

**After downloading:**
- Open GIF in **CapCut** → add music → export MP4 for Reels/Shorts
- Import PNG to **Canva** → add animations → schedule via **Buffer / Later**
        """)
