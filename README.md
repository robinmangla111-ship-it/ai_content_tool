# 🎬 ContentAI Studio

An all-in-one AI content tool for creators — built with Python + Streamlit.
Inspired by creators like Vaibhav Sisinty who use AI clone workflows at scale.

## ✨ Features

| Feature | Description |
|---|---|
| ✍️ Script Generator | AI-powered scripts for Shorts & long-form with titles & descriptions |
| 🎣 Hook Builder | 5 viral hooks + real-time hook score (0-99) |
| 📅 Content Calendar | 7-day AI content plan exported as CSV/JSON |
| 🗣️ Voice Clone Setup | ElevenLabs + Coqui TTS guides + Python snippets |
| 🎥 Avatar Video Guide | Full Vidnoz/D-ID workflow + self-hosted SadTalker |
| 📊 Analytics Tracker | Session stats + manual video performance log |
| ⚙️ Settings | Multi-provider API key management + deploy guide |

## 🚀 Quick Start

```bash
git clone https://github.com/yourname/ai-content-studio
cd ai-content-studio
pip install -r requirements.txt
streamlit run app.py
```

## 🔑 LLM Providers (priority order)

The app auto-detects which provider to use — no config needed:

1. **Groq** (free, fastest) — add key starting with `gsk_`
2. **OpenAI** — add key starting with `sk-`
3. **Ollama** (local, zero cost) — install + `ollama pull llama3.3`
4. **Demo mode** — works offline with stub responses

Get a free Groq key: https://console.groq.com

## ☁️ Free Deployment

### Streamlit Cloud
1. Push to GitHub
2. Go to share.streamlit.io
3. Connect repo, set `app.py` as entry
4. Add secrets:
```toml
GROQ_API_KEY = "gsk_..."
ELEVEN_API_KEY = "sk_..."
```

### Hugging Face Spaces
- SDK: Streamlit
- Upload all files
- Add secrets in Space settings

## 📦 Free Tool Stack

| Tool | Purpose | Free Tier |
|---|---|---|
| [Groq](https://console.groq.com) | LLM (Scripts, Hooks, Calendar) | Free, fast llama-3.3-70b |
| [ElevenLabs](https://elevenlabs.io) | Voice cloning | 10,000 chars/month |
| [Vidnoz](https://vidnoz.com) | AI avatar videos | 60 min/month |
| [D-ID](https://d-id.com) | AI avatar (more realistic) | 14-day trial |
| [CapCut](https://capcut.com) | Editing + auto-captions | Fully free |
| [Ollama](https://ollama.ai) | Local LLM | Free forever |
| [Coqui TTS](https://github.com/coqui-ai/TTS) | Local voice clone | Free forever |

## 📁 Project Structure

```
ai_content_tool/
├── app.py               # Main entry point + routing
├── requirements.txt
├── core/
│   ├── llm.py           # Multi-provider LLM engine
│   └── prompts.py       # All prompt templates
└── pages/
    ├── dashboard.py
    ├── script_gen.py
    ├── hook_builder.py
    ├── calendar_page.py
    ├── voice_clone.py
    ├── avatar_guide.py
    ├── analytics.py
    └── settings_page.py
```

## 🛠️ Extending

Add a new page in 3 steps:
1. Create `pages/my_page.py` with a `render()` function
2. Add it to the sidebar radio in `app.py`
3. Add the route at the bottom of `app.py`

Add a new LLM provider in `core/llm.py` — follow the `_groq_complete` pattern.
