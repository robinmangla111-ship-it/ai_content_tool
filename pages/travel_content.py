"""
✈ AI Travel Content Creator
=================================
FREE tools used:
  • Hugging Face FLUX.1-schnell  → AI background image generation
  • Groq (llama-3.3-70b)         → Prompt enhancement + copy generation
  • Gemini 2.5 Flash (fallback)  → Copy generation if no Groq key
  • Pillow                       → Banner compositing, GIF creation

Features:
  • Single banner for any platform
  • Multi-scene animated GIF slideshow (20-30s) → import to CapCut for MP4
  • Bulk export ZIP (all platform sizes)
  • Persistent brand kit: logo, cert badge, social links
  • Full copy generation: title, subtitle, highlights, YouTube/Insta/FB/WA captions
"""

import streamlit as st
import sys, os, io, json, time, base64, zipfile, re
import requests
from PIL import Image, ImageDraw, ImageFont

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ─────────────────────────────────────────────────────────────────────────────
# KEY HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get(sk, sec, env):
    v = st.session_state.get(sk, "").strip()
    if v: return v
    try:
        v = str(st.secrets.get(sec, "")).strip()
        if v: return v
    except Exception:
        pass
    return os.getenv(env, "").strip()

def _hf_key():     return _get("hf_token",     "HF_TOKEN",       "HF_TOKEN")
def _groq_key():   return _get("groq_api_key", "GROQ_API_KEY",   "GROQ_API_KEY")
def _gemini_key(): return _get("gemini_key",   "GEMINI_API_KEY", "GEMINI_API_KEY")

def _llm_available(): return bool(_groq_key() or _gemini_key())

# ─────────────────────────────────────────────────────────────────────────────
# PLATFORM SIZES
# ─────────────────────────────────────────────────────────────────────────────

PLATFORMS = {
    "Instagram Post (1:1)            1080×1080": (1080, 1080),
    "Instagram / Reels Story (9:16)  1080×1920": (1080, 1920),
    "YouTube Thumbnail (16:9)        1280×720":  (1280,  720),
    "YouTube Shorts (9:16)           1080×1920": (1080, 1920),
    "Facebook Post (1.91:1)          1200×630":  (1200,  630),
    "Facebook Cover                  820×312":   ( 820,  312),
    "WhatsApp Status (9:16)          1080×1920": (1080, 1920),
    "Twitter/X Post (16:9)           1200×675":  (1200,  675),
    "LinkedIn Banner                 1584×396":  (1584,  396),
}

# ─────────────────────────────────────────────────────────────────────────────
# IMAGE STYLES  (appended to prompts)
# ─────────────────────────────────────────────────────────────────────────────

IMG_STYLES = {
    "📸 Photorealistic":      "ultra-realistic travel photography, golden hour lighting, professional DSLR, 8k, sharp",
    "🎨 Cinematic":           "cinematic wide shot, dramatic lighting, film grain, movie still, anamorphic lens",
    "🌅 Aerial / Drone":      "aerial drone photography, bird's eye view, stunning landscape, vivid colors, 8k",
    "🖼️ Vintage Poster":      "vintage travel poster, retro art deco style, bold colors, classic typography aesthetic",
    "✏️ Illustration":        "digital illustration, vibrant colors, travel poster style, flat design with depth",
    "🌙 Night / Moody":       "night photography, city lights, long exposure, moody atmosphere, neon reflections",
    "🏺 Cultural / Artistic": "cultural artistic style, folk art inspired, rich textures, warm earthy tones",
}

# ─────────────────────────────────────────────────────────────────────────────
# LLM HELPERS  (Groq preferred → Gemini fallback)
# ─────────────────────────────────────────────────────────────────────────────

def _call_groq(system: str, user: str, max_tokens: int = 800) -> str:
    key = _groq_key()
    if not key: return ""
    try:
        from groq import Groq
        client = Groq(api_key=key)
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"system","content":system},{"role":"user","content":user}],
            max_tokens=max_tokens, temperature=0.75,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        st.warning(f"Groq error: {e}")
        return ""


def _call_gemini(prompt: str, max_tokens: int = 800) -> str:
    key = _gemini_key()
    if not key: return ""
    url  = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.8},
    }
    try:
        r = requests.post(url, params={"key": key}, json=body, timeout=30)
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        st.warning(f"Gemini error: {e}")
        return ""


def _llm(system: str, user: str, max_tokens: int = 800) -> str:
    """Try Groq first, fall back to Gemini."""
    result = _call_groq(system, user, max_tokens)
    if not result:
        result = _call_gemini(f"{system}\n\n{user}", max_tokens)
    return result


def _parse_json(raw: str):
    clean = re.sub(r"```(?:json)?|```", "", raw).strip()
    start = min(
        (clean.find("{") if "{" in clean else len(clean)),
        (clean.find("[") if "[" in clean else len(clean)),
    )
    return json.loads(clean[start:])


# ── LLM tasks ─────────────────────────────────────────────────────────────────

def enhance_image_prompt(desc: str, style: str, destination: str) -> str:
    system = (
        "You are an expert Stable Diffusion / FLUX image prompt writer for travel photography. "
        "Turn the description into a rich visual prompt. "
        "RULES: No people. No text. No logos. Just scenery/place/atmosphere. "
        "Specific about lighting, time of day, composition, colors. "
        "Output ONLY the prompt, no preamble, max 100 words."
    )
    user = (
        f"Destination: {destination}\n"
        f"Description: {desc}\n"
        f"Style: {style}\n"
        "Write the image generation prompt:"
    )
    result = _llm(system, user, max_tokens=150)
    return result or f"{desc}, {destination}, {style}, no text, no watermark"


def generate_all_copy(destination: str, package_type: str,
                       duration: str, extra: str) -> dict:
    system = (
        "You are a top travel marketing copywriter for Indian travel agencies. "
        "Return ONLY valid JSON, no markdown fences, no preamble."
    )
    user = (
        f"Destination: {destination}\n"
        f"Package type: {package_type}\nDuration: {duration}\nDetails: {extra or 'none'}\n\n"
        "Return JSON with keys: title, subtitle, package_name, price_hint, cta, "
        "highlights (array of 5), youtube_title, instagram_caption, facebook_caption, "
        "whatsapp_status, short_video_script (3 punchy sentences for 30-sec reel), "
        "scene_prompts (array of 5 image scene descriptions for AI image generation)."
    )
    raw = _llm(system, user, max_tokens=1000)
    if not raw: return {}
    try:
        return _parse_json(raw)
    except Exception:
        return {}


def generate_scene_captions(pkg_name: str, scenes: list, n: int) -> list:
    system = (
        "Generate short punchy captions for travel video slides. "
        "Each max 6 words with 1 emoji. Output ONLY a JSON array of strings."
    )
    user = f"Package: {pkg_name}\nScenes: {scenes}\nGenerate {n} captions:"
    raw = _llm(system, user, max_tokens=200)
    if not raw:
        return [f"✨ Scene {i+1}" for i in range(n)]
    try:
        data = _parse_json(raw)
        return [str(c) for c in data[:n]]
    except Exception:
        return [s[:30] for s in scenes[:n]]

# ─────────────────────────────────────────────────────────────────────────────
# AI IMAGE GENERATION  (Hugging Face FLUX.1-schnell — free)
# ─────────────────────────────────────────────────────────────────────────────

HF_MODEL_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"


def generate_ai_image(prompt: str, width: int, height: int,
                       retry: bool = True) -> Image.Image | None:
    """
    Generate image via HF Inference API. Returns PIL Image or None (→ gradient fallback).
    Free tier: ~50-100 images/month.
    """
    hf_key = _hf_key()
    if not hf_key:
        return None

    headers = {"Authorization": f"Bearer {hf_key}"}
    payload = {
        "inputs": prompt,
        "parameters": {
            "width":  min(width,  1024),
            "height": min(height, 1024),
            "num_inference_steps": 4,
        }
    }

    def _parse_img(r):
        img = Image.open(io.BytesIO(r.content)).convert("RGBA")
        ratio = max(width / img.width, height / img.height)
        nw, nh = int(img.width*ratio), int(img.height*ratio)
        img = img.resize((nw, nh), Image.LANCZOS)
        l = (nw-width)//2; t = (nh-height)//2
        return img.crop((l, t, l+width, t+height))

    try:
        r = requests.post(HF_MODEL_URL, headers=headers, json=payload, timeout=90)
        ct = r.headers.get("content-type","")
        if r.status_code == 200 and ct.startswith("image"):
            return _parse_img(r)
        elif r.status_code == 503 and retry:
            st.toast("⏳ HF model loading — retrying in 15s…")
            time.sleep(15)
            r2 = requests.post(HF_MODEL_URL, headers=headers, json=payload, timeout=90)
            if r2.status_code == 200 and r2.headers.get("content-type","").startswith("image"):
                return _parse_img(r2)
        elif r.status_code == 401:
            st.error("❌ Invalid HF token. Check your token in Brand Kit.")
        elif r.status_code == 429:
            st.warning("⚠️ HF free quota reached — using gradient background.")
        else:
            st.warning(f"HF API {r.status_code} — using gradient background.")
        return None
    except Exception as e:
        st.warning(f"Image gen failed ({e}) — using gradient background.")
        return None

# ─────────────────────────────────────────────────────────────────────────────
# FONT LOADER
# ─────────────────────────────────────────────────────────────────────────────

def _font(size: int, bold: bool = False):
    paths = [
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf",
        f"/usr/share/fonts/truetype/liberation/LiberationSans{'-Bold' if bold else '-Regular'}.ttf",
        f"/usr/share/fonts/truetype/ubuntu/Ubuntu-{'B' if bold else 'R'}.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for p in paths:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except: pass
    return ImageFont.load_default()

# ─────────────────────────────────────────────────────────────────────────────
# IMAGE COMPOSITING HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _gradient_bg(w, h, c1=(15,40,80), c2=(60,15,50)):
    img = Image.new("RGBA", (w, h))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        draw.line([(0,y),(w,y)], fill=(
            int(c1[0]+(c2[0]-c1[0])*t),
            int(c1[1]+(c2[1]-c1[1])*t),
            int(c1[2]+(c2[2]-c1[2])*t), 255))
    return img


def _overlay(img, alpha=140):
    ov = Image.new("RGBA", img.size, (0,0,0,alpha))
    return Image.alpha_composite(img.convert("RGBA"), ov)


def _wrap(text, font, max_w, draw):
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


def _shadow(draw, xy, text, font, fill, s=3):
    draw.text((xy[0]+s, xy[1]+s), text, font=font, fill=(0,0,0,165))
    draw.text(xy, text, font=font, fill=fill)


def _pill(draw, x, y, text, font, bg, fg, pad=14):
    bb = draw.textbbox((0,0), text, font=font)
    tw, th = bb[2]-bb[0], bb[3]-bb[1]
    draw.rounded_rectangle([x,y,x+tw+pad*2,y+th+pad], radius=(th+pad)//2, fill=bg)
    draw.text((x+pad, y+pad//2), text, font=font, fill=fg)
    return x+tw+pad*2


def _social_bar(draw, w, h, fb, insta, web, accent, font):
    bh = 56; by = h-bh
    draw.rectangle([0,by,w,h], fill=(0,0,0,170))
    items = []
    if fb:    items.append(f"f  {fb}")
    if insta: items.append(f"@  {insta}")
    if web:   items.append(f"🌐 {web}")
    if not items: return
    line = "   ·   ".join(items)
    bb = draw.textbbox((0,0), line, font=font)
    tw = bb[2]-bb[0]
    draw.text(((w-tw)//2, by+(bh-(bb[3]-bb[1]))//2), line, font=font, fill=accent+(255,))


def _paste_asset(canvas, asset_bytes, position, max_px, bottom_res=60):
    asset = Image.open(io.BytesIO(asset_bytes)).convert("RGBA")
    r = min(max_px/asset.width, max_px/asset.height)
    nw, nh = int(asset.width*r), int(asset.height*r)
    asset = asset.resize((nw,nh), Image.LANCZOS)
    W, H = canvas.size; m = 20
    pos_map = {
        "Top Left":    (m, m), "Top Right":    (W-nw-m, m),
        "Bottom Left": (m, H-nh-m-bottom_res),
        "Bottom Right":(W-nw-m, H-nh-m-bottom_res),
    }
    x, y = pos_map.get(position, (W-nw-m, m))
    canvas.paste(asset, (x,y), asset)
    return canvas

# ─────────────────────────────────────────────────────────────────────────────
# MAIN BANNER COMPOSER
# ─────────────────────────────────────────────────────────────────────────────

def compose_banner(
    bg_img, w, h,
    package_name="", headline="", subheadline="",
    highlights=None, price="", cta="",
    slide_caption="", slide_num=None,
    logo_bytes=None, logo_pos="Top Right",
    cert_bytes=None,
    fb="", insta="", web="",
    overlay_alpha=140,
    accent=(255,200,50),
    text_color=(255,255,255),
) -> Image.Image:

    highlights = highlights or []

    canvas = bg_img.copy().convert("RGBA") if bg_img else _gradient_bg(w, h)
    canvas = _overlay(canvas, overlay_alpha)
    draw   = ImageDraw.Draw(canvas)

    sc     = min(w,h)/1080
    margin = int(55*sc); mw = w-margin*2
    cy     = int(55*sc)
    white  = text_color+(255,); acc4 = accent+(255,)

    fT  = _font(int(74*sc), bold=True)
    fS  = _font(int(40*sc))
    fH  = _font(int(30*sc))
    fP  = _font(int(58*sc), bold=True)
    fC  = _font(int(36*sc), bold=True)
    fSm = _font(int(24*sc))
    fSl = _font(int(54*sc), bold=True)
    fNm = _font(int(22*sc))

    # ── VIDEO SLIDE MODE ─────────────────────────────────────────────────────
    if slide_caption:
        if slide_num:
            nb = draw.textbbox((0,0), slide_num, font=fNm)
            draw.text((w-margin-(nb[2]-nb[0]), int(28*sc)), slide_num,
                      font=fNm, fill=accent+(200,))
        wrapped = _wrap(slide_caption, fSl, mw, draw)
        bb = draw.multiline_textbbox((0,0), wrapped, font=fSl)
        tx = (w-(bb[2]-bb[0]))//2; ty = (h-(bb[3]-bb[1]))//2-int(20*sc)
        _shadow(draw, (tx,ty), wrapped, fSl, white, s=4)
        if package_name:
            pb = draw.textbbox((0,0), package_name, font=fSm)
            px = (w-(pb[2]-pb[0])-28)//2
            _pill(draw, px, h-int(115*sc), package_name, fSm,
                  accent+(210,), (15,15,15,255), pad=14)
    else:
        # ── NORMAL BANNER ────────────────────────────────────────────────────
        if package_name:
            _pill(draw, margin, cy, f"  ✈  {package_name.upper()}  ",
                  fSm, accent+(205,), (10,10,10,255), pad=16)
            cy += int(58*sc)
            draw.rectangle([margin,cy,margin+int(70*sc),cy+4], fill=acc4)
            cy += int(20*sc)

        if headline:
            wrapped = _wrap(headline, fT, mw, draw)
            _shadow(draw, (margin,cy), wrapped, fT, white)
            bb = draw.multiline_textbbox((margin,cy), wrapped, font=fT)
            cy += bb[3]-bb[1]+int(14*sc)

        if subheadline:
            wrapped = _wrap(subheadline, fS, mw, draw)
            _shadow(draw, (margin,cy), wrapped, fS, acc4)
            bb = draw.multiline_textbbox((margin,cy), wrapped, font=fS)
            cy += bb[3]-bb[1]+int(28*sc)

        for hl in highlights[:6]:
            line = f"  ✓  {hl}"
            _shadow(draw, (margin,cy), line, fH, white)
            bb = draw.textbbox((margin,cy), line, font=fH)
            cy += bb[3]-bb[1]+int(7*sc)
        if highlights: cy += int(18*sc)

        if price:
            _shadow(draw, (margin,cy), f"From  {price}", fP, acc4)
            bb = draw.textbbox((margin,cy), f"From  {price}", font=fP)
            cy += bb[3]-bb[1]+int(22*sc)

        if cta:
            _pill(draw, margin, cy, f"  {cta}  ", fC, accent+(230,), (20,20,20,255), pad=20)

    _social_bar(draw, w, h, fb, insta, web, accent, fSm)

    if logo_bytes:
        canvas = _paste_asset(canvas, logo_bytes, logo_pos, int(130*sc), bottom_res=62)
    if cert_bytes:
        canvas = _paste_asset(canvas, cert_bytes, "Bottom Left", int(90*sc), bottom_res=62)

    return canvas.convert("RGB")


def img_bytes(img, fmt="PNG") -> bytes:
    buf = io.BytesIO(); img.save(buf, format=fmt, quality=95); return buf.getvalue()


def make_gif(frames, ms=2500) -> bytes:
    thumbs = []
    for f in frames:
        scale = 540 / f.width
        thumbs.append(f.resize((int(f.width*scale), int(f.height*scale)), Image.LANCZOS))
    buf = io.BytesIO()
    thumbs[0].save(buf, format="GIF", save_all=True,
                   append_images=thumbs[1:], duration=ms, loop=0, optimize=True)
    return buf.getvalue()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE
# ─────────────────────────────────────────────────────────────────────────────

def render():

    # ── CSS ───────────────────────────────────────────────────────────────────
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=Inter:wght@400;500;600&display=swap');
    .tc-hero { font-family:'Syne',sans-serif; font-size:2.3rem; font-weight:800;
               background:linear-gradient(135deg,#f59e0b,#ef4444,#8b5cf6);
               -webkit-background-clip:text; -webkit-text-fill-color:transparent; }
    .tc-sub  { font-family:'Inter',sans-serif; color:#94a3b8; font-size:.95rem; margin-top:2px; }
    .badge   { display:inline-block; padding:3px 12px; border-radius:20px; font-size:.72rem;
               font-weight:700; letter-spacing:.05em; margin-right:6px; margin-bottom:10px; }
    .b-free  { background:linear-gradient(135deg,#16a34a,#0284c7); color:#fff; }
    .b-ai    { background:linear-gradient(135deg,#7c3aed,#db2777); color:#fff; }
    .copy-box{ background:#1e293b; border:1px solid #334155; border-radius:10px;
               padding:13px 17px; font-family:'Inter',sans-serif; font-size:.84rem;
               color:#e2e8f0; line-height:1.65; white-space:pre-wrap; margin-bottom:8px; }
    .copy-lbl{ font-size:.68rem; font-weight:700; letter-spacing:.09em;
               color:#64748b; text-transform:uppercase; margin-bottom:3px; }
    .empty   { border:1px dashed #334155; border-radius:14px;
               padding:70px 20px; text-align:center; }
    .e-icon  { font-size:3rem; }
    .e-text  { color:#64748b; margin-top:10px; font-size:.88rem; }
    .key-box { background:#0f1f1a; border:1px solid #22c55e55;
               border-radius:10px; padding:14px 18px; line-height:1.8; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<span class="badge b-ai">✦ AI IMAGE GEN</span>'
                '<span class="badge b-free">100% FREE TOOLS</span>', unsafe_allow_html=True)
    st.markdown('<div class="tc-hero">✈ AI Travel Content Creator</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="tc-sub">Describe your package → AI generates the scene → '
        'brand composited → banners & video for every platform</div>',
        unsafe_allow_html=True
    )
    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # BRAND KIT SIDEBAR
    # ─────────────────────────────────────────────────────────────────────────
    with st.expander("🏷️ Brand Kit — Logo · Cert Badge · Social Links · API Keys", expanded=False):
        k1, k2, k3 = st.columns(3)

        with k1:
            st.markdown("**🖼️ Company Logo**")
            logo_up = st.file_uploader("PNG (transparent)", type=["png","jpg","jpeg"], key="bk_logo")
            if logo_up:
                st.session_state["brand_logo"] = logo_up.read()
            if st.session_state.get("brand_logo"):
                st.image(st.session_state["brand_logo"], width=110,
                         caption="✓ Saved" if not logo_up else "New logo")

        with k2:
            st.markdown("**🏅 Certification Badge**")
            cert_up = st.file_uploader("Award / cert badge", type=["png","jpg","jpeg"], key="bk_cert")
            if cert_up:
                st.session_state["brand_cert"] = cert_up.read()
            if st.session_state.get("brand_cert"):
                st.image(st.session_state["brand_cert"], width=80,
                         caption="✓ Saved" if not cert_up else "New badge")

        with k3:
            st.markdown("**🔗 Social Links**")
            fb_v    = st.text_input("Facebook page",    value=st.session_state.get("bk_fb",""),    key="_fb")
            insta_v = st.text_input("Instagram handle", value=st.session_state.get("bk_insta",""), key="_ig")
            web_v   = st.text_input("Website",          value=st.session_state.get("bk_web",""),   key="_wb")
            if st.button("💾 Save", use_container_width=True):
                st.session_state.update(bk_fb=fb_v, bk_insta=insta_v, bk_web=web_v)
                st.success("Brand kit saved!")

        st.markdown("---")
        st.markdown("##### 🔑 API Keys (all free)")
        a1, a2, a3 = st.columns(3)

        with a1:
            hf_v = st.text_input(
                "🤗 Hugging Face Token",
                type="password",
                value=st.session_state.get("hf_token",""),
                placeholder="hf_xxxxxxxxxx",
                help="huggingface.co → Settings → Access Tokens → New (Read)",
            )
            if hf_v: st.session_state["hf_token"] = hf_v.strip()
            if _hf_key(): st.success("HF ✓ — AI images ON")
            else:          st.warning("No HF key → gradient bg")

        with a2:
            groq_v = st.text_input(
                "⚡ Groq API Key",
                type="password",
                value=st.session_state.get("groq_api_key",""),
                placeholder="gsk_xxxxxxxxxx",
                help="console.groq.com → API Keys → Create (free)",
            )
            if groq_v: st.session_state["groq_api_key"] = groq_v.strip()
            if _groq_key(): st.success("Groq ✓ — fast LLM")
            else:            st.info("Optional — Gemini used as fallback")

        with a3:
            gem_v = st.text_input(
                "🔵 Gemini API Key (fallback LLM)",
                type="password",
                value=st.session_state.get("gemini_key",""),
                placeholder="AIzaSy...",
                help="aistudio.google.com/app/apikey — free, 250 req/day",
            )
            if gem_v: st.session_state["gemini_key"] = gem_v.strip()
            if _gemini_key(): st.success("Gemini ✓ — LLM fallback ready")
            else:              st.info("Get free key at aistudio.google.com")

    # ── Brand kit values for use everywhere ───────────────────────────────────
    logo_bytes = st.session_state.get("brand_logo")
    cert_bytes = st.session_state.get("brand_cert")
    bk_fb      = st.session_state.get("bk_fb","")
    bk_insta   = st.session_state.get("bk_insta","")
    bk_web     = st.session_state.get("bk_web","")

    st.markdown("---")

    # ── TABS ──────────────────────────────────────────────────────────────────
    tab_copy, tab_single, tab_video, tab_bulk = st.tabs([
        "🤖 AI Copy Generator",
        "🖼️ Single Banner",
        "🎬 Video Slideshow",
        "📦 Bulk Export",
    ])

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 1 — AI COPY GENERATOR
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_copy:
        st.markdown("### 🤖 AI Travel Copy Generator")
        st.caption("Groq (llama-3.3-70b) or Gemini 2.5 Flash — both free. Generates all "
                   "marketing copy + AI image scene prompts for your package.")

        cl, cr = st.columns([1,1], gap="large")

        with cl:
            cp_dest  = st.text_input("🗺️ Destination", placeholder="Rajasthan, India")
            cp_type  = st.selectbox("🏷️ Package Type", [
                "Cultural & Heritage Tour","Beach & Relaxation","Adventure & Trekking",
                "Wildlife Safari","Honeymoon Package","Family Holiday",
                "Pilgrimage / Religious Tour","Luxury Getaway","Budget Backpacker","Corporate / MICE",
            ])
            cp_dur   = st.text_input("📅 Duration", placeholder="7 Nights / 8 Days")
            cp_extra = st.text_area("💬 Key highlights / extras",
                                    placeholder="Desert safari, camel ride, folk dinner, "
                                                "Jaipur city tour, Udaipur lake cruise…", height=100)
            cp_gen   = st.button("✨ Generate All Copy + Scene Prompts",
                                  type="primary", use_container_width=True,
                                  disabled=not (_llm_available() and cp_dest.strip()))
            if not _llm_available():
                st.caption("⚠️ Add Groq or Gemini key in Brand Kit to enable AI copy.")

        with cr:
            if cp_gen:
                with st.spinner("AI writing your travel copy…"):
                    result = generate_all_copy(cp_dest, cp_type, cp_dur, cp_extra)
                if result:
                    st.session_state["ai_copy"] = result
                    st.session_state["ai_dest"] = cp_dest
                    st.success("✅ Done! Switch to Single Banner or Video Slideshow — all fields pre-filled.")
                else:
                    st.error("Empty response. Check your API key and try again.")

            ai = st.session_state.get("ai_copy", {})
            if ai:
                def _box(label, val):
                    if val:
                        st.markdown(f'<div class="copy-lbl">{label}</div>', unsafe_allow_html=True)
                        v = "\n".join(f"• {h}" for h in val) if isinstance(val, list) else str(val)
                        st.markdown(f'<div class="copy-box">{v}</div>', unsafe_allow_html=True)

                _box("HEADLINE", ai.get("title",""))
                _box("SUBTITLE", ai.get("subtitle",""))
                _box("PACKAGE NAME", ai.get("package_name",""))
                _box("PRICE HINT", ai.get("price_hint",""))
                _box("CALL TO ACTION", ai.get("cta",""))
                _box("HIGHLIGHTS", ai.get("highlights",[]))
                st.markdown("---")
                _box("📺 YouTube Title", ai.get("youtube_title",""))
                _box("📸 Instagram Caption", ai.get("instagram_caption",""))
                _box("👥 Facebook Caption", ai.get("facebook_caption",""))
                _box("📱 WhatsApp Status", ai.get("whatsapp_status",""))
                _box("🎬 30-sec Reel Script", ai.get("short_video_script",""))
                if ai.get("scene_prompts"):
                    _box("🎨 AI Scene Prompts (for Video tab)", ai.get("scene_prompts",[]))
                st.info("👉 Go to **Single Banner** or **Video Slideshow** — fields are pre-filled!")
            else:
                st.markdown("""<div class="empty"><div class="e-icon">🤖</div>
                <div class="e-text">Enter destination → Generate All Copy</div></div>""",
                unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 2 — SINGLE BANNER
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_single:
        ai = st.session_state.get("ai_copy",{})
        sl, sr = st.columns([1,1], gap="large")

        with sl:
            st.markdown("### 🎨 AI Scene")
            s_dest  = st.text_input("Destination", value=st.session_state.get("ai_dest",""),
                                     placeholder="Rajasthan, India", key="s_dest")
            s_desc  = st.text_area("Describe the scene for AI to generate",
                                    height=90, key="s_desc",
                                    placeholder="Majestic Amber Fort at golden sunset, "
                                                "Rajasthan desert, camel silhouettes, warm orange sky")
            s_style = st.selectbox("Image style", list(IMG_STYLES.keys()), key="s_style")
            s_enh   = st.checkbox("✨ Auto-enhance prompt with AI", value=True, key="s_enh",
                                   disabled=not _llm_available())

            st.markdown("### 📐 Format")
            s_plat   = st.selectbox("Platform", list(PLATFORMS.keys()), key="s_plat")
            sw, sh   = PLATFORMS[s_plat]

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
            s_cta    = st.text_input("Call to action",
                                      value=ai.get("cta","Book Now →") if use_ai else "Book Now →",
                                      key="s_cta")
            default_hl = "\n".join(ai.get("highlights",[])) if use_ai else ""
            s_hl_raw = st.text_area("Highlights (one per line)", value=default_hl, height=100,
                                     placeholder="Amber Fort Sunrise\nDesert Safari\nCamel Camp",
                                     key="s_hl")
            s_hl     = [l.strip() for l in s_hl_raw.splitlines() if l.strip()]

            c1, c2   = st.columns(2)
            with c1: s_lpos = st.selectbox("Logo position",
                                            ["Top Right","Top Left","Bottom Right","Bottom Left"],
                                            key="s_lpos")
            with c2: s_ov   = st.slider("Overlay darkness", 80, 220, 140, key="s_ov")

            s_gen    = st.button("🚀 Generate Banner", type="primary", use_container_width=True)

        with sr:
            st.markdown("### 👁️ Preview")

            if s_gen:
                if not s_desc.strip():
                    st.error("Please describe the scene you want AI to generate.")
                else:
                    with st.spinner("1/3 Enhancing prompt…"):
                        sfx = IMG_STYLES[s_style]
                        final_p = (enhance_image_prompt(s_desc, sfx, s_dest)
                                   if s_enh and _llm_available()
                                   else f"{s_desc}, {s_dest}, {sfx}, no text, no watermark")

                    st.caption(f"📝 *{final_p[:130]}…*")

                    with st.spinner("2/3 Generating AI image (15-30s)…"):
                        bg = generate_ai_image(final_p, sw, sh)

                    with st.spinner("3/3 Compositing branding…"):
                        banner = compose_banner(
                            bg_img=bg, w=sw, h=sh,
                            package_name=s_pkg, headline=s_head,
                            subheadline=s_sub, highlights=s_hl,
                            price=s_price, cta=s_cta,
                            logo_bytes=logo_bytes, logo_pos=s_lpos,
                            cert_bytes=cert_bytes,
                            fb=bk_fb, insta=bk_insta, web=bk_web,
                            overlay_alpha=s_ov,
                        )

                    st.session_state["s_banner"] = img_bytes(banner)
                    st.session_state["s_name"]   = f"{s_pkg or 'banner'}_{s_plat[:14]}.png"

            if st.session_state.get("s_banner"):
                st.image(st.session_state["s_banner"], use_container_width=True)
                st.download_button("📥 Download PNG",
                    data=st.session_state["s_banner"],
                    file_name=st.session_state.get("s_name","banner.png"),
                    mime="image/png", use_container_width=True)
                st.success("✅ Ready to post!")
            else:
                st.markdown("""<div class="empty"><div class="e-icon">🤖</div>
                <div class="e-text">Describe a scene → AI generates it → brand overlaid</div>
                </div>""", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 3 — VIDEO SLIDESHOW
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_video:
        ai = st.session_state.get("ai_copy",{})
        st.markdown("### 🎬 Multi-Scene Animated Slideshow (20-30s)")
        st.info(
            "Each scene = AI generates a unique image + caption. "
            "Output is an animated GIF. Import into **CapCut** → add music → export MP4 for Reels/Shorts."
        )

        vl, vr = st.columns([1,1], gap="large")

        with vl:
            v_dest   = st.text_input("Destination", value=st.session_state.get("ai_dest",""),
                                      placeholder="Kerala, India", key="v_dest")
            v_pkg    = st.text_input("Package name",
                                      value=ai.get("package_name","") if ai else "",
                                      placeholder="Backwaters Bliss — 5 Days", key="v_pkg")
            v_plat   = st.selectbox("Format", [
                "Instagram / Reels Story (9:16)  1080×1920",
                "YouTube Shorts (9:16)           1080×1920",
                "Instagram Post (1:1)            1080×1080",
                "YouTube Thumbnail (16:9)        1280×720",
            ], key="v_plat")
            vw, vh   = PLATFORMS[v_plat]
            v_style  = st.selectbox("Image style", list(IMG_STYLES.keys()), key="v_style")
            v_lpos   = st.selectbox("Logo position", ["Top Right","Top Left"], key="v_lpos")
            v_ov     = st.slider("Overlay darkness", 80, 220, 150, key="v_ov")
            v_dur    = st.slider("Seconds per scene", 2, 5, 3, key="v_dur")
            v_price  = st.text_input("Price (shown on last slide)",
                                      value=ai.get("price_hint","") if ai else "",
                                      placeholder="₹22,999/person", key="v_price")
            v_autocap = st.checkbox("✨ AI writes slide captions automatically",
                                     value=_llm_available(), disabled=not _llm_available())

            st.markdown("### 🎞️ Scenes")
            st.caption("Describe each scene image. Leave blank to skip.")

            # Pre-fill from AI scene_prompts if available
            ai_scenes = ai.get("scene_prompts",[]) if ai else []
            ai_hls    = ai.get("highlights",[]) if ai else []

            n_scenes = st.slider("Number of scenes", 3, 8, min(5, max(3, len(ai_scenes))), key="v_nsc")

            scene_descs = []; scene_caps_manual = []
            for i in range(n_scenes):
                sc, cp = st.columns([2,1])
                default_scene = ai_scenes[i] if i < len(ai_scenes) else ""
                default_cap   = ai_hls[i] if i < len(ai_hls) else ""
                with sc:
                    s = st.text_input(f"Scene {i+1} — image description",
                                       value=default_scene, key=f"vs_{i}",
                                       placeholder=f"Scene {i+1} description")
                    scene_descs.append(s)
                with cp:
                    c = st.text_input("Caption", value=default_cap, key=f"vc_{i}",
                                       placeholder=f"Caption {i+1}")
                    scene_caps_manual.append(c)

            v_gen = st.button("🎬 Generate Slideshow", type="primary",
                               use_container_width=True,
                               disabled=not any(s.strip() for s in scene_descs))

        with vr:
            st.markdown("### 👁️ Preview")

            if v_gen:
                valid = [(s.strip(), scene_caps_manual[i])
                         for i, s in enumerate(scene_descs) if s.strip()]
                if not valid:
                    st.error("Fill in at least one scene description.")
                else:
                    # AI captions
                    if v_autocap and _llm_available():
                        with st.spinner("AI writing captions…"):
                            captions = generate_scene_captions(
                                v_pkg, [s for s,_ in valid], len(valid))
                    else:
                        captions = [c or s[:30] for s,c in valid]

                    sfx    = IMG_STYLES[v_style]
                    frames = []
                    prog   = st.progress(0, text="Generating scenes…")
                    total  = len(valid)

                    for idx, (scene_desc, _) in enumerate(valid):
                        prog.progress(idx/total, text=f"Scene {idx+1}/{total}: generating…")

                        full_p = (enhance_image_prompt(scene_desc, sfx, v_dest)
                                  if _llm_available()
                                  else f"{scene_desc}, {v_dest}, {sfx}, no text")

                        bg = generate_ai_image(full_p, vw, vh)
                        cap = captions[idx] if idx < len(captions) else f"Scene {idx+1}"

                        frame = compose_banner(
                            bg_img=bg, w=vw, h=vh,
                            package_name=v_pkg if idx == 0 else "",
                            price=v_price if idx == total-1 else "",
                            cta="Book Now →" if idx == total-1 else "",
                            slide_caption=cap,
                            slide_num=f"{idx+1:02d} / {total:02d}",
                            logo_bytes=logo_bytes, logo_pos=v_lpos,
                            cert_bytes=cert_bytes,
                            fb=bk_fb, insta=bk_insta, web=bk_web,
                            overlay_alpha=v_ov,
                        )
                        frames.append(frame)

                    prog.progress(1.0, text="Building GIF…")
                    gif = make_gif(frames, ms=v_dur*1000)
                    st.session_state["v_gif"]    = gif
                    st.session_state["v_frames"] = [img_bytes(f) for f in frames]
                    st.session_state["v_pkg"]    = v_pkg
                    st.session_state["v_caps"]   = captions
                    prog.empty()
                    st.success(f"✅ {len(frames)}-scene GIF · {len(gif)//1024} KB")

            gif = st.session_state.get("v_gif")
            if gif:
                b64 = base64.b64encode(gif).decode()
                st.markdown(f'<img src="data:image/gif;base64,{b64}" '
                            f'style="width:100%;border-radius:10px">', unsafe_allow_html=True)
                st.download_button("📥 Download GIF", data=gif,
                    file_name=f"{st.session_state.get('v_pkg','video')}_slideshow.gif",
                    mime="image/gif", use_container_width=True)

                if st.session_state.get("v_frames"):
                    zbuf = io.BytesIO()
                    with zipfile.ZipFile(zbuf,"w") as zf:
                        for i, fb2 in enumerate(st.session_state["v_frames"]):
                            zf.writestr(f"scene_{i+1:02d}.png", fb2)
                    zbuf.seek(0)
                    st.download_button("📥 Download Frames ZIP", data=zbuf.getvalue(),
                        file_name="frames.zip", mime="application/zip", use_container_width=True)

                caps = st.session_state.get("v_caps",[])
                if caps:
                    with st.expander("📝 AI slide captions"):
                        for i,c in enumerate(caps):
                            st.markdown(f"**{i+1}.** {c}")

                st.markdown("---")
                st.markdown("**🎵 Add music & export as MP4 (free):**")
                st.markdown(
                    "1. Import GIF into **[CapCut](https://capcut.com)** (free)\n"
                    "2. Add music from CapCut's library or [Pixabay Music](https://pixabay.com/music/)\n"
                    "3. Export as 1080×1920 MP4 → upload to Reels / Shorts"
                )
            else:
                st.markdown("""<div class="empty"><div class="e-icon">🎬</div>
                <div class="e-text">Add scenes → Generate → Download GIF → Add music in CapCut</div>
                </div>""", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════════
    # TAB 4 — BULK EXPORT
    # ═══════════════════════════════════════════════════════════════════════════
    with tab_bulk:
        ai = st.session_state.get("ai_copy",{})
        st.markdown("### 📦 One AI Image → All Platform Sizes")
        st.info("Generates the AI image once at full quality, then crops & composites for every platform.")

        bl, br = st.columns([1,1], gap="large")

        with bl:
            b_dest   = st.text_input("Destination", placeholder="Goa, India", key="b_dest")
            b_desc   = st.text_area("Scene description (AI generates this image)",
                                     height=80, key="b_desc",
                                     placeholder="Pristine beach, turquoise sea, palm trees, golden sunset")
            b_style  = st.selectbox("Style", list(IMG_STYLES.keys()), key="b_style")
            b_use_ai = bool(ai) and st.checkbox("⚡ Fill content from AI Copy tab", value=bool(ai), key="b_useai")

            b_pkg    = st.text_input("Package Name", key="b_pkg",
                                      value=ai.get("package_name","") if b_use_ai else "",
                                      placeholder="Goa Beach Holiday — 5N/6D")
            b_head   = st.text_input("Headline", key="b_head",
                                      value=ai.get("title","") if b_use_ai else "")
            b_sub    = st.text_input("Subheadline", key="b_sub",
                                      value=ai.get("subtitle","") if b_use_ai else "")
            b_price  = st.text_input("Price", key="b_price",
                                      value=ai.get("price_hint","") if b_use_ai else "")
            b_cta    = st.text_input("CTA", key="b_cta",
                                      value=ai.get("cta","Book Now →") if b_use_ai else "Book Now →")
            def_hl   = "\n".join(ai.get("highlights",[])) if b_use_ai else ""
            b_hl_raw = st.text_area("Highlights (one per line)", key="b_hl", value=def_hl, height=90)
            b_hl     = [l.strip() for l in b_hl_raw.splitlines() if l.strip()]
            b_lpos   = st.radio("Logo position",
                                 ["Top Right","Top Left","Bottom Right","Bottom Left"],
                                 horizontal=True, key="b_lpos")
            b_plats  = st.multiselect("Export for", list(PLATFORMS.keys()),
                                       default=list(PLATFORMS.keys())[:4])
            b_gen    = st.button("📦 Generate All Sizes", type="primary",
                                  use_container_width=True, disabled=not (b_desc.strip() and b_plats))

        with br:
            st.markdown("### 📋 Results")

            if b_gen and b_plats and b_desc.strip():
                sfx = IMG_STYLES[b_style]

                with st.spinner("1/2 Generating AI image…"):
                    final_p = (enhance_image_prompt(b_desc, sfx, b_dest)
                               if _llm_available()
                               else f"{b_desc}, {b_dest}, {sfx}, no text")
                    master = generate_ai_image(final_p, 1024, 1024)

                with st.spinner(f"2/2 Compositing {len(b_plats)} banners…"):
                    zbuf = io.BytesIO()
                    with zipfile.ZipFile(zbuf,"w") as zf:
                        preview_done = False
                        for p_name in b_plats:
                            pw, ph = PLATFORMS[p_name]
                            if master:
                                ratio = max(pw/master.width, ph/master.height)
                                nw, nh = int(master.width*ratio), int(master.height*ratio)
                                bg_r = master.resize((nw,nh), Image.LANCZOS)
                                l = (nw-pw)//2; t = (nh-ph)//2
                                bg_crop = bg_r.crop((l,t,l+pw,t+ph))
                            else:
                                bg_crop = None

                            banner = compose_banner(
                                bg_img=bg_crop, w=pw, h=ph,
                                package_name=b_pkg, headline=b_head,
                                subheadline=b_sub, highlights=b_hl,
                                price=b_price, cta=b_cta,
                                logo_bytes=logo_bytes, logo_pos=b_lpos,
                                cert_bytes=cert_bytes,
                                fb=bk_fb, insta=bk_insta, web=bk_web,
                            )
                            safe = p_name.split("(")[0].strip().replace(" ","_").replace("/","-")
                            zf.writestr(f"{b_pkg or 'banner'}_{safe}_{pw}x{ph}.png", img_bytes(banner))

                            if not preview_done:
                                st.image(img_bytes(banner), caption=p_name, use_container_width=True)
                                preview_done = True

                zbuf.seek(0)
                st.success(f"✅ {len(b_plats)} banners ready!")
                st.download_button("📥 Download ZIP", data=zbuf.getvalue(),
                    file_name=f"{b_pkg or 'banners'}_all_platforms.zip",
                    mime="application/zip", use_container_width=True)
            else:
                st.markdown("""<div class="empty"><div class="e-icon">📦</div>
                <div class="e-text">One AI image → resized for every platform → ZIP</div>
                </div>""", unsafe_allow_html=True)

    # ── TIPS ──────────────────────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("🤗 How to get your free API keys"):
        st.markdown("""
**Hugging Face (AI image generation):**
1. [huggingface.co](https://huggingface.co) → Sign up free
2. Profile → Settings → Access Tokens → **New token (Read)**
3. Paste in Brand Kit above
- Free tier: ~50-100 images/month · Model: FLUX.1-schnell (4-step, ~20s)

**Groq (fast LLM — copy generation + prompt enhancement):**
1. [console.groq.com](https://console.groq.com) → Sign up free
2. API Keys → Create key
- Free: generous daily limits · Model: llama-3.3-70b

**Gemini (LLM fallback — if no Groq key):**
1. [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) → Sign in with Google
2. Create API key (starts with `AIza`)
- Free: 250 requests/day, no credit card
        """)

    with st.expander("💡 Image prompt tips for stunning travel banners"):
        st.markdown("""
**Include in every scene description:**
- Time of day: *golden hour, sunrise, blue hour, starry night, midday*
- Atmosphere: *dramatic clouds, misty, crystal clear, hazy, magical*
- Composition: *wide angle, aerial view, close-up, panoramic, bird's eye*
- Add always: **no text, no watermark, no people**

**Great example prompts:**
> *Taj Mahal at golden sunrise, reflection in fountain pool, dramatic orange sky, wide angle, 8k, no text, no people*

> *Traditional Kerala houseboat on tranquil backwaters, lush coconut palms, golden sunset reflection, cinematic, no text*

> *Baga Beach Goa, turquoise waves, palm trees swaying, tropical paradise, aerial drone shot, no people*
        """)
