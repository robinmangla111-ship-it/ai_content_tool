"""
LLM engine — priority order:
  1. Groq  (free tier, very fast llama-3/mixtral)
  2. OpenAI (if key provided)
  3. Ollama (fully local, zero cost)
  4. Stub  (offline demo mode)
"""

from __future__ import annotations
import os, json, textwrap, re
import streamlit as st
from typing import Generator

# ── Provider detection ───────────────────────────────────────────────────────

def _get_key() -> str:
    # Priority: session state → env var → Streamlit secrets
    key = st.session_state.get("api_key", "")
    if key:
        return key
    key = os.getenv("GROQ_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
    if key:
        return key
    try:
        # Streamlit Cloud secrets
        return st.secrets.get("GROQ_API_KEY", "") or st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        return ""

def _provider() -> str:
    key = _get_key()
    if not key:
        # try Ollama
        try:
            import requests
            r = requests.get("http://localhost:11434/api/tags", timeout=2)
            if r.ok:
                return "ollama"
        except Exception:
            pass
        return "stub"
    if key.startswith("gsk_"):
        return "groq"
    return "openai"

# ── Groq ─────────────────────────────────────────────────────────────────────

def _groq_complete(messages: list[dict], model="llama-3.3-70b-versatile", stream=False) -> str | Generator:
    from groq import Groq
    client = Groq(api_key=_get_key())
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=stream,
        temperature=0.8,
        max_tokens=2048,
    )
    if stream:
        def gen():
            for chunk in resp:
                delta = chunk.choices[0].delta.content or ""
                yield delta
        return gen()
    return resp.choices[0].message.content

# ── OpenAI ───────────────────────────────────────────────────────────────────

def _openai_complete(messages: list[dict], model="gpt-4o-mini", stream=False) -> str | Generator:
    from openai import OpenAI
    client = OpenAI(api_key=_get_key())
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        stream=stream,
        temperature=0.8,
        max_tokens=2048,
    )
    if stream:
        def gen():
            for chunk in resp:
                delta = chunk.choices[0].delta.content or ""
                yield delta
        return gen()
    return resp.choices[0].message.content

# ── Ollama ───────────────────────────────────────────────────────────────────

def _ollama_complete(messages: list[dict], model="llama3", stream=False) -> str | Generator:
    import requests
    payload = {"model": model, "messages": messages, "stream": stream}
    r = requests.post("http://localhost:11434/api/chat", json=payload, stream=stream, timeout=120)
    if stream:
        def gen():
            for line in r.iter_lines():
                if line:
                    d = json.loads(line)
                    yield d.get("message", {}).get("content", "")
        return gen()
    return r.json()["message"]["content"]

# ── Stub (offline demo) ──────────────────────────────────────────────────────

STUBS = {
    "script": textwrap.dedent("""\
        [HOOK — 0:00-0:05]
        Did you know 90% of creators quit before they ever go viral?

        [PROBLEM — 0:05-0:20]
        Most people spend hours writing scripts, recording, editing…
        only to get 47 views. The algorithm doesn't care how hard you worked.

        [SOLUTION — 0:20-0:40]
        But what if AI could do all of that in 60 seconds?
        I used three free tools — no budget, no team — and hit 100K views.

        [CTA — 0:40-0:50]
        Follow for the exact workflow. I'm dropping it tomorrow.
    """),
    "hooks": [
        "This simple trick got me 100K views overnight (and it's completely free)",
        "Stop doing this if you want to grow on YouTube in 2025",
        "I tested every AI tool so you don't have to — here's what actually works",
        "Nobody talks about this, but it's the #1 reason creators fail",
        "The 60-second workflow that replaced my entire content team",
    ],
    "calendar": [
        {"day": "Mon", "idea": "Tool reveal: Top 3 free AI tools for creators", "format": "Short", "hook_score": 87},
        {"day": "Tue", "idea": "Behind the scenes: How I make AI clone videos", "format": "Long", "hook_score": 91},
        {"day": "Wed", "idea": "Myth vs fact: AI content is NOT cheating", "format": "Short", "hook_score": 78},
        {"day": "Thu", "idea": "Step-by-step: Clone your voice in 5 minutes free", "format": "Tutorial", "hook_score": 94},
        {"day": "Fri", "idea": "Weekly AI news digest (trending)", "format": "Short", "hook_score": 82},
        {"day": "Sat", "idea": "Q&A: Your biggest AI content questions answered", "format": "Long", "hook_score": 75},
        {"day": "Sun", "idea": "Motivational: The future belongs to AI-first creators", "format": "Short", "hook_score": 80},
    ],
}

def _stub_complete(prompt: str, mode: str = "script") -> str:
    if mode == "hooks":
        return "\n".join(f"{i+1}. {h}" for i, h in enumerate(STUBS["hooks"]))
    if mode == "calendar":
        return json.dumps(STUBS["calendar"])
    return STUBS["script"]

# ── Public API ───────────────────────────────────────────────────────────────

def complete(
    system: str,
    user: str,
    mode: str = "script",
    stream: bool = False,
) -> str | Generator:
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    provider = _provider()

    if provider == "groq":
        return _groq_complete(messages, stream=stream)
    elif provider == "openai":
        return _openai_complete(messages, stream=stream)
    elif provider == "ollama":
        return _ollama_complete(messages, stream=stream)
    else:
        # offline stub — simulate streaming
        text = _stub_complete(user, mode)
        if stream:
            def gen():
                for word in text.split():
                    yield word + " "
            return gen()
        return text

def get_provider_badge() -> str:
    p = _provider()
    badges = {
        "groq":   "⚡ Groq (Free)",
        "openai": "🟢 OpenAI",
        "ollama": "🖥️ Ollama (Local)",
        "stub":   "🔌 Demo Mode",
    }
    return badges.get(p, p)
