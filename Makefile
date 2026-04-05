# ContentAI Studio — Makefile
# Usage: make <target>

.PHONY: install run cli-script cli-hooks cli-calendar lint clean deploy-check

# ── Setup ─────────────────────────────────────────────────────────────────────

install:
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt
	@echo "✅ Done. Run 'make run' to start."

install-local:
	@echo "📦 Installing with local AI support (Coqui TTS)..."
	pip install -r requirements.txt
	pip install TTS
	@echo "🖥️  For local LLM: curl -fsSL https://ollama.ai/install.sh | sh && ollama pull llama3.3"

# ── Run ───────────────────────────────────────────────────────────────────────

run:
	@echo "🚀 Launching ContentAI Studio..."
	streamlit run app.py

run-port:
	streamlit run app.py --server.port 8502

# ── CLI shortcuts ─────────────────────────────────────────────────────────────

# Usage: make script TOPIC="How to build AI clone"
script:
	python cli.py script --topic "$(TOPIC)" --niche "$(or $(NICHE),AI & Technology)" --out script_output.txt

# Usage: make hooks TOPIC="AI content creation"
hooks:
	python cli.py hooks --topic "$(TOPIC)" --out hooks_output.txt

# Usage: make calendar NICHE="Finance"
calendar:
	python cli.py calendar --niche "$(or $(NICHE),AI & Technology)" --out calendar.json

# Usage: make tts FILE=script_output.txt
tts:
	python cli.py tts --file "$(or $(FILE),script_output.txt)" --out voice_output.mp3

# ── Dev ───────────────────────────────────────────────────────────────────────

lint:
	@echo "🔍 Linting..."
	python -m py_compile app.py core/llm.py core/prompts.py
	python -m py_compile pages/dashboard.py pages/script_gen.py pages/hook_builder.py
	python -m py_compile pages/calendar_page.py pages/voice_clone.py pages/avatar_guide.py
	python -m py_compile pages/analytics.py pages/settings_page.py cli.py
	@echo "✅ All files OK"

test-stub:
	@echo "🧪 Testing stub mode (no API key required)..."
	python cli.py script --topic "AI clones for content creators"
	@echo "✅ Stub mode works"

# ── Deploy checks ─────────────────────────────────────────────────────────────

deploy-check:
	@echo "🔍 Checking deploy readiness..."
	@python -c "import streamlit; print(f'  Streamlit: {streamlit.__version__}')"
	@python -c "import requests; print(f'  Requests: {requests.__version__}')"
	@python -c "import plotly; print(f'  Plotly: {plotly.__version__}')" 2>/dev/null || echo "  Plotly: not installed (optional)"
	@echo "✅ Ready to deploy"

# ── Clean ─────────────────────────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -f script_output.txt hooks_output.txt calendar.json voice_output.mp3
	@echo "🧹 Cleaned"

# ── Help ──────────────────────────────────────────────────────────────────────

help:
	@echo ""
	@echo "ContentAI Studio — Available commands:"
	@echo ""
	@echo "  make install          Install all dependencies"
	@echo "  make install-local    Install + local TTS/LLM support"
	@echo "  make run              Launch Streamlit web UI"
	@echo "  make lint             Syntax check all Python files"
	@echo "  make test-stub        Test without any API key"
	@echo ""
	@echo "  make script TOPIC='your topic'     Generate script"
	@echo "  make hooks  TOPIC='your topic'     Generate 5 hooks"
	@echo "  make calendar NICHE='Finance'      7-day content plan"
	@echo "  make tts FILE=script_output.txt    Convert to audio"
	@echo ""
	@echo "  make deploy-check     Verify ready to deploy"
	@echo "  make clean            Remove cache and temp files"
	@echo ""
