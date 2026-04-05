import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.llm import complete, get_provider_badge
from core.prompts import HOOK_SYSTEM, HOOK_USER

HOOK_FORMULAS = {
    "Curiosity Gap":    "Nobody talks about [X], but it's the #1 reason [Y]",
    "Shocking Stat":    "[Surprising number]% of [audience] don't know [fact]",
    "Myth Bust":        "You've been lied to about [common belief]",
    "Threat + Promise": "Stop [doing X] before it's too late — here's what to do instead",
    "Social Proof":     "I tried [X] for [time] — here's what actually happened",
    "Curiosity Number": "[N] [things] that will [outcome] (most people miss #[N])",
}

def score_hook(hook: str) -> int:
    """Heuristic hook scorer."""
    score = 40
    if any(c.isdigit() for c in hook): score += 15
    words = hook.lower().split()
    power_words = {"secret","free","fast","easy","proven","shocking","finally","never","always","stop","warning","biggest","only","exact","real"}
    score += min(20, sum(5 for w in words if w in power_words))
    if "?" in hook: score += 10
    if len(hook) < 70: score += 10
    if "you" in words: score += 5
    return min(score, 99)

def render():
    st.markdown("# 🎣 Hook Builder")
    st.markdown(f"*Powered by {get_provider_badge()}*")
    st.markdown("---")

    col_l, col_r = st.columns([1,1], gap="large")

    with col_l:
        st.markdown("### Generate Hooks with AI")
        topic    = st.text_input("Topic", placeholder="How to build an AI avatar for free")
        niche    = st.text_input("Niche", placeholder="AI & Content Creation", value=st.session_state.get("niche",""))
        audience = st.text_input("Audience", placeholder="Aspiring YouTubers & creators")

        gen_btn = st.button("⚡ Generate 5 Viral Hooks", use_container_width=True, type="primary")

        st.markdown("---")
        st.markdown("### 🧪 Hook Formula Builder")
        formula_name = st.selectbox("Pick a formula", list(HOOK_FORMULAS.keys()))
        st.info(f"**Template:** {HOOK_FORMULAS[formula_name]}")
        custom_hook = st.text_area("Write your hook using this template", height=80, placeholder="Fill in the blanks above...")
        if custom_hook:
            score = score_hook(custom_hook)
            bar_color = "#10b981" if score >= 80 else "#f59e0b" if score >= 60 else "#ef4444"
            st.markdown(f"""
            <div style="margin-top:8px">
                <div style="display:flex;justify-content:space-between;margin-bottom:4px">
                    <span style="font-size:12px;color:#888">Hook Score</span>
                    <span style="font-size:14px;font-weight:700;color:{bar_color}">{score}/99</span>
                </div>
                <div style="background:#1a1a2e;border-radius:4px;height:6px">
                    <div style="background:{bar_color};width:{score}%;height:6px;border-radius:4px;transition:width 0.3s"></div>
                </div>
            </div>""", unsafe_allow_html=True)

    with col_r:
        st.markdown("### 📊 Generated Hooks")

        if gen_btn:
            if not topic.strip():
                st.error("Enter a topic first.")
                return
            with st.spinner("Generating viral hooks..."):
                hooks_raw = complete(
                    HOOK_SYSTEM,
                    HOOK_USER.format(topic=topic, niche=niche or "general", audience=audience or "general audience"),
                    mode="hooks",
                )
            hooks = [h.strip() for h in hooks_raw.strip().split("\n") if h.strip()]
            st.session_state["last_hooks"] = hooks
            n = st.session_state.get("hooks_generated", 0) + len(hooks)
            st.session_state["hooks_generated"] = n

        hooks = st.session_state.get("last_hooks", [])

        if hooks:
            for hook in hooks:
                # clean numbering
                clean = hook.lstrip("0123456789.-) ").strip()
                score = score_hook(clean)
                bar_color = "#10b981" if score >= 80 else "#f59e0b" if score >= 60 else "#ef4444"
                label = "🔥 Hot" if score >= 80 else "⚡ Good" if score >= 60 else "🔧 Needs work"
                st.markdown(f"""
                <div class="content-card" style="margin-bottom:12px">
                    <div style="font-size:14px;color:#e0e0f0;font-weight:500;margin-bottom:10px">"{clean}"</div>
                    <div style="display:flex;align-items:center;gap:12px">
                        <div style="flex:1;background:#1a1a2e;border-radius:3px;height:4px">
                            <div style="background:{bar_color};width:{score}%;height:4px;border-radius:3px"></div>
                        </div>
                        <span style="font-size:11px;color:{bar_color};white-space:nowrap">{score}/99 · {label}</span>
                    </div>
                </div>""", unsafe_allow_html=True)

            all_text = "\n".join(hooks)
            st.download_button("📥 Download All Hooks", data=all_text, file_name="hooks.txt", use_container_width=True)
        else:
            st.markdown("""
            <div class="content-card" style="text-align:center;padding:60px 20px">
                <div style="font-size:48px">🎣</div>
                <div style="color:#555;margin-top:12px">Enter a topic and generate hooks</div>
            </div>""", unsafe_allow_html=True)

    # ── Hook scoring guide ──
    st.markdown("---")
    st.markdown("### 📖 Hook Scoring Breakdown")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("""<div class="content-card" style="border-color:#10b98140">
        <div style="color:#10b981;font-weight:700;font-size:16px">🔥 80-99 — Hot</div>
        <div style="color:#666;font-size:12px;margin-top:6px">Numbers ✓ Power words ✓ Short ✓ "You" ✓</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown("""<div class="content-card" style="border-color:#f59e0b40">
        <div style="color:#f59e0b;font-weight:700;font-size:16px">⚡ 60-79 — Good</div>
        <div style="color:#666;font-size:12px;margin-top:6px">Missing 1-2 elements. Refine the phrasing.</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown("""<div class="content-card" style="border-color:#ef444440">
        <div style="color:#ef4444;font-weight:700;font-size:16px">🔧 &lt;60 — Needs work</div>
        <div style="color:#666;font-size:12px;margin-top:6px">Too generic. Add specificity and power words.</div>
        </div>""", unsafe_allow_html=True)
