"""
✈ Professional Flyer Generator — 7 Wonders World Travels style
================================================================
Generates 3 flyer types matching the uploaded reference designs:
  1. PACKAGE FLYER  — photo collage + itinerary + price box + hotel list
  2. SERVICE FLYER  — colored pill service cards + features
  3. PROMO FLYER    — large hero photo + bold headline + CTA

Design system extracted from reference flyers:
  • Navy dark header + gold company name
  • Gold accent bars top/bottom of sections
  • Colored pill cards for services (blue/green/orange/purple/red)
  • Gold price highlight box
  • White service cards with navy border
  • Social bar (white) + contact bar (navy) + cert bar (white)
  • Certification logos: IATA · OTAI · ADTOI · NIMA · ETAA etc.

AI: Groq (free) or Gemini (free 250 req/day) for copy generation
Rendering: Pure Pillow with 2× supersampling → LANCZOS downscale
"""

import streamlit as st
import sys, os, io, json, re, zipfile, base64
from PIL import (Image, ImageDraw, ImageFont, ImageFilter,
                 ImageEnhance, ImageChops)

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ─────────────────────────────────────────────────────────────────────────────
# DESIGN SYSTEM  (extracted from 7WW reference flyers)
# ─────────────────────────────────────────────────────────────────────────────
NAVY      = (26, 42, 94)
NAVY_MID  = (36, 51, 112)
NAVY_LT   = (52, 73, 140)
GOLD      = (201, 168, 76)
GOLD_LT   = (245, 216, 120)
GOLD_DK   = (139, 105, 20)
WHITE     = (255, 255, 255)
OFF_WHITE = (248, 246, 240)
TEXT_DARK = (22, 22, 42)
TEXT_MID  = (80, 80, 100)

PILL_COLORS = [
    (41,  128, 185),   # steel blue  — Tour Packages
    (39,  174, 96),    # emerald     — Visa
    (230, 126, 34),    # amber       — Hotel
    (142, 68,  173),   # purple      — Rail
    (192, 57,  43),    # crimson     — Flight
    (22,  160, 133),   # teal        — extra
    (52,  73,  94),    # dark slate  — extra
]

# Platform sizes
PLATFORMS = {
    "WhatsApp / Instagram Story 9:16 (900×1600)": (900, 1600),
    "Instagram Post 1:1 (1080×1080)":             (1080, 1080),
    "YouTube Thumbnail 16:9 (1280×720)":           (1280, 720),
    "Facebook Post (1200×630)":                    (1200, 630),
    "A4 Portrait PDF (2480×3508)":                 (2480, 3508),
    "Square Flyer (1080×1080)":                    (1080, 1080),
}

SSAA = 2  # 2× supersampling for antialiased text

# ─────────────────────────────────────────────────────────────────────────────
# FONT CACHE
# ─────────────────────────────────────────────────────────────────────────────
_FC: dict = {}
def F(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    k = (size, bold)
    if k in _FC: return _FC[k]
    paths = [
        f"/usr/share/fonts/truetype/dejavu/DejaVuSans{'-Bold' if bold else ''}.ttf",
        f"/usr/share/fonts/truetype/liberation/LiberationSans{'-Bold' if bold else '-Regular'}.ttf",
        f"/usr/share/fonts/truetype/ubuntu/Ubuntu-{'B' if bold else 'R'}.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                f = ImageFont.truetype(p, size)
                _FC[k] = f
                return f
            except Exception:
                pass
    return ImageFont.load_default()

# ─────────────────────────────────────────────────────────────────────────────
# KEY HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def _get(sk, sec, ev=""):
    v = st.session_state.get(sk, "").strip()
    if v: return v
    try:
        v = str(st.secrets.get(sec,"")).strip()
        if v: return v
    except Exception:
        pass
    return os.getenv(ev,"").strip()

def _groq_key():   return _get("groq_key",   "GROQ_API_KEY",   "GROQ_API_KEY")
def _gemini_key(): return _get("gemini_key", "GEMINI_API_KEY", "GEMINI_API_KEY")
def _llm_ok():     return bool(_groq_key() or _gemini_key())

# ─────────────────────────────────────────────────────────────────────────────
# LLM
# ─────────────────────────────────────────────────────────────────────────────
def _groq(system, user, tokens=900):
    key = _groq_key()
    if not key: return ""
    try:
        from groq import Groq
        r = Groq(api_key=key).chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"system","content":system},{"role":"user","content":user}],
            max_tokens=tokens, temperature=0.72,
            response_format={"type":"json_object"},
        )
        return r.choices[0].message.content.strip()
    except Exception as e:
        st.toast(f"Groq: {e}", icon="⚠️")
        return ""

def _gemini(combined, tokens=900):
    key = _gemini_key()
    if not key: return ""
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
    body = {"contents":[{"parts":[{"text":combined}]}],
            "generationConfig":{"maxOutputTokens":tokens,"temperature":0.75,
                                "responseMimeType":"application/json"}}
    try:
        import requests as _req
        r = _req.post(url, params={"key":key}, json=body, timeout=30)
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception as e:
        st.toast(f"Gemini: {e}", icon="⚠️")
        return ""

def _parse(raw):
    try:
        clean = re.sub(r"```(?:json)?|```","",raw).strip()
        s = clean.find("{")
        return json.loads(clean[s:]) if s>=0 else json.loads(clean)
    except Exception:
        return {}

def ai_content(prompt_text: str, flyer_type: str, brand: dict) -> dict:
    system = f"""You are a professional Indian travel marketing copywriter.
Generate flyer content for a "{flyer_type}" flyer for a travel agency.
Return ONLY valid JSON. Keys depend on flyer type:

For PACKAGE flyer:
  headline (ALL CAPS, punchy, max 10 words),
  subheadline (e.g. "5 Nights / 6 Days"),
  destination, duration,
  itinerary (array of objects: {{nights, city}} e.g. [{{"nights":"2 Nights","city":"Thimphu"}}]),
  price (e.g. "Rs 28,777"), price_note (e.g. "per person twin sharing | Breakfast & Dinner"),
  price_validity (e.g. "Valid till 30 Sep 2026"),
  hotels (array of objects: {{city, options}} e.g. [{{"city":"Thimphu","options":"Lhayuel Hotel / similar"}}]),
  highlights (array of 4-5 short strings),
  tagline (1 short inspiring sentence),
  hashtags (string of 8 hashtags)

For SERVICE flyer:
  headline (ALL CAPS, e.g. "YOUR GATEWAY TO THE WORLD"),
  subheadline (e.g. "Tourist & Business Services for All Countries"),
  services (array of 5 objects: {{icon, title, description}}),
  cta (e.g. "Contact Us Today!"),
  tagline, hashtags

For PROMO flyer:
  headline (ALL CAPS, very punchy),
  subheadline, offer_text (e.g. "EXCLUSIVE DEAL"),
  price, price_note, valid_till,
  highlights (array of 4 short strings),
  cta, tagline, hashtags
"""
    user = (f"Travel agency: {brand.get('name','7 Wonders World Travels')}\n"
            f"Request: {prompt_text}\n"
            f"Generate {flyer_type} flyer content:")
    raw = _groq(system, user) or _gemini(f"{system}\n\nReturn ONLY valid JSON.\n\n{user}")
    data = _parse(raw) if raw else {}

    # Smart defaults based on prompt text
    if flyer_type == "PACKAGE":
        data.setdefault("headline", prompt_text.upper()[:50])
        data.setdefault("subheadline","5 Nights / 6 Days")
        data.setdefault("destination","Bhutan")
        data.setdefault("duration","6 Days / 5 Nights")
        data.setdefault("itinerary",[{"nights":"2 Nights","city":"Thimphu"},{"nights":"1 Night","city":"Punakha"},{"nights":"2 Nights","city":"Paro"}])
        data.setdefault("price","Rs 28,777")
        data.setdefault("price_note","per person twin sharing | Breakfast & Dinner | minimum 4 guests")
        data.setdefault("price_validity","Valid till 30 Sep 2026")
        data.setdefault("hotels",[{"city":"Thimphu","options":"Lhayuel Hotel / similar"},{"city":"Punakha","options":"White Dragon / similar"},{"city":"Paro","options":"Taktshang Village Lodge / similar"}])
        data.setdefault("highlights",["Toyota vehicle","Guide & Sightseeing","Airport Transfers","All Taxes Included"])
        data.setdefault("tagline","Your dream journey begins with a single step.")
        data.setdefault("hashtags","#Bhutan #Travel #TourPackage #7WondersTravels #Wanderlust #Holiday")
    elif flyer_type == "SERVICE":
        data.setdefault("headline","YOUR GATEWAY TO THE WORLD")
        data.setdefault("subheadline","Tourist & Business Visas for All Countries")
        data.setdefault("services",[
            {"icon":"🗺️","title":"Tour Packages","description":"Explore the World with Curated Tours"},
            {"icon":"🛂","title":"Visa Assistance","description":"Hassle-Free Processing & Compliance"},
            {"icon":"🏨","title":"Hotel Bookings","description":"Best Accommodation Rates Globally"},
            {"icon":"🚂","title":"Euro Rail","description":"Seamless Europe Train Travel Bookings"},
            {"icon":"✈️","title":"Flight Bookings","description":"Best Airfares Domestic & International"},
        ])
        data.setdefault("cta","Call Us Today!")
        data.setdefault("tagline","Trusted | Compliant | Affordable")
        data.setdefault("hashtags","#Travel #Visa #TourPackage #7WondersTravels #India")
    else:  # PROMO
        data.setdefault("headline","JOIN THE ADVENTURE!")
        data.setdefault("subheadline","Contact Us for Exclusive Travel Deals & Tips!")
        data.setdefault("offer_text","EXCLUSIVE DEAL")
        data.setdefault("price","₹24,999")
        data.setdefault("price_note","per person | All Inclusive")
        data.setdefault("valid_till","Limited Period Offer")
        data.setdefault("highlights",["Flights Included","Hotels Included","Sightseeing","24/7 Support"])
        data.setdefault("cta","Book Now! Call +91 97112 81598")
        data.setdefault("tagline","Your Ultimate Travel Partner Since 2015")
        data.setdefault("hashtags","#Travel #Holiday #Explore #7WondersTravels")
    return data

# ─────────────────────────────────────────────────────────────────────────────
# DRAWING HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def rr(draw, box, r, fill=None, outline=None, width=2):
    draw.rounded_rectangle(list(box), radius=r, fill=fill, outline=outline, width=width)

def _tw(draw, xy, text, font, fill, sw=0, sf=(0,0,0)):
    if sw:
        draw.text(xy, text, font=font, fill=fill, stroke_width=sw, stroke_fill=sf)
    else:
        draw.text(xy, text, font=font, fill=fill)

def cx_text(draw, text, font, y, W, fill, sw=0, sf=(0,0,0)):
    bb = draw.textbbox((0,0),text,font=font)
    tw = bb[2]-bb[0]; th = bb[3]-bb[1]
    x = max(0,(W-tw)//2)
    _tw(draw,(x,y),text,font,fill,sw,sf)
    return th

def wrap_text(text, font, max_w, draw):
    words=text.split(); lines=[]; line=""
    for w in words:
        test=(line+" "+w).strip()
        if draw.textbbox((0,0),test,font=font)[2]<=max_w: line=test
        else:
            if line: lines.append(line)
            line=w
    if line: lines.append(line)
    return "\n".join(lines)

def cover_crop(img: Image.Image, w, h) -> Image.Image:
    img=img.convert("RGB")
    r=max(w/img.width, h/img.height)
    nw,nh=int(img.width*r),int(img.height*r)
    img=img.resize((nw,nh),Image.LANCZOS)
    l,t=(nw-w)//2,(nh-h)//2
    return img.crop((l,t,l+w,t+h))

def _enhance(img):
    img=ImageEnhance.Brightness(img).enhance(1.04)
    img=ImageEnhance.Contrast(img).enhance(1.08)
    img=ImageEnhance.Color(img).enhance(1.12)
    return img

def gradient_rect(draw, x1, y1, x2, y2, c1, c2, axis="v"):
    """Fill a rectangle with a gradient."""
    if axis=="v":
        for y in range(y1,y2):
            t=(y-y1)/(y2-y1)
            r=int(c1[0]+(c2[0]-c1[0])*t)
            g=int(c1[1]+(c2[1]-c1[1])*t)
            b=int(c1[2]+(c2[2]-c1[2])*t)
            draw.line([(x1,y),(x2,y)],fill=(r,g,b))
    else:
        for x in range(x1,x2):
            t=(x-x1)/(x2-x1)
            r=int(c1[0]+(c2[0]-c1[0])*t)
            g=int(c1[1]+(c2[1]-c1[1])*t)
            b=int(c1[2]+(c2[2]-c1[2])*t)
            draw.line([(x,y1),(x,y2)],fill=(r,g,b))

def load_img_bytes(b):
    img=Image.open(io.BytesIO(bytes(b))).convert("RGB")
    return _enhance(img)

# ─────────────────────────────────────────────────────────────────────────────
# COMMON SECTIONS
# ─────────────────────────────────────────────────────────────────────────────
def draw_header(canvas, draw, W, brand, sc):
    """Navy header with gold company name. Returns bottom y."""
    hh = int(190*sc)
    # Navy background
    draw.rectangle([0,0,W,hh],fill=NAVY)
    # Top gold bar
    draw.rectangle([0,0,W,int(6*sc)],fill=GOLD)
    # Logo placeholder (circle with "7")
    lc=(W//2, int(70*sc)); lr=int(42*sc)
    draw.ellipse([lc[0]-lr,lc[1]-lr,lc[0]+lr,lc[1]+lr],fill=GOLD,outline=GOLD_LT,width=int(2*sc))
    draw.ellipse([lc[0]-lr+int(4*sc),lc[1]-lr+int(4*sc),
                  lc[0]+lr-int(4*sc),lc[1]+lr-int(4*sc)],fill=NAVY)
    f7=F(int(44*sc),bold=True)
    cx_text(draw,"7",f7,lc[1]-int(26*sc),W,GOLD)

    # If logo image provided, overlay it
    logo_bytes=st.session_state.get("brand_logo")
    if logo_bytes:
        try:
            logo=Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
            max_w=int(160*sc); max_h=int(100*sc)
            r_logo=min(max_w/logo.width, max_h/logo.height)
            nw,nh=int(logo.width*r_logo),int(logo.height*r_logo)
            logo=logo.resize((nw,nh),Image.LANCZOS)
            canvas.paste(logo,((W-nw)//2,int(10*sc)),logo)
        except Exception:
            pass

    # Company name
    name=brand.get("name","7 WONDERS WORLD")
    parts=name.upper().split()
    line1=" ".join(parts[:3]) if len(parts)>=3 else name.upper()
    line2=" ".join(parts[3:6]) if len(parts)>3 else ""
    line3=brand.get("suffix","TRAVELS PVT LTD")
    line4=brand.get("since","SINCE 2015")

    fN1=F(int(28*sc),bold=True)
    fN2=F(int(22*sc),bold=True)
    fN3=F(int(18*sc))
    fSince=F(int(15*sc))

    y0=int(120*sc)
    cx_text(draw,line1,fN1,y0,W,GOLD)
    if line2:
        y0+=int(32*sc)
        cx_text(draw,line2,fN2,y0,W,GOLD)
    y0+=int(30*sc)
    cx_text(draw,line3,fN2,y0,W,WHITE)
    y0+=int(26*sc)
    cx_text(draw,line4,fSince,y0,W,GOLD_LT)

    # Bottom gold line
    draw.rectangle([0,hh-int(4*sc),W,hh],fill=GOLD)
    return hh


def draw_footer(canvas, draw, W, H, brand, sc):
    """Social bar + contact bar + cert bar + copyright. Returns top y."""
    # Cert bar (bottom 100px)
    cert_y=H-int(100*sc)
    draw.rectangle([0,cert_y,W,H],fill=WHITE)
    draw.rectangle([0,cert_y,W,cert_y+int(3*sc)],fill=GOLD)
    fCertTitle=F(int(15*sc))
    cx_text(draw,"— Certification of Trust & Active Membership —",fCertTitle,
            cert_y+int(8*sc),W,(120,120,120))
    certs=brand.get("certs",["IATA","OTAI","ADTOI","NIMA","ETAA"])
    fCert=F(int(13*sc),bold=True)
    total_cert_w=sum(draw.textbbox((0,0),c,font=fCert)[2]+int(22*sc) for c in certs)
    cx2=(W-total_cert_w)//2+10
    for c in certs:
        bb=draw.textbbox((0,0),c,font=fCert)
        cw=bb[2]-bb[0]+int(16*sc); ch=bb[3]-bb[1]+int(10*sc)
        rr(draw,[cx2,cert_y+int(32*sc),cx2+cw,cert_y+int(32*sc)+ch],6,outline=NAVY,width=2)
        draw.text((cx2+int(8*sc),cert_y+int(37*sc)),c,font=fCert,fill=NAVY)
        cx2+=cw+int(6*sc)

    # Copyright line
    draw.rectangle([0,H-int(26*sc),W,H],fill=NAVY)
    fCopy=F(int(13*sc))
    cx_text(draw,f"© 2025 {brand.get('name','7 Wonders World Travels')}. All Rights Reserved.",
            fCopy,H-int(22*sc),W,(200,200,200))

    # Contact bar
    contact_y=cert_y-int(85*sc)
    draw.rectangle([0,contact_y,W,cert_y],fill=NAVY_MID)
    fCt=F(int(20*sc))
    fCtB=F(int(20*sc),bold=True)
    web=brand.get("website","www.7wwtravels.com")
    phone=brand.get("phone","+91 97112 81598")
    email1=brand.get("email1","vidhi@7wwtravels.com")
    email2=brand.get("email2","anand@7wwtravels.com")
    cx_text(draw,f"{web}  |  {phone}",fCtB,contact_y+int(12*sc),W,WHITE)
    cx_text(draw,f"{email1}  |  {email2}",fCt,contact_y+int(44*sc),W,GOLD_LT)

    # Social bar
    social_y=contact_y-int(80*sc)
    draw.rectangle([0,social_y,W,contact_y],fill=OFF_WHITE)
    draw.rectangle([0,social_y,W,social_y+int(3*sc)],fill=NAVY)
    fSocTitle=F(int(22*sc),bold=True)
    fSoc=F(int(18*sc))
    cx_text(draw,"FOLLOW US",fSocTitle,social_y+int(8*sc),W,NAVY)
    fb=brand.get("facebook","7wwtravels")
    ig=brand.get("instagram","7ww_travels")
    yt=brand.get("youtube","@7wwtravels")
    li=brand.get("linkedin","7wwtravels/")
    soc_line=f"f  {fb}   ·   @  {ig}   ·   ▶  {yt}   ·   in  {li}"
    cx_text(draw,soc_line,fSoc,social_y+int(42*sc),W,NAVY)
    return social_y


# ─────────────────────────────────────────────────────────────────────────────
# FLYER TYPE 1: PACKAGE  (like Bhutan flyer)
# ─────────────────────────────────────────────────────────────────────────────
def render_package(photos, W, H, content, brand, qr_bytes=None):
    sc=min(W,H)/900
    W2,H2=W*SSAA,H*SSAA
    sc2=min(W2,H2)/900

    canvas=Image.new("RGB",(W2,H2),OFF_WHITE)
    draw=ImageDraw.Draw(canvas)

    # Header
    hdr_bot=draw_header(canvas,draw,W2,brand,sc2)
    footer_top=draw_footer(canvas,draw,W2,H2,brand,sc2)
    content_h=footer_top-hdr_bot
    cy=hdr_bot

    # ── HEADLINE BAND ──────────────────────────────────────────────────────────
    hl_h=int(155*sc2)
    gradient_rect(draw,0,cy,W2,cy+hl_h,NAVY,NAVY_MID)
    draw.rectangle([0,cy,W2,cy+int(5*sc2)],fill=GOLD)
    fHL=F(int(46*sc2),bold=True)
    fSub=F(int(26*sc2))
    hl=content.get("headline","YOUR BHUTAN ADVENTURE AWAITS")
    wrapped_hl=wrap_text(hl,fHL,W2-int(60*sc2),draw)
    lines=wrapped_hl.split("\n")
    y_hl=cy+int(14*sc2)
    for line in lines:
        cx_text(draw,line,fHL,y_hl,W2,GOLD,sw=2,sf=GOLD_DK)
        bb=draw.textbbox((0,0),line,font=fHL)
        y_hl+=bb[3]-bb[1]+int(6*sc2)
    cx_text(draw,content.get("subheadline","5 Nights / 6 Days"),fSub,y_hl,W2,WHITE)
    cy+=hl_h

    # ── PHOTO MOSAIC + ITINERARY ───────────────────────────────────────────────
    mid_h=int(380*sc2)
    gap=int(6*sc2)
    left_w=int(W2*0.46)
    right_w=W2-left_w-gap

    # Photo left side
    if len(photos)>=3:
        ph=(mid_h-gap*2)//3
        for i in range(3):
            tile=cover_crop(photos[i],left_w,ph)
            canvas.paste(tile,(0,cy+i*(ph+gap)))
    elif len(photos)==2:
        ph=(mid_h-gap)//2
        for i in range(2):
            tile=cover_crop(photos[i],left_w,ph)
            canvas.paste(tile,(0,cy+i*(ph+gap)))
    elif len(photos)==1:
        tile=cover_crop(photos[0],left_w,mid_h)
        canvas.paste(tile,(0,cy))
    else:
        # Gradient placeholder
        gradient_rect(draw,0,cy,left_w,cy+mid_h,NAVY_MID,NAVY)

    # Right side: light background + itinerary
    draw.rectangle([left_w+gap,cy,W2,cy+mid_h],fill=WHITE)
    rx=left_w+gap+int(20*sc2); ry=cy+int(20*sc2)

    # Duration badge
    fDur=F(int(32*sc2),bold=True)
    fDurSub=F(int(20*sc2))
    _tw(draw,(rx,ry),content.get("duration","5 Nights / 6 Days"),fDur,NAVY,sw=1,sf=NAVY_LT)
    ry+=int(44*sc2)

    # Itinerary dots
    itinerary=content.get("itinerary",[])
    fItin=F(int(22*sc2),bold=True)
    fItinSub=F(int(18*sc2))
    dot_x=rx+int(15*sc2)
    for item in itinerary:
        # connector line
        draw.rectangle([dot_x+int(8*sc2),ry+int(12*sc2),
                         dot_x+int(12*sc2),ry+int(52*sc2)],fill=GOLD)
        draw.ellipse([dot_x,ry+int(4*sc2),dot_x+int(20*sc2),ry+int(24*sc2)],
                      fill=GOLD,outline=GOLD_DK,width=int(2*sc2))
        _tw(draw,(dot_x+int(28*sc2),ry),item.get("nights",""),fItin,NAVY)
        _tw(draw,(dot_x+int(28*sc2),ry+int(26*sc2)),item.get("city",""),fItinSub,TEXT_MID)
        ry+=int(64*sc2)

    cy+=mid_h+gap

    # ── PRICE BOX ─────────────────────────────────────────────────────────────
    price_h=int(130*sc2)
    draw.rectangle([0,cy,W2,cy+price_h],fill=GOLD_LT)
    draw.rectangle([0,cy,W2,cy+int(4*sc2)],fill=GOLD_DK)
    draw.rectangle([0,cy+price_h-int(4*sc2),W2,cy+price_h],fill=GOLD_DK)

    fOffer=F(int(22*sc2),bold=True)
    fPrice=F(int(46*sc2),bold=True)
    fPNote=F(int(19*sc2))
    fValid=F(int(16*sc2))

    cx_text(draw,"SPECIAL OFFER:",fOffer,cy+int(8*sc2),W2,NAVY)
    bb=draw.textbbox((0,0),"SPECIAL OFFER:",font=fOffer)
    offer_w=bb[2]-bb[0]
    pr_text=content.get("price","Rs 28,777")
    # Price centered below
    cx_text(draw,pr_text,fPrice,cy+int(34*sc2),W2,NAVY,sw=1,sf=GOLD_DK)
    cx_text(draw,content.get("price_note","per person twin sharing | Breakfast & Dinner"),
            fPNote,cy+int(88*sc2),W2,TEXT_DARK)
    cx_text(draw,content.get("price_validity","T&C Apply"),
            fValid,cy+int(112*sc2),W2,TEXT_MID)
    cy+=price_h+int(16*sc2)

    # ── HOTEL LIST ─────────────────────────────────────────────────────────────
    hotel_h=int(170*sc2)
    draw.rectangle([int(16*sc2),cy,W2-int(16*sc2),cy+hotel_h],fill=WHITE)
    rr(draw,[int(16*sc2),cy,W2-int(16*sc2),cy+hotel_h],
       int(10*sc2),outline=NAVY,width=int(2*sc2))
    fHotelTitle=F(int(22*sc2),bold=True)
    fHotel=F(int(19*sc2))
    _tw(draw,(int(36*sc2),cy+int(12*sc2)),"Standard Accommodation:",fHotelTitle,NAVY)
    hotel_y=cy+int(44*sc2)
    for h in content.get("hotels",[]):
        city=h.get("city","")
        opts=h.get("options","")
        _tw(draw,(int(36*sc2),hotel_y),f"• {city} – {opts}",fHotel,TEXT_DARK)
        hotel_y+=int(34*sc2)
    cy+=hotel_h+int(12*sc2)

    # ── HIGHLIGHTS STRIP ──────────────────────────────────────────────────────
    hls=content.get("highlights",[])
    if hls:
        strip_h=int(60*sc2)
        gradient_rect(draw,0,cy,W2,cy+strip_h,NAVY,NAVY_MID)
        fHl=F(int(19*sc2))
        hl_text="   ✓  ".join(hls[:5])
        cx_text(draw,"✓  "+hl_text,fHl,cy+int(16*sc2),W2,GOLD_LT)
        cy+=strip_h+int(10*sc2)

    # ── QR + CONTACT inline ────────────────────────────────────────────────────
    if qr_bytes:
        try:
            qr=Image.open(io.BytesIO(qr_bytes)).convert("RGB")
            qr_size=int(100*sc2)
            qr=qr.resize((qr_size,qr_size),Image.LANCZOS)
            qr_x=int(20*sc2)
            qr_y=cy+int(8*sc2)
            canvas.paste(qr,(qr_x,qr_y))
            fQr=F(int(17*sc2),bold=True)
            _tw(draw,(qr_x+qr_size+int(16*sc2),qr_y+int(10*sc2)),"SCAN TO BOOK",fQr,NAVY)
            fQrSub=F(int(15*sc2))
            _tw(draw,(qr_x+qr_size+int(16*sc2),qr_y+int(36*sc2)),
                brand.get("website","www.7wwtravels.com"),fQrSub,TEXT_MID)
        except Exception:
            pass

    return canvas.convert("RGB").resize((W,H),Image.LANCZOS)


# ─────────────────────────────────────────────────────────────────────────────
# FLYER TYPE 2: SERVICE  (like Visa / Services flyer)
# ─────────────────────────────────────────────────────────────────────────────
def render_service(photos, W, H, content, brand):
    sc=min(W,H)/900
    W2,H2=W*SSAA,H*SSAA
    sc2=min(W2,H2)/900

    canvas=Image.new("RGB",(W2,H2),OFF_WHITE)
    draw=ImageDraw.Draw(canvas)

    hdr_bot=draw_header(canvas,draw,W2,brand,sc2)
    footer_top=draw_footer(canvas,draw,W2,H2,brand,sc2)
    cy=hdr_bot

    # ── HEADLINE BAND ──────────────────────────────────────────────────────────
    hl_h=int(200*sc2)
    gradient_rect(draw,0,cy,W2,cy+hl_h,NAVY,NAVY_MID)
    draw.rectangle([0,cy,W2,cy+int(5*sc2)],fill=GOLD)
    fHL=F(int(58*sc2),bold=True)
    fSub=F(int(28*sc2))
    hl=content.get("headline","YOUR GATEWAY TO THE WORLD")
    lines=wrap_text(hl,fHL,W2-int(80*sc2),draw).split("\n")
    y_hl=cy+int(18*sc2)
    for line in lines:
        cx_text(draw,line,fHL,y_hl,W2,GOLD,sw=2,sf=GOLD_DK)
        bb=draw.textbbox((0,0),line,font=fHL)
        y_hl+=bb[3]-bb[1]+int(8*sc2)
    cx_text(draw,content.get("subheadline","Expert Travel Services"),fSub,y_hl,W2,WHITE)
    cy+=hl_h

    # ── HERO PHOTO (if provided) ───────────────────────────────────────────────
    if photos:
        hero_h=int(230*sc2)
        hero=cover_crop(photos[0],W2,hero_h)
        # Slight darken for overlay
        overlay=Image.new("RGBA",(W2,hero_h),(NAVY[0],NAVY[1],NAVY[2],80))
        hero_rgba=hero.convert("RGBA")
        hero_rgba.alpha_composite(overlay)
        canvas.paste(hero_rgba.convert("RGB"),(0,cy))

        # World landmarks style silhouette text
        fLandmark=F(int(19*sc2))
        cx_text(draw,"🗼 Paris  ·  🏛️ Rome  ·  🗽 New York  ·  🕌 Dubai  ·  🏯 Bhutan",
                fLandmark,cy+hero_h-int(38*sc2),W2,WHITE)
        cy+=hero_h+int(12*sc2)
    else:
        cy+=int(10*sc2)

    # ── SERVICE PILLS ─────────────────────────────────────────────────────────
    services=content.get("services",[])
    pill_h=int(88*sc2)
    fSvcTitle=F(int(28*sc2),bold=True)
    fSvcDesc=F(int(21*sc2))
    for i,svc in enumerate(services[:6]):
        col=PILL_COLORS[i%len(PILL_COLORS)]
        col_lt=tuple(min(255,c+40) for c in col)
        col_dk=tuple(max(0,c-40) for c in col)
        py=cy+i*(pill_h+int(10*sc2))
        mx=int(16*sc2)
        # Pill with gradient
        gradient_rect(draw,mx,py,W2-mx,py+pill_h,col,col_dk)
        rr(draw,[mx,py,W2-mx,py+pill_h],int(14*sc2),outline=col_lt,width=int(2*sc2))
        # Left circle icon
        cx_icon=mx+int(50*sc2); cy_icon=py+pill_h//2
        draw.ellipse([cx_icon-int(32*sc2),cy_icon-int(32*sc2),
                       cx_icon+int(32*sc2),cy_icon+int(32*sc2)],
                      fill=col_lt,outline=WHITE,width=int(2*sc2))
        icon=svc.get("icon","✈️")
        fIcon=F(int(28*sc2))
        bb=draw.textbbox((0,0),icon,font=fIcon)
        draw.text((cx_icon-(bb[2]-bb[0])//2, cy_icon-(bb[3]-bb[1])//2),
                  icon,font=fIcon,fill=WHITE)
        # Text
        tx=mx+int(100*sc2)
        _tw(draw,(tx,py+int(12*sc2)),svc.get("title","Service"),fSvcTitle,WHITE,sw=1,sf=col_dk)
        _tw(draw,(tx,py+int(50*sc2)),svc.get("description",""),fSvcDesc,(240,240,240))

        # Right icon (mirrored)
        cx_r=W2-mx-int(50*sc2)
        draw.ellipse([cx_r-int(28*sc2),cy_icon-int(28*sc2),
                       cx_r+int(28*sc2),cy_icon+int(28*sc2)],
                      fill=col_lt,outline=WHITE,width=int(2*sc2))

    cy+=len(services[:6])*(pill_h+int(10*sc2))+int(16*sc2)

    # ── CTA BAND ──────────────────────────────────────────────────────────────
    if cy < footer_top-int(80*sc2):
        cta_h=int(80*sc2)
        gradient_rect(draw,0,cy,W2,cy+cta_h,GOLD_DK,GOLD)
        fCTA=F(int(32*sc2),bold=True)
        cx_text(draw,content.get("cta","Contact Us Today!"),fCTA,
                cy+(cta_h-int(40*sc2))//2,W2,NAVY,sw=1,sf=GOLD_DK)

    return canvas.convert("RGB").resize((W,H),Image.LANCZOS)


# ─────────────────────────────────────────────────────────────────────────────
# FLYER TYPE 3: PROMO  (bold hero + offer)
# ─────────────────────────────────────────────────────────────────────────────
def render_promo(photos, W, H, content, brand):
    sc=min(W,H)/900
    W2,H2=W*SSAA,H*SSAA
    sc2=min(W2,H2)/900

    canvas=Image.new("RGB",(W2,H2),NAVY)
    draw=ImageDraw.Draw(canvas)

    hdr_bot=draw_header(canvas,draw,W2,brand,sc2)
    footer_top=draw_footer(canvas,draw,W2,H2,brand,sc2)
    cy=hdr_bot

    # ── HERO PHOTO (full width, large) ────────────────────────────────────────
    hero_h=int(420*sc2)
    if photos:
        hero=cover_crop(photos[0],W2,hero_h)
        # Darkening vignette overlay
        ov=Image.new("RGBA",(W2,hero_h),(0,0,0,0))
        ovd=ImageDraw.Draw(ov)
        for y in range(hero_h):
            t=(y/hero_h)**1.8
            a=int(200*t)
            ovd.line([(0,y),(W2,y)],fill=(10,15,40,a))
        hero_rgba=hero.convert("RGBA")
        hero_rgba.alpha_composite(ov)
        canvas.paste(hero_rgba.convert("RGB"),(0,cy))
    else:
        gradient_rect(draw,0,cy,W2,cy+hero_h,(50,80,140),NAVY)

    # ── HEADLINE OVER PHOTO ────────────────────────────────────────────────────
    draw.rectangle([0,cy,W2,cy+int(5*sc2)],fill=GOLD)
    fHL=F(int(62*sc2),bold=True)
    fSub=F(int(30*sc2))
    hl=content.get("headline","JOIN THE ADVENTURE!")
    lines=wrap_text(hl,fHL,W2-int(80*sc2),draw).split("\n")
    y_hl=cy+int(22*sc2)
    for line in lines:
        cx_text(draw,line,fHL,y_hl,W2,GOLD,sw=3,sf=(0,0,0,200))
        bb=draw.textbbox((0,0),line,font=fHL)
        y_hl+=bb[3]-bb[1]+int(8*sc2)
    cx_text(draw,content.get("subheadline",""),fSub,y_hl,W2,WHITE,sw=2,sf=(0,0,0,160))
    cy+=hero_h+int(16*sc2)

    # ── OFFER BADGE ────────────────────────────────────────────────────────────
    offer_h=int(110*sc2)
    draw.rectangle([0,cy,W2,cy+offer_h],fill=GOLD_LT)
    draw.rectangle([0,cy,W2,cy+int(4*sc2)],fill=GOLD_DK)
    draw.rectangle([0,cy+offer_h-int(4*sc2),W2,cy+offer_h],fill=GOLD_DK)
    fOffer=F(int(26*sc2),bold=True)
    fPrice=F(int(50*sc2),bold=True)
    cx_text(draw,content.get("offer_text","EXCLUSIVE DEAL"),fOffer,cy+int(6*sc2),W2,NAVY)
    cx_text(draw,content.get("price","₹24,999"),fPrice,cy+int(36*sc2),W2,NAVY,sw=1,sf=GOLD_DK)
    fNote=F(int(18*sc2))
    cx_text(draw,content.get("price_note","per person | All Inclusive"),fNote,
            cy+int(90*sc2),W2,TEXT_DARK)
    cy+=offer_h+int(16*sc2)

    # ── HIGHLIGHT CARDS ────────────────────────────────────────────────────────
    hls=content.get("highlights",[])
    if hls:
        cols=2; rows=(len(hls[:6])+1)//2
        card_w=(W2-int(48*sc2))//cols; card_h=int(70*sc2)
        for i,hl_item in enumerate(hls[:6]):
            col_i=i%cols; row_i=i//cols
            cx_card=int(16*sc2)+col_i*(card_w+int(16*sc2))
            cy_card=cy+row_i*(card_h+int(10*sc2))
            rr(draw,[cx_card,cy_card,cx_card+card_w,cy_card+card_h],
               int(10*sc2),fill=WHITE,outline=NAVY,width=int(2*sc2))
            fHl=F(int(22*sc2))
            draw.text((cx_card+int(16*sc2),cy_card+int(18*sc2)),
                       f"✓  {hl_item}",font=fHl,fill=NAVY)
        cy+=rows*(card_h+int(10*sc2))+int(16*sc2)

    # ── MULTI-PHOTO STRIP ─────────────────────────────────────────────────────
    if len(photos)>1:
        strip_h=int(120*sc2)
        n=min(len(photos)-1,4)
        strip_w=(W2-int((n+1)*8*sc2))//n
        for i in range(n):
            px=int(8*sc2)+i*(strip_w+int(8*sc2))
            tile=cover_crop(photos[i+1],strip_w,strip_h)
            canvas.paste(tile,(px,cy))
            # Thin border
            draw.rectangle([px,cy,px+strip_w,cy+strip_h],outline=WHITE,width=int(3*sc2))
        cy+=strip_h+int(16*sc2)

    # ── CTA BAND ──────────────────────────────────────────────────────────────
    if cy < footer_top-int(80*sc2):
        cta_h=int(80*sc2)
        gradient_rect(draw,0,cy,W2,cy+cta_h,NAVY_MID,NAVY)
        draw.rectangle([0,cy,W2,cy+int(4*sc2)],fill=GOLD)
        fCTA=F(int(28*sc2),bold=True)
        cx_text(draw,content.get("cta","Book Now! Contact Us Today"),fCTA,
                cy+(cta_h-int(36*sc2))//2,W2,GOLD,sw=1,sf=GOLD_DK)

    # ── VALID / TAGLINE ────────────────────────────────────────────────────────
    if content.get("valid_till") and cy+int(40*sc2)<footer_top:
        fV=F(int(17*sc2))
        cy2=cy+cta_h+int(8*sc2) if cy < footer_top-int(80*sc2) else cy
        cx_text(draw,content.get("valid_till","Limited Period Offer"),fV,cy2,W2,(140,140,160))

    return canvas.convert("RGB").resize((W,H),Image.LANCZOS)


# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def to_bytes(img,fmt="PNG",quality=95):
    buf=io.BytesIO()
    img.convert("RGB").save(buf,format=fmt,quality=quality)
    return buf.getvalue()

def load_photos(raw_bytes_list):
    """Load and enhance photos from cached bytes."""
    out=[]
    for b in raw_bytes_list:
        try:
            img=Image.open(io.BytesIO(bytes(b))).convert("RGB")
            out.append(_enhance(img))
        except Exception:
            pass
    return out

# ─────────────────────────────────────────────────────────────────────────────
# PAGE
# ─────────────────────────────────────────────────────────────────────────────
def render():
    st.markdown("""<style>
    .fhero{font-size:2rem;font-weight:800;
      background:linear-gradient(120deg,#c9a84c,#1a2a5e);
      -webkit-background-clip:text;-webkit-text-fill-color:transparent}
    .fhero-s{color:#6b7280;font-size:.88rem;margin-top:2px}
    .bdg{display:inline-block;padding:3px 12px;border-radius:20px;
         font-size:.7rem;font-weight:700;margin-right:6px;margin-bottom:8px}
    .b1{background:#1a2a5e;color:#c9a84c}
    .b2{background:#c9a84c;color:#1a2a5e}
    .b3{background:linear-gradient(135deg,#7c3aed,#db2777);color:#fff}
    .empty{border:1px dashed #374151;border-radius:12px;padding:60px 20px;text-align:center}
    .ei{font-size:2.8rem}.et{color:#6b7280;margin-top:8px;font-size:.85rem}
    </style>""", unsafe_allow_html=True)

    st.markdown('<span class="bdg b1">✈ TRAVEL AGENCY</span>'
                '<span class="bdg b2">🏆 PRODUCTION FLYERS</span>'
                '<span class="bdg b3">🤖 AI COPY</span>',unsafe_allow_html=True)
    st.markdown('<div class="fhero">Professional Flyer Generator</div>',unsafe_allow_html=True)
    st.markdown('<div class="fhero-s">Like your reference designs — package flyers, service flyers, promo posters</div>',
                unsafe_allow_html=True)
    st.markdown("---")

    # ── BRAND KIT ─────────────────────────────────────────────────────────────
    with st.expander("🏷️ Brand Kit — set once, applied to every flyer", expanded=False):
        b1,b2,b3 = st.columns(3)
        with b1:
            st.markdown("**🖼️ Company Logo**")
            lu=st.file_uploader("Logo PNG",type=["png","jpg","jpeg"],key="bk_logo")
            if lu: st.session_state["brand_logo"]=lu.read()
            if st.session_state.get("brand_logo"):
                st.image(st.session_state["brand_logo"],width=110)
                if st.button("✕",key="rm_logo"): del st.session_state["brand_logo"]

        with b2:
            st.markdown("**🏅 Cert Badge**")
            cu=st.file_uploader("Badge",type=["png","jpg","jpeg"],key="bk_cert")
            if cu: st.session_state["brand_cert"]=cu.read()
            if st.session_state.get("brand_cert"):
                st.image(st.session_state["brand_cert"],width=80)
            st.markdown("**Certifications (comma-separated):**")
            certs_raw=st.text_input("",value=st.session_state.get("bk_certs","IATA,OTAI,ADTOI,NIMA,ETAA"),
                                     key="_certs",label_visibility="collapsed")
            st.session_state["bk_certs"]=certs_raw

        with b3:
            st.markdown("**🏢 Company Details**")
            bn=st.text_input("Company Name",value=st.session_state.get("bk_name","7 WONDERS WORLD"),key="_bn")
            bsuffix=st.text_input("Line 2",value=st.session_state.get("bk_suffix","TRAVELS PVT LTD"),key="_bsuffix")
            bsince=st.text_input("Est. / Since",value=st.session_state.get("bk_since","SINCE 2015"),key="_bsince")
            bweb=st.text_input("Website",value=st.session_state.get("bk_web","www.7wwtravels.com"),key="_bweb")
            bphone=st.text_input("Phone",value=st.session_state.get("bk_phone","+91 97112 81598"),key="_bphone")
            be1=st.text_input("Email 1",value=st.session_state.get("bk_e1","vidhi@7wwtravels.com"),key="_be1")
            be2=st.text_input("Email 2",value=st.session_state.get("bk_e2","anand@7wwtravels.com"),key="_be2")

            st.markdown("**📱 Social Handles**")
            bfb=st.text_input("Facebook",value=st.session_state.get("bk_fb","7wwtravels"),key="_bfb")
            big=st.text_input("Instagram",value=st.session_state.get("bk_ig","7ww_travels"),key="_big")
            byt=st.text_input("YouTube",value=st.session_state.get("bk_yt","@7wwtravels"),key="_byt")
            bli=st.text_input("LinkedIn",value=st.session_state.get("bk_li","7wwtravels/"),key="_bli")

            if st.button("💾 Save Brand Kit",use_container_width=True):
                st.session_state.update(
                    bk_name=bn,bk_suffix=bsuffix,bk_since=bsince,
                    bk_web=bweb,bk_phone=bphone,bk_e1=be1,bk_e2=be2,
                    bk_fb=bfb,bk_ig=big,bk_yt=byt,bk_li=bli)
                st.success("Brand Kit saved!")

        st.markdown("---")
        st.markdown("##### 🔑 AI Keys (free)")
        ka,kb=st.columns(2)
        with ka:
            gq=st.text_input("⚡ Groq",type="password",
                              value=st.session_state.get("groq_key",""),
                              placeholder="gsk_...",key="gq_in",
                              help="console.groq.com → free, fast")
            if gq: st.session_state["groq_key"]=gq.strip()
            st.success("✓ Groq active") if _groq_key() else st.info("console.groq.com")
        with kb:
            gm=st.text_input("🔵 Gemini",type="password",
                              value=st.session_state.get("gemini_key",""),
                              placeholder="AIzaSy...",key="gm_in",
                              help="aistudio.google.com/app/apikey — 250 req/day free")
            if gm: st.session_state["gemini_key"]=gm.strip()
            st.success("✓ Gemini active") if _gemini_key() else st.info("aistudio.google.com")

    # Build brand dict from session
    brand = {
        "name":    st.session_state.get("bk_name","7 WONDERS WORLD"),
        "suffix":  st.session_state.get("bk_suffix","TRAVELS PVT LTD"),
        "since":   st.session_state.get("bk_since","SINCE 2015"),
        "website": st.session_state.get("bk_web","www.7wwtravels.com"),
        "phone":   st.session_state.get("bk_phone","+91 97112 81598"),
        "email1":  st.session_state.get("bk_e1","vidhi@7wwtravels.com"),
        "email2":  st.session_state.get("bk_e2","anand@7wwtravels.com"),
        "facebook":  st.session_state.get("bk_fb","7wwtravels"),
        "instagram": st.session_state.get("bk_ig","7ww_travels"),
        "youtube":   st.session_state.get("bk_yt","@7wwtravels"),
        "linkedin":  st.session_state.get("bk_li","7wwtravels/"),
        "certs": [c.strip() for c in st.session_state.get("bk_certs","IATA,OTAI,ADTOI,NIMA,ETAA").split(",") if c.strip()],
    }

    st.markdown("---")

    # ── FLYER TABS ────────────────────────────────────────────────────────────
    tab_pkg, tab_svc, tab_promo, tab_bulk = st.tabs([
        "📦 Package Flyer",
        "🛂 Service Flyer",
        "🎯 Promo Flyer",
        "📥 Bulk Export",
    ])

    # ════════════════════════════════════════════════════════════════════════
    # PACKAGE FLYER
    # ════════════════════════════════════════════════════════════════════════
    with tab_pkg:
        st.markdown("### 📦 Tour Package Flyer")
        st.caption("Like your Bhutan reference — photo collage + itinerary + price box + hotel list")
        pl,pr=st.columns([1,1],gap="large")
        with pl:
            st.markdown("**📸 Destination Photos (upload 2-4)**")
            pkg_photos=st.file_uploader("",type=["jpg","jpeg","png","webp"],
                                         accept_multiple_files=True,key="pkg_photos",
                                         label_visibility="collapsed")
            # Read bytes immediately
            pkg_bytes=[]
            if pkg_photos:
                names=[p.name for p in pkg_photos]
                if st.session_state.get("_pkg_names")!=names:
                    fresh=[]
                    for p in pkg_photos[:6]:
                        try:
                            p.seek(0); b=p.read()
                            if b and len(b)>100:
                                Image.open(io.BytesIO(b)).verify()
                                fresh.append(b)
                        except Exception: pass
                    st.session_state["_pkg_bytes"]=fresh
                    st.session_state["_pkg_names"]=names
                pkg_bytes=st.session_state.get("_pkg_bytes",[])
                if pkg_bytes:
                    cols=st.columns(min(len(pkg_bytes),4))
                    for i,b in enumerate(pkg_bytes):
                        try:
                            img=Image.open(io.BytesIO(b))
                            s=100/img.width
                            cols[i].image(to_bytes(img.resize((100,int(img.height*s)),Image.LANCZOS)),
                                           use_container_width=True)
                        except Exception: pass
            else:
                pkg_bytes=st.session_state.get("_pkg_bytes",[])

            st.markdown("**QR Code (optional)**")
            qr_file=st.file_uploader("QR code image",type=["png","jpg"],key="pkg_qr")
            qr_bytes=qr_file.read() if qr_file else None

            st.markdown("**✍️ Describe the package**")
            pkg_prompt=st.text_area("",height=90,key="pkg_prompt",
                placeholder="Bhutan 5 nights 6 days, Rs 28777 per person, Thimphu 2N + Punakha 1N + Paro 2N, twin sharing, breakfast dinner included, Toyota vehicle",
                label_visibility="collapsed")
            platform=st.selectbox("Platform",list(PLATFORMS.keys()),key="pkg_plat")

            st.markdown("**🔧 Manual overrides** (leave blank to use AI)")
            pkg_hl   =st.text_input("Headline (optional)",key="pkg_hl")
            pkg_price=st.text_input("Price (optional)",key="pkg_price")
            pkg_valid=st.text_input("Valid till (optional)",key="pkg_valid")

            gen_pkg=st.button("🚀 Generate Package Flyer",type="primary",
                               use_container_width=True,
                               disabled=not pkg_prompt.strip())

        with pr:
            st.markdown("### 👁️ Preview")
            if gen_pkg and pkg_prompt.strip():
                with st.spinner("🤖 AI generating package content…"):
                    content=ai_content(pkg_prompt,"PACKAGE",brand)
                if pkg_hl:    content["headline"]=pkg_hl
                if pkg_price: content["price"]=pkg_price
                if pkg_valid: content["price_validity"]=pkg_valid

                photos=load_photos(pkg_bytes)
                W,H=PLATFORMS[platform]
                with st.spinner(f"Rendering {W}×{H} at 2× quality…"):
                    flyer=render_package(photos,W,H,content,brand,qr_bytes)

                st.session_state.update(pkg_flyer=to_bytes(flyer,"JPEG",95),
                                         pkg_flyer_png=to_bytes(flyer,"PNG"),
                                         pkg_content=content)

            if st.session_state.get("pkg_flyer"):
                st.image(st.session_state["pkg_flyer"],use_container_width=True)
                d1,d2=st.columns(2)
                with d1:
                    st.download_button("📥 JPEG",data=st.session_state["pkg_flyer"],
                        file_name="package_flyer.jpg",mime="image/jpeg",use_container_width=True)
                with d2:
                    st.download_button("📥 PNG",data=st.session_state["pkg_flyer_png"],
                        file_name="package_flyer.png",mime="image/png",use_container_width=True)
                st.success("✅ Ready!")

                if st.session_state.get("pkg_content"):
                    c=st.session_state["pkg_content"]
                    with st.expander("📋 AI-Generated Copy"):
                        st.text_area("Hashtags",value=c.get("hashtags",""),height=60)
                        st.text_area("Tagline",value=c.get("tagline",""),height=50)
            else:
                st.markdown('<div class="empty"><div class="ei">📦</div>'
                            '<div class="et">Fill in details → Generate</div></div>',
                            unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # SERVICE FLYER
    # ════════════════════════════════════════════════════════════════════════
    with tab_svc:
        st.markdown("### 🛂 Service / Visa Flyer")
        st.caption("Like your 'Your Gateway to the World' reference — services as colored pills")
        sl,sr=st.columns([1,1],gap="large")
        with sl:
            st.markdown("**📸 Hero Photo (optional)**")
            svc_photo=st.file_uploader("Background photo",type=["jpg","jpeg","png","webp"],key="svc_photo")
            svc_bytes=[]
            if svc_photo:
                try:
                    svc_photo.seek(0); b=svc_photo.read()
                    Image.open(io.BytesIO(b)).verify()
                    svc_bytes=[b]
                    st.image(b,use_container_width=True)
                except Exception:
                    st.warning("Invalid image")

            st.markdown("**✍️ Describe your services**")
            svc_prompt=st.text_area("",height=90,key="svc_prompt",
                placeholder="Visa services for all countries — tourist visa, business visa, tour packages, hotel bookings, euro rail, flight bookings",
                label_visibility="collapsed")
            svc_plat=st.selectbox("Platform",list(PLATFORMS.keys()),key="svc_plat")

            svc_hl=st.text_input("Headline (optional)",key="svc_hl")
            gen_svc=st.button("🚀 Generate Service Flyer",type="primary",
                               use_container_width=True,disabled=not svc_prompt.strip())

        with sr:
            st.markdown("### 👁️ Preview")
            if gen_svc and svc_prompt.strip():
                with st.spinner("🤖 AI generating service content…"):
                    content=ai_content(svc_prompt,"SERVICE",brand)
                if svc_hl: content["headline"]=svc_hl

                photos=load_photos(svc_bytes)
                W,H=PLATFORMS[svc_plat]
                with st.spinner(f"Rendering {W}×{H}…"):
                    flyer=render_service(photos,W,H,content,brand)

                st.session_state.update(svc_flyer=to_bytes(flyer,"JPEG",95),
                                         svc_flyer_png=to_bytes(flyer,"PNG"))

            if st.session_state.get("svc_flyer"):
                st.image(st.session_state["svc_flyer"],use_container_width=True)
                d1,d2=st.columns(2)
                with d1:
                    st.download_button("📥 JPEG",data=st.session_state["svc_flyer"],
                        file_name="service_flyer.jpg",mime="image/jpeg",use_container_width=True)
                with d2:
                    st.download_button("📥 PNG",data=st.session_state["svc_flyer_png"],
                        file_name="service_flyer.png",mime="image/png",use_container_width=True)
                st.success("✅ Ready!")
            else:
                st.markdown('<div class="empty"><div class="ei">🛂</div>'
                            '<div class="et">Fill in details → Generate</div></div>',
                            unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # PROMO FLYER
    # ════════════════════════════════════════════════════════════════════════
    with tab_promo:
        st.markdown("### 🎯 Promotional Flyer")
        st.caption("Bold hero photo + offer price + highlights — like 'Join the Adventure' reference")
        ol,or_=st.columns([1,1],gap="large")
        with ol:
            st.markdown("**📸 Photos (upload 1-4)**")
            promo_photos=st.file_uploader("",type=["jpg","jpeg","png","webp"],
                                           accept_multiple_files=True,key="promo_photos",
                                           label_visibility="collapsed")
            promo_bytes=[]
            if promo_photos:
                names=[p.name for p in promo_photos]
                if st.session_state.get("_promo_names")!=names:
                    fresh=[]
                    for p in promo_photos[:5]:
                        try:
                            p.seek(0); b=p.read()
                            if b and len(b)>100:
                                Image.open(io.BytesIO(b)).verify()
                                fresh.append(b)
                        except Exception: pass
                    st.session_state["_promo_bytes"]=fresh
                    st.session_state["_promo_names"]=names
                promo_bytes=st.session_state.get("_promo_bytes",[])
                if promo_bytes:
                    cols=st.columns(min(len(promo_bytes),4))
                    for i,b in enumerate(promo_bytes):
                        try:
                            img=Image.open(io.BytesIO(b))
                            s=100/img.width
                            cols[i].image(to_bytes(img.resize((100,int(img.height*s)),Image.LANCZOS)),
                                           use_container_width=True)
                        except Exception: pass
            else:
                promo_bytes=st.session_state.get("_promo_bytes",[])

            st.markdown("**✍️ Describe the promotion**")
            promo_prompt=st.text_area("",height=90,key="promo_prompt",
                placeholder="Special summer offer — Europe tours from Rs 89,999, flights + hotels + visa, 10 nights, limited seats available",
                label_visibility="collapsed")
            promo_plat=st.selectbox("Platform",list(PLATFORMS.keys()),key="promo_plat")
            promo_hl=st.text_input("Headline (optional)",key="promo_hl")
            promo_price=st.text_input("Price (optional)",key="promo_price")
            gen_promo=st.button("🚀 Generate Promo Flyer",type="primary",
                                 use_container_width=True,disabled=not promo_prompt.strip())

        with or_:
            st.markdown("### 👁️ Preview")
            if gen_promo and promo_prompt.strip():
                with st.spinner("🤖 AI generating promo content…"):
                    content=ai_content(promo_prompt,"PROMO",brand)
                if promo_hl:    content["headline"]=promo_hl
                if promo_price: content["price"]=promo_price

                photos=load_photos(promo_bytes)
                W,H=PLATFORMS[promo_plat]
                with st.spinner(f"Rendering {W}×{H}…"):
                    flyer=render_promo(photos,W,H,content,brand)

                st.session_state.update(promo_flyer=to_bytes(flyer,"JPEG",95),
                                         promo_flyer_png=to_bytes(flyer,"PNG"),
                                         promo_content=content)

            if st.session_state.get("promo_flyer"):
                st.image(st.session_state["promo_flyer"],use_container_width=True)
                d1,d2=st.columns(2)
                with d1:
                    st.download_button("📥 JPEG",data=st.session_state["promo_flyer"],
                        file_name="promo_flyer.jpg",mime="image/jpeg",use_container_width=True)
                with d2:
                    st.download_button("📥 PNG",data=st.session_state["promo_flyer_png"],
                        file_name="promo_flyer.png",mime="image/png",use_container_width=True)
                st.success("✅ Ready!")
                if st.session_state.get("promo_content"):
                    c=st.session_state["promo_content"]
                    with st.expander("📋 AI Copy"):
                        st.text_area("Hashtags",value=c.get("hashtags",""),height=60)
            else:
                st.markdown('<div class="empty"><div class="ei">🎯</div>'
                            '<div class="et">Fill in details → Generate</div></div>',
                            unsafe_allow_html=True)

    # ════════════════════════════════════════════════════════════════════════
    # BULK EXPORT
    # ════════════════════════════════════════════════════════════════════════
    with tab_bulk:
        st.markdown("### 📥 Bulk Export — same flyer in all platform sizes")
        st.info("Uses whichever flyer was last generated (Package / Service / Promo)")

        generated={}
        if st.session_state.get("pkg_flyer_png"):    generated["Package"]=st.session_state["pkg_flyer_png"]
        if st.session_state.get("svc_flyer_png"):    generated["Service"]=st.session_state["svc_flyer_png"]
        if st.session_state.get("promo_flyer_png"):  generated["Promo"]=st.session_state["promo_flyer_png"]

        if not generated:
            st.markdown('<div class="empty"><div class="ei">📥</div>'
                        '<div class="et">Generate a flyer first in the other tabs</div></div>',
                        unsafe_allow_html=True)
        else:
            sel=st.selectbox("Which flyer?",list(generated.keys()))
            sel_plats=st.multiselect("Export for",list(PLATFORMS.keys()),
                                      default=list(PLATFORMS.keys())[:5])
            if st.button("📦 Generate ZIP",type="primary",
                          use_container_width=True,disabled=not sel_plats):
                src=Image.open(io.BytesIO(generated[sel])).convert("RGB")
                zbuf=io.BytesIO()
                prog=st.progress(0)
                with zipfile.ZipFile(zbuf,"w",zipfile.ZIP_DEFLATED) as zf:
                    for i,pname in enumerate(sel_plats):
                        W2,H2=PLATFORMS[pname]
                        resized=src.resize((W2,H2),Image.LANCZOS)
                        safe=re.sub(r"[^\w]","_",pname)[:30]
                        zf.writestr(f"{sel}_flyer_{safe}_{W2}x{H2}.jpg",
                                    to_bytes(resized,"JPEG",93))
                        prog.progress((i+1)/len(sel_plats))
                prog.empty(); zbuf.seek(0)
                st.success(f"✅ {len(sel_plats)} sizes ready!")
                st.download_button("📥 Download ZIP",data=zbuf.getvalue(),
                    file_name=f"{sel}_flyer_all_platforms.zip",
                    mime="application/zip",use_container_width=True)

    st.markdown("---")
    with st.expander("💡 Tips for best flyers"):
        st.markdown("""
**Package Flyer (Bhutan style):**
- Upload 3 photos: wide landscape, monastery/temple, mountain/nature
- Prompt: include city-wise nights breakdown, exact price, inclusions
- Example: *"Bhutan 6 days 5 nights, Rs 28777, Thimphu 2N + Punakha 1N + Paro 2N, twin sharing, breakfast dinner, Toyota, 4 guests min"*

**Service Flyer (Gateway style):**
- Upload 1 wide photo with world landmarks or maps
- Prompt: list all your services
- Example: *"Visa for all countries — tourist, business, corporate. Also tour packages, hotels, euro rail, flight bookings"*

**Promo Flyer (Adventure style):**
- Upload 1 bold hero photo + 2-3 smaller activity photos
- Prompt: include the offer, price, urgency
- Example: *"Summer Europe special — 10 nights Rs 89,999 per person, flights hotels visa, limited seats, book before June 30"*

**Photo tips:**
- Minimum 1200px wide for crisp output (2× supersampling renders at 2400px)
- Landscape orientation works best for hero photos
- Portrait-oriented temple/monument shots work well in the 3-tile mosaic
        """)
