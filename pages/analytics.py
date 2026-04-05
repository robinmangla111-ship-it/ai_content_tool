import streamlit as st
import json
from datetime import date, timedelta
import random

def render():
    st.markdown("# 📊 Analytics Tracker")
    st.markdown("Track your content performance and session stats.")
    st.markdown("---")

    tab1, tab2 = st.tabs(["📈 Session Stats", "📋 Video Tracker"])

    with tab1:
        st.markdown("### 🔢 This Session")
        c1,c2,c3,c4 = st.columns(4)
        stats = [
            ("📝", "Scripts Generated", st.session_state.get("scripts_made", 0)),
            ("🎣", "Hooks Generated",   st.session_state.get("hooks_generated", 0)),
            ("📅", "Calendars Made",    st.session_state.get("calendars_made", 0)),
            ("⚡", "AI Calls Made",     st.session_state.get("ai_calls", 0)),
        ]
        for col, (icon, label, val) in zip([c1,c2,c3,c4], stats):
            with col:
                st.markdown(f"""<div class="metric-card">
                <div style="font-size:24px">{icon}</div>
                <div style="font-size:28px;font-weight:700;color:#a78bfa;margin:4px 0">{val}</div>
                <div style="font-size:11px;color:#555">{label}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("### 📊 Simulated Channel Growth")
        st.info("Connect real YouTube/Instagram analytics via their APIs. Below is a sample projection.")

        # Simulated data
        days = [(date.today() - timedelta(days=i)).strftime("%b %d") for i in range(29,-1,-1)]
        base = 100
        views = []
        for i in range(30):
            base = int(base * random.uniform(1.01, 1.08))
            views.append(base)

        import sys, os
        try:
            import plotly.graph_objects as go
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=days, y=views,
                fill="tozeroy",
                line=dict(color="#5c5cff", width=2),
                fillcolor="rgba(92,92,255,0.1)",
                name="Views",
            ))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#888", family="Space Grotesk"),
                margin=dict(l=0, r=0, t=10, b=0),
                xaxis=dict(showgrid=False, color="#333"),
                yaxis=dict(showgrid=True, gridcolor="#1e1e2e", color="#333"),
                height=250,
            )
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            st.line_chart(dict(zip(days, views)))

    with tab2:
        st.markdown("### 📋 Video Performance Log")
        st.markdown("Manually track your published videos here.")

        with st.form("add_video"):
            c1,c2,c3 = st.columns(3)
            with c1: title  = st.text_input("Video Title")
            with c2: views  = st.number_input("Views", min_value=0, step=100)
            with c3: likes  = st.number_input("Likes", min_value=0, step=10)
            c4,c5 = st.columns(2)
            with c4: fmt   = st.selectbox("Format", ["Short", "Long", "Tutorial"])
            with c5: pub   = st.date_input("Published", value=date.today())
            submitted = st.form_submit_button("➕ Add Video", use_container_width=True)

            if submitted and title:
                videos = st.session_state.get("videos", [])
                videos.append({"title": title, "views": views, "likes": likes, "format": fmt, "date": str(pub)})
                st.session_state["videos"] = videos
                st.success("Video added!")

        videos = st.session_state.get("videos", [])
        if videos:
            st.markdown("---")
            total_views = sum(v["views"] for v in videos)
            total_likes = sum(v["likes"] for v in videos)
            avg_views   = total_views // len(videos)

            m1,m2,m3 = st.columns(3)
            m1.metric("Total Views", f"{total_views:,}")
            m2.metric("Total Likes", f"{total_likes:,}")
            m3.metric("Avg Views/Video", f"{avg_views:,}")

            for v in reversed(videos):
                er = f"{(v['likes']/v['views']*100):.1f}%" if v["views"] > 0 else "—"
                st.markdown(f"""
                <div class="content-card" style="display:flex;align-items:center;gap:16px;padding:12px 16px">
                    <div style="flex:1;font-size:13px;color:#e0e0f0">{v['title']}</div>
                    <span style="font-size:10px;color:#5c5cff;background:#1e1e3e;padding:2px 8px;border-radius:6px">{v['format']}</span>
                    <span style="font-size:12px;color:#888">{v['date']}</span>
                    <span style="font-size:12px;color:#a78bfa;min-width:60px;text-align:right">{v['views']:,} views</span>
                    <span style="font-size:12px;color:#10b981;min-width:40px;text-align:right">ER {er}</span>
                </div>""", unsafe_allow_html=True)

            col_exp = st.download_button(
                "📥 Export as JSON",
                data=json.dumps(videos, indent=2),
                file_name="video_analytics.json",
                use_container_width=True,
            )
        else:
            st.markdown("""
            <div class="content-card" style="text-align:center;padding:60px 20px">
                <div style="font-size:48px">📊</div>
                <div style="color:#555;margin-top:12px">Add your first video above to start tracking</div>
            </div>""", unsafe_allow_html=True)
