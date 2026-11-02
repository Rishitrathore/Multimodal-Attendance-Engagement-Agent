"""Explainable analytics and recommendation layer for classroom sessions.

Recommendations describe observable session-level activity patterns. They are
not judgments about an individual learner's attention, ability, or performance.
"""
import csv
import json
from collections import Counter
from pathlib import Path


def _read_rows(path):
    path = Path(path)
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _num(row, key, default=0.0):
    try:
        return float(row.get(key, default) or default)
    except (TypeError, ValueError):
        return default


def generate_analytics_and_recommendations(
    insights_file="multimodal_insights.csv",
    session_file="attendance.csv",
    output_file="recommendations.csv",
    summary_file="analytics_recommendations.json",
):
    """Create explainable instructor/student insights from fused time windows."""
    windows = _read_rows(insights_file)
    sessions = _read_rows(session_file)
    recommendations = []
    scores = [_num(row, "engagement_score") for row in windows]
    average = round(sum(scores) / len(scores), 1) if scores else 0.0
    low_windows = [r for r in windows if _num(r, "engagement_score") < 35]
    high_windows = [r for r in windows if _num(r, "engagement_score") >= 70]
    speech_windows = [r for r in windows if r.get("audio_class") == "Probable speech"]
    noise_windows = [r for r in windows if r.get("audio_class") == "Background noise"]
    missing_visual = [r for r in windows if _num(r, "visible_face_count") == 0]

    def add(priority, audience, category, evidence, suggestion, reason):
        recommendations.append({
            "priority": priority,
            "audience": audience,
            "category": category,
            "evidence": evidence,
            "recommendation": suggestion,
            "why_it_may_help": reason,
        })

    if not windows:
        add("Info", "Instructor", "No session data", "No fused time windows were found.",
            "Run a classroom session first, then reopen the dashboard.",
            "The analytics engine needs timestamped visual and audio observations.")
    else:
        if len(low_windows) / len(windows) >= 0.30:
            add("High", "Instructor", "Repeated low activity",
                f"{len(low_windows)} of {len(windows)} windows had an activity indicator below 35.",
                "Try a short recap, interactive question, poll, or pair discussion, then review the next session.",
                "A change in teaching format can help vary the pace; the score alone cannot explain why activity was low.")
        if len(high_windows) / len(windows) >= 0.25:
            add("Positive", "Instructor", "Active session periods",
                f"{len(high_windows)} of {len(windows)} windows had an activity indicator of 70 or higher.",
                "Note the activity used during these periods and consider reusing it where appropriate.",
                "Comparing session segments can help identify formats associated with more observable activity.")
        if len(noise_windows) / len(windows) >= 0.20:
            add("Medium", "Instructor", "Background noise",
                f"Background noise was the dominant audio class in {len(noise_windows)} windows.",
                "Check microphone placement and room noise; repeat key instructions if needed.",
                "Clearer audio can improve recording quality and make session-level audio patterns more useful.")
        if len(missing_visual) / len(windows) >= 0.20:
            add("Medium", "Instructor", "Limited visual observations",
                f"No face was detected in {len(missing_visual)} windows.",
                "Check camera framing, lighting, and whether the camera view is appropriate for the room.",
                "Missing detections can result from camera conditions and should not be treated as absence.")
        if len(speech_windows) / len(windows) < 0.10:
            add("Low", "Instructor", "Low detected speech activity",
                f"Probable speech was detected in {len(speech_windows)} of {len(windows)} windows.",
                "If discussion is part of the lesson, consider inviting questions or adding a brief discussion.",
                "The audio classifier is heuristic; quiet speech may not be detected and silence does not mean disengagement.")
        add("Info", "Student", "Session reflection",
            f"The session activity indicator averaged {average}/100 across {len(windows)} time windows.",
            "Reflect on which parts of the lesson felt clear or difficult, and note one question to revisit.",
            "The indicator summarizes room-level signals and is not an individual student score.")
        add("Info", "Instructor", "Review before acting",
            "Visual and audio signals are approximate and may be affected by camera, microphone, room, and accessibility conditions.",
            "Use these insights as prompts for human review; do not use them for grading, discipline, or individual ranking.",
            "Observable presence, movement, and sound cannot establish attention, understanding, or learning.")

    # Instructor-facing teaching prompts based on temporal patterns. These are
    # deliberately session-level and never label an individual learner.
    teaching_suggestions = []

    def add_teaching(pattern, evidence, suggestion, rationale, priority="Medium"):
        teaching_suggestions.append({
            "priority": priority, "pattern": pattern, "evidence": evidence,
            "suggestion": suggestion, "rationale": rationale,
        })

    if windows:
        # Find consecutive low-score windows rather than treating isolated dips
        # as sustained patterns. A run of 3 windows is the default trigger.
        low_runs = []
        run = []
        for row in windows:
            if _num(row, "engagement_score") < 35:
                run.append(row)
            else:
                if len(run) >= 3:
                    low_runs.append(run)
                run = []
        if len(run) >= 3:
            low_runs.append(run)

        for low_run in low_runs:
            start = low_run[0].get("window_start_seconds", "?")
            end = low_run[-1].get("window_end_seconds", "?")
            add_teaching(
                "Sustained low activity",
                f"Activity indicator stayed below 35 for {len(low_run)} consecutive windows ({start}s–{end}s).",
                "Consider pausing for a short recap, asking a low-pressure question, or using a brief pair/poll activity; then compare the next few windows.",
                "A change of pace may help re-engage the room. The signal cannot explain the cause of the low score.",
                "High",
            )

        # Detect meaningful falls between adjacent windows (20+ points).
        drops = []
        for previous, current in zip(windows, windows[1:]):
            before = _num(previous, "engagement_score")
            after = _num(current, "engagement_score")
            if before - after >= 20:
                drops.append((previous, current, before, after))
        if drops:
            prev, cur, before, after = max(drops, key=lambda item: item[2] - item[3])
            add_teaching(
                "Sudden activity drop",
                f"Indicator decreased from {before:.0f} to {after:.0f} between {prev.get('window_end_seconds', '?')}s and {cur.get('window_start_seconds', '?')}s.",
                "Review what changed around this point (topic transition, explanation length, or activity format); consider a quick comprehension check before continuing.",
                "A sharp change can identify a useful segment to review, but does not prove that learners lost attention.",
                "Medium",
            )

        # Highlight peak windows as examples to review, not proof of success.
        peak = max(windows, key=lambda row: _num(row, "engagement_score"))
        if _num(peak, "engagement_score") >= 70:
            add_teaching(
                "Peak activity period",
                f"Highest indicator was {_num(peak, 'engagement_score'):.0f}/100 during {peak.get('window_start_seconds', '?')}s–{peak.get('window_end_seconds', '?')}s.",
                "Review the teaching format or activity used during this segment and consider reusing it where it fits the lesson.",
                "Identifying active segments can help instructors reflect on approaches associated with stronger observable room activity.",
                "Positive",
            )

        noisy = [row for row in windows if row.get("audio_class") == "Background noise" or _num(row, "background_noise_fraction") >= 0.5]
        if len(noisy) / len(windows) >= 0.2:
            add_teaching(
                "Noisy classroom conditions",
                f"Background noise was dominant or at least half of the audio activity in {len(noisy)} of {len(windows)} windows.",
                "Check room noise and microphone placement; pause briefly or repeat key instructions if they may have been difficult to hear.",
                "Reducing recording or room noise can improve communication and the reliability of audio-based session summaries.",
                "Medium",
            )

        if not teaching_suggestions:
            add_teaching(
                "No strong pattern detected",
                "The configured thresholds for sustained low activity, sharp drops, peak activity, and noisy conditions were not met.",
                "Continue with the planned lesson and use instructor observation and learner feedback to guide any changes.",
                "Not every session requires an automated teaching prompt; the indicators are approximate.",
                "Info",
            )

    teaching_fields = ["priority", "pattern", "evidence", "suggestion", "rationale"]
    with Path("teaching_suggestions.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=teaching_fields)
        writer.writeheader()
        writer.writerows(teaching_suggestions)

    fields = ["priority", "audience", "category", "evidence", "recommendation", "why_it_may_help"]
    with Path(output_file).open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(recommendations)

    latest_session = sessions[-1] if sessions else {}
    summary = {
        "schema_version": "1.0",
        "windows_analyzed": len(windows),
        "average_activity_indicator": average,
        "low_activity_window_count": len(low_windows),
        "high_activity_window_count": len(high_windows),
        "probable_speech_window_count": len(speech_windows),
        "background_noise_window_count": len(noise_windows),
        "windows_without_face_detection": len(missing_visual),
        "most_common_audio_class": Counter(r.get("audio_class", "Unknown") for r in windows).most_common(1)[0][0] if windows else "Unknown",
        "session_record": latest_session,
        "recommendations": recommendations,
        "instructor_teaching_suggestions": teaching_suggestions,
        "ethical_note": "These are room/session-level activity insights, not individual attention, identity, ability, or learning assessments. Do not use them for grading or disciplinary decisions. Human review and appropriate consent are required.",
    }
    Path(summary_file).write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
