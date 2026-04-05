import streamlit as st
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.llm import complete, get_provider_badge
from core.prompts import SCRIPT_SYSTEM, SCRIPT_USER, TITLE_SYSTEM, TITLE_USER, DESCRIPTION_SYSTEM, DESCRIPTION_USER

def render():
    st.markdown("# ✍️ Script Generator")
    st.markdown(f"*Powered by {get_provider_badge()}*")
    st.markdown("---")

    col_form, col_out = st.columns([1, 1], gap="large")

    with col_form:
        st.markdown("### ⚙️ Script Config")

        topic = st.text_area(
            "Topic / Idea",
            placeholder="e.g. How to build an AI clone of yourself using free tools in 2025",
            height=80,
        )

        c1, c2 = st.columns(2)
        with c1:
            niche = st.selectbox("Niche", [
                "AI & Technology", "Finance & Investing", "Health & Fitness",
                "Personal Development", "Marketing & Business", "Education",
                "Entertainment", "Travel", "Food", "Gaming", "Other",
            ])
        with c2:
            audience = st.text_input("Target Audience", placeholder="e.g. Aspiring creators aged 18-30")

        c3, c4 = st.columns(2)
        with c3:
            tone = st.selectbox("Tone", ["Energetic & Fast", "Educational", "Storytelling", "Motivational", "Conversational", "Bold & Direct"])
        with c4:
            length = st.selectbox("Length", ["60 seconds (Short)", "90 seconds (Short+)", "3-5 minutes (Mid)", "8-12 minutes (Long)"])

        keywords = st.text_input("SEO Keywords (comma separated)", placeholder="AI clone, free tools, content creator")

        include_titles = st.checkbox("Also generate 5 video titles", value=True)
        include_desc   = st.checkbox("Also generate YouTube description", value=False)

        generate = st.button("🚀 Generate Script", use_container_width=True, type="primary")

    with col_out:
        st.markdown("### 📄 Generated Script")

        if generate:
            if not topic.strip():
                st.error("Please enter a topic first.")
                return

            # ── Script ──
            prompt = SCRIPT_USER.format(
                topic=topic, niche=niche, audience=audience or "general audience",
                tone=tone, length=length, keywords=keywords or "none specified",
            )
            script_placeholder = st.empty()
            with st.spinner("Writing your script..."):
                result = complete(SCRIPT_SYSTEM, prompt, mode="script", stream=True)
                full_script = ""
                for chunk in result:
                    full_script += chunk
                    script_placeholder.markdown(f"""<div class="copy-box">{full_script}</div>""", unsafe_allow_html=True)

            st.session_state["last_script"] = full_script
            n = st.session_state.get("scripts_made", 0) + 1
            st.session_state["scripts_made"] = n

            st.download_button(
                "📥 Download Script (.txt)",
                data=full_script,
                file_name=f"script_{topic[:30].replace(' ','_')}.txt",
                mime="text/plain",
                use_container_width=True,
            )

            # ── Titles ──
            if include_titles:
                st.markdown("---")
                st.markdown("### 🏷️ Suggested Titles")
                with st.spinner("Generating titles..."):
                    titles = complete(
                        TITLE_SYSTEM,
                        TITLE_USER.format(topic=topic, keyword=keywords.split(",")[0] if keywords else topic),
                    )
                st.markdown(f"""<div class="copy-box">{titles}</div>""", unsafe_allow_html=True)

            # ── Description ──
            if include_desc:
                st.markdown("---")
                st.markdown("### 📝 YouTube Description")
                with st.spinner("Writing description..."):
                    desc = complete(
                        DESCRIPTION_SYSTEM,
                        DESCRIPTION_USER.format(summary=topic, niche=niche),
                    )
                st.markdown(f"""<div class="copy-box">{desc}</div>""", unsafe_allow_html=True)

        elif st.session_state.get("last_script"):
            st.markdown(f"""<div class="copy-box">{st.session_state['last_script']}</div>""", unsafe_allow_html=True)
            st.caption("⬆️ Last generated script")
        else:
            st.markdown("""
            <div class="content-card" style="text-align:center;padding:60px 20px;color:#333">
                <div style="font-size:48px">📝</div>
                <div style="color:#555;margin-top:12px">Fill in the config and hit Generate</div>
            </div>""", unsafe_allow_html=True)

    # ── Tips ──
    st.markdown("---")
    with st.expander("💡 Pro tips for better scripts"):
        st.markdown("""
**Hook formula:** [Shocking stat/question] + [Who it's for] + [Outcome]
> *"87% of YouTube Shorts fail in the first 3 seconds. If you're a creator, this will save your channel."*

**Tone guide:**
- **Energetic:** Use "you", "right now", "stop", contractions
- **Educational:** Use "here's why", "the reason is", "what most people miss"
- **Storytelling:** Start with "Last week I...", build tension, resolve

**Length sweet spots:**
- Shorts: 45-58 seconds spoken (algorithm favors 100% watch time)
- Long form: 8-12 min (enough for mid-rolls)
        """)
