import streamlit as st

def render():
    st.markdown("# ⚙️ Settings")
    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(["🔑 API Keys", "👤 Profile", "🚀 Deployment"])

    with tab1:
        st.markdown("### API Key Configuration")
        st.info("Keys are stored in session state only — never sent anywhere except the API you configure.")

        with st.expander("⚡ Groq (Recommended — Free)", expanded=True):
            st.markdown("Get your free key at [console.groq.com](https://console.groq.com)")
            groq_key = st.text_input("Groq API Key", type="password",
                value=st.session_state.get("api_key","") if st.session_state.get("api_key","").startswith("gsk_") else "",
                placeholder="gsk_...")
            if groq_key:
                st.session_state["api_key"] = groq_key

        with st.expander("🟢 OpenAI (Paid)"):
            oai_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
            if oai_key:
                st.session_state["api_key"] = oai_key

        with st.expander("🖥️ Ollama (Local — Zero Cost)"):
            st.markdown("Install: `curl -fsSL https://ollama.ai/install.sh | sh`")
            st.code("ollama pull llama3.3", language="bash")
            st.markdown("Then just run this app — it auto-detects Ollama if no API key is set.")
            model = st.selectbox("Local model", ["llama3.3", "llama3.1", "mistral", "phi4", "gemma3"])
            st.session_state["ollama_model"] = model

        with st.expander("🗣️ ElevenLabs (Voice Clone)"):
            el_key  = st.text_input("ElevenLabs Key", type="password", placeholder="sk_...")
            el_vid  = st.text_input("Voice ID (from your clone)", placeholder="21m00Tcm4TlvDq8ikWAM")
            if el_key:  st.session_state["eleven_key"] = el_key
            if el_vid:  st.session_state["eleven_voice_id"] = el_vid

        if st.button("💾 Save All Keys", use_container_width=True, type="primary"):
            st.success("All keys saved for this session!")

    with tab2:
        st.markdown("### Your Creator Profile")
        st.markdown("These defaults pre-fill every generator.")

        niche    = st.text_input("Your Niche", value=st.session_state.get("niche","AI & Content Creation"))
        audience = st.text_input("Target Audience", value=st.session_state.get("audience","Aspiring creators"))
        style    = st.selectbox("Content Style", ["Educational", "Entertaining", "Motivational", "News", "Tutorial"],
                    index=["Educational","Entertaining","Motivational","News","Tutorial"].index(
                        st.session_state.get("content_style","Educational")))
        freq     = st.slider("Videos/week", 1, 7, st.session_state.get("freq", 5))

        if st.button("💾 Save Profile", use_container_width=True):
            st.session_state["niche"] = niche
            st.session_state["audience"] = audience
            st.session_state["content_style"] = style
            st.session_state["freq"] = freq
            st.success("Profile saved!")

    with tab3:
        st.markdown("### 🚀 Deploy for Free")

        with st.expander("☁️ Streamlit Cloud (Recommended)", expanded=True):
            st.markdown("""
1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your repo → set `app.py` as entry point
4. Add your API keys in **Secrets** (Settings → Secrets):
```toml
GROQ_API_KEY = "gsk_your_key_here"
ELEVEN_API_KEY = "sk_your_key"
```
5. Click Deploy — live in ~2 minutes. **Completely free.**
""")

        with st.expander("🤗 Hugging Face Spaces"):
            st.markdown("""
1. Create account at [huggingface.co](https://huggingface.co)
2. New Space → SDK: Streamlit → Upload your files
3. Add secrets in Space settings
4. **Free tier** includes persistent storage + GPU access
""")

        with st.expander("🖥️ Run Locally"):
            st.code("""
git clone https://github.com/yourname/ai-content-tool
cd ai-content-tool
pip install -r requirements.txt
streamlit run app.py
# Opens at http://localhost:8501
""", language="bash")

        st.markdown("---")
        st.markdown("### 📦 requirements.txt")
        reqs = """streamlit>=1.35.0
groq>=0.9.0
openai>=1.30.0
requests>=2.31.0
plotly>=5.18.0"""
        st.code(reqs, language="text")
        st.download_button("📥 Download requirements.txt", data=reqs, file_name="requirements.txt")
