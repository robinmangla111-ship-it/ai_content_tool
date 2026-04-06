"""
🏖️ AI Travel Content Creator
===============================
- AI generates the background image from your prompt (Hugging Face FLUX.1-schnell)
- LLM enhances your prompt for better image quality (Groq - already in app)
- Pillow composites: logo, cert badge, text, social links
- Single banner OR multi-screen video slideshow (20-30s animated GIF)
- Reusable brand kit: logo + cert badge saved in session
- All platforms: YouTube, Instagram, Facebook, WhatsApp
- 100% free tools
"""

import streamlit as st
import sys, os, io, json, time, base64, zipfile
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ── Key helpers ───────────────────────────────────────────────────────────────

def _get(sk, sec, env):
    v = st.session_state.get(sk, "").strip()
    if v: return v
    try:
        v = str(st.secrets.get(sec, "")).strip()
        if v: return v
    except Exception:
        pass
    return os.getenv(env, "").strip()

def _hf_key():   return _get("hf_token",  "HF_TOKEN",      "HF_TOKEN")
def _llm_key():  return _get("api_key",   "GROQ_API_KEY",  "GROQ_API_KEY")

# ── Platform sizes ────────────────────────────────────────────────────────────

PLATFORMS = {
    "Instagram Post (1:1)":          (1080, 1080),
    "Instagram / Reels Story (9:16)": (1080, 1920),
    "YouTube Thumbnail (16:9)":       (1280,  720),
    "YouTube Shorts (9:16)":          (1080, 1920),
    "Facebook Post (1.91:1)":         (1200,  630),
    "WhatsApp Status (9:16)":         (1080, 1920),
    "Twitter/X Post (16:9)":          (1200,  675),
    "LinkedIn Post (1.91:1)":         (1200,  628),
}

# ── Travel image styles ───────────────────────────────────────────────────────

IMG_STYLES = {
    "📸 Photorealistic":      "ultra-realistic travel photography, golden hour lighting, professional DSLR, 8k, sharp",
    "🎨 Cinematic":           "cinematic wide shot, dramatic lighting, film grain, movie still, anamorphic lens",
    "✏️ Illustration":        "digital illustration, vibrant colors, travel poster style, flat design with depth",
    "🌅 Aerial / Drone":      "aerial drone photography, bird's eye view, stunning landscape, vivid colors",
    "🖼️ Vintage Poster":      "vintage travel poster, retro art deco style, bold colors, classic typography aesthetic",
    "🌙 Night / Moody":       "night photography, city lights, long exposure, moody atmosphere, neon reflections",
    "🏺 Cultural / Artistic": "cultural artistic style, folk art inspired, rich textures, warm earthy tones",
}

# ── Font loader ───────────────────────────────────────────────────────────────

def _font(size: int, bold: bool = False):
    paths = [
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf",
        f"/usr/share/fonts/truetype/liberation/LiberationSans{'-Bold' if bold else '-Regular'}.ttf",
        f"/usr/share/fonts/truetype/ubuntu/Ubuntu-{'B' if bold else 'R'}.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            try: return ImageFont.truetype(p, size)
            except: pass
    return ImageFont.load_default()

# ── LLM prompt enhancer ───────────────────────────────────────────────────────

def enhance_prompt(user_prompt: str, style_suffix: str, destination: str) -> str:
    """Use Groq to turn a simple description into a rich image generation prompt."""
    key = _llm_key()
    if not key:
        return f"{user_prompt}, {destination}, {style_suffix}, no text, no watermark"

    system = (
        "You are an expert at writing Stable Diffusion / FLUX image generation prompts. "
        "Turn the user's travel description into a rich, detailed visual prompt. "
        "RULES: No people in the image. No text. No logos. Just scenery/place/atmosphere. "
        "Be very specific about lighting, time of day, composition, colors. "
        "Output ONLY the prompt, no explanation, max 120 words."
    )
    user = (
        f"Travel destination: {destination}\n"
        f"User description: {user_prompt}\n"
        f"Style requirement: {style_suffix}\n"
        "Write the image generation prompt:"
    )
    try:
        from groq import Groq
        client = Groq(api_key=key)
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"system","content":system},{"role":"user","content":user}],
            max_tokens=200, temperature=0.7,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return f"{user_prompt}, {destination}, {style_suffix}, no text, no watermark"


def generate_scene_captions(package_name: str, scenes: list[str], n: int) -> list[str]:
    """Generate short captions for each video scene."""
    key = _llm_key()
    if not key:
        return scenes[:n] if scenes else [f"Scene {i+1}" for i in range(n)]

    system = (
        "Generate short, punchy captions for travel video slides. "
        "Each caption max 6 words. Output ONLY a JSON array of strings, nothing else."
    )
    user = f"Package: {package_name}\nScenes: {scenes}\nGenerate {n} captions (one per scene):"
    try:
        from groq import Groq
        client = Groq(api_key=key)
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"system","content":system},{"role":"user","content":user}],
            max_tokens=200, temperature=0.8,
        )
        raw = resp.choices[0].message.content.strip()
        import re
        m = re.search(r'\[.*?\]', raw, re.DOTALL)
        return json.loads(m.group()) if m else scenes[:n]
    except Exception:
        return scenes[:n] if scenes else [f"Scene {i+1}" for i in range(n)]

# ── AI Image Generation via HF Inference API ─────────────────────────────────

def generate_ai_image(prompt: str, width: int, height: int) -> Image.Image | None:
    """
    Generate image via Hugging Face Inference API (FLUX.1-schnell).
    Free tier: ~100 small credits/month. Very fast model.
    Falls back to gradient placeholder if no key or quota exceeded.
    """
    hf_key = _hf_key()
    if not hf_key:
        return None   # caller will use gradient fallback

    # HF Inference API endpoint for FLUX.1-schnell
    url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
    headers = {"Authorization": f"Bearer {hf_key}"}

    # HF returns image at 1024x1024 or similar — we resize after
    payload = {
        "inputs": prompt,
        "parameters": {
            "width":  min(width,  1024),
            "height": min(height, 1024),
            "num_inference_steps": 4,   # schnell = 4 steps is enough
        }
    }

    try:
        r = requests.post(url, headers=headers, json=payload, timeout=90)
        if r.status_code == 200 and r.headers.get("content-type","").startswith("image"):
            img = Image.open(io.BytesIO(r.content)).convert("RGBA")
            # Resize to target canvas (cover crop)
            ratio  = max(width / img.width, height / img.height)
            nw, nh = int(img.width * ratio), int(img.height * ratio)
            img    = img.resize((nw, nh), Image.LANCZOS)
            left   = (nw - width)  // 2
            top    = (nh - height) // 2
            return img.crop((left, top, left + width, top + height))
        elif r.status_code == 503:
            st.warning("⏳ HF model loading (cold start) — retrying in 15s...")
            time.sleep(15)
            r2 = requests.post(url, headers=headers, json=payload, timeout=90)
            if r2.status_code == 200:
                img = Image.open(io.BytesIO(r2.content)).convert("RGBA")
                ratio  = max(width / img.width, height / img.height)
                nw, nh = int(img.width * ratio), int(img.height * ratio)
                img    = img.resize((nw, nh), Image.LANCZOS)
                left   = (nw - width) // 2
                top    = (nh - height) // 2
                return img.crop((left, top, left + width, top + height))
        elif r.status_code == 401:
            st.error("❌ Invalid HF token (401). Check your Hugging Face API token.")
        elif r.status_code == 429:
            st.warning("⚠️ HF free quota reached. Using gradient background instead.")
        else:
            st.warning(f"HF API returned {r.status_code}. Using gradient background.")
        return None
    except Exception as e:
        st.warning(f"Image generation failed ({e}). Using gradient background.")
        return None


def _gradient_bg(w: int, h: int, c1=(20,40,80), c2=(80,20,60)) -> Image.Image:
    img  = Image.new("RGBA", (w, h))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t = y / h
        r = int(c1[0] + (c2[0]-c1[0])*t)
        g = int(c1[1] + (c2[1]-c1[1])*t)
        b = int(c1[2] + (c2[2]-c1[2])*t)
        draw.line([(0,y),(w,y)], fill=(r,g,b,255))
    return img

# ── Compositing helpers ───────────────────────────────────────────────────────

def _overlay(img: Image.Image, alpha: int = 140) -> Image.Image:
    """Dark overlay for text readability."""
    ov = Image.new("RGBA", img.size, (0, 0, 0, alpha))
    return Image.alpha_composite(img.convert("RGBA"), ov)


def _wrap(text, font, max_w, draw):
    words = text.split()
    lines, line = [], ""
    for w in words:
        test = (line + " " + w).strip()
        if draw.textbbox((0,0), test, font=font)[2] <= max_w:
            line = test
        else:
            if line: lines.append(line)
            line = w
    if line: lines.append(line)
    return "\n".join(lines)


def _shadow_text(draw, xy, text, font, fill, shadow=3):
    draw.text((xy[0]+shadow, xy[1]+shadow), text, font=font, fill=(0,0,0,160))
    draw.text(xy, text, font=font, fill=fill)


def _pill(draw, x, y, text, font, bg, fg, pad=14):
    bb   = draw.textbbox((0,0), text, font=font)
    tw   = bb[2]-bb[0]; th = bb[3]-bb[1]
    r    = (th + pad) // 2
    draw.rounded_rectangle([x, y, x+tw+pad*2, y+th+pad], radius=r, fill=bg)
    draw.text((x+pad, y+pad//2), text, font=font, fill=fg)
    return x + tw + pad*2


def _paste_asset(canvas: Image.Image, asset_bytes: bytes,
                 position: str, max_px: int, bottom_reserve: int = 56) -> Image.Image:
    """Paste logo or cert badge at given position."""
    asset = Image.open(io.BytesIO(asset_bytes)).convert("RGBA")
    r     = min(max_px / asset.width, max_px / asset.height)
    nw, nh = int(asset.width*r), int(asset.height*r)
    asset  = asset.resize((nw, nh), Image.LANCZOS)
    W, H   = canvas.size
    m = 20
    pos_map = {
        "Top Left":     (m, m),
        "Top Right":    (W-nw-m, m),
        "Bottom Left":  (m, H-nh-m-bottom_reserve),
        "Bottom Right": (W-nw-m, H-nh-m-bottom_reserve),
    }
    x, y = pos_map.get(position, (W-nw-m, m))
    canvas.paste(asset, (x, y), asset)
    return canvas


def _social_bar(draw, w, h, fb, insta, web, accent_rgb, font):
    bh = 56
    draw.rectangle([0, h-bh, w, h], fill=(0,0,0,170))
    items = []
    if fb:    items.append(f"f  {fb}")
    if insta: items.append(f"@  {insta}")
    if web:   items.append(f"  {web}")
    if not items: return
    line  = "   ·   ".join(items)
    bb    = draw.textbbox((0,0), line, font=font)
    tw    = bb[2]-bb[0]
    tx    = (w - tw) // 2
    ty    = h - bh + (bh - (bb[3]-bb[1])) // 2
    draw.text((tx, ty), line, font=font, fill=accent_rgb+(255,))

# ── Full banner composer ──────────────────────────────────────────────────────

def compose_banner(
    bg_img: Image.Image | None,    # already sized or None → gradient
    w: int, h: int,
    # text fields
    package_name: str = "",
    headline: str = "",
    subheadline: str = "",
    highlights: list[str] = None,
    price: str = "",
    cta: str = "",
    caption: str = "",             # for video frames
    # brand
    logo_bytes: bytes | None = None,
    logo_pos: str = "Top Right",
    cert_bytes: bytes | None = None,
    # social
    fb: str = "", insta: str = "", web: str = "",
    # style
    overlay_alpha: int = 140,
    accent: tuple = (255, 200, 50),
    text_color: tuple = (255, 255, 255),
    show_price_pill: bool = True,
) -> Image.Image:

    highlights = highlights or []

    # Background
    if bg_img is None:
        canvas = _gradient_bg(w, h, (15,40,80), (60,15,50))
    else:
        canvas = bg_img.copy().convert("RGBA")
    canvas = _overlay(canvas, overlay_alpha)

    draw   = ImageDraw.Draw(canvas)
    sc     = min(w, h) / 1080       # scale factor
    margin = int(55 * sc)
    mw     = w - margin * 2        # max text width
    cy     = int(55 * sc)

    # Fonts
    fT  = _font(int(74*sc), bold=True)   # title
    fS  = _font(int(40*sc), bold=False)  # subtitle
    fH  = _font(int(30*sc), bold=False)  # highlights
    fP  = _font(int(58*sc), bold=True)   # price
    fC  = _font(int(36*sc), bold=True)   # CTA
    fSm = _font(int(24*sc), bold=False)  # small / social

    white  = text_color + (255,)
    accent4= accent + (255,)

    # Package name pill
    if package_name:
        _pill(draw, margin, cy,
              f"  ✈  {package_name.upper()}  ", fSm,
              accent+(200,), (10,10,10,255), pad=16)
        cy += int(56*sc)
        draw.rectangle([margin, cy, margin+int(70*sc), cy+4], fill=accent4)
        cy += int(20*sc)

    # Headline
    if headline:
        wrapped = _wrap(headline, fT, mw, draw)
        _shadow_text(draw, (margin, cy), wrapped, fT, white)
        bb = draw.multiline_textbbox((margin,cy), wrapped, font=fT)
        cy += bb[3]-bb[1] + int(14*sc)

    # Subheadline
    if subheadline:
        wrapped = _wrap(subheadline, fS, mw, draw)
        _shadow_text(draw, (margin, cy), wrapped, fS, accent4)
        bb = draw.multiline_textbbox((margin,cy), wrapped, font=fS)
        cy += bb[3]-bb[1] + int(28*sc)

    # Highlights
    for hl in highlights[:6]:
        line = f"  ✓  {hl}"
        _shadow_text(draw, (margin, cy), line, fH, white)
        bb = draw.textbbox((margin,cy), line, font=fH)
        cy += bb[3]-bb[1] + int(6*sc)
    if highlights:
        cy += int(18*sc)

    # Price
    if price and show_price_pill:
        _shadow_text(draw, (margin, cy), f"From  {price}", fP, accent4)
        bb = draw.textbbox((margin,cy), f"From  {price}", font=fP)
        cy += bb[3]-bb[1] + int(22*sc)

    # CTA
    if cta:
        _pill(draw, margin, cy, f"  {cta}  ", fC,
              accent+(230,), (20,20,20,255), pad=20)

    # Caption (for video frames — shown at bottom centre)
    if caption:
        bb   = draw.textbbox((0,0), caption, font=fC)
        tw   = bb[2]-bb[0]
        tx   = (w - tw) // 2
        ty   = h - int(120*sc)
        draw.rounded_rectangle(
            [tx-20, ty-10, tx+tw+20, ty+(bb[3]-bb[1])+10],
            radius=10, fill=(0,0,0,160)
        )
        draw.text((tx, ty), caption, font=fC, fill=white)

    # Social bar
    _social_bar(draw, w, h, fb, insta, web, accent, fSm)

    # Logo
    if logo_bytes:
        canvas = _paste_asset(canvas, logo_bytes, logo_pos,
                              max_px=int(130*sc), bottom_reserve=60)

    # Cert badge (always bottom-left)
    if cert_bytes:
        canvas = _paste_asset(canvas, cert_bytes, "Bottom Left",
                              max_px=int(90*sc), bottom_reserve=60)

    return canvas.convert("RGB")


def img_bytes(img: Image.Image, fmt="PNG") -> bytes:
    buf = io.BytesIO()
    img.save(buf, format=fmt, quality=95)
    return buf.getvalue()


def make_gif(frames: list[Image.Image], fps_duration_ms: int = 2500) -> bytes:
    """Convert list of PIL Images → animated GIF bytes."""
    # Resize to 540-wide for manageable file size
    thumbs = []
    for f in frames:
        w, h = f.size
        scale = 540 / w
        thumbs.append(f.resize((int(w*scale), int(h*scale)), Image.LANCZOS))
    buf = io.BytesIO()
    thumbs[0].save(
        buf, format="GIF", save_all=True,
        append_images=thumbs[1:],
        duration=fps_duration_ms, loop=0, optimize=True,
    )
    return buf.getvalue()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE
# ─────────────────────────────────────────────────────────────────────────────

def render():
    st.markdown("# 🏖️ AI Travel Content Creator")
    st.markdown(
        "Describe your travel package → AI generates the scene → "
        "Your logo & branding composited automatically → Download for any platform."
    )

    # ── BRAND KIT (persistent in session) ────────────────────────────────────
    with st.expander("🏷️ Brand Kit — Logo, Cert & Social Links (saved for all content)", expanded=False):
        bk_col1, bk_col2, bk_col3 = st.columns(3)
        with bk_col1:
            st.markdown("**Company Logo**")
            logo_up = st.file_uploader("Upload logo (PNG transparent preferred)",
                                        type=["png","jpg","jpeg"], key="bk_logo")
            if logo_up:
                st.session_state["brand_logo"] = logo_up.read()
                st.image(st.session_state["brand_logo"], width=120)
            elif st.session_state.get("brand_logo"):
                st.image(st.session_state["brand_logo"], width=120, caption="Saved ✓")

        with bk_col2:
            st.markdown("**Certification Badge**")
            cert_up = st.file_uploader("Upload cert/award badge",
                                        type=["png","jpg","jpeg"], key="bk_cert")
            if cert_up:
                st.session_state["brand_cert"] = cert_up.read()
                st.image(st.session_state["brand_cert"], width=80)
            elif st.session_state.get("brand_cert"):
                st.image(st.session_state["brand_cert"], width=80, caption="Saved ✓")

        with bk_col3:
            st.markdown("**Social Links**")
            fb_val    = st.text_input("Facebook page",    value=st.session_state.get("bk_fb",""),    key="_bk_fb")
            insta_val = st.text_input("Instagram handle", value=st.session_state.get("bk_insta",""), key="_bk_insta")
            web_val   = st.text_input("Website",          value=st.session_state.get("bk_web",""),   key="_bk_web")
            if st.button("💾 Save Brand Kit"):
                st.session_state["bk_fb"]    = fb_val
                st.session_state["bk_insta"] = insta_val
                st.session_state["bk_web"]   = web_val
                st.success("Brand kit saved for this session!")

        # HF token
        st.markdown("---")
        hf_col1, hf_col2 = st.columns([3,1])
        with hf_col1:
            hf_tok = st.text_input(
                "🤗 Hugging Face Token (for AI image generation)",
                type="password",
                value=st.session_state.get("hf_token",""),
                placeholder="hf_xxxxxxxxxxxxxxxxxxxxxxxxxx",
                help="Free at huggingface.co → Settings → Access Tokens → New token (read)",
            )
            if hf_tok:
                st.session_state["hf_token"] = hf_tok.strip()
        with hf_col2:
            st.markdown("<br>", unsafe_allow_html=True)
            if not _hf_key():
                st.warning("No HF token → gradient background used")
            else:
                st.success("HF token set ✓")

    st.markdown("---")

    # ── TABS ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs([
        "🖼️ Single Banner",
        "🎬 Video Slideshow (20-30s)",
        "📦 Bulk Export (all platforms)",
    ])

    # Pull brand kit from session
    logo_bytes = st.session_state.get("brand_logo")
    cert_bytes = st.session_state.get("brand_cert")
    fb         = st.session_state.get("bk_fb", "")
    insta      = st.session_state.get("bk_insta", "")
    web        = st.session_state.get("bk_web", "")

    # ════════════════════════════════════════════════════════════════════════
    # TAB 1: SINGLE BANNER
    # ════════════════════════════════════════════════════════════════════════
    with tab1:
        c_left, c_right = st.columns([1, 1], gap="large")

        with c_left:
            st.markdown("### 🎨 AI Image Prompt")
            destination = st.text_input("Destination / Location",
                                        placeholder="Rajasthan, India · Bali, Indonesia")
            prompt_desc = st.text_area(
                "Describe the scene you want AI to generate",
                height=90,
                placeholder=(
                    "Majestic Amber Fort at golden sunset, Rajasthan desert landscape, "
                    "camel silhouettes, warm orange sky"
                ),
            )
            img_style   = st.selectbox("Image style", list(IMG_STYLES.keys()))
            enhance_btn = st.checkbox("✨ Auto-enhance prompt with AI (uses Groq)", value=True)

            st.markdown("### 📐 Format")
            platform  = st.selectbox("Platform", list(PLATFORMS.keys()))
            w, h      = PLATFORMS[platform]

            st.markdown("### ✍️ Package Content")
            pkg_name   = st.text_input("Package name", placeholder="Royal Rajasthan — 7 Days")
            headline   = st.text_input("Headline",     placeholder="Discover the Land of Maharajas")
            subline    = st.text_input("Subheadline",  placeholder="Heritage · Desert · Culture")
            price      = st.text_input("Price",        placeholder="₹29,999/person")
            cta_text   = st.text_input("Call to action", value="Book Now →")
            hl_raw     = st.text_area("Highlights (one per line)",
                                      placeholder="Amber Fort Sunrise\nDesert Safari\nCamel Camp\nJaipur Markets",
                                      height=100)
            highlights = [l.strip() for l in hl_raw.splitlines() if l.strip()]

            st.markdown("### 🎨 Style")
            c1, c2 = st.columns(2)
            with c1: logo_pos = st.selectbox("Logo position",
                                             ["Top Right","Top Left","Bottom Right","Bottom Left"])
            with c2: overlay_alpha = st.slider("Overlay darkness", 80, 220, 140)

            gen_single = st.button("🚀 Generate Banner", type="primary", use_container_width=True)

        with c_right:
            st.markdown("### 👁️ Preview")

            if gen_single:
                if not prompt_desc.strip():
                    st.error("Please describe the scene first.")
                else:
                    with st.spinner("Step 1/3: Enhancing prompt with AI..."):
                        style_sfx = IMG_STYLES[img_style]
                        final_prompt = (
                            enhance_prompt(prompt_desc, style_sfx, destination)
                            if enhance_btn and _llm_key()
                            else f"{prompt_desc}, {destination}, {style_sfx}, no text"
                        )

                    st.caption(f"📝 Enhanced prompt: *{final_prompt[:120]}...*")

                    with st.spinner("Step 2/3: Generating AI image (15-30s)..."):
                        bg = generate_ai_image(final_prompt, w, h)

                    with st.spinner("Step 3/3: Compositing branding..."):
                        banner = compose_banner(
                            bg_img=bg, w=w, h=h,
                            package_name=pkg_name, headline=headline,
                            subheadline=subline, highlights=highlights,
                            price=price, cta=cta_text,
                            logo_bytes=logo_bytes, logo_pos=logo_pos,
                            cert_bytes=cert_bytes,
                            fb=fb, insta=insta, web=web,
                            overlay_alpha=overlay_alpha,
                        )

                    b = img_bytes(banner)
                    st.session_state["s_banner"] = b
                    st.session_state["s_name"]   = f"{pkg_name or 'banner'}_{platform[:12]}.png"

            if st.session_state.get("s_banner"):
                st.image(st.session_state["s_banner"], use_container_width=True)
                st.download_button(
                    "📥 Download PNG",
                    data=st.session_state["s_banner"],
                    file_name=st.session_state.get("s_name","banner.png"),
                    mime="image/png",
                    use_container_width=True,
                )
            else:
                st.markdown("""
                <div style="border:0.5px solid var(--color-border-tertiary);border-radius:12px;
                            padding:80px 20px;text-align:center">
                    <div style="font-size:48px">🤖</div>
                    <div style="color:var(--color-text-secondary);margin-top:12px;font-size:14px">
                        Describe a scene → AI generates it → your brand overlaid
                    </div>
                </div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # TAB 2: VIDEO SLIDESHOW
    # ════════════════════════════════════════════════════════════════════════
    with tab2:
        st.markdown("### 🎬 Multi-Scene Video (20-30 seconds)")
        st.info(
            "Each 'scene' = AI generates a different image + your caption overlaid. "
            "Output is an animated GIF (20-30s). Import into CapCut to add music "
            "and export as MP4 for YouTube Shorts / Reels."
        )

        vc_l, vc_r = st.columns([1, 1], gap="large")

        with vc_l:
            v_dest      = st.text_input("Destination", placeholder="Kerala, India", key="v_dest")
            v_pkg       = st.text_input("Package name", placeholder="Backwaters Bliss — 5 Days", key="v_pkg")
            v_platform  = st.selectbox("Format", [
                "Instagram / Reels Story (9:16)",
                "YouTube Shorts (9:16)",
                "Instagram Post (1:1)",
            ], key="v_plat")
            vw, vh      = PLATFORMS[v_platform]
            v_style     = st.selectbox("Image style", list(IMG_STYLES.keys()), key="v_style")
            v_logo_pos  = st.selectbox("Logo position", ["Top Right","Top Left"], key="v_lpos")
            v_overlay   = st.slider("Overlay darkness", 80, 220, 150, key="v_ov")
            v_duration  = st.slider("Seconds per scene", 2, 5, 3, key="v_dur")

            st.markdown("### 🎞️ Scenes")
            st.caption("Each scene = one AI-generated image. Describe 4-8 scenes.")

            n_scenes = st.slider("Number of scenes", 3, 8, 5, key="v_nsc")

            scenes = []
            captions_input = []
            for i in range(n_scenes):
                sc, cp = st.columns([2, 1])
                with sc:
                    s = st.text_input(
                        f"Scene {i+1} — describe the image",
                        placeholder=["Houseboat at sunrise on backwaters",
                                     "Elephant at Periyar wildlife sanctuary",
                                     "Kathakali dance performance in temple",
                                     "Tea plantation in Munnar hills",
                                     "Beach at Varkala cliffs at golden hour"][i % 5],
                        key=f"sc_{i}",
                    )
                    scenes.append(s)
                with cp:
                    c = st.text_input(
                        "Caption",
                        placeholder=["Houseboat Sunrise","Wildlife Safari",
                                     "Cultural Show","Tea Highlands","Clifftop Beach"][i % 5],
                        key=f"cp_{i}",
                    )
                    captions_input.append(c)

            v_price  = st.text_input("Price", placeholder="₹22,999/person", key="v_price")
            v_gen_cp = st.checkbox("✨ AI auto-generates captions from scene descriptions", value=True)

            gen_video = st.button("🎬 Generate Video Slideshow", type="primary",
                                  use_container_width=True,
                                  disabled=not any(scenes))

        with vc_r:
            st.markdown("### 👁️ Slideshow Preview")

            if gen_video:
                valid_scenes = [(s.strip(), captions_input[i]) for i, s in enumerate(scenes) if s.strip()]
                if not valid_scenes:
                    st.error("Fill in at least one scene description.")
                else:
                    # Generate AI captions if requested
                    if v_gen_cp and _llm_key():
                        with st.spinner("Generating scene captions with AI..."):
                            scene_descs = [s for s, _ in valid_scenes]
                            ai_caps = generate_scene_captions(v_pkg, scene_descs, len(valid_scenes))
                    else:
                        ai_caps = [c for _, c in valid_scenes]

                    style_sfx = IMG_STYLES[v_style]
                    frames    = []
                    prog      = st.progress(0, text="Generating scenes...")

                    for idx, (scene_desc, _) in enumerate(valid_scenes):
                        prog.progress((idx) / len(valid_scenes),
                                      text=f"Scene {idx+1}/{len(valid_scenes)}: generating image...")

                        # Enhance prompt
                        full_prompt = (
                            enhance_prompt(scene_desc, style_sfx, v_dest)
                            if _llm_key()
                            else f"{scene_desc}, {v_dest}, {style_sfx}, no text"
                        )

                        # Generate image
                        bg = generate_ai_image(full_prompt, vw, vh)

                        # Caption for this frame
                        cap = ai_caps[idx] if idx < len(ai_caps) else scene_desc[:30]

                        # Compose frame — only show caption + logo + social on video frames
                        frame = compose_banner(
                            bg_img=bg, w=vw, h=vh,
                            package_name=v_pkg if idx == 0 else "",
                            headline="" if idx > 0 else v_pkg,
                            subheadline="",
                            highlights=[],
                            price=v_price if idx == len(valid_scenes)-1 else "",
                            cta="Book Now →" if idx == len(valid_scenes)-1 else "",
                            caption=cap,
                            logo_bytes=logo_bytes,
                            logo_pos=v_logo_pos,
                            cert_bytes=cert_bytes,
                            fb=fb, insta=insta, web=web,
                            overlay_alpha=v_overlay,
                        )
                        frames.append(frame)

                    prog.progress(1.0, text="Building animated GIF...")
                    gif = make_gif(frames, fps_duration_ms=v_duration * 1000)
                    st.session_state["v_gif"]    = gif
                    st.session_state["v_frames"] = [img_bytes(f) for f in frames]
                    st.session_state["v_pkg"]    = v_pkg
                    prog.empty()
                    st.success(f"✅ {len(frames)}-scene slideshow · {len(gif)//1024} KB")

            gif = st.session_state.get("v_gif")
            if gif:
                b64 = base64.b64encode(gif).decode()
                st.markdown(
                    f'<img src="data:image/gif;base64,{b64}" style="width:100%;border-radius:8px">',
                    unsafe_allow_html=True,
                )
                st.download_button(
                    "📥 Download GIF",
                    data=gif,
                    file_name=f"{st.session_state.get('v_pkg','video')}_slideshow.gif",
                    mime="image/gif",
                    use_container_width=True,
                )

                # Download individual frames as ZIP
                if st.session_state.get("v_frames"):
                    zbuf = io.BytesIO()
                    with zipfile.ZipFile(zbuf, "w") as zf:
                        for i, fb_bytes in enumerate(st.session_state["v_frames"]):
                            zf.writestr(f"scene_{i+1:02d}.png", fb_bytes)
                    zbuf.seek(0)
                    st.download_button(
                        "📥 Download Individual Frames (ZIP)",
                        data=zbuf.getvalue(),
                        file_name="frames.zip",
                        mime="application/zip",
                        use_container_width=True,
                    )

                st.markdown("---")
                st.markdown("### 🎵 Add Music & Export as MP4")
                st.markdown("""
**Free music + MP4 workflow:**
1. Import your GIF into **[CapCut](https://capcut.com)** (free)
2. Add free music from CapCut's library or upload your own
3. Adjust timing (target 20-30 seconds total)
4. Export as **1080×1920 MP4** → upload to Shorts/Reels

**Free royalty-free music sources:**
- [YouTube Audio Library](https://studio.youtube.com/channel/music) — 100% free
- [Pixabay Music](https://pixabay.com/music/) — free, no attribution
- [Mixkit](https://mixkit.co/free-stock-music/) — free for social media
                """)
            else:
                st.markdown("""
                <div style="border:0.5px solid var(--color-border-tertiary);border-radius:12px;
                            padding:80px 20px;text-align:center">
                    <div style="font-size:48px">🎬</div>
                    <div style="color:var(--color-text-secondary);margin-top:12px;font-size:14px">
                        Add scenes → Generate → Download GIF → Add music in CapCut
                    </div>
                </div>""", unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # TAB 3: BULK EXPORT
    # ════════════════════════════════════════════════════════════════════════
    with tab3:
        st.markdown("### 📦 One prompt → All platform sizes")
        st.info("Generate once, download a ZIP with your banner in every platform format.")

        b_l, b_r = st.columns([1, 1], gap="large")

        with b_l:
            b_dest   = st.text_input("Destination",   placeholder="Goa, India", key="b_dest")
            b_prompt = st.text_area("Scene description", height=80,
                                    placeholder="Pristine white sand beach, turquoise sea, palm trees, golden sunset",
                                    key="b_prompt")
            b_style  = st.selectbox("Style", list(IMG_STYLES.keys()), key="b_style")
            b_pkg    = st.text_input("Package name",  placeholder="Goa Beach Holiday — 5N/6D", key="b_pkg")
            b_head   = st.text_input("Headline",      placeholder="Sun, Sand & Sea", key="b_head")
            b_sub    = st.text_input("Subheadline",   placeholder="All-inclusive from Mumbai", key="b_sub")
            b_price  = st.text_input("Price",         placeholder="₹18,999/person", key="b_price")
            b_cta    = st.text_input("CTA",           value="Book Now →", key="b_cta")
            b_hl     = st.text_area("Highlights",     height=80, key="b_hl",
                                    placeholder="Baga Beach\nWater Sports\nSunset Cruise")
            b_lpos   = st.radio("Logo position",
                                ["Top Right","Top Left","Bottom Right","Bottom Left"],
                                horizontal=True, key="b_lpos")
            b_plats  = st.multiselect("Export for", list(PLATFORMS.keys()),
                                      default=list(PLATFORMS.keys())[:4])
            b_gen    = st.button("📦 Generate All Sizes", type="primary",
                                 use_container_width=True, disabled=not b_plats)

        with b_r:
            st.markdown("### 📋 Results")

            if b_gen and b_plats:
                b_highlights = [l.strip() for l in b_hl.splitlines() if l.strip()]

                # Generate the AI image ONCE at highest resolution, then resize per platform
                with st.spinner("Step 1/2: Generating AI image..."):
                    style_sfx    = IMG_STYLES[b_style]
                    final_prompt = (
                        enhance_prompt(b_prompt, style_sfx, b_dest)
                        if _llm_key()
                        else f"{b_prompt}, {b_dest}, {style_sfx}, no text"
                    )
                    # Generate at 1024×1024 (max HF free), crop per platform later
                    master_bg = generate_ai_image(final_prompt, 1024, 1024)

                with st.spinner(f"Step 2/2: Compositing {len(b_plats)} banners..."):
                    zbuf = io.BytesIO()
                    with zipfile.ZipFile(zbuf, "w") as zf:
                        for p_name in b_plats:
                            pw, ph = PLATFORMS[p_name]
                            # Resize master for this platform
                            if master_bg:
                                ratio = max(pw/master_bg.width, ph/master_bg.height)
                                nw, nh = int(master_bg.width*ratio), int(master_bg.height*ratio)
                                bg_r   = master_bg.resize((nw, nh), Image.LANCZOS)
                                left   = (nw-pw)//2; top = (nh-ph)//2
                                bg_crop = bg_r.crop((left, top, left+pw, top+ph))
                            else:
                                bg_crop = None

                            banner = compose_banner(
                                bg_img=bg_crop, w=pw, h=ph,
                                package_name=b_pkg, headline=b_head,
                                subheadline=b_sub, highlights=b_highlights,
                                price=b_price, cta=b_cta,
                                logo_bytes=logo_bytes, logo_pos=b_lpos,
                                cert_bytes=cert_bytes,
                                fb=fb, insta=insta, web=web,
                            )
                            safe = p_name.split("(")[0].strip().replace(" ","_")
                            zf.writestr(f"{b_pkg or 'banner'}_{safe}_{pw}x{ph}.png",
                                        img_bytes(banner))

                    zbuf.seek(0)

                # Preview first one
                first_w, first_h = PLATFORMS[b_plats[0]]
                if master_bg:
                    ratio = max(first_w/master_bg.width, first_h/master_bg.height)
                    nw, nh = int(master_bg.width*ratio), int(master_bg.height*ratio)
                    bg_r   = master_bg.resize((nw, nh), Image.LANCZOS)
                    left   = (nw-first_w)//2; top = (nh-first_h)//2
                    bg_p   = bg_r.crop((left, top, left+first_w, top+first_h))
                else:
                    bg_p = None

                preview = compose_banner(
                    bg_img=bg_p, w=first_w, h=first_h,
                    package_name=b_pkg, headline=b_head, subheadline=b_sub,
                    highlights=b_highlights, price=b_price, cta=b_cta,
                    logo_bytes=logo_bytes, logo_pos=b_lpos,
                    cert_bytes=cert_bytes, fb=fb, insta=insta, web=web,
                )
                st.image(img_bytes(preview), caption=b_plats[0], use_container_width=True)
                st.success(f"✅ {len(b_plats)} banners ready!")
                st.download_button(
                    "📥 Download ZIP (all sizes)",
                    data=zbuf.getvalue(),
                    file_name=f"{b_pkg or 'banners'}_all_platforms.zip",
                    mime="application/zip",
                    use_container_width=True,
                )
            else:
                st.markdown("""
                <div style="border:0.5px solid var(--color-border-tertiary);border-radius:12px;
                            padding:80px 20px;text-align:center">
                    <div style="font-size:48px">📦</div>
                    <div style="color:var(--color-text-secondary);margin-top:12px;font-size:14px">
                        One AI image → resized for every platform → ZIP download
                    </div>
                </div>""", unsafe_allow_html=True)

    # ── Tips ──────────────────────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("🤗 How to get your free Hugging Face token"):
        st.markdown("""
1. Go to **[huggingface.co](https://huggingface.co)** → Sign up free (no credit card)
2. Click your profile → **Settings** → **Access Tokens**
3. Click **New token** → Type: **Read** → Name it anything → **Generate**
4. Copy the token (starts with `hf_`) → paste it in the Brand Kit section above

**Free tier:** HF gives you a small monthly credit (enough for ~50-100 images/month).
For more images, the cheapest paid option is ~$9/month.

**Model used:** `FLUX.1-schnell` — fastest high-quality free model (4 inference steps, ~20s/image)
        """)

    with st.expander("💡 Prompt writing tips for travel images"):
        st.markdown("""
**Good prompts include:**
- Time of day: *golden hour, blue hour, midday sun, starry night*
- Atmosphere: *misty, dramatic clouds, crystal clear, hazy sunrise*
- Composition: *wide angle, aerial view, close-up texture, panoramic*
- Quality tags: *ultra-realistic, 8k, sharp details, professional photography*

**Always add:** `no text, no watermark, no people` to keep images clean for overlay

**Example for Taj Mahal:**
> *Taj Mahal at golden sunrise, reflection in fountain pool, dramatic orange sky, ultra-realistic photography, wide angle, 8k, no text, no people*

**Example for Kerala backwaters:**
> *Traditional Kerala houseboat on tranquil backwaters, lush green coconut palms, golden sunset reflection, cinematic wide shot, ultra-realistic, 8k, no text*
        """)
