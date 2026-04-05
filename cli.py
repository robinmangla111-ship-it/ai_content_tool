#!/usr/bin/env python3
"""
ContentAI Studio — CLI
Usage:
  python cli.py script  --topic "Your topic" --niche "AI" --length short
  python cli.py hooks   --topic "Your topic"
  python cli.py calendar --niche "AI" --days 7
  python cli.py tts     --text "Hello world" --out output.mp3
"""

import argparse, os, sys, json, textwrap

# ── Minimal env setup (no Streamlit needed) ──────────────────────────────────
os.environ.setdefault("GROQ_API_KEY", os.getenv("GROQ_API_KEY", ""))
os.environ.setdefault("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))

sys.path.insert(0, os.path.dirname(__file__))

# ── Colour helpers ───────────────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
PURPLE = "\033[95m"
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
DIM    = "\033[2m"

def banner():
    print(f"""
{PURPLE}{BOLD}╔══════════════════════════════════════╗
║   🎬  ContentAI Studio  CLI  v1.0   ║
╚══════════════════════════════════════╝{RESET}
""")

def section(title: str):
    print(f"\n{CYAN}{BOLD}── {title} ──{RESET}")

def success(msg: str):
    print(f"{GREEN}✓ {msg}{RESET}")

def warn(msg: str):
    print(f"{YELLOW}⚠ {msg}{RESET}")

def err(msg: str):
    print(f"{RED}✗ {msg}{RESET}")

# ── LLM call (same engine as the UI) ─────────────────────────────────────────
def llm_complete(system: str, user: str, stream: bool = True) -> str:
    """Call LLM with auto provider detection."""
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY", "")

    # Groq
    if api_key.startswith("gsk_"):
        try:
            from groq import Groq
            client = Groq(api_key=api_key)
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role":"system","content":system},{"role":"user","content":user}],
                stream=stream,
                temperature=0.8,
                max_tokens=2048,
            )
            if stream:
                full = ""
                for chunk in resp:
                    delta = chunk.choices[0].delta.content or ""
                    print(delta, end="", flush=True)
                    full += delta
                print()
                return full
            return resp.choices[0].message.content
        except ImportError:
            warn("groq package not found. Run: pip install groq")

    # OpenAI
    elif api_key.startswith("sk-"):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role":"system","content":system},{"role":"user","content":user}],
                stream=stream,
                max_tokens=2048,
            )
            if stream:
                full = ""
                for chunk in resp:
                    delta = chunk.choices[0].delta.content or ""
                    print(delta, end="", flush=True)
                    full += delta
                print()
                return full
            return resp.choices[0].message.content
        except ImportError:
            warn("openai package not found. Run: pip install openai")

    # Ollama
    else:
        try:
            import requests
            payload = {
                "model": os.getenv("OLLAMA_MODEL", "llama3.3"),
                "messages": [{"role":"system","content":system},{"role":"user","content":user}],
                "stream": stream,
            }
            r = requests.post("http://localhost:11434/api/chat", json=payload, stream=stream, timeout=120)
            if stream:
                full = ""
                for line in r.iter_lines():
                    if line:
                        d = json.loads(line)
                        delta = d.get("message",{}).get("content","")
                        print(delta, end="", flush=True)
                        full += delta
                        if d.get("done"):
                            break
                print()
                return full
            return r.json()["message"]["content"]
        except Exception as e:
            warn(f"Ollama not available: {e}")

    # Stub
    warn("No API key found. Using demo stub. Set GROQ_API_KEY for real output.")
    stub = textwrap.dedent("""\
    [HOOK 0:00-0:05]
    Did you know 90% of creators quit before they ever go viral?

    [PROBLEM 0:05-0:20]
    Most people spend hours writing scripts, recording, editing —
    only to get 47 views. The algorithm doesn't care how hard you worked.

    [SOLUTION 0:20-0:40]
    But what if AI could do all of that in 60 seconds?
    Three free tools. No budget. No team. 100K views.

    [CTA 0:40-0:50]
    Follow for the exact workflow. Dropping it tomorrow.
    """)
    print(stub)
    return stub

# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_script(args):
    from core.prompts import SCRIPT_SYSTEM, SCRIPT_USER
    section("Script Generator")
    print(f"{DIM}Topic: {args.topic} | Niche: {args.niche} | Length: {args.length}{RESET}\n")
    prompt = SCRIPT_USER.format(
        topic=args.topic,
        niche=args.niche,
        audience=args.audience,
        tone=args.tone,
        length=args.length,
        keywords=args.keywords,
    )
    result = llm_complete(SCRIPT_SYSTEM, prompt, stream=True)
    if args.out:
        with open(args.out, "w") as f:
            f.write(result)
        success(f"Script saved to {args.out}")


def cmd_hooks(args):
    from core.prompts import HOOK_SYSTEM, HOOK_USER
    section("Hook Builder")
    print(f"{DIM}Topic: {args.topic}{RESET}\n")
    result = llm_complete(
        HOOK_SYSTEM,
        HOOK_USER.format(topic=args.topic, niche=args.niche, audience=args.audience),
        stream=True,
    )
    if args.out:
        with open(args.out, "w") as f:
            f.write(result)
        success(f"Hooks saved to {args.out}")


def cmd_calendar(args):
    from core.prompts import CALENDAR_SYSTEM, CALENDAR_USER
    section("Content Calendar")
    print(f"{DIM}Niche: {args.niche} | Days: {args.days}{RESET}\n")
    result = llm_complete(
        CALENDAR_SYSTEM,
        CALENDAR_USER.format(niche=args.niche, style=args.style, frequency=args.freq, trends=args.trends),
        stream=False,
    )
    # Try parse + pretty print
    try:
        clean = result.strip().lstrip("```json").rstrip("```").strip()
        data = json.loads(clean)
        for day in data:
            score = day.get("hook_score", 0)
            bar = "█" * (score // 10) + "░" * (10 - score // 10)
            color = GREEN if score >= 80 else YELLOW if score >= 60 else RED
            print(f"{BOLD}{day.get('day','?'):5s}{RESET}  {day.get('idea','')}")
            print(f"       {DIM}{day.get('format','Short'):10s}  {color}[{bar}] {score}/100{RESET}")
            print()
        if args.out:
            with open(args.out, "w") as f:
                json.dump(data, f, indent=2)
            success(f"Calendar saved to {args.out}")
    except Exception:
        print(result)


def cmd_tts(args):
    """Generate voice audio via ElevenLabs or Coqui TTS."""
    section("Text-to-Speech")
    el_key  = os.getenv("ELEVEN_API_KEY", "")
    voice_id = os.getenv("ELEVEN_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

    text = args.text
    if args.file:
        with open(args.file) as f:
            text = f.read()

    if el_key:
        import requests
        print(f"Using ElevenLabs voice ID: {voice_id}")
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {"xi-api-key": el_key, "Content-Type": "application/json"}
        payload = {
            "text": text,
            "model_id": "eleven_turbo_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.85},
        }
        r = requests.post(url, json=payload, headers=headers)
        out = args.out or "output.mp3"
        with open(out, "wb") as f:
            f.write(r.content)
        success(f"Audio saved to {out}")

    else:
        warn("ELEVEN_API_KEY not set. Trying Coqui TTS (local)...")
        try:
            from TTS.api import TTS
            tts = TTS("tts_models/en/ljspeech/tacotron2-DDC")
            out = args.out or "output.wav"
            tts.tts_to_file(text=text, file_path=out)
            success(f"Audio saved to {out} (Coqui TTS)")
        except ImportError:
            err("Neither ElevenLabs key nor Coqui TTS found.")
            print("  Option A: Set ELEVEN_API_KEY env var")
            print("  Option B: pip install TTS")


def cmd_ui(args):
    """Launch Streamlit UI."""
    import subprocess
    subprocess.run(["streamlit", "run", os.path.join(os.path.dirname(__file__), "app.py")])


# ── Argument parser ───────────────────────────────────────────────────────────

def main():
    banner()

    parser = argparse.ArgumentParser(
        prog="contentai",
        description="ContentAI Studio — AI content tool for creators",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # script
    p_script = sub.add_parser("script", help="Generate a video script")
    p_script.add_argument("--topic",    required=True)
    p_script.add_argument("--niche",    default="AI & Technology")
    p_script.add_argument("--audience", default="general audience")
    p_script.add_argument("--tone",     default="Energetic & Fast")
    p_script.add_argument("--length",   default="60 seconds (Short)")
    p_script.add_argument("--keywords", default="")
    p_script.add_argument("--out",      default=None, help="Save to file")

    # hooks
    p_hooks = sub.add_parser("hooks", help="Generate 5 viral hooks")
    p_hooks.add_argument("--topic",    required=True)
    p_hooks.add_argument("--niche",    default="AI & Technology")
    p_hooks.add_argument("--audience", default="general audience")
    p_hooks.add_argument("--out",      default=None)

    # calendar
    p_cal = sub.add_parser("calendar", help="Generate 7-day content calendar")
    p_cal.add_argument("--niche",  default="AI & Technology")
    p_cal.add_argument("--style",  default="Educational")
    p_cal.add_argument("--freq",   default=5, type=int)
    p_cal.add_argument("--trends", default="")
    p_cal.add_argument("--days",   default=7, type=int)
    p_cal.add_argument("--out",    default=None)

    # tts
    p_tts = sub.add_parser("tts", help="Convert text to speech (voice clone)")
    p_tts.add_argument("--text", default="", help="Text to speak")
    p_tts.add_argument("--file", default=None, help="Read text from file (e.g. your script)")
    p_tts.add_argument("--out",  default=None, help="Output audio file")

    # ui
    sub.add_parser("ui", help="Launch the Streamlit web UI")

    args = parser.parse_args()

    dispatch = {
        "script":   cmd_script,
        "hooks":    cmd_hooks,
        "calendar": cmd_calendar,
        "tts":      cmd_tts,
        "ui":       cmd_ui,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
