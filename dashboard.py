"""Optional Streamlit dashboard for exploring session-level analytics.

Run from this folder with: streamlit run dashboard.py
The dashboard is a visualization layer; it does not run camera or microphone capture.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent


def read_csv(name: str) -> pd.DataFrame:
    path = BASE_DIR / name
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    try:
        return pd.read_csv(path)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, UnicodeDecodeError) as exc:
        st.warning(f"Could not read {name}: {exc}")
        return pd.DataFrame()


def read_json(name: str) -> dict:
    path = BASE_DIR / name
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError) as exc:
        st.warning(f"Could not read {name}: {exc}")
        return {}


def show_table(frame: pd.DataFrame, *, height: int = 320) -> None:
    if frame.empty:
        st.info("No records are available yet. Run a session first.")
    else:
        st.dataframe(frame, use_container_width=True, hide_index=True, height=height)


st.set_page_config(page_title="Multimodal Attendance Agent", page_icon="📊", layout="wide")
st.title("📊 Multimodal Attendance & Engagement Agent")
st.caption("Optional session-visualization dashboard · Run a session with main.py before exploring results.")

with st.sidebar:
    st.header("Dashboard controls")
    st.write("Data folder:")
    st.code(str(BASE_DIR), language=None)
    if st.button("↻ Refresh session data", use_container_width=True):
        st.rerun()
    st.divider()
    st.caption("Signals are approximate and intended for human review, not grading or disciplinary decisions.")

attendance = read_csv("attendance.csv")
fusion = read_csv("multimodal_insights.csv")
participant_attendance = read_csv("participant_attendance.csv")
recommendations = read_csv("recommendations.csv")
teaching = read_csv("teaching_suggestions.csv")
students = read_csv("student_analytics.csv")
multimodal_summary = read_json("multimodal_session_summary.json")
analytics = read_json("analytics_recommendations.json")
student_data = read_json("student_analytics.json")

# Session overview
st.subheader("Session overview")
if not attendance.empty:
    latest = attendance.iloc[-1]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Recorded sessions", len(attendance))
    c2.metric("Latest duration", f"{float(latest.get('duration_seconds', 0) or 0):.1f} sec")
    c3.metric("Face presence", f"{float(latest.get('face_presence_percent', 0) or 0):.1f}%")
    c4.metric("Audio activity", f"{float(latest.get('audio_activity_percent', 0) or 0):.1f}%")
    st.caption(f"Latest session: {latest.get('date', 'Unknown date')} · {latest.get('start_time', '')}–{latest.get('end_time', '')}")
else:
    st.info("No attendance session has been recorded yet. Start the application with `python main.py`.")

if not fusion.empty and "engagement_score" in fusion.columns:
    avg_score = pd.to_numeric(fusion["engagement_score"], errors="coerce").mean()
    low_count = int((pd.to_numeric(fusion["engagement_score"], errors="coerce") < 35).sum())
    a, b, c = st.columns(3)
    a.metric("Fusion windows", len(fusion))
    b.metric("Average room activity indicator", f"{avg_score:.1f}/100" if pd.notna(avg_score) else "N/A")
    c.metric("Low-activity windows", low_count)

# Explore the different outputs in separate tabs.
tab_attendance, tab_engagement, tab_instructor, tab_students = st.tabs([
    "Attendance", "Engagement timeline", "Instructor insights", "Student session analytics"
])

with tab_attendance:
    st.subheader("Attendance records")
    show_table(attendance)
    st.markdown("**Participant presence summary**")
    show_table(participant_attendance)
    if not attendance.empty:
        st.download_button(
            "Download attendance CSV", attendance.to_csv(index=False).encode("utf-8"),
            file_name="attendance_export.csv", mime="text/csv",
        )

with tab_engagement:
    st.subheader("Room activity over time")
    if fusion.empty:
        st.info("Multimodal timeline will appear after a completed session.")
    elif "engagement_score" not in fusion.columns:
        st.warning("The fusion file does not contain an engagement_score column.")
    else:
        plot = fusion.copy()
        plot["engagement_score"] = pd.to_numeric(plot["engagement_score"], errors="coerce")
        if "window_start_seconds" in plot.columns:
            plot["Time (seconds)"] = pd.to_numeric(plot["window_start_seconds"], errors="coerce")
            plot = plot.set_index("Time (seconds)")
        st.line_chart(plot[["engagement_score"]].dropna(), y="engagement_score")
        useful = [col for col in ["window_start_seconds", "window_end_seconds", "engagement_score",
                                  "engagement_level", "audio_class", "context_label", "score_explanation"]
                  if col in fusion.columns]
        st.markdown("**Timeline details**")
        show_table(fusion[useful])
    if multimodal_summary:
        with st.expander("Session interpretation and summary"):
            st.write("Most common context:", multimodal_summary.get("most_common_context", "Not available"))
            st.write("Average engagement indicator:", multimodal_summary.get("average_engagement_indicator", "Not available"))
            st.write("Engagement level counts:", multimodal_summary.get("engagement_level_counts", {}))
            st.write("Teaching suggestions:", multimodal_summary.get("teaching_suggestions", []))
            st.caption(multimodal_summary.get("interpretation_limit", ""))

with tab_instructor:
    st.subheader("Instructor recommendations")
    if not recommendations.empty:
        if "priority" in recommendations.columns:
            priorities = ["All"] + sorted(recommendations["priority"].dropna().astype(str).unique().tolist())
            selected_priority = st.selectbox("Filter by priority", priorities)
            filtered = recommendations if selected_priority == "All" else recommendations[recommendations["priority"].astype(str) == selected_priority]
        else:
            filtered = recommendations
        show_table(filtered)
    else:
        st.info("Recommendations will appear after analytics are generated.")

    st.subheader("Teaching suggestions")
    if teaching.empty:
        st.info("No teaching suggestions are available yet.")
    else:
        for _, item in teaching.iterrows():
            title = f"{item.get('priority', 'Info')} · {item.get('pattern', 'Session pattern')}"
            with st.expander(title):
                st.write("**Observed evidence**")
                st.write(item.get("evidence", ""))
                st.write("**Possible teaching response**")
                st.write(item.get("suggestion", ""))
                st.caption(item.get("rationale", ""))
    if analytics:
        with st.expander("Analytics summary and limitations"):
            st.json({key: analytics.get(key) for key in ["windows_analyzed", "average_activity_indicator",
                    "low_activity_window_count", "high_activity_window_count", "most_common_audio_class"]})
            st.caption(analytics.get("ethical_note", ""))

with tab_students:
    st.subheader("Student session reflection")
    st.caption("Temporary tracker IDs are not verified identities. No individual engagement score, grade, or peer ranking is produced.")
    participant_rows = student_data.get("participants", []) if student_data else []
    if participant_rows:
        ids = [str(row.get("participant_id", "Unknown")) for row in participant_rows]
        selected_id = st.selectbox("Select temporary participant ID", ids)
        selected = next((row for row in participant_rows if str(row.get("participant_id")) == selected_id), {})
        p1, p2, p3 = st.columns(3)
        p1.metric("Attendance status", selected.get("attendance_status", "Unknown"))
        p2.metric("Visible duration", f"{selected.get('presence_duration_seconds', 0)} sec")
        p3.metric("Observed windows", f"{selected.get('visible_time_windows', 0)} / {selected.get('session_time_windows', 0)}")
        st.write("**Reflection prompt**")
        st.write(selected.get("reflection_prompt", ""))
        st.caption(selected.get("interpretation_note", ""))
        with st.expander("All participant summaries"):
            show_table(students if not students.empty else pd.DataFrame(participant_rows))
    elif not students.empty:
        show_table(students)
    else:
        st.info("Student session summaries will appear after a completed session.")

    reflection = student_data.get("session_reflection", {}) if student_data else {}
    if reflection:
        st.markdown("**Shared room-level reflection**")
        st.metric("Average room activity indicator", f"{reflection.get('average_room_activity_indicator', 0)}/100")
        st.write("Peak activity period:", reflection.get("peak_activity_period") or "Not available")
        st.write(reflection.get("reflection_prompt", ""))
    privacy = student_data.get("privacy_and_ethics", {}) if student_data else {}
    if privacy:
        with st.expander("Privacy and interpretation notes"):
            for label, value in privacy.items():
                st.write(f"**{label.replace('_', ' ').title()}:** {value}")

st.divider()
st.caption("Interpretation note: face visibility, movement, and audio activity are approximate room/session signals. They cannot establish identity, attention, understanding, participation quality, or learning. Use appropriate consent and human review.")
