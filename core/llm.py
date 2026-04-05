"""
LLM engine — priority order:
  1. Groq  (free tier, very fast llama-3/mixtral)  key starts with gsk_
  2. OpenAI (if key provided)                       key starts with sk-
  3. Ollama (fully local, zero cost)
  4. Stub  (offline demo mode)
"""

from __future__ import annotations
import os, json, textwrap
import streamlit as st
from typing import Generator


# ── Key resolution ────────────────────────────────────────────────────────────

def _get_key() -> str:
    # 1. Session state (user typed it in sidebar)
    key = st.session_state.get("api_key", "")
    if key:
        return key

    # 2. Streamlit Cloud secrets (most reliable on cloud)
    try:
        key = st.secrets.get("GROQ_API_KEY", "") or st.secrets.get("OPENAI_API_KEY", "")
        if key:
            return key
    except Exception:
        pass

    # 3. Environment variables (local dev)
    return os.getenv("GROQ_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")


def _provider() -> str:
    key = _get_key()
    if key.startswith("gsk_"):
        return "groq"
    if key.startswith("sk-"):
        return "openai"
    if key:
        return "openai"   # unknown format — try openai

    # Try Ollama
    try:
        import requests
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        if r.ok:
            return "ollama"
    except Exception:
        pass

    return "stub"


# ── Groq ──────────────────────────────────────────────────────────────────────

def _groq_complete(messages: list[dict], stream: bool = False):
    try:
        from groq import Groq
    except ImportError:
        st.error("groq package not installed. Add `groq>=0.9.0` to requirements.txt")
        raise

    client = Groq(api_key=_get_key())
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        stream=stream,
        temperature=0.8,
        max_tokens=2048,
    )
    if stream:
        def gen():
            for chunk in resp:
                yield chunk.choices[0].delta.content or ""
        return gen()
    return resp.choices[0].message.content


# ── OpenAI ────────────────────────────────────────────────────────────────────

def _openai_complete(messages: list[dict], stream: bool = False):
    try:
        from openai import OpenAI
    except ImportError:
        st.error("openai package not installed. Add `openai>=1.30.0` to requirements.txt")
        raise

    client = OpenAI(api_key=_get_key())
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        stream=stream,
        temperature=0.8,
        max_tokens=2048,
    )
    if stream:
        def gen():
            for chunk in resp:
                yield chunk.choices[0].delta.content or ""
        return gen()
    return resp.choices[0].message.content


# ── Ollama ────────────────────────────────────────────────────────────────────

def _ollama_complete(messages: list[dict], stream: bool = False):
    import requests
    payload = {
        "model": os.getenv("OLLAMA_MODEL", "llama3.3"),
        "messages": messages,
        "stream": stream,
    }
    r = requests.post("http://localhost:11434/api/chat",
                      json=payload, stream=stream, timeout=120)
    if stream:
        def gen():
            for line in r.iter_lines():
                if line:
                    d = json.loads(line)
                    yield d.get("message", {}).get("content", "")
        return gen()
    return r.json()["message"]["content"]


# ── Stub (demo / offline) ─────────────────────────────────────────────────────

_STUBS = {
    "script": textwrap.dedent("""\
        [HOOK — 0:00-0:05]
        Did you know 90% of creators quit before they ever go viral?

        [PROBLEM — 0:05-0:20]
        Most people spend hours writing scripts, recording, editing —
        only to get 47 views. The algorithm doesn't care how hard you worked.

        [SOLUTION — 0:20-0:40]
        But what if AI could do all of that in 60 seconds?
        Three free tools. No budget. No team. 100K views.

        [CTA — 0:40-0:50]
        Follow for the exact workflow. Dropping it tomorrow.
    """),
    "hooks": "\n".join([
        "1. This simple trick got me 100K views overnight (and it's completely free)",
        "2. Stop doing this if you want to grow on YouTube in 2025",
        "3. I tested every AI tool so you don't have to — here's what works",
        "4. Nobody talks about this, but it's the #1 reason creators fail",
        "5. The 60-second workflow that replaced my entire content team",
    ]),
    "calendar": json.dumps([
        {"day": "Mon", "idea": "Tool reveal: Top 3 free AI tools for creators", "format": "Short", "hook_score": 87, "notes": ""},
        {"day": "Tue", "idea": "Behind the scenes: How I make AI clone videos",  "format": "Long",  "hook_score": 91, "notes": ""},
        {"day": "Wed", "idea": "Myth vs fact: AI content is NOT cheating",        "format": "Short", "hook_score": 78, "notes": ""},
        {"day": "Thu", "idea": "Step-by-step: Clone your voice in 5 minutes",    "format": "Tutorial", "hook_score": 94, "notes": ""},
        {"day": "Fri", "idea": "Weekly AI news digest",                           "format": "Short", "hook_score": 82, "notes": ""},
        {"day": "Sat", "idea": "Q&A: Your biggest AI questions answered",          "format": "Long",  "hook_score": 75, "notes": ""},
        {"day": "Sun", "idea": "Motivation: The future belongs to AI-first creators", "format": "Short", "hook_score": 80, "notes": ""},
    ]),
}

def _stub_complete(mode: str, stream: bool):
    text = _STUBS.get(mode, _STUBS["script"])
    if stream:
        def gen():
            for word in text.split():
                yield word + " "
        return gen()
    return text


# ── Public API ────────────────────────────────────────────────────────────────

def complete(
    system: str,
    user: str,
    mode: str = "script",
    stream: bool = False,
):
    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": user},
    ]
    provider = _provider()

    if provider == "groq":
        return _groq_complete(messages, stream=stream)
    elif provider == "openai":
        return _openai_complete(messages, stream=stream)
    elif provider == "ollama":
        return _ollama_complete(messages, stream=stream)
    else:
        return _stub_complete(mode, stream=stream)


def get_provider_badge() -> str:
    badges = {
        "groq":   "⚡ Groq (Free)",
        "openai": "🟢 OpenAI",
        "ollama": "🖥️ Ollama (Local)",
        "stub":   "🔌 Demo Mode — add API key in sidebar",
    }
    return badges.get(_provider(), _provider())
