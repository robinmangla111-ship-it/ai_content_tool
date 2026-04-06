import streamlit as st
import sys, os, io, zipfile, textwrap, math, requests, base64
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ─────────────────────────────────────────────────────────────────────────────
# SIZES for every platform
# ─────────────────────────────────────────────────────────────────────────────
SIZES = {
    "YouTube Thumbnail (1280×720)":     (1280, 720),
    "YouTube Shorts / TikTok (1080×1920)": (1080, 1920),
    "Instagram Post Square (1080×1080)": (1080, 1080),
    "Instagram Reel (1080×1920)":        (1080, 1920),
    "Instagram Story (1080×1920)":       (1080, 1920),
    "Facebook Post (1200×630)":          (1200, 630),
    "Facebook Cover (820×312)":          (820, 312),
    "Twitter/X Post (1200×675)":         (1200, 675),
    "LinkedIn Banner (1584×396)":        (1584, 396),
    "WhatsApp Status (1080×1920)":       (1080, 1920),
}

# ─────────────────────────────────────────────────────────────────────────────
# TRAVEL THEMES — gradient colours + accent
# ─────────────────────────────────────────────────────────────────────────────
THEMES = {
    "🌅 Sunset Gold":       {"overlay": (180, 80,  20,  160), "accent": (255, 200, 50),  "text": (255, 255, 255)},
    "🌊 Ocean Blue":        {"overlay": (10,  60,  120, 160), "accent": (0,   200, 220),  "text": (255, 255, 255)},
    "🌿 Jungle Green":      {"overlay": (20,  80,  40,  160), "accent": (100, 220, 100),  "text": (255, 255, 255)},
    "🏜️ Desert Sand":      {"overlay": (140, 100, 40,  155), "accent": (255, 180, 60),   "text": (255, 255, 255)},
    "❄️ Arctic White":      {"overlay": (30,  60,  120, 140), "accent": (180, 230, 255),  "text": (255, 255, 255)},
    "🌸 Cherry Blossom":    {"overlay": (160, 40,  80,  150), "accent": (255, 180, 200),  "text": (255, 255, 255)},
    "🖤 Dark Luxury":       {"overlay": (10,  10,  20,  190), "accent": (220, 180, 80),   "text": (255, 255, 255)},
    "☀️ Bright Summer":     {"overlay": (200, 120, 0,   140), "accent": (255, 240, 80),   "text": (255, 255, 255)},
    "🌙 Midnight Blue":     {"overlay": (15,  15,  60,  180), "accent": (100, 150, 255),  "text": (255, 255, 255)},
}

# ─────────────────────────────────────────────────────────────────────────────
# FONT loading — uses system fonts (always available on Streamlit Cloud)
# ─────────────────────────────────────────────────────────────────────────────

def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Load a system font, gracefully falling back to default."""
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
# CORE IMAGE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _load_bg(uploaded_file, w: int, h: int) -> Image.Image:
    """Load uploaded image, resize+crop to fill target canvas."""
    img = Image.open(uploaded_file).convert("RGBA")
    # scale to fill (cover)
    ratio = max(w / img.width, h / img.height)
    new_w, new_h = int(img.width * ratio), int(img.height * ratio)
    img = img.resize((new_w, new_h), Image.LANCZOS)
    # centre crop
    left = (new_w - w) // 2
    top  = (new_h - h) // 2
    return img.crop((left, top, left + w, top + h))


def _gradient_bg(w: int, h: int, c1: tuple, c2: tuple) -> Image.Image:
    """Create a vertical gradient background."""
    img  = Image.new("RGBA", (w, h))
    draw = ImageDraw.Draw(img)
    for y in range(h):
        t   = y / h
        r   = int(c1[0] + (c2[0] - c1[0]) * t)
        g   = int(c1[1] + (c2[1] - c1[1]) * t)
        b   = int(c1[2] + (c2[2] - c1[2]) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b, 255))
    return img


def _apply_overlay(img: Image.Image, colour: tuple) -> Image.Image:
    """Semi-transparent dark overlay for text readability."""
    overlay = Image.new("RGBA", img.size, colour)
    return Image.alpha_composite(img.convert("RGBA"), overlay)


def _wrap_text(text: str, font: ImageFont.FreeTypeFont,
               max_width: int, draw: ImageDraw.ImageDraw) -> str:
    """Word-wrap text to fit max_width pixels."""
    words  = text.split()
    lines  = []
    line   = ""
    for word in words:
        test = (line + " " + word).strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return "\n".join(lines)


def _draw_shadow_text(draw: ImageDraw.ImageDraw, pos: tuple, text: str,
                      font: ImageFont.FreeTypeFont, fill: tuple,
                      shadow_offset: int = 3):
    """Draw text with a drop shadow for readability."""
    sx, sy = pos[0] + shadow_offset, pos[1] + shadow_offset
    draw.text((sx, sy), text, font=font, fill=(0, 0, 0, 180))
    draw.text(pos, text, font=font, fill=fill)


def _draw_pill(draw: ImageDraw.ImageDraw, x: int, y: int,
               text: str, font: ImageFont.FreeTypeFont,
               bg: tuple, fg: tuple, padding: int = 12):
    """Draw a rounded pill/badge."""
    bbox  = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    rx1, ry1 = x, y
    rx2, ry2 = x + tw + padding * 2, y + th + padding
    r = (ry2 - ry1) // 2
    draw.rounded_rectangle([rx1, ry1, rx2, ry2], radius=r, fill=bg)
    draw.text((rx1 + padding, ry1 + padding // 2), text, font=font, fill=fg)
    return rx2  # return right edge for chaining


def _add_social_bar(draw: ImageDraw.ImageDraw, w: int, h: int,
                    fb: str, insta: str, web: str,
                    accent: tuple, font_sm: ImageFont.FreeTypeFont):
    """Draw social media links bar at bottom."""
    bar_h  = 48
    bar_y  = h - bar_h
    draw.rectangle([0, bar_y, w, h], fill=(0, 0, 0, 160))

    items  = []
    if fb:    items.append(f"f/ {fb}")
    if insta: items.append(f"@ {insta}")
    if web:   items.append(f"🌐 {web}")

    if not items:
        return

    full   = "   •   ".join(items)
    bbox   = draw.textbbox((0, 0), full, font=font_sm)
    tw     = bbox[2] - bbox[0]
    tx     = (w - tw) // 2
    ty     = bar_y + (bar_h - (bbox[3] - bbox[1])) // 2
    draw.text((tx, ty), full, font=font_sm, fill=accent + (255,))


def _paste_logo(canvas: Image.Image, logo_file, position: str,
                max_size: int = 120) -> Image.Image:
    """Paste logo onto canvas at chosen corner."""
    logo = Image.open(logo_file).convert("RGBA")
    # Scale keeping aspect ratio
    ratio = min(max_size / logo.width, max_size / logo.height)
    nw, nh = int(logo.width * ratio), int(logo.height * ratio)
    logo = logo.resize((nw, nh), Image.LANCZOS)

    margin = 20
    W, H   = canvas.size
    positions = {
        "Top Left":     (margin, margin),
        "Top Right":    (W - nw - margin, margin),
        "Bottom Left":  (margin, H - nh - margin - 48),
        "Bottom Right": (W - nw - margin, H - nh - margin - 48),
    }
    x, y = positions.get(position, positions["Top Right"])
    canvas.paste(logo, (x, y), logo)
    return canvas


def _paste_cert_badge(canvas: Image.Image, cert_file,
                      max_size: int = 90) -> Image.Image:
    """Paste certification badge in bottom-left corner."""
    badge = Image.open(cert_file).convert("RGBA")
    ratio = min(max_size / badge.width, max_size / badge.height)
    nw, nh = int(badge.width * ratio), int(badge.height * ratio)
    badge = badge.resize((nw, nh), Image.LANCZOS)
    W, H  = canvas.size
    canvas.paste(badge, (20, H - nh - 20 - 48), badge)
    return canvas


# ─────────────────────────────────────────────────────────────────────────────
# MAIN BANNER GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def generate_banner(
    w: int, h: int,
    theme: dict,
    bg_image=None,
    title: str = "",
    subtitle: str = "",
    package_name: str = "",
    price: str = "",
    highlights: list[str] = None,
    cta: str = "",
    fb: str = "", insta: str = "", website: str = "",
    logo_file=None, logo_pos: str = "Top Right",
    cert_file=None,
    show_divider: bool = True,
) -> Image.Image:

    highlights = highlights or []

    # ── Background ────────────────────────────────────────────────────────────
    if bg_image:
        canvas = _load_bg(bg_image, w, h)
    else:
        canvas = _gradient_bg(w, h, (20, 40, 80), (5, 15, 40))

    canvas = canvas.convert("RGBA")

    # ── Dark overlay for readability ──────────────────────────────────────────
    canvas = _apply_overlay(canvas, theme["overlay"])

    draw   = ImageDraw.Draw(canvas)
    accent = theme["accent"]
    white  = theme["text"]

    # ── Fonts — scale to canvas size ──────────────────────────────────────────
    scale    = min(w, h) / 1080
    f_title  = _font(int(72 * scale), bold=True)
    f_sub    = _font(int(40 * scale), bold=False)
    f_pkg    = _font(int(34 * scale), bold=True)
    f_price  = _font(int(56 * scale), bold=True)
    f_hl     = _font(int(30 * scale), bold=False)
    f_cta    = _font(int(38 * scale), bold=True)
    f_sm     = _font(int(24 * scale), bold=False)

    margin   = int(60 * scale)
    max_w    = w - margin * 2
    cy       = int(60 * scale)   # current y cursor

    # ── Package name pill ─────────────────────────────────────────────────────
    if package_name:
        _draw_pill(draw, margin, cy, f"✈  {package_name.upper()}",
                   f_sm, accent + (220,), (20, 20, 20, 255), padding=14)
        cy += int(52 * scale)

    # ── Divider line ──────────────────────────────────────────────────────────
    if show_divider and package_name:
        draw.rectangle([margin, cy, margin + int(80 * scale), cy + 4],
                       fill=accent + (255,))
        cy += int(18 * scale)

    # ── Title ─────────────────────────────────────────────────────────────────
    if title:
        wrapped = _wrap_text(title, f_title, max_w, draw)
        _draw_shadow_text(draw, (margin, cy), wrapped, f_title, white + (255,))
        bbox = draw.multiline_textbbox((margin, cy), wrapped, font=f_title)
        cy  += (bbox[3] - bbox[1]) + int(16 * scale)

    # ── Subtitle ──────────────────────────────────────────────────────────────
    if subtitle:
        wrapped = _wrap_text(subtitle, f_sub, max_w, draw)
        _draw_shadow_text(draw, (margin, cy), wrapped, f_sub,
                          accent + (255,))
        bbox = draw.multiline_textbbox((margin, cy), wrapped, font=f_sub)
        cy  += (bbox[3] - bbox[1]) + int(30 * scale)

    # ── Highlights (sights + activities) ─────────────────────────────────────
    if highlights:
        for hl in highlights[:6]:
            line = f"  ✓  {hl}"
            _draw_shadow_text(draw, (margin, cy), line, f_hl, white + (230,))
            bbox = draw.textbbox((margin, cy), line, font=f_hl)
            cy  += (bbox[3] - bbox[1]) + int(8 * scale)
        cy += int(20 * scale)

    # ── Price ─────────────────────────────────────────────────────────────────
    if price:
        price_text = f"From  {price}"
        _draw_shadow_text(draw, (margin, cy), price_text, f_price,
                          accent + (255,))
        bbox = draw.textbbox((margin, cy), price_text, font=f_price)
        cy  += (bbox[3] - bbox[1]) + int(24 * scale)

    # ── CTA button ────────────────────────────────────────────────────────────
    if cta:
        cta_text = f"  {cta}  "
        _draw_pill(draw, margin, cy, cta_text, f_cta,
                   accent + (230,), (20, 20, 20, 255), padding=18)

    # ── Social bar ────────────────────────────────────────────────────────────
    _add_social_bar(draw, w, h, fb, insta, website, accent, f_sm)

    # ── Logo ──────────────────────────────────────────────────────────────────
    if logo_file:
        canvas = _paste_logo(canvas, logo_file, logo_pos,
                             max_size=int(130 * scale))

    # ── Certification badge ───────────────────────────────────────────────────
    if cert_file:
        canvas = _paste_cert_badge(canvas, cert_file,
                                   max_size=int(90 * scale))

    return canvas.convert("RGB")


# ─────────────────────────────────────────────────────────────────────────────
# VIDEO SLIDESHOW GENERATOR (Pillow frames → GIF or MP4 via OpenCV if available)
# ─────────────────────────────────────────────────────────────────────────────

def generate_slideshow_gif(frames: list[Image.Image],
                            duration_per_frame: int = 2000) -> bytes:
    """Convert list of PIL Images into an animated GIF."""
    buf = io.BytesIO()
    frames[0].save(
        buf, format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=duration_per_frame,
        loop=0,
        optimize=True,
    )
    return buf.getvalue()


def img_to_bytes(img: Image.Image, fmt: str = "PNG") -> bytes:
    buf = io.BytesIO()
    img.save(buf, format=fmt, quality=95)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# PAGE
# ─────────────────────────────────────────────────────────────────────────────

def render():
    st.markdown("# 🏖️ Travel Content Creator")
    st.markdown(
        "Generate banners, posts & video slideshows for your travel packages — "
        "YouTube, Instagram, Facebook, WhatsApp. 100% free, no API needed."
    )
    st.markdown("---")

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_banner, tab_video, tab_bulk = st.tabs([
        "🖼️ Banner / Post",
        "🎬 Video Slideshow",
        "📦 Bulk Export (all sizes)",
    ])

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 1: SINGLE BANNER
    # ═══════════════════════════════════════════════════════════════════════
    with tab_banner:
        col_form, col_preview = st.columns([1, 1], gap="large")

        with col_form:
            st.markdown("### 📐 Format & Style")
            size_name = st.selectbox("Platform & Size", list(SIZES.keys()))
            theme_name = st.selectbox("Theme / Colour", list(THEMES.keys()))

            st.markdown("### 🖼️ Background Image")
            bg_file = st.file_uploader(
                "Upload background photo (landscape, beach, monument...)",
                type=["jpg", "jpeg", "png", "webp"],
                key="bg_single",
            )
            st.caption("If no image uploaded, a gradient background is used.")

            st.markdown("### ✍️ Content")
            package_name = st.text_input("Package Name", placeholder="Golden Triangle — 7 Days")
            title        = st.text_input("Headline / Title", placeholder="Discover Incredible India")
            subtitle     = st.text_input("Subheadline", placeholder="Sightseeing · Culture · Adventure")
            price        = st.text_input("Price", placeholder="₹24,999 / person")
            cta          = st.text_input("Call to Action", placeholder="Book Now  →", value="Book Now →")

            st.markdown("### 📍 Sights & Activities")
            hl_raw = st.text_area(
                "One per line (shown as checkmarks)",
                placeholder="Taj Mahal Sunrise Tour\nDesert Safari — Jaisalmer\nBackwaters of Kerala\nRiver Rafting — Rishikesh\nCooking Class — Jaipur",
                height=120,
            )
            highlights = [h.strip() for h in hl_raw.strip().splitlines() if h.strip()]

            st.markdown("### 🔗 Social Links")
            c1, c2 = st.columns(2)
            with c1: fb    = st.text_input("Facebook page", placeholder="YourTravelPage")
            with c2: insta = st.text_input("Instagram handle", placeholder="@yourtravel")
            website = st.text_input("Website", placeholder="www.yourtravel.com")

            st.markdown("### 🏷️ Logo & Certification")
            logo_file = st.file_uploader("Company Logo (PNG with transparency preferred)",
                                         type=["png", "jpg", "jpeg"], key="logo_single")
            logo_pos  = st.radio("Logo position", ["Top Right", "Top Left", "Bottom Right", "Bottom Left"],
                                 horizontal=True)
            cert_file = st.file_uploader("Certification Badge (optional)",
                                         type=["png", "jpg", "jpeg"], key="cert_single")

            gen_btn = st.button("🎨 Generate Banner", type="primary", use_container_width=True)

        with col_preview:
            st.markdown("### 👁️ Preview")

            if gen_btn or st.session_state.get("banner_generated"):
                if gen_btn:
                    w, h   = SIZES[size_name]
                    theme  = THEMES[theme_name]
                    img    = generate_banner(
                        w=w, h=h, theme=theme,
                        bg_image=bg_file,
                        title=title, subtitle=subtitle,
                        package_name=package_name,
                        price=price, highlights=highlights, cta=cta,
                        fb=fb, insta=insta, website=website,
                        logo_file=logo_file, logo_pos=logo_pos,
                        cert_file=cert_file,
                    )
                    st.session_state["last_banner"]      = img_to_bytes(img, "PNG")
                    st.session_state["last_banner_name"] = f"{package_name or 'banner'}_{size_name[:15]}.png"
                    st.session_state["banner_generated"] = True

                banner_bytes = st.session_state.get("last_banner")
                if banner_bytes:
                    st.image(banner_bytes, use_container_width=True)
                    st.download_button(
                        "📥 Download PNG",
                        data=banner_bytes,
                        file_name=st.session_state.get("last_banner_name", "banner.png"),
                        mime="image/png",
                        use_container_width=True,
                    )
                    st.success("✅ Ready to post on social media!")
            else:
                st.markdown("""
                <div style="border:0.5px solid var(--color-border-tertiary);border-radius:12px;
                            padding:80px 20px;text-align:center">
                    <div style="font-size:48px">🏖️</div>
                    <div style="color:var(--color-text-secondary);margin-top:12px;font-size:14px">
                        Fill in the details on the left and hit Generate Banner
                    </div>
                </div>""", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 2: VIDEO SLIDESHOW
    # ═══════════════════════════════════════════════════════════════════════
    with tab_video:
        st.markdown("### 🎬 Animated Slideshow")
        st.info(
            "Upload multiple travel photos — the tool generates an animated "
            "slideshow (GIF) with your branding overlay on each frame. "
            "Perfect for WhatsApp Status, Instagram Stories, or as a base for CapCut."
        )

        col_vl, col_vr = st.columns([1, 1], gap="large")

        with col_vl:
            slide_imgs = st.file_uploader(
                "Upload 2-8 travel photos",
                type=["jpg", "jpeg", "png", "webp"],
                accept_multiple_files=True,
                key="slide_imgs",
            )

            v_theme_name = st.selectbox("Theme", list(THEMES.keys()), key="v_theme")
            v_size_name  = st.selectbox("Format", [
                "Instagram Story / Reels (1080×1920)",
                "YouTube Shorts (1080×1920)",
                "Square Post (1080×1080)",
                "YouTube Thumbnail (1280×720)",
            ], key="v_size")
            v_size_map = {
                "Instagram Story / Reels (1080×1920)": (1080, 1920),
                "YouTube Shorts (1080×1920)":          (1080, 1920),
                "Square Post (1080×1080)":             (1080, 1080),
                "YouTube Thumbnail (1280×720)":        (1280, 720),
            }
            vw, vh = v_size_map[v_size_name]

            v_title    = st.text_input("Title on slides", placeholder="Explore Rajasthan", key="v_title")
            v_pkg      = st.text_input("Package name",    placeholder="7 Days Royal Package", key="v_pkg")
            v_fb       = st.text_input("Facebook", placeholder="YourPage", key="v_fb")
            v_insta    = st.text_input("Instagram", placeholder="@handle", key="v_insta")
            v_web      = st.text_input("Website", placeholder="www.yourtravel.com", key="v_web")
            v_logo     = st.file_uploader("Logo (optional)", type=["png","jpg","jpeg"], key="v_logo")
            v_duration = st.slider("Seconds per slide", 1, 5, 2)

            v_gen = st.button("🎬 Generate Slideshow GIF", type="primary",
                              use_container_width=True,
                              disabled=len(slide_imgs or []) < 2)

        with col_vr:
            st.markdown("### 👁️ Preview")

            if v_gen and slide_imgs:
                theme  = THEMES[v_theme_name]
                frames = []
                prog   = st.progress(0, text="Generating frames...")
                for i, f in enumerate(slide_imgs[:8]):
                    frame = generate_banner(
                        w=vw, h=vh, theme=theme,
                        bg_image=f,
                        title=v_title,
                        package_name=v_pkg,
                        highlights=[],
                        fb=v_fb, insta=v_insta, website=v_web,
                        logo_file=v_logo, logo_pos="Top Right",
                    )
                    # Scale down for GIF (keeps file size reasonable)
                    thumb = frame.copy()
                    scale = 540 / vw
                    thumb = thumb.resize((int(vw * scale), int(vh * scale)), Image.LANCZOS)
                    frames.append(thumb)
                    prog.progress((i + 1) / len(slide_imgs))

                prog.empty()
                gif_bytes = generate_slideshow_gif(frames, duration_per_frame=v_duration * 1000)
                st.session_state["last_gif"] = gif_bytes
                st.success(f"✅ {len(frames)}-frame slideshow ready! ({len(gif_bytes)//1024} KB)")

            gif = st.session_state.get("last_gif")
            if gif:
                b64 = base64.b64encode(gif).decode()
                st.markdown(
                    f'<img src="data:image/gif;base64,{b64}" style="width:100%;border-radius:8px">',
                    unsafe_allow_html=True,
                )
                st.download_button(
                    "📥 Download GIF",
                    data=gif,
                    file_name="travel_slideshow.gif",
                    mime="image/gif",
                    use_container_width=True,
                )
                st.caption("💡 Import into CapCut or InShot to add music & export as MP4")
            else:
                st.markdown("""
                <div style="border:0.5px solid var(--color-border-tertiary);border-radius:12px;
                            padding:80px 20px;text-align:center">
                    <div style="font-size:48px">🎬</div>
                    <div style="color:var(--color-text-secondary);margin-top:12px;font-size:14px">
                        Upload 2+ photos → Generate
                    </div>
                </div>""", unsafe_allow_html=True)

    # ═══════════════════════════════════════════════════════════════════════
    # TAB 3: BULK EXPORT
    # ═══════════════════════════════════════════════════════════════════════
    with tab_bulk:
        st.markdown("### 📦 Bulk Export — All Sizes at Once")
        st.info(
            "Fill in your package details once and download a ZIP with banners "
            "in every platform size — YouTube, Instagram, Facebook, Twitter, WhatsApp."
        )

        col_bl, col_br = st.columns([1, 1], gap="large")

        with col_bl:
            b_bg      = st.file_uploader("Background photo", type=["jpg","jpeg","png","webp"], key="b_bg")
            b_theme   = st.selectbox("Theme", list(THEMES.keys()), key="b_theme")
            b_pkg     = st.text_input("Package Name", key="b_pkg", placeholder="Goa Beach Holiday — 5N/6D")
            b_title   = st.text_input("Headline", key="b_title", placeholder="Sun, Sea & Sand")
            b_sub     = st.text_input("Subheadline", key="b_sub", placeholder="All-inclusive packages from Mumbai")
            b_price   = st.text_input("Price", key="b_price", placeholder="₹18,999/person")
            b_cta     = st.text_input("CTA", key="b_cta", value="Book Now →")
            b_hl      = st.text_area("Highlights (one per line)", key="b_hl", height=100,
                                     placeholder="Baga Beach\nWater Sports\nSunset Cruise\nNight Markets")
            b_fb      = st.text_input("Facebook", key="b_fb")
            b_insta   = st.text_input("Instagram", key="b_insta")
            b_web     = st.text_input("Website", key="b_web")
            b_logo    = st.file_uploader("Logo", type=["png","jpg","jpeg"], key="b_logo")
            b_cert    = st.file_uploader("Cert badge", type=["png","jpg","jpeg"], key="b_cert")
            b_logo_p  = st.radio("Logo position", ["Top Right","Top Left","Bottom Right","Bottom Left"],
                                 horizontal=True, key="b_logo_p")

            platforms = st.multiselect(
                "Select platforms to export",
                list(SIZES.keys()),
                default=["YouTube Thumbnail (1280×720)",
                         "Instagram Post Square (1080×1080)",
                         "Instagram Story (1080×1920)",
                         "Facebook Post (1200×630)"],
            )

            bulk_btn = st.button("📦 Generate All & Download ZIP",
                                 type="primary", use_container_width=True,
                                 disabled=not platforms)

        with col_br:
            st.markdown("### 📋 Export Preview")

            if bulk_btn and platforms:
                b_highlights = [h.strip() for h in b_hl.strip().splitlines() if h.strip()]
                theme        = THEMES[b_theme]
                zip_buf      = io.BytesIO()
                prog         = st.progress(0, text="Generating...")

                with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    preview_shown = False
                    for i, p_name in enumerate(platforms):
                        pw, ph = SIZES[p_name]
                        img = generate_banner(
                            w=pw, h=ph, theme=theme,
                            bg_image=b_bg,
                            title=b_title, subtitle=b_sub,
                            package_name=b_pkg,
                            price=b_price, highlights=b_highlights, cta=b_cta,
                            fb=b_fb, insta=b_insta, website=b_web,
                            logo_file=b_logo, logo_pos=b_logo_p,
                            cert_file=b_cert,
                        )
                        safe_name = p_name.split("(")[0].strip().replace(" ", "_").replace("/", "-")
                        fname     = f"{b_pkg or 'banner'}_{safe_name}_{pw}x{ph}.png"
                        png_bytes = img_to_bytes(img, "PNG")
                        zf.writestr(fname, png_bytes)

                        if not preview_shown:
                            st.image(png_bytes, caption=p_name, use_container_width=True)
                            preview_shown = True

                        prog.progress((i + 1) / len(platforms))

                prog.empty()
                zip_buf.seek(0)
                st.success(f"✅ {len(platforms)} banners ready!")
                st.download_button(
                    "📥 Download ZIP",
                    data=zip_buf.getvalue(),
                    file_name=f"{b_pkg or 'banners'}_all_sizes.zip",
                    mime="application/zip",
                    use_container_width=True,
                )
            else:
                st.markdown("""
                <div style="border:0.5px solid var(--color-border-tertiary);border-radius:12px;
                            padding:80px 20px;text-align:center">
                    <div style="font-size:48px">📦</div>
                    <div style="color:var(--color-text-secondary);margin-top:12px;font-size:14px">
                        Configure your package → select platforms → Generate All
                    </div>
                </div>""", unsafe_allow_html=True)

    # ── Tips ──────────────────────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("💡 Tips for better travel banners"):
        st.markdown("""
**Best background photos:**
- Use high-res landscape shots (minimum 1920×1080)
- Golden hour / sunrise / sunset photos work best with any theme
- Make sure main subject isn't dead centre — text overlay needs space

**Per platform tips:**
| Platform | Best size | Key tip |
|---|---|---|
| YouTube Thumbnail | 1280×720 | Keep text large and bold, faces/shock visible |
| Instagram Reels | 1080×1920 | Text in upper/lower third — safe zone for UI |
| Facebook Post | 1200×630 | Text <20% of image for ad delivery |
| WhatsApp Status | 1080×1920 | Simple, clean, max 2-3 lines |

**After downloading:**
- Open in **CapCut** → add music → export as MP4 for Reels/Shorts
- Use **Canva** to add animations (import PNG as background)
- Add to **Buffer** or **Later** for scheduled posting
        """)
