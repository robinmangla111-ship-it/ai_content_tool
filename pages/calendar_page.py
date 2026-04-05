import streamlit as st
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from core.llm import complete, get_provider_badge
from core.prompts import CALENDAR_SYSTEM, CALENDAR_USER

FORMAT_COLORS = {
    "Short":    ("#5c5cff", "#1e1e3e"),
    "Long":     ("#8b5cf6", "#2a1e3e"),
    "Tutorial": ("#06b6d4", "#0e2a30"),
    "Collab":   ("#10b981", "#0e2a1e"),
    "Trending": ("#f59e0b", "#2a200e"),
}

def render():
    st.markdown("# 📅 Content Calendar")
    st.markdown(f"*Powered by {get_provider_badge()}*")
    st.markdown("---")

    with st.expander("⚙️ Calendar Settings", expanded=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            niche = st.text_input("Your Niche", value=st.session_state.get("niche", "AI & Content Creation"))
            st.session_state["niche"] = niche
        with c2:
            style = st.selectbox("Creator Style", ["Educational", "Entertaining", "Motivational", "News & Updates", "Tutorial-heavy", "Storytelling"])
        with c3:
            freq  = st.slider("Videos/week", 1, 7, 5)

        trends = st.text_input("Trending topics to include (optional)", placeholder="e.g. AI agents, Sora, GPT-5")
        gen_btn = st.button("🗓️ Generate 7-Day Calendar", use_container_width=True, type="primary")

    # ── Generate ──
    if gen_btn:
        with st.spinner("Planning your content week..."):
            raw = complete(
                CALENDAR_SYSTEM,
                CALENDAR_USER.format(niche=niche, style=style, frequency=freq, trends=trends or "none specified"),
                mode="calendar",
            )
        # parse JSON
        try:
            # strip possible markdown fences
            clean = raw.strip().lstrip("```json").rstrip("```").strip()
            calendar = json.loads(clean)
        except Exception:
            # fallback: try to extract JSON array
            import re
            match = re.search(r"\[.*\]", raw, re.DOTALL)
            if match:
                try:
                    calendar = json.loads(match.group())
                except Exception:
                    calendar = []
            else:
                calendar = []
        st.session_state["calendar"] = calendar

    calendar = st.session_state.get("calendar", [])

    if calendar:
        st.markdown("---")
        st.markdown("### 📆 Your Week")

        # Summary bar
        formats = [d.get("format","Short") for d in calendar]
        scores  = [d.get("hook_score", 75) for d in calendar]
        avg_score = sum(scores) // len(scores) if scores else 0

        mc1, mc2, mc3, mc4 = st.columns(4)
        mc1.metric("Total Videos", len(calendar))
        mc2.metric("Avg Hook Score", f"{avg_score}/100")
        mc3.metric("Shorts", formats.count("Short"))
        mc4.metric("Long Form", formats.count("Long") + formats.count("Tutorial"))

        st.markdown("---")

        # Calendar grid
        cols = st.columns(len(calendar))
        for col, day_data in zip(cols, calendar):
            day     = day_data.get("day", "?")
            idea    = day_data.get("idea", "")
            fmt     = day_data.get("format", "Short")
            score   = day_data.get("hook_score", 75)
            notes   = day_data.get("notes", "")
            fc, bc  = FORMAT_COLORS.get(fmt, ("#888", "#1a1a1a"))
            bar_col = "#10b981" if score >= 80 else "#f59e0b" if score >= 60 else "#ef4444"

            with col:
                st.markdown(f"""
                <div class="content-card" style="min-height:200px;border-color:{fc}30">
                    <div style="font-weight:700;color:{fc};font-size:13px;margin-bottom:8px">{day}</div>
                    <div style="font-size:12px;color:#e0e0f0;margin-bottom:10px;line-height:1.5">{idea}</div>
                    <div style="display:inline-block;background:{bc};color:{fc};border:1px solid {fc}50;border-radius:5px;padding:2px 8px;font-size:10px;margin-bottom:8px">{fmt}</div>
                    <div style="margin-top:auto">
                        <div style="display:flex;justify-content:space-between;margin-bottom:3px">
                            <span style="font-size:10px;color:#555">Hook Score</span>
                            <span style="font-size:10px;color:{bar_col};font-weight:600">{score}</span>
                        </div>
                        <div style="background:#1a1a2e;border-radius:3px;height:3px">
                            <div style="background:{bar_col};width:{score}%;height:3px;border-radius:3px"></div>
                        </div>
                    </div>
                    {f'<div style="font-size:10px;color:#444;margin-top:8px">{notes}</div>' if notes else ''}
                </div>""", unsafe_allow_html=True)

        st.markdown("---")

        # Export
        csv_lines = ["Day,Idea,Format,Hook Score,Notes"]
        for d in calendar:
            csv_lines.append(f"{d.get('day','')},{d.get('idea','')},{d.get('format','')},{d.get('hook_score','')},{d.get('notes','')}")
        csv = "\n".join(csv_lines)

        cc1, cc2 = st.columns(2)
        with cc1:
            st.download_button("📥 Download Calendar (CSV)", data=csv, file_name="content_calendar.csv", use_container_width=True)
        with cc2:
            st.download_button("📋 Download as JSON", data=json.dumps(calendar, indent=2), file_name="content_calendar.json", use_container_width=True)
    else:
        st.markdown("""
        <div class="content-card" style="text-align:center;padding:80px 20px">
            <div style="font-size:48px">📅</div>
            <div style="color:#555;margin-top:16px;font-size:16px">Configure your settings above and generate your week</div>
        </div>""", unsafe_allow_html=True)
