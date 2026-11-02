"""Privacy-conscious, non-evaluative participant session summaries.

Temporary tracker IDs are not real identities. This module reports observable
presence only; it deliberately does not assign individual engagement scores.
"""
import csv
import json
from pathlib import Path


def _read_csv(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _float(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def generate_student_analytics(
    attendance_file="participant_attendance.csv",
    insights_file="multimodal_insights.csv",
    session_summary_file="multimodal_session_summary.json",
    output_csv="student_analytics.csv",
    output_json="student_analytics.json",
):
    attendance = _read_csv(attendance_file)
    windows = _read_csv(insights_file)
    session_summary = {}
    summary_path = Path(session_summary_file)
    if summary_path.exists():
        try:
            session_summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            session_summary = {}

    total_windows = len(windows)
    peak = session_summary.get("peak_engagement_window")
    low_windows = session_summary.get("lowest_engagement_windows", [])
    participants = []
    for row in attendance:
        pid = str(row.get("participant_id", "")).strip()
        if not pid:
            continue
        visible_windows = [
            window for window in windows
            if pid in [part.strip() for part in str(window.get("participant_ids", "")).split(";") if part.strip()]
        ]
        visible_count = len(visible_windows)
        presence_seconds = round(_float(row.get("presence_duration_seconds")), 1)
        required_seconds = _float(row.get("minimum_required_seconds"))
        attendance_status = row.get("attendance_status", "Unknown")
        observed_share = round((visible_count / total_windows * 100), 1) if total_windows else 0.0
        participants.append({
            "participant_id": pid,
            "attendance_status": attendance_status,
            "presence_duration_seconds": presence_seconds,
            "minimum_required_seconds": required_seconds,
            "visible_time_windows": visible_count,
            "session_time_windows": total_windows,
            "observed_window_share_percent": observed_share,
            "reflection_prompt": "Think about which lesson segments felt clear, and note one topic or question you would like to revisit.",
            "interpretation_note": "This is a temporary tracker ID and an approximate camera-visibility summary, not a verified identity or measure of attention, participation quality, or learning."
        })

    fields = [
        "participant_id", "attendance_status", "presence_duration_seconds",
        "minimum_required_seconds", "visible_time_windows", "session_time_windows",
        "observed_window_share_percent", "reflection_prompt", "interpretation_note"
    ]
    with Path(output_csv).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(participants)

    result = {
        "schema_version": "1.0",
        "participants": participants,
        "session_reflection": {
            "average_room_activity_indicator": session_summary.get("average_engagement_indicator", 0),
            "peak_activity_period": peak,
            "number_of_low_activity_periods": len(low_windows),
            "reflection_prompt": "Review the session timeline and consider when the material felt easiest or hardest to follow. These room-level signals are prompts for reflection, not personal evaluations."
        },
        "privacy_and_ethics": {
            "identity": "Participant IDs are temporary tracker labels and are not linked to student names.",
            "individual_scoring": "No individual engagement score, grade, ranking, or peer comparison is generated.",
            "limitations": "Camera visibility is approximate. Room-level engagement indicators are shared session context and must not be attributed to an individual participant.",
            "recommended_use": "Private learner reflection and session review only; not grading, discipline, or high-stakes decisions."
        }
    }
    Path(output_json).write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
